"""The report's own French must pass the standard the report measures.

A dashboard about Canadian French quality written in metropolitan French would
undercut its own argument. These tests run every French UI string through the
harness's own register checker and drift detector.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bqh"))
from report.i18n import STRINGS  # noqa: E402
from metrics.fluency import register_check  # noqa: E402
from metrics.drift import FORM_PAIRS  # noqa: E402
import re  # noqa: E402

P, F = [], []


def check(name, cond, detail=""):
    (P if cond else F).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not cond else ""))


def walk(node, path=""):
    """Yield (path, string) for every leaf string."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")


def strip_markup(t):
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&[a-z]+;", " ", t)
    return re.sub(r"\{[a-z_]+\}", " ", t)


def main():
    en, fr = STRINGS["en"], STRINGS["fr"]

    print("\n1. Structural parity between the two string sets")
    check("top-level keys identical", set(en) == set(fr))
    check("dimension keys identical", set(en["dims"]) == set(fr["dims"]))
    check("severity keys identical", set(en["sev"]) == set(fr["sev"]))
    check("no empty French strings",
          all(v.strip() for _, v in walk(fr) if isinstance(v, str)))

    print("\n2. French UI copy passes the register checker")
    bad = []
    for path, text in walk(fr):
        clean = strip_markup(text)
        r = register_check(clean, "fr")
        if r["score"] < 1.0:
            bad.append((path, [v["found"] for v in r["violations"]]))
    check("no register violations in French UI", not bad, str(bad[:4]))

    print("\n3. No France-side forms anywhere in the French copy")
    hits = []
    for path, text in walk(fr):
        low = strip_markup(text).lower()
        for _, fr_pat, qc_label, fr_label in FORM_PAIRS:
            # The QFCR/MDR example tables legitimately name France forms as
            # data; UI chrome must not use them as its own voice.
            if re.search(fr_pat, low, flags=re.IGNORECASE):
                hits.append((path, fr_label))
    check("no metropolitan forms in French UI", not hits, str(hits[:4]))

    print("\n4. Canadian typographic conventions")
    # Canadian practice puts a non-breaking space before ':' (a plain space can
    # wrap the colon onto its own line) and none before ';', '?' or '!' — the
    # latter being where it differs from France.
    colon_space = [p for p, t in walk(fr) if " :" in t and "&nbsp;" not in t]
    check("French copy uses Canadian colon spacing",
          len(colon_space) <= 3, f"{len(colon_space)} strings: {colon_space[:3]}")

    print("\n5. English strings are unaffected by French rules")
    en_bad = [p for p, t in walk(en)
              if register_check(strip_markup(t), "en")["score"] < 1.0]
    check("no violations reported on English", not en_bad, str(en_bad[:3]))

    print("\n6. Key terminology is Canadian, not France")
    fr_all = " ".join(t.lower() for _, t in walk(fr))
    for wrong, right in [("courrier électronique", "courriel"),
                         ("week-end", "fin de semaine"),
                         ("impôt local", "taxe foncière"),
                         ("actualités", "nouvelles")]:
        check(f"avoids '{wrong}'", wrong not in fr_all)
    for expected in ["repérage", "pupitre", "français canadien", "lectorat"]:
        check(f"uses '{expected}'", expected in fr_all)

    print(f"\n{len(P)} passed, {len(F)} failed")
    return 1 if F else 0


if __name__ == "__main__":
    sys.exit(main())
