"""Build the companion site into site/dist/.

    python3 site/build.py            # writes site/dist
    python3 site/build.py --out DIR

Stdlib only. Every figure on the site is read from results.json and
results_embed.json, never typed into the copy, so the site cannot disagree
with the report it links to. The test count is read by running the suites.

English is served at /, French at /fr/. Both reports are published under
/report/ exactly as the harness wrote them.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from content import REPO, SITE, STRINGS  # noqa: E402

SUITES = ["test_harness", "test_register", "test_drift", "test_i18n", "test_newdims",
          "test_site_i18n"]

# The comparison table: the dimensions where the two backends can differ, then
# the generation-side ones that show they do not. Labels live in content.py,
# where the French is tested.
FINDING_DIMS = ["retrieval_p_at_1", "retrieval_recall", "retrieval_ndcg",
                "grounding_in_context", "content_coverage", "fluency_register",
                "localization"]


# ── numbers, the way each language writes them ────────────────────────────────

def num(x, spec, lang):
    s = format(x, spec)
    return s.replace(".", ",") if lang == "fr" else s


def pct(x, lang):
    return f"{x * 100:.0f}" + ("&nbsp;%" if lang == "fr" else "%")


def signed(x, lang):
    # A true minus sign, so a negative gap reads as one at a glance.
    return num(x, "+.3f", lang).replace("-", "−")


# ── facts ────────────────────────────────────────────────────────────────────

def count_checks():
    """(checks, suites), read by running them. A failing suite stops the build."""
    total = suites = 0
    for s in SUITES:
        path = ROOT / "tests" / f"{s}.py"
        if not path.exists():
            continue
        out = subprocess.run([sys.executable, str(path)], capture_output=True, text=True,
                             cwd=ROOT).stdout
        m = re.search(r"(\d+) passed, (\d+) failed", out)
        if not m:
            raise SystemExit(f"{s}: could not read a result")
        if int(m.group(2)):
            raise SystemExit(f"{s}: {m.group(2)} failing — not publishing a site that says otherwise")
        total += int(m.group(1))
        suites += 1
    return total, suites


def facts(bm25, embed, lang, checks):
    s = bm25["summary"]
    sv, fc, dr = s["severity"], s["false_correction"], s["drift"]
    ed, md, tm = s["editorial"], s["media"], s["terminology"]
    return {
        "parity": pct(sv["parity_rate"], lang),
        "parity_embed": pct(embed["summary"]["severity"]["parity_rate"], lang),
        "unserved": sv["n_unserved"],
        "qfcr": pct(fc["qfcr"], lang), "qfcr_alt": fc["forms_altered"],
        "qfcr_n": fc["valid_forms_present"],
        "cov": signed(s["dimensions"]["content_coverage"]["gap"], lang),
        "media": pct(md["a11y_rate"], lang),
        "mdr": pct(dr["mdr"], lang), "mdr_sub": dr["substituted"],
        "mdr_n": dr["scored_opportunities"], "mdr_reph": dr["rephrased"],
        "term_fr": num(tm["fr"]["score"], ".3f", lang),
        "term_en": num(tm["en"]["score"], ".3f", lang),
        "tags": ed["total_tags_dropped"], "seo": ed["n_missing_seo"],
        "docs": s.get("n_docs", len(json.loads(
            (ROOT / "bqh/corpus/documents.json").read_text())["documents"])),
        "queries": s["n_queries"], "checks": checks[0], "suites": checks[1],
    }


# ── page ─────────────────────────────────────────────────────────────────────

def fill(text, f):
    return text.format(**f) if "{" in text else text


def attr(text):
    """Strings in content.py are HTML; attributes need them as plain text."""
    return html.escape(html.unescape(re.sub(r"<[^>]+>", "", text)), quote=True)


def img(lang, name, alt, cls="shot"):
    return (f'<img class="{cls}" src="/img/{lang}/{name}.png" alt="{attr(alt)}" '
            f'decoding="async">')


def head(T, lang, path, title=None):
    other = "fr" if lang == "en" else "en"
    here = f"{SITE}{path}"
    alt_path = {"en": "/", "fr": "/fr/"}
    t = attr(title or T["title"])
    d = attr(T["description"])
    return f"""<!doctype html>
<html lang="{'fr-CA' if lang == 'fr' else 'en-CA'}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="canonical" href="{here}">
<link rel="alternate" hreflang="en-CA" href="{SITE}{alt_path['en']}">
<link rel="alternate" hreflang="fr-CA" href="{SITE}{alt_path['fr']}">
<link rel="alternate" hreflang="x-default" href="{SITE}/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="French Drift">
<meta property="og:locale" content="{'fr_CA' if lang == 'fr' else 'en_CA'}">
<meta property="og:locale:alternate" content="{'en_CA' if lang == 'fr' else 'fr_CA'}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{here}">
<meta property="og:image" content="{SITE}/img/{lang}/overview.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{SITE}/img/{lang}/overview.png">
<meta name="color-scheme" content="light dark">
<link rel="stylesheet" href="/style.css">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
</head>"""


def chrome(T, lang):
    other = "fr" if lang == "en" else "en"
    home = "/" if lang == "en" else "/fr/"
    other_home = "/fr/" if lang == "en" else "/"
    links = "".join(f'<a href="{home}{h}">{html.escape(n)}</a>' for h, n in T["nav"])
    return f"""<a class="skip" href="#main">{T['skip']}</a>
<header class="chrome">
  <div class="wrap chrome-in">
    <a class="brand" href="{home}"><span class="brand-mark" aria-hidden="true">EN<i>/</i>FR</span>
      <span class="brand-name">French Drift</span></a>
    <nav aria-label="{'Sections' if lang == 'en' else 'Sections'}">{links}</nav>
    <div class="chrome-act">
      <a class="lang" href="{other_home}" hreflang="{other}" lang="{other}">{T['other_name']}</a>
      <a class="btn btn-sm" href="/report/?lang={lang}">{T['nav_report']}</a>
    </div>
  </div>
</header>"""


def footer(T, lang, f):
    return f"""<footer class="foot">
  <div class="wrap">
    <p class="disclaimer">{fill(T['disclaimer'], f)}</p>
    <div class="foot-row">
      <span class="brand-name">French Drift</span>
      <span>{T['brand_sub']}</span>
      <a href="{REPO}">{T['nav_repo']}</a>
      <a href="{REPO}/blob/main/LICENSE">{T['footer_license']}</a>
      <a href="{'/fr/' if lang == 'en' else '/'}" lang="{'fr' if lang == 'en' else 'en'}">{T['other_name']}</a>
    </div>
    <p class="self">{T['footer_self']}</p>
  </div>
</footer>"""


def finding_table(T, lang, bm25, embed):
    rows = ""
    for d in FINDING_DIMS:
        a = bm25["summary"]["dimensions"][d]["gap"]
        b = embed["summary"]["dimensions"][d]["gap"]
        flipped = (a > 0) != (b > 0) and abs(b) > 0.0005
        same = abs(a - b) < 0.0005
        cls = "flip" if flipped else ("same" if same else "")
        rows += (f'<tr class="{cls}"><th scope="row">{T['dim_labels'][d]}</th>'
                 f'<td class="num">{signed(a, lang)}</td>'
                 f'<td class="num">{signed(b, lang)}</td></tr>')
    return f"""<div class="tablewrap"><table class="cmp">
  <thead><tr><th scope="col">{T['th_dim']}</th><th scope="col" class="num">{T['th_bm25']}</th>
    <th scope="col" class="num">{T['th_embed']}</th></tr></thead>
  <tbody>{rows}</tbody></table></div>"""


def qfcr_table(T, lang, bm25):
    note = T["removed_note"]
    rows = ""
    for e in bm25["summary"]["false_correction"]["events"][:10]:
        to = e["replaced_with"]
        gone = to.startswith("(")
        rows += (f'<tr><td class="term ok">{html.escape(e["quebec"])}</td>'
                 f'<td class="arrow" aria-hidden="true">→</td>'
                 f'<td class="term {"gone" if gone else "bad"}"'
                 f'{"" if gone else " lang=\"fr\""}>{html.escape(note if gone else to)}</td></tr>')
    return f"""<div class="tablewrap"><table class="swap" lang="fr">
  <thead><tr><th scope="col">{T['qfcr_th_from']}</th><th aria-hidden="true"></th>
    <th scope="col">{T['qfcr_th_to']}</th></tr></thead>
  <tbody>{rows}</tbody></table></div>"""


def page(lang, bm25, embed, checks):
    T = STRINGS[lang]
    f = facts(bm25, embed, lang, checks)
    path = "/" if lang == "en" else "/fr/"

    stats = "".join(f"""<div class="stat {cls}"><div class="stat-n">{f[k]}</div>
      <div class="stat-l">{T['stat_' + k]}</div><p>{T['stat_' + k + '_d']}</p></div>"""
                    for k, cls in [("parity", "warn"), ("qfcr", "bad"), ("cov", ""),
                                   ("media", "")])

    shots = "".join(f"""<figure class="shot-card">
      <a class="shot-frame" href="/img/{lang}/{name}.png">{img(lang, name, h + '. ' + p)}</a>
      <figcaption><strong>{h}</strong> {p}</figcaption></figure>"""
                    for name, h, p in T["shots"])

    tiers = "".join(f'<li class="t{i}"><strong>{h}</strong><span>{p}</span></li>'
                    for i, (h, p) in enumerate(T["tiers"]))
    dims = "".join(f'<div class="dim"><h4>{h}</h4><p>{fill(p, f)}</p></div>'
                   for h, p in T["dims"])

    return f"""{head(T, lang, path)}
<body>
{chrome(T, lang)}
<main id="main" tabindex="-1">

<section class="hero">
  <div class="wrap hero-grid">
    <div class="hero-copy">
      <span class="kicker">{T['kicker']}</span>
      <h1>{T['h1']}</h1>
      <p class="lede">{T['lede']}</p>
      <div class="ctas">
        <a class="btn" href="/report/?lang={lang}">{T['cta_report']}</a>
        <a class="btn btn-ghost" href="{REPO}">{T['cta_repo']} ↗</a>
      </div>
    </div>
    <figure class="hero-shot">
      <div class="shot-frame">{img(lang, 'overview', fill(T['hero_alt'], f), 'shot eager')}</div>
      <figcaption>{T['hero_cap']}</figcaption>
    </figure>
  </div>
  <div class="wrap stats">{stats}</div>
</section>

<section id="finding" class="band">
  <div class="wrap">
    <span class="kicker">{T['k_finding']}</span>
    <h2>{T['h_finding']}</h2>
    <div class="split">
      <div>
        <p>{T['p_finding_1']}</p>
        {finding_table(T, lang, bm25, embed)}
        <p>{T['p_finding_2']}</p>
      </div>
      <aside class="callout">
        <h3>{T['callout_h']}</h3>
        <p>{T['callout_p']}</p>
        <figure>
          <div class="shot-frame">{img(lang, 'embedding-overview', T['shot_embed_alt'])}</div>
          <figcaption>{T['shot_embed_cap']} <a href="/report/embedding?lang={lang}">{T['embed_link']} →</a></figcaption>
        </figure>
      </aside>
    </div>
  </div>
</section>

<section id="metrics" class="band alt">
  <div class="wrap">
    <span class="kicker">{T['k_metrics']}</span>
    <h2>{T['h_metrics']}</h2>
    <div class="metric-grid">
      <div class="metric">
        <div class="metric-n">{f['mdr']}</div>
        <h3>{T['mdr_h']}</h3>
        <p>{fill(T['mdr_p'], f)}</p>
      </div>
      <div class="metric bad">
        <div class="metric-n">{f['qfcr']}</div>
        <h3>{T['qfcr_h']}</h3>
        <p>{fill(T['qfcr_p'], f)}</p>
        {qfcr_table(T, lang, bm25)}
      </div>
    </div>
    <p class="close">{T['metrics_close']}</p>
    <figure class="wide-shot">
      <div class="shot-frame">{img(lang, 'drift', T['shot_drift_alt'])}</div>
      <figcaption>{T['shot_drift_cap']}</figcaption>
    </figure>
  </div>
</section>

<section id="report" class="band">
  <div class="wrap">
    <span class="kicker">{T['k_report']}</span>
    <h2>{T['h_report']}</h2>
    <p class="intro">{T['p_report']}</p>
    <div class="gallery">{shots}</div>
    <p class="ctas center"><a class="btn" href="/report/?lang={lang}">{T['cta_report']}</a></p>
  </div>
</section>

<section id="measures" class="band alt">
  <div class="wrap">
    <span class="kicker">{T['k_measures']}</span>
    <h2>{T['h_measures']}</h2>
    <div class="measures">
      <div>
        <h3>{T['tiers_h']}</h3>
        <ol class="tiers">{tiers}</ol>
      </div>
      <div>
        <h3>{T['dims_h']}</h3>
        <div class="dims">{dims}</div>
      </div>
    </div>
  </div>
</section>

<section class="band">
  <div class="wrap">
    <span class="kicker">{T['k_honest']}</span>
    <h2>{T['h_honest']}</h2>
    <div class="honest">
      <div><h3><span class="dot real"></span>{T['real_h']}</h3><p>{T['real_p']}</p></div>
      <div><h3><span class="dot model"></span>{T['model_h']}</h3><p>{T['model_p']}</p></div>
      <div><h3><span class="dot frozen"></span>{T['frozen_h']}</h3><p>{T['frozen_p']}</p></div>
    </div>
  </div>
</section>

<section id="run" class="band dark">
  <div class="wrap run">
    <div>
      <span class="kicker">{T['k_run']}</span>
      <h2>{T['h_run']}</h2>
      <p>{fill(T['p_run'], f)}</p>
      <p class="ctas"><a class="btn btn-light" href="{REPO}">{T['cta_repo_2']} ↗</a></p>
    </div>
    <div class="terms">
<pre><code><span class="c">$</span> git clone {REPO}.git
<span class="c">$</span> cd media-french-scaner
<span class="c">$</span> python3 bqh/harness.py --report report.html
<span class="c">$</span> python3 tests/test_harness.py</code></pre>
      <p>{T['run_embed']}</p>
<pre><code><span class="c">$</span> ./setup_ollama.sh
<span class="c">$</span> python3 bqh/harness.py --retriever embedding</code></pre>
      <p>{T['run_live']}</p>
<pre><code><span class="c">$</span> export OPENROUTER_API_KEY=…
<span class="c">$</span> python3 bqh/harness.py --live --provider openrouter</code></pre>
    </div>
  </div>
</section>

</main>
{footer(T, lang, f)}
</body>
</html>
"""


def not_found(bm25, embed, checks):
    # One 404 for both languages: Pages serves the nearest 404.html walking up,
    # so /fr/ gets its own below.
    out = {}
    for lang in ("en", "fr"):
        T = STRINGS[lang]
        f = facts(bm25, embed, lang, checks)
        home = "/" if lang == "en" else "/fr/"
        out[lang] = f"""{head(T, lang, home, T['nf_title'] + ' — French Drift')}
<body>
{chrome(T, lang)}
<main id="main" tabindex="-1" class="nf">
  <div class="wrap">
    <span class="kicker">404</span>
    <h1>{T['nf_h']}</h1>
    <p>{T['nf_p']}</p>
    <p class="ctas"><a class="btn" href="{home}">{T['nf_home']}</a></p>
  </div>
</main>
{footer(T, lang, f)}
</body>
</html>
"""
    return out


# The site and the reports need different policies. The site runs no script at
# all; the reports are single self-contained files with an inline toggle.
HEADERS = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: interest-cohort=()
  X-Frame-Options: DENY

/
  Content-Security-Policy: default-src 'none'; img-src 'self'; style-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'

/fr/*
  Content-Security-Policy: default-src 'none'; img-src 'self'; style-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'

/index.html
  Content-Security-Policy: default-src 'none'; img-src 'self'; style-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'

/report/*
  Content-Security-Policy: default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'

/img/*
  Cache-Control: public, max-age=86400
"""


def build(out: Path):
    bm25 = json.loads((ROOT / "results.json").read_text())
    embed = json.loads((ROOT / "results_embed.json").read_text())
    checks = count_checks()

    if out.exists():
        shutil.rmtree(out)
    (out / "fr").mkdir(parents=True)
    (out / "report").mkdir()

    (out / "index.html").write_text(page("en", bm25, embed, checks))
    (out / "fr" / "index.html").write_text(page("fr", bm25, embed, checks))
    nf = not_found(bm25, embed, checks)
    (out / "404.html").write_text(nf["en"])
    (out / "fr" / "404.html").write_text(nf["fr"])

    shutil.copy(ROOT / "report.html", out / "report" / "index.html")
    shutil.copy(ROOT / "report_embed.html", out / "report" / "embedding.html")
    shutil.copytree(HERE / "static" / "img", out / "img")
    for name in ("style.css", "favicon.svg"):
        shutil.copy(HERE / "static" / name, out / name)

    (out / "_headers").write_text(HEADERS)
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n")
    urls = "".join(f"""  <url><loc>{SITE}{p}</loc>
    <xhtml:link rel="alternate" hreflang="en-CA" href="{SITE}/"/>
    <xhtml:link rel="alternate" hreflang="fr-CA" href="{SITE}/fr/"/>
  </url>
""" for p in ("/", "/fr/"))
    urls += "".join(f"  <url><loc>{SITE}{p}</loc></url>\n"
                    for p in ("/report/", "/report/embedding"))
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + urls + "</urlset>\n")
    print(f"built {out} · {checks[0]} checks passing in {checks[1]} suites")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE / "dist")
    build(ap.parse_args().out)
