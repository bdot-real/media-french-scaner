"""Terminology consistency and readability parity across a corpus of answers.

Two failure modes that are invisible when you score answers one at a time.

--------------------------------------------------------------------------
Terminology consistency
--------------------------------------------------------------------------
A pipeline can render the same institution or programme three different ways
across a run — "assurance-emploi", "assurance chômage", "régime d'assurance
emploi" — and each answer looks fine in isolation. For a broadcaster this is a
house-style failure that erodes trust and breaks archive search, and it is
systematically worse in the second language, where no single reviewer sees all
the output.

Measured as: for each concept with a defined canonical form, the share of
mentions that use it. Variants are counted and named, so the finding is a
style-guide entry rather than a number.

--------------------------------------------------------------------------
Readability parity
--------------------------------------------------------------------------
French renders the same content 15-20% longer than English. A naive
readability comparison therefore reports French as harder to read on every
story, which is an artefact, not a finding.

What is worth measuring is whether the *gap* is stable. A French answer set
that runs far longer than the expected expansion is drifting toward
officialese — the register problem the fluency check catches word by word,
showing up at the level of sentence construction.
"""
import re
import statistics

from .retrieval import tokenize

# Concept -> (canonical form, [variant patterns]). Variants are all *plausible*
# renderings a model might produce; the point is consistency, not correctness.
TERM_SETS = {
    "fr": {
        "employment_insurance": ("assurance-emploi",
                                 [r"assurance[- ]emploi", r"assurance chômage",
                                  r"prestations de chômage",
                                  r"assurance[- ]chomage"]),
        "school_trustee": ("conseiller scolaire",
                           [r"conseillers?[- ]scolaires?", r"commissaires?[- ]d'école",
                            r"administrateurs?[- ]scolaires?"]),
        "warming_centre": ("halte-chaleur",
                           [r"haltes?[- ]chaleur", r"centres?[- ]de[- ]réchauffement",
                            r"centres?[- ]d['’]hébergement[- ]chauff\w*",
                            r"refuges?[- ]chauffés?"]),
        "closm": ("communauté de langue officielle en situation minoritaire",
                  [r"communautés?[- ]de[- ]langue[- ]officielle",
                   r"\bCLOSM\b", r"communautés?[- ]francophones?[- ]minoritaires?",
                   r"minorités?[- ]linguistiques?"]),
        "property_tax": ("taxe foncière",
                         [r"taxes?[- ]foncières?", r"impôts?[- ]fonciers?",
                          r"impôts?[- ]locaux?"]),
        "long_term_care": ("soins de longue durée",
                           [r"soins[- ]de[- ]longue[- ]durée", r"CHSLD",
                            r"hébergement[- ]de[- ]longue[- ]durée"]),
    },
    "en": {
        "employment_insurance": ("employment insurance",
                                 [r"employment insurance", r"\bEI\b",
                                  r"unemployment insurance", r"jobless benefits"]),
        "school_trustee": ("school trustee",
                           [r"school trustees?", r"school board members?",
                            r"school commissioners?"]),
        "warming_centre": ("warming centre",
                           [r"warming centres?", r"warming centers?",
                            r"heated shelters?"]),
        "closm": ("official language minority community",
                  [r"official language minority communit\w+", r"\bOLMC\b",
                   r"linguistic minorit\w+"]),
        "property_tax": ("property tax",
                         [r"property taxe?s?", r"municipal taxe?s?",
                          r"local taxe?s?"]),
        "long_term_care": ("long-term care",
                           [r"long[- ]term care", r"\bLTC\b",
                            r"nursing homes?"]),
    },
}


def terminology_consistency(answers, lang):
    """Share of mentions using the canonical form, per concept."""
    joined = " ".join(answers).lower()
    concepts = []
    for key, (canonical, variants) in TERM_SETS.get(lang, {}).items():
        # Variants overlap by design ("regime d'assurance-emploi" contains
        # "assurance-emploi"), so counting each pattern independently
        # double-counts the same span and understates consistency. Claim each
        # character span once, longest match first.
        claimed = []
        counts = {}
        # Canonical first, then longest: a canonical match must never be
        # claimed by an overlapping variant pattern.
        order = sorted(enumerate(variants),
                       key=lambda iv: (iv[0] != 0, -len(iv[1])))
        for idx, pat in order:
            n = 0
            for m in re.finditer(pat, joined, flags=re.IGNORECASE):
                if any(m.start() < e and m.end() > s_ for s_, e in claimed):
                    continue
                claimed.append((m.start(), m.end()))
                n += 1
            if n:
                counts[pat] = n
        total = sum(counts.values())
        if not total:
            continue
        canon_n = counts.get(variants[0], 0)
        concepts.append({
            "concept": key,
            "canonical": canonical,
            "mentions": total,
            "canonical_mentions": canon_n,
            "consistency": round(canon_n / total, 4),
            "variants": sorted(
                ({"pattern": p, "n": n} for p, n in counts.items()),
                key=lambda v: -v["n"]),
        })
    if not concepts:
        return {"score": 1.0, "concepts": [], "n_concepts": 0}
    weighted = sum(c["consistency"] * c["mentions"] for c in concepts)
    total_mentions = sum(c["mentions"] for c in concepts)
    return {
        "score": round(weighted / total_mentions, 4),
        "n_concepts": len(concepts),
        "concepts": sorted(concepts, key=lambda c: c["consistency"]),
    }


# The oft-cited "French runs 15-20% longer" figure applies to raw text. This
# harness compares *content* tokens after stopword removal, and the French
# stoplist is larger (articles, contracted forms, more prepositions), which
# cancels most of that expansion.
#
# Measured across the 68 defect-free EN/FR answer pairs in this corpus:
#   mean ratio 1.00, median 1.00, stdev 0.115, p10 0.85, p90 1.15
#
# So parity is the expectation, and the tolerance is set just outside the
# observed spread. Guessing this constant produced false "content dropped"
# verdicts on faithful French; it is measured, and should be re-measured if the
# corpus or answer style changes materially.
EXPECTED_EXPANSION = 1.00
EXPANSION_TOLERANCE = 0.30


def readability_parity(en_answers, fr_answers):
    """Is the FR/EN length relationship within the expected expansion band?"""
    def stats(answers, lang):
        lens, sents = [], []
        for a in answers:
            lens.append(len(tokenize(a, lang)))
            parts = [s for s in re.split(r"[.!?]+", a) if s.strip()]
            if parts:
                sents.append(sum(len(s.split()) for s in parts) / len(parts))
        return (statistics.mean(lens) if lens else 0.0,
                statistics.mean(sents) if sents else 0.0)

    en_tok, en_sent = stats(en_answers, "en")
    fr_tok, fr_sent = stats(fr_answers, "fr")
    ratio = (fr_tok / en_tok) if en_tok else 1.0
    deviation = abs(ratio - EXPECTED_EXPANSION)
    score = max(0.0, 1.0 - deviation / EXPANSION_TOLERANCE)
    if deviation <= 0.15:  # inside the observed p10-p90 spread
        verdict = "within expected expansion"
    elif ratio < EXPECTED_EXPANSION:
        verdict = "French materially shorter than expected — content likely dropped"
    else:
        verdict = "French materially longer than expected — drifting toward officialese"
    return {
        "score": round(min(1.0, score), 4),
        "ratio": round(ratio, 4),
        "expected": EXPECTED_EXPANSION,
        "en_tokens": round(en_tok, 1), "fr_tokens": round(fr_tok, 1),
        "en_sentence_len": round(en_sent, 1), "fr_sentence_len": round(fr_sent, 1),
        "verdict": verdict,
    }
