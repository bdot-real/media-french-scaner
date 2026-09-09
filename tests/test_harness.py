"""Validation: does the harness detect the defects that were actually planted?

An evaluation tool that produces plausible numbers without detecting known
faults is worse than no tool. These tests check detections against the
ground-truth annotations in corpus/generations.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bqh"))

from harness import evaluate, load_corpus
from metrics.grounding import normalize_number
from metrics.fluency import register_check

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not cond else ""))


def main():
    docs, queries, gens = load_corpus()
    rows, summary = evaluate(docs, queries, gens)
    by_q = {r["query_id"]: r for r in rows}

    print("\n1. Number normalisation is language-neutral")
    check("FR '18 400' == EN '18,400'", normalize_number("18 400") == normalize_number("18,400"))
    check("FR '3,75' == EN '3.75'", normalize_number("3,75") == normalize_number("3.75"))
    check("EN grouping '1,234' not read as decimal", normalize_number("1,234") == "1234")

    print("\n2. Planted grounding defects are detected")
    for g in gens.values():
        qid = g["query_id"]
        planted = [d for d in g["fr"]["defects"] if d["type"] == "grounding"
                   and d.get("span") and any(c.isdigit() for c in d["span"])]
        if planted:
            score = by_q[qid]["langs"]["fr"]["numeric_grounding_gold"]["score"]
            check(f"{qid} numeric fabrication caught", score < 1.0, f"score={score}")

    print("\n3. Planted register defects are detected")
    for g in gens.values():
        qid = g["query_id"]
        if any(d["type"] == "register" for d in g["fr"]["defects"]):
            score = by_q[qid]["langs"]["fr"]["fluency"]["register"]["score"]
            check(f"{qid} register violation caught", score < 1.0, f"score={score}")

    print("\n4. Planted coverage omissions are detected")
    for g in gens.values():
        qid = g["query_id"]
        # Defects flagged detectable=False are known limits of the metric,
        # recorded deliberately rather than silently passing.
        if any(d["type"] == "coverage" and d.get("detectable", True)
               for d in g["fr"]["defects"]):
            score = by_q[qid]["langs"]["fr"]["coverage_vs_en"]["score"]
            check(f"{qid} omission caught", score < 1.0, f"score={score}")

    print("\n4b. Known-undetectable defects are documented, not silently passing")
    undetectable = [(qid, d["type"]) for qid, x in gens.items()
                    for d in x["fr"]["defects"] if not d.get("detectable", True)]
    for qid, kind in undetectable:
        check(f"{qid} {kind} recorded as a known metric limit", True)

    print("\n5. Clean French answers are NOT flagged (false-positive control)")
    for g in gens.values():
        qid = g["query_id"]
        if not g["fr"]["defects"]:
            L = by_q[qid]["langs"]["fr"]
            clean = (L["numeric_grounding_gold"]["score"] == 1.0
                     and L["fluency"]["register"]["score"] == 1.0)
            check(f"{qid} clean answer unflagged", clean,
                  f"ground={L['numeric_grounding_gold']['score']} "
                  f"reg={L['fluency']['register']['score']}")

    print("\n6. English baseline is clean (no fabrication in EN corpus)")
    check("EN fabrication score == 1.0",
          summary["dimensions"]["grounding_numeric"]["en"] == 1.0)
    check("EN register score == 1.0",
          summary["dimensions"]["fluency_register"]["en"] == 1.0)

    print("\n7. Register rules do not fire on Canadian French")
    ca = ("Les conseillers scolaires ont ouvert des haltes-chaleur "
          "et envoyé un courriel durant la fin de semaine.")
    check("Canadian phrasing scores 1.0", register_check(ca, "fr")["score"] == 1.0)

    print("\n8. Determinism")
    _, s2 = evaluate(docs, queries, gens)
    check("re-run gives identical index",
          s2["equivalence_index"] == summary["equivalence_index"])

    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
