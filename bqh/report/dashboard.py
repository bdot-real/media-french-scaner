"""Self-contained HTML quality-equivalence dashboard.

No external assets: the file opens anywhere, including offline in an interview
room. Palette is the validated two-series pair (blue/orange) from the data-viz
reference palette; both modes pass all six checks at all-pairs strictness.
"""
import html
import json

DIM_LABELS = {
    "retrieval_p_at_1": ("Retrieval precision@1", "Top result is a gold document"),
    "retrieval_recall": ("Retrieval recall@3", "Gold documents found in top 3"),
    "retrieval_ndcg": ("Retrieval nDCG@3", "Rank quality of gold documents"),
    "grounding_numeric": ("Grounding — fabrication", "Figures absent from the source document"),
    "grounding_in_context": ("Grounding — in retrieved context", "Figures unsupported by what retrieval returned"),
    "grounding_entailment": ("Grounding — lexical entailment", "Content words traceable to source"),
    "content_coverage": ("Content coverage vs EN", "Does FR carry the same facts as EN"),
    "fluency_register": ("Canadian French register", "Metropolitan forms and anglicisms"),
    "fluency_overall": ("Fluency (composite)", "Register and readability combined"),
}


SEV_ORDER = ["no_answer", "wrong_fact", "wrong_docs", "omission", "register"]
SEV_LABEL = {"no_answer": "No answer returned", "wrong_fact": "Unsupported fact",
             "wrong_docs": "Different sources", "omission": "Reduced content",
             "register": "Register"}
SEV_RANK = {"no_answer": 0, "wrong_fact": 1, "wrong_docs": 2, "omission": 3,
            "register": 4}


def esc(x):
    return html.escape(str(x), quote=True)


def _bar_row(name, vals):
    label, desc = DIM_LABELS.get(name, (name, ""))
    en, fr, gap = vals["en"], vals["fr"], vals["gap"]
    status = "ok" if vals["equivalent"] else "divergent"
    lo, hi = min(en, fr), max(en, fr)
    return f"""
    <tr class="dim {status}">
      <th scope="row">
        <span class="dim-name">{esc(label)}</span>
        <span class="dim-desc">{esc(desc)}</span>
      </th>
      <td class="plot">
        <svg viewBox="0 0 100 22" preserveAspectRatio="none" role="img"
             aria-label="English {en:.3f}, French {fr:.3f}, gap {gap:+.3f}">
          <line x1="0" y1="11" x2="100" y2="11" class="track"/>
          <line x1="{lo*100:.2f}" y1="11" x2="{hi*100:.2f}" y2="11" class="gapline"/>
          <circle cx="{en*100:.2f}" cy="11" r="4.2" class="mark-en"/>
          <circle cx="{fr*100:.2f}" cy="11" r="4.2" class="mark-fr"/>
        </svg>
      </td>
      <td class="num en">{en:.3f}</td>
      <td class="num fr">{fr:.3f}</td>
      <td class="num gap">{gap:+.3f}</td>
      <td class="status"><span class="pill {status}">{'equivalent' if status=='ok' else 'divergent'}</span></td>
    </tr>"""


def render(summary, rows):
    dims = summary["dimensions"]
    idx = summary["equivalence_index"]
    failing = summary["failing_dimensions"]
    worst = max(dims.items(), key=lambda kv: abs(kv[1]["gap"]))

    dim_rows = "".join(_bar_row(n, v) for n, v in dims.items())

    lex = "".join(f"""
      <tr><td class="term">{esc(w['term'])}</td>
          <td class="cov"><span class="covbar"><span style="width:{w['coverage']*100:.0f}%"></span></span>
              <span class="covnum">{w['coverage']:.2f}</span></td>
          <td class="qs">{esc(', '.join(w['queries']))}</td></tr>"""
        for w in summary["weak_lexicon"][:10])

    div = ""
    for d in summary["divergent_queries"]:
        issues = []
        if d["en_p1"] != d["fr_p1"]:
            issues.append("retrieval miss")
        if d["fr_ground"] < 1.0:
            issues.append("fabricated figure")
        if d["fr_register"] < 1.0:
            issues.append("register")
        if d["fr_coverage"] < 1.0:
            issues.append("omission")
        div += f"""
      <tr><td class="qid">{esc(d['query_id'])}</td>
          <td>{esc(d['divergence_class'] or '—')}</td>
          <td class="issues">{''.join(f'<span class="tag">{esc(i)}</span>' for i in issues)}</td>
          <td class="note">{esc(d['note'] or '')}</td></tr>"""

    # Per-query detail for the appendix table
    detail = ""
    for r in rows:
        en, fr = r["langs"]["en"], r["langs"]["fr"]
        detail += f"""
      <tr><td class="qid">{esc(r['query_id'])}</td>
          <td class="qtext">{esc(r['langs']['en']['answer'][:90])}…</td>
          <td class="num">{en['p_at_1']:.2f}</td><td class="num">{fr['p_at_1']:.2f}</td>
          <td class="num">{en['numeric_grounding_gold']['score']:.2f}</td>
          <td class="num">{fr['numeric_grounding_gold']['score']:.2f}</td>
          <td class="num">{fr['fluency']['register']['score']:.2f}</td>
          <td class="num">{fr['coverage_vs_en']['score']:.2f}</td></tr>"""

    sv = summary.get("severity")
    parity = f"{sv['parity_rate']*100:.0f}%" if sv else "—"
    ndim = len(dims)
    if sv and sv["n_unserved"]:
        headline = (f"<strong>{sv['n_unserved']} quer"
                    f"{'y' if sv['n_unserved']==1 else 'ies'} where the French "
                    f"reader was not served</strong> — either no answer was "
                    f"returned, or the answer asserted a fact the source does "
                    f"not support. Both are mandate failures, not quality deltas.")
    elif sv and sv["cases"]:
        headline = (f"<strong>{len(sv['cases'])} of {summary['n_queries']} queries "
                    f"diverged</strong> between English and French, though none "
                    f"left the French reader unserved.")
    else:
        headline = "<strong>No divergence detected</strong> across the query set."

    sevblock = ""
    if sv and sv["cases"]:
        tiles = "".join(
            f'<div class="sev-tile r{SEV_RANK.get(t,5)}">'
            f'<div class="sev-n">{sv["counts"][t]}</div>'
            f'<div class="sev-l">{esc(SEV_LABEL.get(t,t))}</div></div>'
            for t in SEV_ORDER if sv["counts"].get(t))
        cards = ""
        for c in sv["cases"][:4]:
            cards += f"""
      <div class="case r{SEV_RANK.get(c['tier'],5)}">
        <div class="case-h"><span class="case-tier">{esc(SEV_LABEL.get(c['tier'],c['tier']))}</span>
          <span class="qid">{esc(c['query_id'])}</span></div>
        <div class="case-why">{esc(c['reasons'][0] if c['reasons'] else '')}</div>
        <div class="case-ab"><span class="ab-l">EN</span>
          <span class="ab-t">{esc(c['en_answer'][:200])}</span></div>
        <div class="case-ab"><span class="ab-l fr">FR</span>
          <span class="ab-t">{esc(c['fr_answer'][:200])}</span></div>
      </div>"""
        sevblock = f"""<h2>What the French reader experienced</h2>
<p class="h2sub">Every query classified by its worst outcome, ordered by reader impact.</p>
<div class="card">
  <div class="sev-row">{tiles}</div>
  {cards}
</div>"""

    # --- MDR / QFCR ---
    dr = summary.get("drift") or {}
    qf = summary.get("false_correction") or {}
    driftblock = ""
    if dr.get("scored_opportunities") or qf.get("valid_forms_present"):
        ev = "".join(
            f"<tr><td class=\"term\">{esc(e['quebec'])}</td>"
            f"<td class=\"term drift-to\">{esc(e['france'])}</td>"
            f"<td class=\"num\">{e['n']}</td>"
            f"<td class=\"qid\">{esc(e['where'])}</td></tr>"
            for e in dr.get("events", [])[:8])
        qev = "".join(
            f"<tr><td class=\"term\">{esc(e['quebec'])}</td>"
            f"<td class=\"term drift-to\">{esc(e['replaced_with'])}</td>"
            f"<td class=\"num\">{e['n']}</td>"
            f"<td class=\"qid\">{esc(e['where'])}</td></tr>"
            for e in qf.get("events", [])[:8])
        driftblock = f"""<h2>Metropolitan drift and false correction</h2>
<p class="h2sub">Two Canadian-specific metrics generic French evaluation does not provide.</p>
<div class="card">
  <div class="sev-row">
    <div class="sev-tile {'r1' if dr.get('mdr',0) > 0.2 else ''}">
      <div class="sev-n">{dr.get('mdr',0)*100:.0f}%</div>
      <div class="sev-l">Metropolitan drift rate</div></div>
    <div class="sev-tile {'r0' if qf.get('qfcr',0) > 0.5 else ''}">
      <div class="sev-n">{qf.get('qfcr',0)*100:.0f}%</div>
      <div class="sev-l">Quebec false correction rate</div></div>
    <div class="sev-tile"><div class="sev-n">{dr.get('rephrased',0)}</div>
      <div class="sev-l">Rephrased — not drift</div></div>
  </div>
  <p class="note-p"><strong>MDR</strong> counts substitutions only:
  {dr.get('substituted',0)} of {dr.get('scored_opportunities',0)} scored
  opportunities. {dr.get('rephrased',0)} cases where the model rephrased around
  the term are excluded from the denominator entirely — verbosity is not drift,
  and scoring it either way would bias the rate.</p>
  {'<table><thead><tr><th>Quebec form</th><th>Replaced with</th><th class="num">n</th><th>Where</th></tr></thead><tbody>' + ev + '</tbody></table>' if ev else ''}
  <p class="note-p" style="margin-top:16px"><strong>QFCR</strong> sends already-correct
  Canadian French through a naive &ldquo;corrige ce texte&rdquo; prompt, so any
  alteration is a false correction by construction:
  {qf.get('forms_altered',0)} of {qf.get('valid_forms_present',0)} valid Quebec
  forms were altered. A pipeline can generate perfect Canadian French and still
  ship metropolitan copy because the proofreading step rewrote it.</p>
  {'<table><thead><tr><th>Valid Quebec form</th><th>Proofreader changed it to</th><th class="num">n</th><th>Probe</th></tr></thead><tbody>' + qev + '</tbody></table>' if qev else ''}
</div>"""

    # --- media metadata ---
    md = summary.get("media") or {}
    mediablock = ""
    if md.get("n_assets"):
        kinds = "".join(
            f'<div class="sev-tile {"r0" if v["inaccessible"] else ""}">'
            f'<div class="sev-n">{v["n"]}</div>'
            f'<div class="sev-l">{esc(k)} · {v["inaccessible"]} failing</div></div>'
            for k, v in md["by_kind"].items())
        arows = "".join(
            f"<tr class=\"{'bad' if not a['accessible'] else ''}\">"
            f"<td class=\"term\">{esc(a['asset_id'])}</td>"
            f"<td>{esc(a['kind'])}</td>"
            f"<td>{''.join(f'<span class=chip data-s={esc(v)}>{esc(f)}: {esc(v)}</span>' for f, v in a['fields'].items() if v != 'n/a')}</td>"
            f"<td class=\"num\">{a['score']:.2f}</td>"
            f"<td class=\"note\">{esc(', '.join(a['a11y_failures']))}</td></tr>"
            for a in md["assets"])
        mediablock = f"""<h2>Media metadata — images, video, audio</h2>
<p class="h2sub">Alt text, captions, credits, and transcripts. The asset is reused
 across both language sites; the descriptors often are not.</p>
<div class="card">
  <div class="sev-row">
    <div class="sev-tile {'r0' if md['a11y_rate'] < 0.9 else ''}">
      <div class="sev-n">{md['a11y_rate']*100:.0f}%</div>
      <div class="sev-l">Accessible in French</div></div>
    {kinds}
  </div>
  <p class="note-p">{md['n_inaccessible']} of {md['n_assets']} assets leave French
  users without access to content English users can reach — missing or
  untranslated alt text, or a missing transcript on timed media. Untranslated is
  worse than missing: it passes a null check in a CMS audit.</p>
  <div class="scroll"><table>
    <thead><tr><th>Asset</th><th>Kind</th><th>Field states</th>
      <th class="num">Score</th><th>Accessibility</th></tr></thead>
    <tbody>{arows}</tbody></table></div>
</div>"""

    # --- editorial metadata ---
    ed = summary.get("editorial") or {}
    edblock = ""
    if ed.get("n_docs"):
        erows = "".join(
            f"<tr><td class=\"qid\">{esc(r['doc_id'])}</td>"
            f"<td>{esc(r['desk'] or '')}</td>"
            f"<td class=\"num\">{r['n_tags_fr']}/{r['n_tags_en']}</td>"
            f"<td><span class=chip data-s={esc(r['seo_state'])}>{esc(r['seo_state'])}</span></td>"
            f"<td class=\"num\">{r['score']:.2f}</td></tr>"
            for r in ed["rows"])
        edblock = f"""<h2>Editorial metadata</h2>
<p class="h2sub">Tags and SEO descriptions drive archive retrieval and topic pages —
 a French story tagged with fewer concepts is less discoverable in French.</p>
<div class="card">
  <div class="sev-row">
    <div class="sev-tile"><div class="sev-n">{ed['total_tags_dropped']}</div>
      <div class="sev-l">Tags dropped in FR</div></div>
    <div class="sev-tile {'r1' if ed['n_missing_seo'] else ''}">
      <div class="sev-n">{ed['n_missing_seo']}</div>
      <div class="sev-l">Missing FR SEO</div></div>
    <div class="sev-tile"><div class="sev-n">{ed['score']:.2f}</div>
      <div class="sev-l">Editorial parity</div></div>
  </div>
  <div class="scroll"><table>
    <thead><tr><th>Document</th><th>Desk</th><th class="num">FR/EN tags</th>
      <th>SEO description</th><th class="num">Score</th></tr></thead>
    <tbody>{erows}</tbody></table></div>
</div>"""

    # --- segmentation ---
    segs = summary.get("segments") or {}
    segblock = ""
    if segs:
        tabs = ""
        for axis in ("desk", "region", "topic"):
            items = [x for x in segs.get(axis, []) if x["worst_gap"] > 0.001][:8]
            if not items:
                continue
            srows = "".join(
                f"<tr><td>{esc(x['segment'])}{' <span class=thin>thin</span>' if x['thin'] else ''}</td>"
                f"<td class=\"num\">{x['n']}</td>"
                f"<td class=\"num\">{x['divergent']}</td>"
                f"<td class=\"num\">{x['unserved']}</td>"
                f"<td class=\"num gap\">{x['worst_gap']:+.3f}</td></tr>"
                for x in items)
            tabs += f"""<div class="segcol"><h3>By {esc(axis)}</h3><table>
              <thead><tr><th>{esc(axis).title()}</th><th class="num">n</th>
                <th class="num">Div.</th><th class="num">Unsvd</th>
                <th class="num">Gap</th></tr></thead>
              <tbody>{srows}</tbody></table></div>"""
        if tabs:
            segblock = f"""<h2>Where divergence concentrates</h2>
<p class="h2sub">An aggregate says whether the pipeline is failing; segmentation says
 where, which is what routes it to an owner.</p>
<div class="card"><div class="segrow">{tabs}</div></div>"""

    mode = summary.get("mode", "offline")
    worst_label = DIM_LABELS.get(worst[0], (worst[0], ""))[0]

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bilingual Quality Harness</title>
<style>
:root {{
  color-scheme: light;
  --surface-0:#f4f4f2; --surface-1:#fcfcfb; --border:#e2e1dd;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#7a7975;
  --series-en:#2a78d6; --series-fr:#eb6834;
  --track:#e6e5e1; --good:#0ca30c; --critical:#d92020;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --surface-0:#111110; --surface-1:#1a1a19; --border:#333331;
    --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#8f8e86;
    --series-en:#3987e5; --series-fr:#d95926;
    --track:#2e2e2b; --good:#3ab53a; --critical:#f06a6a;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --surface-0:#111110; --surface-1:#1a1a19; --border:#333331;
  --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#8f8e86;
  --series-en:#3987e5; --series-fr:#d95926;
  --track:#2e2e2b; --good:#3ab53a; --critical:#f06a6a;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--surface-0);color:var(--text-primary);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}}
.wrap{{max-width:1080px;margin:0 auto;padding:40px 24px 72px}}
header{{margin-bottom:28px}}
.eyebrow{{font-size:12px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--text-muted);font-weight:600}}
h1{{font-size:29px;line-height:1.2;margin:8px 0 6px;letter-spacing:-.02em}}
.sub{{color:var(--text-secondary);max-width:66ch;margin:0}}
.meta{{margin-top:12px;font-size:13px;color:var(--text-muted)}}
.meta code{{background:var(--surface-1);border:1px solid var(--border);
  border-radius:4px;padding:1px 6px;font-size:12px}}
.card{{background:var(--surface-1);border:1px solid var(--border);
  border-radius:10px;padding:22px;margin:20px 0}}
.hero{{display:flex;gap:34px;align-items:flex-start;flex-wrap:wrap}}
.hero-fig{{font-size:60px;line-height:1;font-weight:650;letter-spacing:-.03em}}
.hero-fig.warn{{color:var(--critical)}}
.hero-lab{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--text-muted);font-weight:600;margin-top:8px}}
.hero-txt{{flex:1;min-width:280px;color:var(--text-secondary)}}
.hero-txt strong{{color:var(--text-primary)}}
h2{{font-size:17px;margin:34px 0 4px;letter-spacing:-.01em}}
.h2sub{{color:var(--text-muted);font-size:13px;margin:0 0 12px}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th,td{{text-align:left;padding:9px 10px;border-bottom:1px solid var(--border);
  vertical-align:middle}}
thead th{{font-size:11px;text-transform:uppercase;letter-spacing:.07em;
  color:var(--text-muted);font-weight:600;border-bottom:1px solid var(--border)}}
tbody tr:last-child td,tbody tr:last-child th{{border-bottom:none}}
.dim th{{font-weight:500;width:33%}}
.dim-name{{display:block;color:var(--text-primary)}}
.dim-desc{{display:block;font-size:11.5px;color:var(--text-muted);margin-top:1px}}
td.plot{{width:31%;padding:9px 14px}}
td.plot svg{{width:100%;height:22px;overflow:visible}}
.track{{stroke:var(--track);stroke-width:2;vector-effect:non-scaling-stroke}}
.gapline{{stroke:var(--text-muted);stroke-width:2;opacity:.45;
  vector-effect:non-scaling-stroke}}
.mark-en{{fill:var(--series-en);stroke:var(--surface-1);stroke-width:1.5;
  vector-effect:non-scaling-stroke}}
.mark-fr{{fill:var(--series-fr);stroke:var(--surface-1);stroke-width:1.5;
  vector-effect:non-scaling-stroke}}
.num{{text-align:right;font-variant-numeric:tabular-nums;width:8%;
  font-feature-settings:"tnum"}}
td.en{{color:var(--series-en);font-weight:600}}
td.fr{{color:var(--series-fr);font-weight:600}}
td.gap{{color:var(--text-secondary)}}
.pill{{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;
  border-radius:99px;border:1px solid}}
.pill.ok{{color:var(--good);border-color:color-mix(in srgb,var(--good) 40%,transparent)}}
.pill.divergent{{color:var(--critical);
  border-color:color-mix(in srgb,var(--critical) 45%,transparent)}}
.legend{{display:flex;gap:18px;font-size:12.5px;color:var(--text-secondary);
  margin:0 0 14px;align-items:center}}
.legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;
  margin-right:6px;vertical-align:-1px}}
.covbar{{display:inline-block;width:88px;height:7px;background:var(--track);
  border-radius:99px;overflow:hidden;vertical-align:middle;margin-right:8px}}
.covbar span{{display:block;height:100%;background:var(--series-fr);
  border-radius:99px}}
.covnum{{font-variant-numeric:tabular-nums;color:var(--text-secondary);font-size:12px}}
.term{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}}
.qid{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;
  color:var(--text-secondary)}}
.tag{{display:inline-block;font-size:11px;padding:1.5px 7px;border-radius:4px;
  background:color-mix(in srgb,var(--series-fr) 15%,transparent);
  color:var(--text-primary);margin-right:4px;
  border:1px solid color-mix(in srgb,var(--series-fr) 30%,transparent)}}
.note,.qs{{color:var(--text-muted);font-size:12px}}
.qtext{{color:var(--text-secondary);font-size:12px}}
.scroll{{overflow-x:auto}}
.sev-row{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}}
.sev-tile{{flex:1;min-width:104px;padding:12px 14px;border-radius:8px;
  border:1px solid var(--border);background:var(--surface-0)}}
.sev-tile.r0{{border-color:color-mix(in srgb,var(--critical) 55%,transparent);
  background:color-mix(in srgb,var(--critical) 9%,var(--surface-0))}}
.sev-tile.r1{{border-color:color-mix(in srgb,var(--critical) 38%,transparent)}}
.sev-n{{font-size:26px;font-weight:650;line-height:1;letter-spacing:-.02em}}
.sev-tile.r0 .sev-n{{color:var(--critical)}}
.sev-l{{font-size:11px;color:var(--text-muted);margin-top:5px;
  text-transform:uppercase;letter-spacing:.06em;font-weight:600}}
.case{{border:1px solid var(--border);border-left:3px solid var(--text-muted);
  border-radius:7px;padding:13px 15px;margin-top:11px;background:var(--surface-0)}}
.case.r0{{border-left-color:var(--critical)}}
.case.r1{{border-left-color:var(--critical);opacity:.96}}
.case-h{{display:flex;gap:9px;align-items:baseline;margin-bottom:3px}}
.case-tier{{font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:.06em}}
.case.r0 .case-tier{{color:var(--critical)}}
.case-why{{font-size:12.5px;color:var(--text-secondary);margin-bottom:9px}}
.case-ab{{display:flex;gap:9px;margin-top:5px;font-size:12.5px;line-height:1.45}}
.ab-l{{flex:0 0 22px;font-size:10px;font-weight:700;color:var(--series-en);
  padding-top:2px;letter-spacing:.05em}}
.ab-l.fr{{color:var(--series-fr)}}
.ab-t{{color:var(--text-secondary)}}
.note-p{{font-size:13px;color:var(--text-secondary);margin:12px 0 4px;max-width:78ch}}
.drift-to{{color:var(--series-fr)}}
.chip{{display:inline-block;font-size:10.5px;padding:1px 6px;border-radius:4px;
  margin:1px 3px 1px 0;border:1px solid var(--border);color:var(--text-secondary)}}
.chip[data-s="missing"]{{color:var(--critical);
  border-color:color-mix(in srgb,var(--critical) 45%,transparent)}}
.chip[data-s="untranslated"]{{color:var(--critical);
  border-color:color-mix(in srgb,var(--critical) 45%,transparent)}}
.chip[data-s="truncated"]{{color:var(--series-fr);
  border-color:color-mix(in srgb,var(--series-fr) 45%,transparent)}}
tr.bad td{{background:color-mix(in srgb,var(--critical) 6%,transparent)}}
.segrow{{display:flex;gap:22px;flex-wrap:wrap}}
.segcol{{flex:1;min-width:250px}}
.segcol h3{{font-size:12px;text-transform:uppercase;letter-spacing:.07em;
  color:var(--text-muted);margin:0 0 6px}}
.thin{{font-size:10px;color:var(--text-muted);border:1px solid var(--border);
  border-radius:3px;padding:0 4px}}
footer{{margin-top:40px;padding-top:18px;border-top:1px solid var(--border);
  font-size:12px;color:var(--text-muted)}}
@media (max-width:720px){{
  td.plot{{display:none}} .dim th{{width:auto}}
  .hero-fig{{font-size:46px}}
}}
</style></head><body>
<div class="wrap">
<header>
  <div class="eyebrow">Bilingual Quality Harness</div>
  <h1>EN / FR output equivalence for a journalistic RAG workflow</h1>
  <p class="sub">Measures whether an AI content pipeline performs <em>equivalently</em>
  in English and Canadian French — not whether it performs adequately in each.
  The unit of analysis is the gap between the two, because that gap is what a
  bilingual public-service mandate actually commits to.</p>
  <div class="meta">{summary['n_queries']} parallel queries · 12 parallel documents ·
   Canadian French (Radio-Canada conventions)<br>
   mode <code>{esc(mode)}</code> · retrieval <code>{esc(summary.get('retriever','bm25'))}</code></div>
</header>

<div class="card hero">
  <div>
    <div class="hero-fig {'warn' if sv and sv['parity_rate'] < 0.9 else ''}">{parity}</div>
    <div class="hero-lab">Service parity</div>
  </div>
  <div class="hero-txt">
    <p style="margin-top:0">{headline}</p>
    <p style="margin-bottom:0">Equivalence index {idx:.3f} across
    {ndim} dimensions. A mean over all queries understates this: bilingual
    public service is not an average commitment, so the harness leads with the
    worst outcome a reader actually experienced.</p>
  </div>
</div>

{sevblock}

<h2>Quality dimensions</h2>
<p class="h2sub">Each row is one metric measured independently in both languages.
 The connecting line is the equivalence gap.</p>
<div class="card">
  <div class="legend">
    <span><i style="background:var(--series-en)"></i>English</span>
    <span><i style="background:var(--series-fr)"></i>Canadian French</span>
    <span style="color:var(--text-muted)">— scale 0 to 1, higher is better</span>
  </div>
  <div class="scroll"><table>
    <thead><tr><th>Dimension</th><th>0 → 1</th><th class="num">EN</th>
      <th class="num">FR</th><th class="num">Gap</th><th>Status</th></tr></thead>
    <tbody>{dim_rows}</tbody>
  </table></div>
</div>

<h2>Root cause — lexicon coverage</h2>
<p class="h2sub">Canadian French administrative and regional vocabulary that the
 retriever represents weakly. This is what converts a red number into a fix.</p>
<div class="card"><div class="scroll"><table>
  <thead><tr><th>Term (stemmed)</th><th>Model coverage</th><th>Affected queries</th></tr></thead>
  <tbody>{lex}</tbody>
</table></div></div>

<h2>Divergent queries</h2>
<p class="h2sub">Every query where the French output differs materially from the English.</p>
<div class="card"><div class="scroll"><table>
  <thead><tr><th>Query</th><th>Class</th><th>Detected issues</th><th>Note</th></tr></thead>
  <tbody>{div}</tbody>
</table></div></div>

{driftblock}

{mediablock}

{edblock}

{segblock}

<h2>Per-query detail</h2>
<p class="h2sub">Full result table — the accessible view of every number above.</p>
<div class="card"><div class="scroll"><table>
  <thead><tr><th>Query</th><th>EN answer</th><th class="num">EN P@1</th>
    <th class="num">FR P@1</th><th class="num">EN grnd</th><th class="num">FR grnd</th>
    <th class="num">FR reg</th><th class="num">FR cov</th></tr></thead>
  <tbody>{detail}</tbody>
</table></div></div>

<footer>
Equivalence threshold {summary.get('threshold', 0.08):.2f} on any dimension.
Grounding is scored against gold context (fabrication) and against retrieved
context (in-context support) separately, so a retrieval miss is not misreported
as a hallucination. Offline mode uses a frozen corpus for determinism;
<code>--live</code> generates answers through the Claude API instead.
</footer>
</div></body></html>"""
