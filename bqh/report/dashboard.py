"""Self-contained HTML quality-equivalence dashboard.

No external assets: the file opens anywhere, including offline in an interview
room. Palette is the validated two-series pair (blue/orange) from the data-viz
reference palette; both modes pass all six checks at all-pairs strictness.
"""
import html
import json
import re

from .i18n import STRINGS

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


DOC_HEAD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bilingual Quality Harness</title>
<style>
:root {
  color-scheme: light;
  --surface-0:#f4f4f2; --surface-1:#fcfcfb; --border:#e2e1dd;
  --text-primary:#0b0b0b; --text-secondary:#52514e; --text-muted:#7a7975;
  --series-en:#2a78d6; --series-fr:#eb6834;
  --track:#e6e5e1; --good:#0ca30c; --critical:#d92020;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --surface-0:#111110; --surface-1:#1a1a19; --border:#333331;
    --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#8f8e86;
    --series-en:#3987e5; --series-fr:#d95926;
    --track:#2e2e2b; --good:#3ab53a; --critical:#f06a6a;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface-0:#111110; --surface-1:#1a1a19; --border:#333331;
  --text-primary:#ffffff; --text-secondary:#c3c2b7; --text-muted:#8f8e86;
  --series-en:#3987e5; --series-fr:#d95926;
  --track:#2e2e2b; --good:#3ab53a; --critical:#f06a6a;
}
*{box-sizing:border-box}
body{margin:0;background:var(--surface-0);color:var(--text-primary);
  font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:40px 24px 72px}
header{margin-bottom:28px}
.eyebrow{font-size:12px;letter-spacing:.09em;text-transform:uppercase;
  color:var(--text-muted);font-weight:600}
h1{font-size:29px;line-height:1.2;margin:8px 0 6px;letter-spacing:-.02em}
.sub{color:var(--text-secondary);max-width:66ch;margin:0}
.meta{margin-top:12px;font-size:13px;color:var(--text-muted)}
.meta code{background:var(--surface-1);border:1px solid var(--border);
  border-radius:4px;padding:1px 6px;font-size:12px}
.card{background:var(--surface-1);border:1px solid var(--border);
  border-radius:10px;padding:22px;margin:20px 0}
.hero{display:flex;gap:34px;align-items:flex-start;flex-wrap:wrap}
.hero-fig{font-size:60px;line-height:1;font-weight:650;letter-spacing:-.03em}
.hero-fig.warn{color:var(--critical)}
.hero-lab{font-size:12px;text-transform:uppercase;letter-spacing:.08em;
  color:var(--text-muted);font-weight:600;margin-top:8px}
.hero-txt{flex:1;min-width:280px;color:var(--text-secondary)}
.hero-txt strong{color:var(--text-primary)}
h2{font-size:17px;margin:34px 0 4px;letter-spacing:-.01em}
.h2sub{color:var(--text-muted);font-size:13px;margin:0 0 12px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--border);
  vertical-align:middle}
thead th{font-size:11px;text-transform:uppercase;letter-spacing:.07em;
  color:var(--text-muted);font-weight:600;border-bottom:1px solid var(--border)}
tbody tr:last-child td,tbody tr:last-child th{border-bottom:none}
.dim th{font-weight:500;width:33%}
.dim-name{display:block;color:var(--text-primary)}
.dim-desc{display:block;font-size:11.5px;color:var(--text-muted);margin-top:1px}
td.plot{width:31%;padding:9px 14px}
td.plot svg{width:100%;height:22px;overflow:visible}
.track{stroke:var(--track);stroke-width:2;vector-effect:non-scaling-stroke}
.gapline{stroke:var(--text-muted);stroke-width:2;opacity:.45;
  vector-effect:non-scaling-stroke}
.mark-en{fill:var(--series-en);stroke:var(--surface-1);stroke-width:1.5;
  vector-effect:non-scaling-stroke}
.mark-fr{fill:var(--series-fr);stroke:var(--surface-1);stroke-width:1.5;
  vector-effect:non-scaling-stroke}
.num{text-align:right;font-variant-numeric:tabular-nums;width:8%;
  font-feature-settings:"tnum"}
td.en{color:var(--series-en);font-weight:600}
td.fr{color:var(--series-fr);font-weight:600}
td.gap{color:var(--text-secondary)}
.pill{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;
  border-radius:99px;border:1px solid}
.pill.ok{color:var(--good);border-color:color-mix(in srgb,var(--good) 40%,transparent)}
.pill.divergent{color:var(--critical);
  border-color:color-mix(in srgb,var(--critical) 45%,transparent)}
.legend{display:flex;gap:18px;font-size:12.5px;color:var(--text-secondary);
  margin:0 0 14px;align-items:center}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;
  margin-right:6px;vertical-align:-1px}
.covbar{display:inline-block;width:88px;height:7px;background:var(--track);
  border-radius:99px;overflow:hidden;vertical-align:middle;margin-right:8px}
.covbar span{display:block;height:100%;background:var(--series-fr);
  border-radius:99px}
.covnum{font-variant-numeric:tabular-nums;color:var(--text-secondary);font-size:12px}
.term{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.qid{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;
  color:var(--text-secondary)}
.tag{display:inline-block;font-size:11px;padding:1.5px 7px;border-radius:4px;
  background:color-mix(in srgb,var(--series-fr) 15%,transparent);
  color:var(--text-primary);margin-right:4px;
  border:1px solid color-mix(in srgb,var(--series-fr) 30%,transparent)}
.note,.qs{color:var(--text-muted);font-size:12px}
.qtext{color:var(--text-secondary);font-size:12px}
.scroll{overflow-x:auto}
.sev-row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}
.sev-tile{flex:1;min-width:104px;padding:12px 14px;border-radius:8px;
  border:1px solid var(--border);background:var(--surface-0)}
.sev-tile.r0{border-color:color-mix(in srgb,var(--critical) 55%,transparent);
  background:color-mix(in srgb,var(--critical) 9%,var(--surface-0))}
.sev-tile.r1{border-color:color-mix(in srgb,var(--critical) 38%,transparent)}
.sev-n{font-size:26px;font-weight:650;line-height:1;letter-spacing:-.02em}
.sev-tile.r0 .sev-n{color:var(--critical)}
.sev-l{font-size:11px;color:var(--text-muted);margin-top:5px;
  text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.case{border:1px solid var(--border);border-left:3px solid var(--text-muted);
  border-radius:7px;padding:13px 15px;margin-top:11px;background:var(--surface-0)}
.case.r0{border-left-color:var(--critical)}
.case.r1{border-left-color:var(--critical);opacity:.96}
.case-h{display:flex;gap:9px;align-items:baseline;margin-bottom:3px}
.case-tier{font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:.06em}
.case.r0 .case-tier{color:var(--critical)}
.case-why{font-size:12.5px;color:var(--text-secondary);margin-bottom:9px}
.case-ab{display:flex;gap:9px;margin-top:5px;font-size:12.5px;line-height:1.45}
.ab-l{flex:0 0 22px;font-size:10px;font-weight:700;color:var(--series-en);
  padding-top:2px;letter-spacing:.05em}
.ab-l.fr{color:var(--series-fr)}
.ab-t{color:var(--text-secondary)}
.note-p{font-size:13px;color:var(--text-secondary);margin:12px 0 4px;max-width:78ch}
.drift-to{color:var(--series-fr)}
.chip{display:inline-block;font-size:10.5px;padding:1px 6px;border-radius:4px;
  margin:1px 3px 1px 0;border:1px solid var(--border);color:var(--text-secondary)}
.chip[data-s="missing"]{color:var(--critical);
  border-color:color-mix(in srgb,var(--critical) 45%,transparent)}
.chip[data-s="untranslated"]{color:var(--critical);
  border-color:color-mix(in srgb,var(--critical) 45%,transparent)}
.chip[data-s="truncated"]{color:var(--series-fr);
  border-color:color-mix(in srgb,var(--series-fr) 45%,transparent)}
tr.bad td{background:color-mix(in srgb,var(--critical) 6%,transparent)}
.segrow{display:flex;gap:22px;flex-wrap:wrap}
.segcol{flex:1;min-width:250px}
.segcol h3{font-size:12px;text-transform:uppercase;letter-spacing:.07em;
  color:var(--text-muted);margin:0 0 6px}
.thin{font-size:10px;color:var(--text-muted);border:1px solid var(--border);
  border-radius:3px;padding:0 4px}
footer{margin-top:40px;padding-top:18px;border-top:1px solid var(--border);
  font-size:12px;color:var(--text-muted)}
@media (max-width:720px){
  td.plot{display:none} .dim th{width:auto}
  .hero-fig{font-size:46px}
}
.hrow{display:flex;justify-content:space-between;align-items:flex-start;gap:16px}
.langtog{font:inherit;font-size:12px;font-weight:600;letter-spacing:.03em;
  padding:5px 13px;border-radius:99px;cursor:pointer;background:var(--surface-1);
  color:var(--text-primary);border:1px solid var(--border);white-space:nowrap}
.langtog:hover{border-color:var(--series-en);color:var(--series-en)}
.langtog:focus-visible{outline:2px solid var(--series-en);outline-offset:2px}
[data-lang][hidden]{display:none}
</style></head><body>
"""

DOC_TAIL = """
<script>
(function () {
  // Both language versions are already in the DOM; the toggle only shows one.
  // No data is recomputed, so the two views cannot disagree about the numbers.
  var views = document.querySelectorAll('[data-lang]');
  function show(lang) {
    Array.prototype.forEach.call(views, function (v) {
      v.hidden = v.getAttribute('data-lang') !== lang;
    });
    document.documentElement.lang = lang;
    try { localStorage.setItem('bqh-lang', lang); } catch (e) {}
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.langtog');
    if (b) { show(b.getAttribute('data-switch')); }
  });
  // An explicit ?lang= wins, so a link from a French page lands on French even
  // when the reader's browser is set to English.
  var asked = (location.search.match(/[?&]lang=(en|fr)(?:&|$)/) || [])[1];
  var saved = asked || null;
  if (!saved) {
    try { saved = localStorage.getItem('bqh-lang'); } catch (e) {}
  }
  // Fall back to the browser language so a francophone reader opening the file
  // cold lands on French without touching the control.
  if (!saved) {
    saved = (navigator.language || 'en').toLowerCase().indexOf('fr') === 0 ? 'fr' : 'en';
  }
  show(saved);
})();
</script>
</body></html>
"""


SEV_ORDER = ["no_answer", "wrong_fact", "wrong_docs", "omission", "register"]
SEV_LABEL = {"no_answer": "No answer returned", "wrong_fact": "Unsupported fact",
             "wrong_docs": "Different sources", "omission": "Reduced content",
             "register": "Register"}
SEV_RANK = {"no_answer": 0, "wrong_fact": 1, "wrong_docs": 2, "omission": 3,
            "register": 4}


def localize_reason(text, T):
    """Render a severity reason in the report's language.

    severity.classify() writes its reasons in English, and results.json keeps
    them that way. The French view re-renders the known patterns rather than
    showing English prose under a French heading; anything unrecognised is
    shown as-is, escaped.
    """
    W = T["why"]
    fixed = {"French declined to answer; English answered": "fr_refused",
             "English declined to answer; French answered": "en_refused",
             "French omits content present in English": "omits"}
    if text in fixed:
        return W[fixed[text]]
    m = re.fullmatch(r"French asserts unsupported figure\(s\): (.*)", text)
    if m:
        figs = re.sub(r"(?<=\d)\.(?=\d)", T["decimal"], m.group(1))
        return W["figures"].format(x=esc(figs))
    m = re.fullmatch(r"French omits content present in English: (.*)", text)
    if m:
        return W["omits_x"].format(x=esc(m.group(1)))
    m = re.fullmatch(r"Gold-document retrieval diverged \((.*)\)", text)
    if m:
        parts = []
        for part in m.group(1).split("; "):
            side, _, ids = part.partition(": ")
            key = {"EN-only": "en_only", "FR-only": "fr_only"}.get(side)
            parts.append(W[key].format(x=esc(ids)) if key else esc(part))
        return W["diverged"].format(x="; ".join(parts))
    m = re.fullmatch(r"Register: '(.*)' → '(.*)'", text)
    if m:
        return W["register"].format(x=esc(m.group(1)), y=esc(m.group(2)))
    return esc(text)


def esc(x):
    return html.escape(str(x), quote=True)


def num(x, spec, T):
    """A number as the reader's language writes it: 0,959 in French, not 0.959.

    The harness flags anglo decimals in French copy as a localization defect,
    so its own report does not get to ship them.
    """
    return format(x, spec).replace(".", T["decimal"])


def pct(x, T):
    return f"{x * 100:.0f}{T['pct']}"


def word(x, T):
    """An enumerated value the metrics emit in English, in the report's language."""
    return esc(T["vocab"].get(x, x))


def field_state(field, state, T):
    """'alt: missing' / 'texte de remplacement : manquant', agreeing in gender."""
    label, fem = T["fields"].get(field, (field, False))
    forms = T["states"].get(state)
    shown = forms[1 if fem else 0] if forms else state
    sep = "&nbsp;: " if T["decimal"] == "," else ": "
    return f"{esc(label)}{sep}{esc(shown)}"


def a11y_failure(text, T):
    """'alt text missing' -> 'texte de remplacement manquant'."""
    for field in ("alt text", "transcript", "caption", "credit"):
        if text.startswith(field + " "):
            state = text[len(field) + 1:]
            label, fem = T["fields"].get(field, (field, False))
            forms = T["states"].get(state)
            return esc(f"{label} {forms[1 if fem else 0] if forms else state}")
    return esc(text)


def segment_name(x, T):
    return esc(T["segments"].get(x, x))


def retriever_label(x, T):
    if x.startswith("embedding"):
        return esc(T["vocab"]["embedding"] + x[len("embedding"):])
    return word(x, T)


def _bar_row(name, vals, T):
    label, desc = T["dims"].get(name, (name, ""))
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
             aria-label="{T['vocab']['aria_plot'].format(en=num(en, '.3f', T), fr=num(fr, '.3f', T), gap=num(gap, '+.3f', T))}">
          <line x1="0" y1="11" x2="100" y2="11" class="track"/>
          <line x1="{lo*100:.2f}" y1="11" x2="{hi*100:.2f}" y2="11" class="gapline"/>
          <circle cx="{en*100:.2f}" cy="11" r="4.2" class="mark-en"/>
          <circle cx="{fr*100:.2f}" cy="11" r="4.2" class="mark-fr"/>
        </svg>
      </td>
      <td class="num en">{num(en, '.3f', T)}</td>
      <td class="num fr">{num(fr, '.3f', T)}</td>
      <td class="num gap">{num(gap, '+.3f', T)}</td>
      <td class="status"><span class="pill {status}">{T['eq_ok'] if status=='ok' else T['eq_bad']}</span></td>
    </tr>"""


def render_lang(summary, rows, lang):
    """Render the page body for one language. Both are emitted into one file."""
    T = STRINGS[lang]
    DIM = T["dims"]
    SEVL = T["sev"]
    dims = summary["dimensions"]
    idx = summary["equivalence_index"]
    failing = summary["failing_dimensions"]
    worst = max(dims.items(), key=lambda kv: abs(kv[1]["gap"]))

    dim_rows = "".join(_bar_row(n, v, T) for n, v in dims.items())

    lex = "".join(f"""
      <tr><td class="term">{esc(w['term'])}</td>
          <td class="cov"><span class="covbar"><span style="width:{w['coverage']*100:.0f}%"></span></span>
              <span class="covnum">{num(w['coverage'], '.2f', T)}</span></td>
          <td class="qs">{esc(', '.join(w['queries']))}</td></tr>"""
        for w in summary["weak_lexicon"][:10])

    div = ""
    for d in summary["divergent_queries"]:
        issues = []
        if d["en_p1"] != d["fr_p1"]:
            issues.append(T["vocab"]["retrieval miss"])
        if d["fr_ground"] < 1.0:
            issues.append(T["vocab"]["fabricated figure"])
        if d["fr_register"] < 1.0:
            issues.append(T["vocab"]["register"])
        if d["fr_coverage"] < 1.0:
            issues.append(T["vocab"]["omission"])
        div += f"""
      <tr><td class="qid">{esc(d['query_id'])}</td>
          <td>{esc(d['divergence_class'] or '—')}</td>
          <td class="issues">{''.join(f'<span class="tag">{esc(i)}</span>' for i in issues)}</td>
          <td class="note">{esc(d['note'] or '')}</td></tr>"""

    # Per-query detail for the appendix table
    # Sort divergent queries first. Sorted by query id, the 54 of 78 rows that
    # are legitimately all-1.00 come first and the reader scrolls through a
    # wall of identical values before reaching anything that varies — the
    # findings end up buried by the clean majority.
    _sev_rank = {"no_answer": 0, "wrong_fact": 1, "wrong_docs": 2,
                 "omission": 3, "register": 4, "none": 5}
    detail_rows = sorted(rows, key=lambda r: (_sev_rank.get(r.get("severity"), 5),
                                              r["query_id"]))

    def _cell(v, good=1.0):
        """Recede perfect scores so the values that differ carry the eye."""
        cls = "num" if v < good else "num pass"
        return f'<td class="{cls}">{num(v, ".2f", T)}</td>'

    DETAIL_CLEAN_SHOWN = 12
    clean_total = sum(1 for r in detail_rows if r.get("severity", "none") == "none")
    clean_shown = 0
    detail = ""
    for r in detail_rows:
        if r.get("severity", "none") == "none":
            clean_shown += 1
            if clean_shown > DETAIL_CLEAN_SHOWN:
                continue
        en, fr = r["langs"]["en"], r["langs"]["fr"]
        tier = r.get("severity", "none")
        badge = ("" if tier == "none" else
                 f'<span class="rowtag r{_sev_rank.get(tier,5)}">'
                 f'{esc(SEVL.get(tier, tier))}</span>')
        detail += f"""
      <tr class="{'divrow' if tier != 'none' else 'cleanrow'}">
          <td class="qid">{esc(r['query_id'])}{badge}</td>
          <td class="qtext">{esc(r['langs']['en']['answer'][:90])}…</td>
          {_cell(en['p_at_1'])}{_cell(fr['p_at_1'])}
          {_cell(en['numeric_grounding_gold']['score'])}
          {_cell(fr['numeric_grounding_gold']['score'])}
          {_cell(fr['fluency']['register']['score'])}
          {_cell(fr['coverage_vs_en']['score'])}</tr>"""

    detail_note = T["detail_withheld"].format(
        hidden=max(0, clean_total - DETAIL_CLEAN_SHOWN), total=len(detail_rows)
    ) if clean_total > DETAIL_CLEAN_SHOWN else ""
    # Never truncate silently: a capped table with no note reads as "this is
    # everything", which is the same failure the harness flags elsewhere.
    detail_note_html = (f'<p class="note-p">{detail_note}</p>'
                        if detail_note else "")

    sv = summary.get("severity")
    parity = pct(sv['parity_rate'], T) if sv else "—"
    ndim = len(dims)
    if sv and sv["n_unserved"]:
        headline = (f"<strong>{sv['n_unserved']} "
                    f"{T['unserved_one'] if sv['n_unserved']==1 else T['unserved_many']}"
                    f"</strong> {T['unserved_tail']}")
    elif sv and sv["cases"]:
        headline = (f"<strong>{len(sv['cases'])} {T['diverged_mid']} {summary['n_queries']}</strong> "
                    f"{T['diverged_tail']}")
    else:
        headline = f"<strong>{T['no_div']}</strong>"

    sevblock = ""
    if sv and sv["cases"]:
        tiles = "".join(
            f'<div class="sev-tile r{SEV_RANK.get(t,5)}">'
            f'<div class="sev-n">{sv["counts"][t]}</div>'
            f'<div class="sev-l">{esc(SEVL.get(t,t))}</div></div>'
            for t in SEV_ORDER if sv["counts"].get(t))
        cards = ""
        for c in sv["cases"][:4]:
            cards += f"""
      <div class="case r{SEV_RANK.get(c['tier'],5)}">
        <div class="case-h"><span class="case-tier">{esc(SEVL.get(c['tier'],c['tier']))}</span>
          <span class="qid">{esc(c['query_id'])}</span></div>
        <div class="case-why">{localize_reason(c['reasons'][0], T) if c['reasons'] else ''}</div>
        <div class="case-ab"><span class="ab-l">EN</span>
          <span class="ab-t">{esc(c['en_answer'][:200])}</span></div>
        <div class="case-ab"><span class="ab-l fr">FR</span>
          <span class="ab-t">{esc(c['fr_answer'][:200])}</span></div>
      </div>"""
        sevblock = f"""<h2>{T['h_experience']}</h2>
<p class="h2sub">{T['sub_experience']}</p>
<div class="card">
  <div class="sev-row">{tiles}</div>
  {cards}
</div>"""

    # --- MDR / QFCR ---
    dr = summary.get("drift") or {}
    qf = summary.get("false_correction") or {}
    n_docs = summary.get("n_docs", "?")
    other = "fr" if lang == "en" else "en"
    footer = T["footer"].format(thr=num(summary.get('threshold', 0.08), '.2f', T))
    mdr_note = T["mdr_note"].format(sub=dr.get("substituted", 0),
                                    scored=dr.get("scored_opportunities", 0),
                                    reph=dr.get("rephrased", 0))
    qfcr_note = T["qfcr_note"].format(alt=qf.get("forms_altered", 0),
                                      present=qf.get("valid_forms_present", 0))
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
            f"<td class=\"term drift-to\">{word(e['replaced_with'], T)}</td>"
            f"<td class=\"num\">{e['n']}</td>"
            f"<td class=\"qid\">{esc(e['where'])}</td></tr>"
            for e in qf.get("events", [])[:8])
        # Built outside the template: a plain string nested in the f-string
        # below is not interpolated, and shipped its placeholders verbatim.
        drift_table = (
            f'<table><thead><tr><th>{T["th_qform"]}</th><th>{T["th_replaced"]}</th>'
            f'<th class="num">{T["th_n"]}</th><th>{T["th_where"]}</th></tr></thead>'
            f'<tbody>{ev}</tbody></table>' if ev else '')
        qfcr_table = (
            f'<table><thead><tr><th>{T["th_valid"]}</th><th>{T["th_changed"]}</th>'
            f'<th class="num">{T["th_n"]}</th><th>{T["th_probe"]}</th></tr></thead>'
            f'<tbody>{qev}</tbody></table>' if qev else '')
        driftblock = f"""<h2>{T['h_drift']}</h2>
<p class="h2sub">{T['sub_drift']}</p>
<div class="card">
  <div class="sev-row">
    <div class="sev-tile {'r1' if dr.get('mdr',0) > 0.2 else ''}">
      <div class="sev-n">{pct(dr.get('mdr',0), T)}</div>
      <div class="sev-l">{T['mdr_lab']}</div></div>
    <div class="sev-tile {'r0' if qf.get('qfcr',0) > 0.5 else ''}">
      <div class="sev-n">{pct(qf.get('qfcr',0), T)}</div>
      <div class="sev-l">{T['qfcr_lab']}</div></div>
    <div class="sev-tile"><div class="sev-n">{dr.get('rephrased',0)}</div>
      <div class="sev-l">{T['reph_lab']}</div></div>
  </div>
  <p class="note-p">{mdr_note}</p>
  {drift_table}
  <p class="note-p" style="margin-top:16px">{qfcr_note}</p>
  {qfcr_table}
</div>"""

    # --- media metadata ---
    md = summary.get("media") or {}
    media_note = T["media_note"].format(bad=md.get("n_inaccessible", 0),
                                        total=md.get("n_assets", 0)) if md else ""
    media_ok_note = (T["media_ok"].format(n=md["n_assets"] - md["n_inaccessible"])
                     if md.get("n_assets") else "")
    mediablock = ""
    if md.get("n_assets"):
        kinds = "".join(
            f'<div class="sev-tile {"r0" if v["inaccessible"] else ""}">'
            f'<div class="sev-n">{v["n"]}</div>'
            f'<div class="sev-l">{word(k, T)} · {v["inaccessible"]}</div></div>'
            for k, v in md["by_kind"].items())
        arows = "".join(
            f"<tr class=\"{'bad' if not a['accessible'] else ''}\">"
            f"<td class=\"term\">{esc(a['asset_id'])}</td>"
            f"<td>{word(a['kind'], T)}</td>"
            f"<td>{''.join(f'<span class=chip data-s={esc(v)}>{field_state(f, v, T)}</span>' for f, v in a['fields'].items() if v != 'n/a')}</td>"
            f"<td class=\"num\">{num(a['score'], '.2f', T)}</td>"
            f"<td class=\"note\">{', '.join(a11y_failure(x, T) for x in a['a11y_failures'])}</td></tr>"
            for a in md["assets"] if not a["accessible"])
        mediablock = f"""<h2>{T['h_media']}</h2>
<p class="h2sub">{T['sub_media']}</p>
<div class="card">
  <div class="sev-row">
    <div class="sev-tile {'r0' if md['a11y_rate'] < 0.9 else ''}">
      <div class="sev-n">{pct(md['a11y_rate'], T)}</div>
      <div class="sev-l">{T['a11y_lab']}</div></div>
    {kinds}
  </div>
  <p class="note-p">{media_note} {media_ok_note}</p>
  <div class="scroll"><table>
    <thead><tr><th>{T['th_asset']}</th><th>{T['th_kind']}</th><th>{T['th_fields']}</th>
      <th class="num">{T['th_score']}</th><th>{T['th_a11y']}</th></tr></thead>
    <tbody>{arows}</tbody></table></div>
</div>"""

    # --- editorial metadata ---
    ed = summary.get("editorial") or {}
    _ed_ok = sum(1 for r in (ed.get("rows") or []) if r["score"] == 1.0)
    ed_ok_note = T["ed_ok"].format(n=_ed_ok) if ed.get("n_docs") else ""
    edblock = ""
    if ed.get("n_docs"):
        erows = "".join(
            f"<tr><td class=\"qid\">{esc(r['doc_id'])}</td>"
            f"<td>{segment_name(r['desk'] or '', T)}</td>"
            f"<td class=\"num\">{r['n_tags_fr']}/{r['n_tags_en']}</td>"
            f"<td><span class=chip data-s={esc(r['seo_state'])}>{esc(T['states'].get(r['seo_state'], (r['seo_state'],)*2)[1])}</span></td>"
            f"<td class=\"num\">{num(r['score'], '.2f', T)}</td></tr>"
            for r in ed["rows"] if r["score"] < 1.0)
        edblock = f"""<h2>{T['h_ed']}</h2>
<p class="h2sub">{T['sub_ed']}</p>
<div class="card">
  <div class="sev-row">
    <div class="sev-tile"><div class="sev-n">{ed['total_tags_dropped']}</div>
      <div class="sev-l">{T['tags_lab']}</div></div>
    <div class="sev-tile {'r1' if ed['n_missing_seo'] else ''}">
      <div class="sev-n">{ed['n_missing_seo']}</div>
      <div class="sev-l">{T['seo_lab']}</div></div>
    <div class="sev-tile"><div class="sev-n">{num(ed['score'], '.2f', T)}</div>
      <div class="sev-l">{T['edpar_lab']}</div></div>
  </div>
  <p class="note-p">{ed_ok_note}</p>
  <div class="scroll"><table>
    <thead><tr><th>{T['th_doc']}</th><th>{T['th_desk']}</th><th class="num">{T['th_tags']}</th>
      <th>{T['th_seo']}</th><th class="num">{T['th_score']}</th></tr></thead>
    <tbody>{erows}</tbody></table></div>
</div>"""

    # --- terminology + answerability ---
    tm = (summary.get("terminology") or {}).get("fr") or {}
    an = summary.get("answerability") or {}
    rp = summary.get("readability_parity") or {}
    langblock = ""
    if tm.get("n_concepts") or an.get("per_language"):
        trows = "".join(
            f"<tr class=\"{'divrow' if c['consistency'] < 1.0 else ''}\">"
            f"<td>{esc(c['concept'].replace('_',' '))}</td>"
            f"<td class=\"term\">{esc(c['canonical'][:46])}</td>"
            f"<td class=\"num\">{pct(c['consistency'], T)}</td>"
            f"<td class=\"num\">{c['mentions']}</td>"
            f"<td class=\"note\">{esc(', '.join(v['pattern'][:26] for v in c['variants'][1:3]))}</td></tr>"
            for c in tm.get("concepts", []))
        asym = "".join(
            f"<tr class=\"divrow\"><td class=\"qid\">{esc(a['query_id'])}</td>"
            f"<td>{esc(a['served'].upper())}</td><td>{esc(a['denied'].upper())}</td></tr>"
            for a in an.get("asymmetric", [])[:8])
        fr_ans = an.get("per_language", {}).get("fr", {})
        en_ans = an.get("per_language", {}).get("en", {})
        asym_table = (
            f'<div class="scroll"><table><thead><tr><th>{T["th_query"]}</th>'
            f'<th>{T["vocab"]["served"]}</th><th>{T["vocab"]["denied"]}</th></tr></thead>'
            f'<tbody>{asym}</tbody></table></div>' if asym else '')
        langblock = f"""<h2>{T['h_lang']}</h2>
<p class="h2sub">{T['sub_lang']}</p>
<div class="card">
  <div class="sev-row">
    <div class="sev-tile {'r1' if tm.get('score',1) < 0.9 else ''}">
      <div class="sev-n">{pct(tm.get('score',1), T)}</div>
      <div class="sev-l">{T['term_lab']}</div></div>
    <div class="sev-tile"><div class="sev-n">{pct(fr_ans.get('answer_rate',1), T)}</div>
      <div class="sev-l">{T['answer_lab']}</div></div>
    <div class="sev-tile {'r0' if an.get('n_asymmetric') else ''}">
      <div class="sev-n">{an.get('n_asymmetric',0)}</div>
      <div class="sev-l">{T['asym_lab']}</div></div>
  </div>
  <p class="note-p">{T['term_note']}</p>
  <div class="scroll"><table>
    <thead><tr><th>{T['th_concept']}</th><th>{T['th_canonical']}</th>
      <th class="num">{T['th_uses']}</th><th class="num">{T['th_mentions']}</th>
      <th>{T['th_replaced']}</th></tr></thead>
    <tbody>{trows}</tbody></table></div>
  <p class="note-p" style="margin-top:16px">{T['answer_note']}
   EN {pct(en_ans.get('answer_rate',1), T)} · FR {pct(fr_ans.get('answer_rate',1), T)}.
   {word(rp.get('verdict',''), T)} (FR/EN {num(rp.get('ratio',1), '.2f', T)}).</p>
  {asym_table}
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
                f"<tr><td>{segment_name(x['segment'], T)}{' <span class=thin>'+esc(T['thin'])+'</span>' if x['thin'] else ''}</td>"
                f"<td class=\"num\">{x['n']}</td>"
                f"<td class=\"num\">{x['divergent']}</td>"
                f"<td class=\"num\">{x['unserved']}</td>"
                f"<td class=\"num gap\">{num(x['worst_gap'], '+.3f', T)}</td></tr>"
                for x in items)
            tabs += f"""<div class="segcol"><h3>{esc(T.get("by_"+axis, axis))}</h3><table>
              <thead><tr><th>{word(axis, T)}</th><th class="num">{T['th_n']}</th>
                <th class="num">{T['th_div']}</th><th class="num">{T['th_unsvd']}</th>
                <th class="num">{T['th_gap']}</th></tr></thead>
              <tbody>{srows}</tbody></table></div>"""
        if tabs:
            segblock = f"""<h2>{T['h_seg']}</h2>
<p class="h2sub">{T['sub_seg']}</p>
<div class="card"><div class="segrow">{tabs}</div></div>"""

    mode = summary.get("mode", "offline")
    worst_label = DIM.get(worst[0], (worst[0], ""))[0]

    return f"""<div class="wrap" data-lang="{lang}" {'hidden' if lang != 'en' else ''}>
<header>
  <div class="hrow">
    <div class="eyebrow">{T['eyebrow']}</div>
    <button type="button" class="langtog" data-switch="{other}"
            aria-label="{T['other_lang']}">{T['other_lang']}</button>
  </div>
  <h1>{T['title']}</h1>
  <p class="sub">{T['intro']}</p>
  <div class="meta">{summary['n_queries']} {T['meta_docs']} · {n_docs} {T['meta_docs2']} ·
   {T['meta_cf']}<br>
   {T['meta_mode']} <code>{word(mode, T)}</code> · {T['meta_retr']} <code>{retriever_label(summary.get('retriever','bm25'), T)}</code></div>
</header>

<div class="card hero">
  <div>
    <div class="hero-fig {'warn' if sv and sv['parity_rate'] < 0.9 else ''}">{parity}</div>
    <div class="hero-lab">{T['parity_lab']}</div>
  </div>
  <div class="hero-txt">
    <p style="margin-top:0">{headline}</p>
    <p style="margin-bottom:0">{T['eq_index']} {num(idx, '.3f', T)} · {ndim}
    {T['th_dim'].lower()}s. {T['hero_tail']}</p>
  </div>
</div>

{sevblock}

<h2>{T['h_dims']}</h2>
<p class="h2sub">{T['sub_dims']}</p>
<div class="card">
  <div class="legend">
    <span><i style="background:var(--series-en)"></i>{T['legend_en']}</span>
    <span><i style="background:var(--series-fr)"></i>{T['legend_fr']}</span>
    <span style="color:var(--text-muted)">{T['legend_scale']}</span>
  </div>
  <div class="scroll"><table>
    <thead><tr><th>{T['th_dim']}</th><th>0 → 1</th><th class="num">EN</th>
      <th class="num">FR</th><th class="num">{T['th_gap']}</th><th>{T['th_status']}</th></tr></thead>
    <tbody>{dim_rows}</tbody>
  </table></div>
</div>

<h2>{T['h_lex']}</h2>
<p class="h2sub">{T['sub_lex']}</p>
<div class="card"><div class="scroll"><table>
  <thead><tr><th>{T['th_term']}</th><th>{T['th_cov']}</th><th>{T['th_affected']}</th></tr></thead>
  <tbody>{lex}</tbody>
</table></div></div>

{driftblock}

{mediablock}

{edblock}

{langblock}

{segblock}

<h2>{T['h_detail']}</h2>
<p class="h2sub">{T['sub_detail']}</p>
<div class="card"><div class="scroll"><table>
  <thead><tr><th>{T['th_query']}</th><th>{T['th_en_ans']}</th><th class="num">EN P@1</th>
    <th class="num">FR P@1</th><th class="num">EN {T['vocab']['col_grnd']}</th><th class="num">FR {T['vocab']['col_grnd']}</th>
    <th class="num">FR {T['vocab']['col_reg']}</th><th class="num">FR {T['vocab']['col_cov']}</th></tr></thead>
  <tbody>{detail}</tbody>
</table></div>
  {detail_note_html}</div>

<footer>{footer}</footer>
</div>"""


def render(summary, rows):
    """Full document containing both language versions and a toggle.

    Both languages ship in one self-contained file rather than two: a reviewer
    who receives the report can switch language without needing a second file,
    and the two views are guaranteed to describe the same run. The toggle is
    plain DOM show/hide — no data is re-computed, so the numbers cannot drift
    between the two.
    """
    body = render_lang(summary, rows, "en") + render_lang(summary, rows, "fr")
    return (DOC_HEAD + body + DOC_TAIL)
