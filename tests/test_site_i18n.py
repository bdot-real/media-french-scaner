"""The companion site's French must pass the standard the harness measures.

Same argument as test_i18n.py, applied to site/content.py: a site arguing that
metropolitan French is a defect cannot be written in it. Every French string is
run through the harness's own register checker and drift detector.
"""
import re
import string
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bqh"))
sys.path.insert(0, str(ROOT / "site"))
from content import STRINGS  # noqa: E402
from metrics.fluency import register_check  # noqa: E402
from metrics.drift import FORM_PAIRS  # noqa: E402

P, F = [], []


def check(name, cond, detail=""):
    (P if cond else F).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not cond else ""))


def walk(node, path=""):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, (list, tuple)):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")


def strip(t):
    t = re.sub(r"<code>.*?</code>", " ", t)     # code is code, not prose
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&[a-z]+;", " ", t)
    return re.sub(r"\{[a-z_]+\}", " ", t)


def fields(t):
    return sorted(f for _, f, _, _ in string.Formatter().parse(t) if f)


def main():
    en, fr = STRINGS["en"], STRINGS["fr"]
    en_leaves, fr_leaves = dict(walk(en)), dict(walk(fr))

    print("\n1. Structural parity")
    check("same keys in both languages", set(en_leaves) == set(fr_leaves),
          str(set(en_leaves) ^ set(fr_leaves)))
    check("no empty French strings", all(v.strip() for v in fr_leaves.values()))
    mism = [k for k in en_leaves if k in fr_leaves
            and fields(en_leaves[k]) != fields(fr_leaves[k])]
    check("same figures referenced in both languages", not mism, str(mism[:4]))

    print("\n2. French passes the register checker")
    bad = []
    for path, text in fr_leaves.items():
        r = register_check(strip(text), "fr")
        if r["score"] < 1.0:
            bad.append((path, [v["found"] for v in r["violations"]]))
    check("no register violations", not bad, str(bad[:4]))

    print("\n3. No France-side forms in the site's own voice")
    hits = [(p, lab) for p, t in fr_leaves.items()
            for _, pat, _, lab in FORM_PAIRS
            if re.search(pat, strip(t).lower(), flags=re.IGNORECASE)]
    check("no metropolitan forms", not hits, str(hits[:4]))

    print("\n4. Canadian typography")
    # A non-breaking space before ':' and inside guillemets; none before ; ? !
    loose_colon = [p for p, t in fr_leaves.items() if re.search(r"[^\s;]:", strip_code(t))
                   and not re.search(r"https?:", t)]
    check("non-breaking space before every colon", not loose_colon, str(loose_colon[:3]))
    plain_space = [p for p, t in fr_leaves.items() if re.search(r" [:»]|« ", t)]
    check("colon and guillemet spaces are non-breaking", not plain_space, str(plain_space[:3]))
    fr_space = [p for p, t in fr_leaves.items() if re.search(r"(\s|&nbsp;)[;?!]", t)]
    check("no space before ; ? !", not fr_space, str(fr_space[:3]))
    straight = [p for p, t in fr_leaves.items() if '"' in strip(t)]
    check("French quotes use guillemets", not straight, str(straight[:3]))

    print("\n5. Terminology is Canadian")
    fr_all = " ".join(strip(t).lower() for t in fr_leaves.values())
    for wrong in ["courrier électronique", "week-end", "email", "mail ", "actualités",
                  "recherche d'information"]:
        check(f"avoids '{wrong.strip()}'", wrong not in fr_all)
    for expected in ["repérage", "véracité", "lectorat", "français canadien", "pupitre"]:
        check(f"uses '{expected}'", expected in fr_all)

    print("\n6. English is untouched by French rules")
    en_bad = [p for p, t in en_leaves.items() if register_check(strip(t), "en")["score"] < 1.0]
    check("no violations reported on English", not en_bad, str(en_bad[:3]))

    print(f"\n{len(P)} passed, {len(F)} failed")
    return 1 if F else 0


def strip_code(t):
    return re.sub(r"<code>.*?</code>", " ", re.sub(r"&nbsp;:", " ", t))


if __name__ == "__main__":
    sys.exit(main())
