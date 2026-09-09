"""Bilingual Quality Harness — evaluation runner.

Measures whether an AI content workflow performs *equivalently* in English and
French, rather than whether it performs adequately in each. The unit of
analysis is the gap, not the score.

Offline by default (frozen corpus, deterministic, no network). Pass --live to
generate answers from the Claude API instead of the frozen set.
"""
import argparse
import json
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metrics.retrieval import (BilingualRetriever, ndcg_at_k, precision_at_k,
                               recall_at_k, reciprocal_rank)
from metrics.grounding import (coverage_vs_reference, lexical_entailment,
                               numeric_grounding)
from metrics.fluency import fluency_score

CORPUS = Path(__file__).resolve().parent / "corpus"
LANGS = ("en", "fr")
# A gap wider than this on any dimension is a finding, not noise. Chosen so
# that a single failed query in a 16-query set (6.25%) does not trip the alarm
# but a systematic pattern does.
EQUIVALENCE_THRESHOLD = 0.08


def load_corpus():
    docs = json.loads((CORPUS / "documents.json").read_text())["documents"]
    queries = json.loads((CORPUS / "queries.json").read_text())["queries"]
    gens = json.loads((CORPUS / "generations.json").read_text())["generations"]
    return docs, queries, {g["query_id"]: g for g in gens}


def generate_live(query, lang, contexts, model):
    """Generate an answer with the Claude API. Only used with --live."""
    try:
        import anthropic
    except ImportError:
        raise SystemExit(
            "--live requires the anthropic package: pip install anthropic"
        )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("--live requires ANTHROPIC_API_KEY to be set.")

    client = anthropic.Anthropic()
    style = (
        "Réponds en français canadien (normes de Radio-Canada), pas en français "
        "métropolitain. N'affirme rien qui ne soit pas dans les sources."
        if lang == "fr" else
        "Answer in English. Assert nothing that is not in the sources."
    )
    joined = "\n\n".join(contexts)
    msg = client.messages.create(
        model=model,
        max_tokens=400,
        system=f"You are a newsroom research assistant. {style} Answer in 1-3 sentences.",
        messages=[{"role": "user",
                   "content": f"Sources:\n{joined}\n\nQuestion: {query}"}],
    )
    return msg.content[0].text.strip()


def evaluate(docs, queries, gens, live=False, model="claude-sonnet-5", k=3):
    by_id = {d["doc_id"]: d for d in docs}
    retrievers = {lang: BilingualRetriever(docs, lang) for lang in LANGS}
    rows = []

    for q in queries:
        row = {"query_id": q["query_id"],
               "divergence_class": q.get("divergence_class"),
               "note": q.get("note"),
               "gold_docs": q["gold_docs"], "langs": {}}

        for lang in LANGS:
            retr = retrievers[lang]
            ranked = retr.retrieve(q[lang], k=k)
            contexts = [by_id[d][lang]["title"] + ". " + by_id[d][lang]["body"]
                        for d in ranked if d in by_id]

            if live:
                answer = generate_live(q[lang], lang, contexts, model)
            else:
                answer = gens[q["query_id"]][lang]["answer"]

            # Grounding is measured against what retrieval actually returned,
            # not against the gold documents. Scoring against gold would hide
            # the compounding failure where French retrieval misses a document
            # and generation then invents its content.
            num = numeric_grounding(answer, contexts, lang)
            # Also score against the gold context. Comparing the two isolates
            # true fabrication (fails against gold too) from unsupported
            # claims that are merely an artefact of a retrieval miss (passes
            # against gold). Without this split, a retrieval failure is
            # misreported as a hallucination.
            gold_ctx = [by_id[d][lang]["title"] + ". " + by_id[d][lang]["body"]
                        for d in q["gold_docs"] if d in by_id]
            num_gold = numeric_grounding(answer, gold_ctx, lang)
            ent = lexical_entailment(answer, contexts, lang)
            flu = fluency_score(answer, lang)

            row["langs"][lang] = {
                "retrieved": ranked,
                "answer": answer,
                "p_at_1": precision_at_k(ranked, q["gold_docs"], 1),
                "p_at_k": precision_at_k(ranked, q["gold_docs"], k),
                "recall_at_k": recall_at_k(ranked, q["gold_docs"], k),
                "mrr": reciprocal_rank(ranked, q["gold_docs"]),
                "ndcg": ndcg_at_k(ranked, q["gold_docs"], k),
                "numeric_grounding": num,
                "numeric_grounding_gold": num_gold,
                "retrieval_induced_loss": round(
                    max(0.0, num_gold["score"] - num["score"]), 4),
                "entailment": ent,
                "fluency": flu,
                "weak_terms": retr.weak_terms(q[lang], ranked),
            }

        # Cross-language content coverage: does FR carry EN's information?
        row["langs"]["fr"]["coverage_vs_en"] = coverage_vs_reference(
            row["langs"]["fr"]["answer"], row["langs"]["en"]["answer"], "fr")
        row["langs"]["en"]["coverage_vs_en"] = {"score": 1.0, "missing": []}
        rows.append(row)

    return rows, aggregate(rows)


DIMENSIONS = [
    ("retrieval_p_at_1", lambda r: r["p_at_1"]),
    ("retrieval_recall", lambda r: r["recall_at_k"]),
    ("retrieval_ndcg", lambda r: r["ndcg"]),
    ("grounding_numeric", lambda r: r["numeric_grounding_gold"]["score"]),
    ("grounding_in_context", lambda r: r["numeric_grounding"]["score"]),
    ("grounding_entailment", lambda r: r["entailment"]["score"]),
    ("content_coverage", lambda r: r["coverage_vs_en"]["score"]),
    ("fluency_register", lambda r: r["fluency"]["register"]["score"]),
    ("fluency_overall", lambda r: r["fluency"]["score"]),
]


def aggregate(rows):
    summary = {"dimensions": {}, "n_queries": len(rows),
               "threshold": EQUIVALENCE_THRESHOLD}
    for name, getter in DIMENSIONS:
        vals = {lang: [getter(r["langs"][lang]) for r in rows] for lang in LANGS}
        en_mean = statistics.mean(vals["en"])
        fr_mean = statistics.mean(vals["fr"])
        summary["dimensions"][name] = {
            "en": round(en_mean, 4),
            "fr": round(fr_mean, 4),
            "gap": round(en_mean - fr_mean, 4),
            "equivalent": abs(en_mean - fr_mean) <= EQUIVALENCE_THRESHOLD,
        }

    gaps = [d["gap"] for d in summary["dimensions"].values()]
    summary["equivalence_index"] = round(
        1.0 - statistics.mean([abs(g) for g in gaps]), 4)
    summary["failing_dimensions"] = [
        n for n, d in summary["dimensions"].items() if not d["equivalent"]]

    # Attribute divergence to specific vocabulary.
    weak = {}
    for r in rows:
        for w in r["langs"]["fr"]["weak_terms"]:
            cur = weak.setdefault(w["term"], {"term": w["term"],
                                              "coverage": w["coverage"],
                                              "queries": []})
            cur["queries"].append(r["query_id"])
    summary["weak_lexicon"] = sorted(weak.values(), key=lambda w: w["coverage"])

    summary["divergent_queries"] = [
        {"query_id": r["query_id"],
         "divergence_class": r["divergence_class"],
         "note": r.get("note"),
         "en_p1": r["langs"]["en"]["p_at_1"],
         "fr_p1": r["langs"]["fr"]["p_at_1"],
         "en_ground": r["langs"]["en"]["numeric_grounding"]["score"],
         "fr_ground": r["langs"]["fr"]["numeric_grounding"]["score"],
         "fr_register": r["langs"]["fr"]["fluency"]["register"]["score"],
         "fr_coverage": r["langs"]["fr"]["coverage_vs_en"]["score"]}
        for r in rows
        if r["langs"]["en"]["p_at_1"] != r["langs"]["fr"]["p_at_1"]
        or r["langs"]["fr"]["numeric_grounding"]["score"] < 1.0
        or r["langs"]["fr"]["fluency"]["register"]["score"] < 1.0
        or r["langs"]["fr"]["coverage_vs_en"]["score"] < 1.0
    ]
    return summary


def print_report(summary):
    d = summary["dimensions"]
    print()
    print("  BILINGUAL QUALITY HARNESS — EN/FR equivalence")
    print(f"  {summary['n_queries']} queries · Canadian French · journalistic corpus")
    print("  " + "-" * 62)
    print(f"  {'DIMENSION':<24}{'EN':>8}{'FR':>8}{'GAP':>9}   STATUS")
    print("  " + "-" * 62)
    for name, vals in d.items():
        flag = "ok" if vals["equivalent"] else "DIVERGENT"
        print(f"  {name:<24}{vals['en']:>8.3f}{vals['fr']:>8.3f}"
              f"{vals['gap']:>+9.3f}   {flag}")
    print("  " + "-" * 62)
    print(f"  Equivalence index: {summary['equivalence_index']:.3f}"
          f"   (1.000 = perfect parity)")
    if summary["failing_dimensions"]:
        print(f"  Divergent dimensions: {', '.join(summary['failing_dimensions'])}")
    if summary["weak_lexicon"]:
        print()
        print("  Lexicon coverage gaps driving retrieval divergence:")
        for w in summary["weak_lexicon"][:6]:
            print(f"    {w['term']:<22} coverage {w['coverage']:.2f}"
                  f"   queries: {', '.join(w['queries'])}")
    print()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true",
                    help="Generate answers via the Claude API instead of the frozen corpus")
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--k", type=int, default=3, help="Retrieval depth")
    ap.add_argument("--json", metavar="PATH", help="Write full results as JSON")
    ap.add_argument("--report", metavar="PATH", help="Write the HTML dashboard")
    args = ap.parse_args()

    docs, queries, gens = load_corpus()
    rows, summary = evaluate(docs, queries, gens, live=args.live,
                             model=args.model, k=args.k)
    summary["mode"] = "live" if args.live else "offline"
    print_report(summary)

    if args.json:
        Path(args.json).write_text(
            json.dumps({"summary": summary, "rows": rows},
                       ensure_ascii=False, indent=2))
        print(f"  JSON written to {args.json}")
    if args.report:
        from report.dashboard import render
        Path(args.report).write_text(render(summary, rows), encoding="utf-8")
        print(f"  Dashboard written to {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
