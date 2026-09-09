"""Answerability: does each language get an answer at all?

The live run surfaced the harness's sharpest finding — a French reader asking
where to warm up during an outage received "les sources ne mentionnent aucune
panne" while the English reader was answered correctly. That is measured here
as a first-class dimension rather than inferred from severity tiers.

Three states per answer:

  answered   substantive response
  refused    model declined — no source, or not enough information
  hedged     answered, but wrapped in uncertainty language that a news desk
             could not publish as-is ("il semblerait que", "possibly")

The asymmetry is what matters. A pipeline that refuses equally in both
languages is conservative; one that refuses more in French is rationing service
by language, and refusals are near-invisible in conventional quality metrics —
a refusal asserts nothing, so it scores perfectly on grounding and register.
"""
import re

from .severity import is_refusal

HEDGE_PATTERNS = {
    "fr": [r"\bil semblerait\b", r"\bil se pourrait\b", r"\bpeut-être\b",
           r"\bprobablement\b", r"\bsemble indiquer\b", r"\bpourrait[- ]être\b",
           r"\bn'est pas clair\b", r"\bdifficile à dire\b",
           r"\bsous réserve\b", r"\bà confirmer\b"],
    "en": [r"\bit (?:seems|appears)\b", r"\bpossibly\b", r"\bperhaps\b",
           r"\bprobably\b", r"\bmight be\b", r"\bunclear\b",
           r"\bhard to say\b", r"\bsubject to confirmation\b",
           r"\bto be confirmed\b", r"\bI think\b"],
}


def classify_answer(text, lang):
    if is_refusal(text):
        return "refused", []
    hedges = [m.group() for pat in HEDGE_PATTERNS.get(lang, [])
              for m in re.finditer(pat, text, flags=re.IGNORECASE)]
    return ("hedged" if hedges else "answered"), hedges


def answerability(rows):
    """Per-language answer states and the asymmetry between them."""
    per = {}
    for lang in ("en", "fr"):
        counts = {"answered": 0, "refused": 0, "hedged": 0}
        cases = []
        for r in rows:
            state, hedges = classify_answer(r["langs"][lang]["answer"], lang)
            r["langs"][lang]["answer_state"] = state
            counts[state] += 1
            if state != "answered":
                cases.append({"query_id": r["query_id"], "state": state,
                              "hedges": hedges})
        n = max(len(rows), 1)
        per[lang] = {
            "counts": counts,
            "answer_rate": round(counts["answered"] / n, 4),
            "refusal_rate": round(counts["refused"] / n, 4),
            "hedge_rate": round(counts["hedged"] / n, 4),
            "cases": cases,
        }

    # Queries where one language answered and the other did not — the finding
    # that conventional quality metrics cannot see, because a refusal asserts
    # nothing and therefore scores perfectly on grounding and register.
    asymmetric = []
    for r in rows:
        en_s = r["langs"]["en"].get("answer_state")
        fr_s = r["langs"]["fr"].get("answer_state")
        if en_s == "answered" and fr_s == "refused":
            asymmetric.append({"query_id": r["query_id"], "served": "en",
                               "denied": "fr"})
        elif fr_s == "answered" and en_s == "refused":
            asymmetric.append({"query_id": r["query_id"], "served": "fr",
                               "denied": "en"})

    return {
        "per_language": per,
        "asymmetric": asymmetric,
        "n_asymmetric": len(asymmetric),
        "refusal_gap": round(per["fr"]["refusal_rate"]
                             - per["en"]["refusal_rate"], 4),
        "answer_gap": round(per["en"]["answer_rate"]
                            - per["fr"]["answer_rate"], 4),
    }
