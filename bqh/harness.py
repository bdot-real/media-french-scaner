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
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metrics.retrieval import (BilingualRetriever, ndcg_at_k, precision_at_k,
                               recall_at_k, reciprocal_rank)
from metrics.grounding import (coverage_vs_reference, lexical_entailment,
                               numeric_grounding)
from metrics.fluency import fluency_score
from metrics import severity as sev

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


SYSTEM_PROMPTS = {
    "fr": ("Tu es un assistant de recherche pour une salle de nouvelles. "
           "Réponds en français canadien (normes de Radio-Canada), pas en "
           "français métropolitain. N'affirme rien qui ne se trouve pas dans "
           "les sources. Réponds en 1 à 3 phrases."),
    "en": ("You are a newsroom research assistant. Answer in English. Assert "
           "nothing that is not in the sources. Answer in 1-3 sentences."),
}


def _build_prompt(query, lang, contexts):
    joined = "\n\n".join(contexts) if contexts else "(no documents retrieved)"
    label = "Sources" if lang == "en" else "Sources"
    q = "Question" if lang == "en" else "Question"
    return SYSTEM_PROMPTS[lang], f"{label}:\n{joined}\n\n{q}: {query}"


def generate_anthropic(query, lang, contexts, model):
    """Generate through the Anthropic API directly."""
    try:
        import anthropic
    except ImportError:
        raise SystemExit(
            "--provider anthropic requires: pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("--provider anthropic requires ANTHROPIC_API_KEY.")

    client = anthropic.Anthropic()
    system, user = _build_prompt(query, lang, contexts)
    msg = client.messages.create(model=model, max_tokens=400, system=system,
                                 messages=[{"role": "user", "content": user}])
    return msg.content[0].text.strip()


def _extract_text(body):
    """Pull the answer text out of an OpenRouter response.

    Returns (text, error). Reasoning models can return `content: null` with the
    output stranded in `reasoning` when the token budget is spent on thinking
    (finish_reason "length"), so a plain body["...']["content"].strip() crashes
    mid-run. Fall back to the reasoning field, and report an empty completion as
    a retryable error rather than silently scoring "" as an answer — an empty
    French answer would otherwise register as a grounding success with nothing
    to contradict.
    """
    try:
        choice = body["choices"][0]
    except (KeyError, IndexError):
        return None, f"malformed response: {str(body)[:160]}"
    msg = choice.get("message") or {}
    for field in ("content", "reasoning"):
        val = msg.get(field)
        if isinstance(val, str) and val.strip():
            return val.strip(), None
    if msg.get("refusal"):
        return None, f"model refused: {msg['refusal']}"
    return None, (f"empty completion (finish_reason="
                  f"{choice.get('finish_reason')!r})")


def generate_openrouter(query, lang, contexts, model, _retries=5):
    """Generate through OpenRouter (stdlib only — no SDK dependency).

    Free-tier OpenRouter endpoints rate-limit and occasionally return a
    provider error, so this retries with backoff. A run that silently dropped
    failed queries would bias the comparison, so exhaustion raises instead.
    """
    import urllib.error
    import urllib.request

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit(
            "--provider openrouter requires OPENROUTER_API_KEY to be set.")

    system, user = _build_prompt(query, lang, contexts)
    payload = json.dumps({
        "model": model,
        "max_tokens": 1200,
        "temperature": 0,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }).encode("utf-8")

    last = None
    retry_after = None
    for attempt in range(_retries):
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions", data=payload,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json",
                     "HTTP-Referer": "https://github.com/bilingual-quality-harness",
                     "X-Title": "Bilingual Quality Harness"})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            if "error" in body:
                last = body["error"].get("message", str(body["error"]))
            else:
                text, last = _extract_text(body)
                if text:
                    return text
            rate_limited = False
        except urllib.error.HTTPError as exc:
            last = f"HTTP Error {exc.code}: {exc.reason}"
            # 429 on a free tier needs a real cooldown, not a 2s nudge; the
            # window is typically tens of seconds. Honour Retry-After if sent.
            rate_limited = exc.code == 429
            if rate_limited:
                hdr = exc.headers.get("Retry-After") if exc.headers else None
                try:
                    retry_after = int(hdr) if hdr else None
                except ValueError:
                    retry_after = None
        except (urllib.error.URLError, KeyError, ValueError, TimeoutError) as exc:
            last = str(exc)
            rate_limited = False
        if attempt < _retries - 1:
            if rate_limited:
                time.sleep(retry_after or (30 * (attempt + 1)))
            else:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"OpenRouter failed after {_retries} attempts: {last}")


PROVIDERS = {"anthropic": generate_anthropic, "openrouter": generate_openrouter}


def evaluate(docs, queries, gens, live=False, model="claude-sonnet-5", k=3,
             provider="anthropic", verbose=False, cache_path=None):
    by_id = {d["doc_id"]: d for d in docs}
    cache = {}
    if cache_path and cache_path.exists():
        cache = json.loads(cache_path.read_text())
        if verbose and cache:
            print(f"  Reusing {len(cache)} cached generations", file=sys.stderr)
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
                ckey = f"{provider}|{model}|{q['query_id']}|{lang}"
                if ckey in cache:
                    answer = cache[ckey]
                else:
                    if verbose:
                        print(f"    {q['query_id']} [{lang}] generating…",
                              file=sys.stderr)
                    answer = PROVIDERS[provider](q[lang], lang, contexts, model)
                    # Checkpoint after every call: a 32-call run that dies at
                    # call 30 should not throw away the first 29.
                    cache[ckey] = answer
                    if cache_path:
                        cache_path.write_text(
                            json.dumps(cache, ensure_ascii=False, indent=2))
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
                "gold_docs": q["gold_docs"],
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

    summary = aggregate(rows)
    summary["severity"] = sev.summarize(rows)
    return rows, summary


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
    sv = summary.get("severity")
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
    if sv:
        print()
        print(f"  Service parity: {sv['parity_rate']*100:.0f}% of queries "
              f"answered equivalently in French")
        if sv["n_unserved"]:
            print(f"  ** {sv['n_unserved']} quer{'y' if sv['n_unserved']==1 else 'ies'} "
                  f"where the French reader was not served **")
        order = [t for t in sev.TIERS if t != "none" and sv["counts"][t]]
        if order:
            print("  Severity: " + " · ".join(
                f"{sev.TIER_META[t]['label']} {sv['counts'][t]}" for t in order))
        for c in sv["cases"][:3]:
            print()
            print(f"  [{sev.TIER_META[c['tier']]['label'].upper()}] {c['query_id']}"
                  f"  {c['reasons'][0] if c['reasons'] else ''}")
            print(f"     EN: {c['en_answer'][:96]}")
            print(f"     FR: {c['fr_answer'][:96]}")
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
                    help="Generate answers from a live model instead of the frozen corpus")
    ap.add_argument("--provider", default="anthropic", choices=sorted(PROVIDERS),
                    help="Live generation backend (default: anthropic)")
    ap.add_argument("--model", default=None,
                    help="Model id; defaults per provider")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="Log each live generation call")
    ap.add_argument("--limit", type=int, metavar="N",
                    help="Evaluate only the first N queries (useful when a "
                         "live provider caps daily requests)")
    ap.add_argument("--cache", metavar="PATH", default="live_cache.json",
                    help="Checkpoint file for live generations "
                         "(default: live_cache.json; use '' to disable)")
    ap.add_argument("--k", type=int, default=3, help="Retrieval depth")
    ap.add_argument("--json", metavar="PATH", help="Write full results as JSON")
    ap.add_argument("--report", metavar="PATH", help="Write the HTML dashboard")
    args = ap.parse_args()

    default_model = {"anthropic": "claude-sonnet-5",
                     "openrouter": "nex-agi/nex-n2.5-pro:free"}
    model = args.model or default_model[args.provider]

    docs, queries, gens = load_corpus()
    if args.limit:
        queries = queries[:args.limit]
    if args.live:
        print(f"  Live generation: {args.provider} · {model} "
              f"({len(queries) * 2} calls)", file=sys.stderr)
    rows, summary = evaluate(docs, queries, gens, live=args.live,
                             model=model, k=args.k, provider=args.provider,
                             verbose=args.verbose,
                             cache_path=Path(args.cache) if (args.live and args.cache) else None)
    summary["mode"] = f"live · {args.provider} · {model}" if args.live else "offline"
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
