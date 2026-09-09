"""Media metadata equivalence: images, video, and audio.

The article text is not the only thing a bilingual newsroom publishes. Every
image, video, and audio clip carries descriptors — alt text, captions, credits,
transcripts — and these are where bilingual parity quietly fails, because the
*asset* is reused across both language sites while only the English descriptors
get written.

That failure has two distinct costs, and they compound:

  accessibility — a French screen-reader user gets nothing where an English one
                  gets a description. Missing alt text is not a quality delta;
                  it is a French user excluded from content an English user can
                  access. For a public broadcaster this is also a regulatory
                  exposure, not just an editorial one.
  discovery     — alt text and captions feed search and archive retrieval, so a
                  French asset with no descriptors is effectively unfindable in
                  the French archive.

Detected failure modes, ordered by severity:

  missing      FR descriptor absent entirely while EN is present
  untranslated FR field byte-identical to EN — the asset shipped without
               anyone translating it, which reads as present in a CMS audit and
               is therefore worse than missing: it passes a null check
  truncated    FR present but far shorter than EN, so content was dropped
  ok           present, translated, comparable length

Video and audio are held to a stricter standard: a missing transcript removes
the only text representation of the content, so it is treated as a hard
accessibility failure rather than a metadata gap.
"""

# Assets whose content is inaccessible without a text alternative.
TIMED_MEDIA = ("video", "audio")

# FR/EN length ratio below which a present descriptor is treated as truncated.
# French runs slightly longer than English for equivalent content, so anything
# under half the English length has certainly lost information.
TRUNCATION_RATIO = 0.5

FIELD_WEIGHT = {          # relative contribution to the asset's parity score
    "alt": 0.45,          # accessibility-critical
    "transcript": 0.35,   # accessibility-critical for timed media
    "caption": 0.15,
    "credit": 0.05,
}


def _classify(en, fr):
    """Compare one EN/FR descriptor pair."""
    en = (en or "").strip()
    fr = (fr or "").strip()
    if not en:
        return "n/a"          # nothing to be equivalent to
    if not fr:
        return "missing"
    if fr == en:
        return "untranslated"
    if len(fr) < len(en) * TRUNCATION_RATIO:
        return "truncated"
    return "ok"


STATE_SCORE = {"ok": 1.0, "truncated": 0.5, "untranslated": 0.25,
               "missing": 0.0, "n/a": None}


def check_asset(asset):
    """Evaluate one media asset's French metadata against its English."""
    kind = asset.get("kind", "image")
    fields = {}

    fields["alt"] = _classify(asset.get("en_alt"), asset.get("fr_alt"))
    fields["caption"] = _classify(asset.get("en_caption"), asset.get("fr_caption"))
    fields["credit"] = _classify(asset.get("en_credit"), asset.get("fr_credit"))
    fields["transcript"] = _classify(asset.get("en_transcript"),
                                     asset.get("fr_transcript"))

    # Credits are proper nouns and legitimately identical in both languages
    # ("CBC/Radio-Canada"), so an identical credit is correct, not untranslated.
    if fields["credit"] == "untranslated":
        fields["credit"] = "ok"

    scored = {f: STATE_SCORE[s] for f, s in fields.items()
              if STATE_SCORE[s] is not None}
    if scored:
        total_w = sum(FIELD_WEIGHT[f] for f in scored)
        score = sum(STATE_SCORE[fields[f]] * FIELD_WEIGHT[f] for f in scored) / total_w
    else:
        score = 1.0

    # Accessibility gate: a timed asset with no French transcript, or any asset
    # with no French alt text, leaves French users without access to content
    # English users can reach. Flagged separately from the weighted score so it
    # cannot be averaged away by well-formed captions and credits.
    a11y = []
    if fields["alt"] in ("missing", "untranslated"):
        a11y.append(f"alt text {fields['alt']}")
    if kind in TIMED_MEDIA and fields["transcript"] in ("missing", "untranslated"):
        a11y.append(f"transcript {fields['transcript']}")

    return {
        "asset_id": asset.get("asset_id"),
        "kind": kind,
        "fields": fields,
        "score": round(score, 4),
        "a11y_failures": a11y,
        "accessible": not a11y,
    }


def evaluate_media(documents):
    """Corpus-level media metadata equivalence."""
    assets, by_kind = [], {}
    for doc in documents:
        for asset in doc.get("media", []):
            r = check_asset(asset)
            r["doc_id"] = doc["doc_id"]
            r["desk"] = doc.get("meta", {}).get("desk")
            assets.append(r)
            by_kind.setdefault(r["kind"], []).append(r)

    if not assets:
        return {"n_assets": 0, "score": 1.0, "assets": [], "by_kind": {},
                "field_counts": {}, "n_inaccessible": 0, "a11y_rate": 1.0}

    field_counts = {}
    for r in assets:
        for f, state in r["fields"].items():
            if state == "n/a":
                continue
            field_counts.setdefault(f, {}).setdefault(state, 0)
            field_counts[f][state] += 1

    inaccessible = [r for r in assets if not r["accessible"]]

    return {
        "n_assets": len(assets),
        "score": round(sum(r["score"] for r in assets) / len(assets), 4),
        "a11y_rate": round(1 - len(inaccessible) / len(assets), 4),
        "n_inaccessible": len(inaccessible),
        "assets": sorted(assets, key=lambda r: (r["accessible"], r["score"])),
        "by_kind": {k: {"n": len(v),
                        "score": round(sum(x["score"] for x in v) / len(v), 4),
                        "inaccessible": sum(1 for x in v if not x["accessible"])}
                    for k, v in sorted(by_kind.items())},
        "field_counts": field_counts,
    }


# ---- editorial metadata --------------------------------------------------

def check_editorial(doc):
    """Headline, deck, tag, and SEO-description equivalence for one document.

    Tags matter more than they look: they drive archive retrieval, related-story
    modules, and topic pages. A French story tagged with fewer concepts than its
    English counterpart is less discoverable in French — the same divergence the
    retrieval metrics measure, arriving through the CMS rather than the model.
    """
    ed = doc.get("editorial")
    if not ed:
        return None

    en_tags = [t.strip().lower() for t in ed.get("en_tags") or []]
    fr_tags = [t.strip().lower() for t in ed.get("fr_tags") or []]
    # Tags are translated, so they cannot be compared by string equality —
    # only the *count* of concepts carried is comparable across languages.
    tag_ratio = (len(fr_tags) / len(en_tags)) if en_tags else 1.0
    tag_state = ("ok" if tag_ratio >= 0.99 else
                 "reduced" if tag_ratio >= 0.5 else "sparse")

    seo_state = _classify(ed.get("en_seo"), ed.get("fr_seo"))
    title_state = _classify(doc["en"]["title"], doc["fr"]["title"])

    score = (min(tag_ratio, 1.0) * 0.4
             + (STATE_SCORE[seo_state] if STATE_SCORE[seo_state] is not None else 1.0) * 0.35
             + (STATE_SCORE[title_state] if STATE_SCORE[title_state] is not None else 1.0) * 0.25)

    return {
        "doc_id": doc["doc_id"],
        "desk": doc.get("meta", {}).get("desk"),
        "tag_state": tag_state,
        "n_tags_en": len(en_tags),
        "n_tags_fr": len(fr_tags),
        "tags_dropped": max(0, len(en_tags) - len(fr_tags)),
        "seo_state": seo_state,
        "title_state": title_state,
        "score": round(score, 4),
    }


def evaluate_editorial(documents):
    rows = [r for r in (check_editorial(d) for d in documents) if r]
    if not rows:
        return {"n_docs": 0, "score": 1.0, "rows": []}
    return {
        "n_docs": len(rows),
        "score": round(sum(r["score"] for r in rows) / len(rows), 4),
        "n_missing_seo": sum(1 for r in rows if r["seo_state"] == "missing"),
        "total_tags_dropped": sum(r["tags_dropped"] for r in rows),
        "rows": sorted(rows, key=lambda r: r["score"]),
    }
