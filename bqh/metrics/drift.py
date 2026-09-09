"""Metropolitan Drift Rate (MDR) and Quebec False Correction Rate (QFCR).

Two metrics a Canadian bilingual pipeline needs that generic French evaluation
does not provide.

--------------------------------------------------------------------------
Metropolitan Drift Rate (MDR)
--------------------------------------------------------------------------
The rate at which a Quebec form is replaced by its France counterpart.

The critical constraint: **MDR counts substitutions only.** If a model rephrases
around a term rather than substituting the metropolitan form, that is verbosity,
not drift. This distinction is what makes MDR actionable — conflating the two
inflates the number with cases where nothing was actually wrong, and a metric
that cries wolf gets ignored.

Three outcomes per opportunity (an opportunity exists when the source text uses
a Quebec form that has a distinct France counterpart):

  substituted — output uses the France form              → counts toward MDR
  preserved   — output keeps the Quebec form             → clean
  rephrased   — output uses neither; the concept is
                expressed some other way, or dropped     → NOT drift

    MDR = substituted / (substituted + preserved)

Rephrased cases are excluded from the denominator entirely: they are not
evidence for or against drift, so scoring them either way would bias the rate.

--------------------------------------------------------------------------
Quebec False Correction Rate (QFCR)
--------------------------------------------------------------------------
The rate at which a "proofread" or "correct this French" prompt incorrectly
"fixes" valid Canadian regional usage.

This is the failure mode that a naive quality-improvement step introduces: a
proofreading pass, applied to correct Canadian French, "corrects" `fin de
semaine` to `week-end` or `courriel` to `email`. The output scores better on
generic French fluency and is *worse* for a Canadian audience.

    QFCR = valid Quebec forms altered / valid Quebec forms present in input

QFCR is measured on text that was already correct, so any change is a false
correction by construction. A pipeline can have excellent MDR and terrible
QFCR — that combination means generation is fine and the proofreading step is
the thing damaging the copy.
"""
import re
import unicodedata

# Quebec form ↔ France counterpart. Each entry is a genuine substitution pair:
# both forms are valid French, and the choice between them is regional, not a
# matter of correctness. This is what makes substitution detectable — an
# occurrence of the France form where the Quebec form stood is unambiguous.
FORM_PAIRS = [
    # (quebec_pattern, france_pattern, quebec_label, france_label)
    (r"\bfins?\s+de\s+semaine\b", r"\bweek-?ends?\b", "fin de semaine", "week-end"),
    (r"\bcourriels?\b", r"\be-?mails?\b", "courriel", "email"),
    (r"\bmagasinage\b", r"\bshopping\b", "magasinage", "shopping"),
    (r"\bstationnements?\b", r"\bparkings?\b", "stationnement", "parking"),
    (r"\bbanlieusards?\b", r"\bnavetteurs?\b", "banlieusard", "navetteur"),
    (r"\bhaltes?-chaleur\b", r"\bcentres?\s+d['’]hébergement\s+chauff\w*",
     "halte-chaleur", "centre d'hébergement chauffé"),
    (r"\bassurance-emploi\b", r"\bassurance\s+chômage\b",
     "assurance-emploi", "assurance chômage"),
    (r"\bconseillers?\s+scolaires?\b", r"\badministrateurs?\s+scolaires?\b",
     "conseiller scolaire", "administrateur scolaire"),
    (r"\btaxes?\s+foncières?\b", r"\bimpôts?\s+locaux?\b",
     "taxe foncière", "impôt local"),
    (r"\btravail\s+partagé\b", r"\bchômage\s+partiel\b",
     "travail partagé", "chômage partiel"),
    (r"\bargent\s+comptant\b", r"\bcash\b", "argent comptant", "cash"),
    (r"\bdéjeuner\b", r"\bpetit\s+déjeuner\b", "déjeuner", "petit déjeuner"),
    (r"\bdîners?\b", r"\bdéjeuners?\b", "dîner", "déjeuner (midi)"),
    (r"\bprésentement\b", r"\bactuellement\b", "présentement", "actuellement"),
    (r"\bcéduler\b", r"\bplanifier\b", "céduler", "planifier"),
    (r"\bdépanneurs?\b", r"\bépiceries?\s+de\s+nuit\b", "dépanneur", "épicerie de nuit"),
]


def _norm(t):
    return unicodedata.normalize("NFC", (t or "").lower())


def _count(pattern, text):
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def measure_drift(source, output):
    """Metropolitan Drift Rate for one source→output pair.

    `source` is the reference Canadian French text (what the pipeline was given
    or should have produced); `output` is what the model emitted.
    """
    events = []
    substituted = preserved = rephrased = 0

    for qc_pat, fr_pat, qc_label, fr_label in FORM_PAIRS:
        src_n = _count(qc_pat, _norm(source))
        if not src_n:
            continue  # no opportunity: the source never used this Quebec form
        out_qc = _count(qc_pat, _norm(output))
        out_fr = _count(fr_pat, _norm(output))

        # Compare per-opportunity. Preserved occurrences are those the output
        # kept; substituted are France forms that appeared in their place.
        kept = min(out_qc, src_n)
        swapped = min(out_fr, src_n - kept)
        gone = src_n - kept - swapped  # expressed differently, or dropped

        preserved += kept
        substituted += swapped
        rephrased += gone

        if swapped:
            events.append({"type": "substituted", "quebec": qc_label,
                           "france": fr_label, "n": swapped})
        if gone:
            events.append({"type": "rephrased", "quebec": qc_label,
                           "france": fr_label, "n": gone})

    # Rephrasing is excluded from the denominator: it is neither drift nor
    # evidence against it, so counting it either way would bias the rate.
    denom = substituted + preserved
    return {
        "mdr": round(substituted / denom, 4) if denom else 0.0,
        "substituted": substituted,
        "preserved": preserved,
        "rephrased": rephrased,
        "opportunities": substituted + preserved + rephrased,
        "scored_opportunities": denom,
        "events": events,
    }


def measure_false_correction(original, proofread):
    """Quebec False Correction Rate for one proofreading round-trip.

    `original` must be text whose Canadian usage is already correct, so any
    alteration of a Quebec form is a false correction by construction.
    """
    events = []
    present = altered = 0

    for qc_pat, fr_pat, qc_label, fr_label in FORM_PAIRS:
        n_orig = _count(qc_pat, _norm(original))
        if not n_orig:
            continue
        present += n_orig
        n_after = _count(qc_pat, _norm(proofread))
        lost = max(0, n_orig - n_after)
        if lost:
            altered += lost
            became_france = _count(fr_pat, _norm(proofread)) > _count(fr_pat, _norm(original))
            events.append({
                "quebec": qc_label,
                "replaced_with": fr_label if became_france else "(removed/rephrased)",
                "n": lost,
                "to_france_form": became_france,
            })

    return {
        "qfcr": round(altered / present, 4) if present else 0.0,
        "valid_forms_present": present,
        "forms_altered": altered,
        "events": events,
    }


def corpus_drift(pairs):
    """Aggregate MDR over (source, output) pairs."""
    sub = pres = reph = 0
    events = []
    for src, out, tag in pairs:
        r = measure_drift(src, out)
        sub += r["substituted"]
        pres += r["preserved"]
        reph += r["rephrased"]
        for e in r["events"]:
            if e["type"] == "substituted":
                events.append({**e, "where": tag})
    denom = sub + pres
    return {
        "mdr": round(sub / denom, 4) if denom else 0.0,
        "substituted": sub, "preserved": pres, "rephrased": reph,
        "scored_opportunities": denom,
        "events": sorted(events, key=lambda e: -e["n"]),
    }


def corpus_false_correction(pairs):
    """Aggregate QFCR over (original, proofread) pairs."""
    present = altered = 0
    events = []
    for orig, proof, tag in pairs:
        r = measure_false_correction(orig, proof)
        present += r["valid_forms_present"]
        altered += r["forms_altered"]
        for e in r["events"]:
            events.append({**e, "where": tag})
    return {
        "qfcr": round(altered / present, 4) if present else 0.0,
        "valid_forms_present": present, "forms_altered": altered,
        "events": sorted(events, key=lambda e: -e["n"]),
    }
