"""Per-query failure severity.

A mean hides the case that matters. In the live run the harness reported
"equivalence 0.958, all dimensions pass" while a French user asking where to
warm up during a power outage received no answer at all. Averaged across 13
queries, a total service failure became a rounding error.

Public-service bilingualism is not an average commitment. A single query where
one language is served and the other is not is a mandate failure regardless of
how well the other fifteen scored. This module classifies each query's worst
outcome so the dashboard can lead with severity, not with a mean.

Tiers are ordered by what a reader actually experiences:

  no_answer   FR returns nothing usable while EN answers. The reader is simply
              not served. Worst possible outcome.
  wrong_fact  FR asserts a figure or claim absent from the source. Actively
              misinforms — worse than silence in journalism.
  wrong_docs  Retrieval diverged; FR answered from different sources than EN.
              Substantively different answers to the same question.
  omission    FR is accurate but carries less information than EN. A reduced
              edition of the story.
  register    FR is accurate and complete but reads as foreign — metropolitan
              forms, anglicisms, wrong statutory terms.
  none        No detected divergence.
"""
import re

TIERS = ["no_answer", "wrong_fact", "wrong_docs", "omission", "register", "none"]

TIER_META = {
    "no_answer":  {"rank": 0, "label": "No answer returned",
                   "desc": "French reader is not served at all"},
    "wrong_fact": {"rank": 1, "label": "Unsupported fact",
                   "desc": "Asserts a figure absent from the source"},
    "wrong_docs": {"rank": 2, "label": "Different sources",
                   "desc": "Retrieval diverged between languages"},
    "omission":   {"rank": 3, "label": "Reduced content",
                   "desc": "Accurate but carries less than the English"},
    "register":   {"rank": 4, "label": "Register",
                   "desc": "Not Canadian French"},
    "none":       {"rank": 5, "label": "Equivalent", "desc": ""},
}

# A model that correctly declines when retrieval returned nothing relevant.
# Detecting this matters: a refusal scores well on grounding (nothing asserted,
# nothing to contradict) and on register (no violations possible), so without an
# explicit check the worst outcome for the reader looks like a clean pass.
REFUSAL_PATTERNS = [
    r"\bne mentionn\w*\b", r"\bne (?:pré|pre)cis\w*\b",
    r"\baucun\w*\s+(?:information|mention|indication|source|endroit|détail)",
    r"\bles sources (?:fournies |disponibles )?ne\b",
    r"\bimpossible de répondre\b", r"\bje ne (?:peux|dispose)\b",
    r"\bpas (?:d'|de )information\b", r"\bne permet(?:tent)? pas de\b",
    r"\bsources? (?:provided|available) (?:do|does) not\b",
    r"\bno (?:information|mention|indication)\b",
    r"\bcannot (?:answer|determine)\b", r"\bdon't have (?:enough )?information\b",
]


def is_refusal(text):
    """Does this answer decline to answer rather than answering?"""
    if not text or len(text.strip()) < 12:
        return True
    low = text.lower()
    return any(re.search(p, low) for p in REFUSAL_PATTERNS)


def classify(en, fr):
    """Worst-case severity tier for one query, given both language results.

    `en` and `fr` are the per-language result dicts built by the harness.
    """
    reasons = []

    en_ref, fr_ref = is_refusal(en["answer"]), is_refusal(fr["answer"])
    if fr_ref and not en_ref:
        reasons.append("French declined to answer; English answered")
        return "no_answer", reasons
    if en_ref and not fr_ref:
        reasons.append("English declined to answer; French answered")
        return "no_answer", reasons

    if fr["numeric_grounding_gold"]["score"] < 1.0:
        bad = fr["numeric_grounding_gold"]["unsupported"]
        reasons.append(f"French asserts unsupported figure(s): {', '.join(bad)}")
        return "wrong_fact", reasons

    # Only count retrieval divergence that could change the answer. Differing
    # at rank 2-3 while both languages surface the same gold document is a
    # ranking artefact, not a service failure — counting it inflates the tier
    # and buries the cases that actually harmed the reader.
    gold = set(en.get("gold_docs") or [])
    en_gold = [d for d in en["retrieved"] if d in gold]
    fr_gold = [d for d in fr["retrieved"] if d in gold]
    if set(en_gold) != set(fr_gold):
        only_en = [d for d in en_gold if d not in fr_gold]
        only_fr = [d for d in fr_gold if d not in en_gold]
        detail = []
        if only_en:
            detail.append(f"EN-only: {', '.join(only_en)}")
        if only_fr:
            detail.append(f"FR-only: {', '.join(only_fr)}")
        reasons.append("Gold-document retrieval diverged ("
                       + "; ".join(detail) + ")")
        return "wrong_docs", reasons

    if fr["coverage_vs_en"]["score"] < 1.0:
        miss = fr["coverage_vs_en"]["missing"]
        reasons.append("French omits content present in English"
                       + (f": {', '.join(miss)}" if miss else ""))
        return "omission", reasons

    viol = fr["fluency"]["register"]["violations"]
    if viol:
        worst = min(viol, key=lambda v: {"high": 0, "medium": 1, "low": 2}[v["severity"]])
        reasons.append(f"Register: '{worst['found']}' → '{worst['preferred']}'")
        return "register", reasons

    return "none", reasons


def summarize(rows):
    """Severity distribution plus the worst cases, for the dashboard headline."""
    counts = {t: 0 for t in TIERS}
    cases = []
    for r in rows:
        tier, reasons = classify(r["langs"]["en"], r["langs"]["fr"])
        counts[tier] += 1
        r["severity"] = tier
        r["severity_reasons"] = reasons
        if tier != "none":
            cases.append({
                "query_id": r["query_id"],
                "tier": tier,
                "rank": TIER_META[tier]["rank"],
                "reasons": reasons,
                "en_answer": r["langs"]["en"]["answer"],
                "fr_answer": r["langs"]["fr"]["answer"],
                "divergence_class": r.get("divergence_class"),
            })
    cases.sort(key=lambda c: (c["rank"], c["query_id"]))

    served = sum(counts[t] for t in ("none", "register"))
    return {
        "counts": counts,
        "cases": cases,
        # The headline number: share of queries where the French reader got a
        # substantively equivalent answer. Register issues still count as
        # served — the reader got the facts, if not the idiom.
        "parity_rate": round(served / len(rows), 4) if rows else 1.0,
        "worst_tier": cases[0]["tier"] if cases else "none",
        "n_unserved": counts["no_answer"] + counts["wrong_fact"],
    }
