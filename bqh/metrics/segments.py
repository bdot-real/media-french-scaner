"""Segment divergence by document metadata: desk, region, topic, recency.

An aggregate equivalence number tells you *whether* the pipeline is failing;
segmentation tells you *where*, which is what makes it fixable. "French
retrieval underperforms" is not an actionable statement. "French retrieval
underperforms on the Politics and Municipal desks, and specifically on
social-programme vocabulary" routes to an owner.

Segments are computed from the documents a query's gold set points at, so a
query inherits the metadata of the content it should have retrieved.
"""
import statistics

AXES = ("desk", "region", "topic")


def _query_segments(row, by_id):
    """Metadata values attached to a query, via its gold documents."""
    vals = {a: set() for a in AXES}
    for doc_id in row.get("gold_docs", []):
        doc = by_id.get(doc_id)
        if not doc:
            continue
        meta = doc.get("meta", {})
        for a in AXES:
            v = meta.get(a) if a != "topic" else doc.get("topic")
            if v:
                vals[a].add(v)
    return vals


# Metrics worth segmenting, with how to read them off a per-language result.
SEG_METRICS = {
    "retrieval_p_at_1": lambda L: L["p_at_1"],
    "content_coverage": lambda L: L["coverage_vs_en"]["score"],
    "fluency_register": lambda L: L["fluency"]["register"]["score"],
}


def segment(rows, documents, min_n=2):
    """Per-segment EN/FR gaps. Segments below `min_n` queries are reported
    but flagged, because a one-query segment is an anecdote, not a trend."""
    by_id = {d["doc_id"]: d for d in documents}
    buckets = {a: {} for a in AXES}

    for row in rows:
        segs = _query_segments(row, by_id)
        for axis in AXES:
            for value in segs[axis]:
                b = buckets[axis].setdefault(value, {"queries": [], "sev": []})
                b["queries"].append(row)
                b["sev"].append(row.get("severity", "none"))

    out = {}
    for axis, values in buckets.items():
        rows_out = []
        for value, b in values.items():
            entry = {"segment": value, "n": len(b["queries"]),
                     "thin": len(b["queries"]) < min_n,
                     "unserved": sum(1 for s in b["sev"]
                                     if s in ("no_answer", "wrong_fact")),
                     "divergent": sum(1 for s in b["sev"] if s != "none")}
            for name, getter in SEG_METRICS.items():
                en = statistics.mean(getter(q["langs"]["en"]) for q in b["queries"])
                fr = statistics.mean(getter(q["langs"]["fr"]) for q in b["queries"])
                entry[name] = {"en": round(en, 4), "fr": round(fr, 4),
                               "gap": round(en - fr, 4)}
            entry["worst_gap"] = round(
                max(entry[m]["gap"] for m in SEG_METRICS), 4)
            rows_out.append(entry)
        out[axis] = sorted(rows_out, key=lambda r: (-r["worst_gap"], r["segment"]))
    return out
