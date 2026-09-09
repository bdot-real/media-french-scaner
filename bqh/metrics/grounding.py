"""Grounding: is every claim in the answer supported by the retrieved source?

Two checks, both deterministic and both explainable:

  1. Numeric grounding — every figure in the answer must appear in the source.
     Journalism's highest-consequence hallucination is a wrong number, and it
     is the one check you can make exact rather than fuzzy.
  2. Lexical entailment — content-word overlap against the source, which
     catches unsupported qualifiers ("durant la fin de semaine") that carry no
     digits.

Number formats are normalised across languages first: FR writes 18 400 and
3,75; EN writes 18,400 and 3.75. Comparing them naively would report a
grounding failure on every localised figure — a false positive that would
discredit the whole harness.
"""
import re
import unicodedata

from .retrieval import tokenize

# Written-out numerals that appear in journalistic copy.
WORD_NUMBERS = {
    "en": {"two": "2", "three": "3", "four": "4", "five": "5",
           "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
           "eleven": "11", "twelve": "12", "twenty": "20", "thirty": "30",
           "thirty-eight": "38", "forty": "40", "quarter": "0.25"},
    "fr": {"deux": "2", "trois": "3", "quatre": "4",
           "cinq": "5", "six": "6", "sept": "7", "huit": "8", "neuf": "9",
           "dix": "10", "onze": "11", "douze": "12", "vingt": "20",
           "trente": "30", "trente-huit": "38", "quarante": "40",
           "quart": "0.25"},
}


def normalize_number(raw):
    """Canonicalise a numeric string across EN/FR conventions.

    FR: '18 400' (narrow/non-breaking space groups), '3,75' (decimal comma)
    EN: '18,400' (comma groups), '3.75' (decimal point)
    """
    s = raw.strip()
    s = s.replace(" ", "").replace(" ", "").replace(" ", "")
    if "," in s and "." in s:
        # e.g. 1,234.56 -> EN grouping + decimal point
        s = s.replace(",", "")
    elif "," in s:
        # FR decimal comma, unless it is clearly EN grouping (3 digits after)
        if re.search(r",\d{3}\b", s) and not re.search(r",\d{1,2}$", s):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    try:
        val = float(s)
    except ValueError:
        return None
    return f"{val:g}"


def extract_numbers(text, lang):
    """All numeric values in the text, canonicalised."""
    found = set()
    for m in re.finditer(r"\d[\d   ,.]*\d|\d", text):
        n = normalize_number(m.group())
        if n is not None:
            found.add(n)
    lowered = unicodedata.normalize("NFC", text.lower())
    for word, val in WORD_NUMBERS.get(lang, {}).items():
        if re.search(rf"\b{re.escape(word)}\b", lowered):
            found.add(normalize_number(val))
    return found


def numeric_grounding(answer, sources, lang):
    """Fraction of the answer's figures that appear in the source text."""
    ans_nums = extract_numbers(answer, lang)
    src_nums = set()
    for s in sources:
        src_nums |= extract_numbers(s, lang)
    if not ans_nums:
        return {"score": 1.0, "checked": 0, "unsupported": []}
    unsupported = sorted(ans_nums - src_nums)
    return {
        "score": 1.0 - len(unsupported) / len(ans_nums),
        "checked": len(ans_nums),
        "unsupported": unsupported,
    }


def lexical_entailment(answer, sources, lang):
    """Content-word support: share of answer terms present in the source."""
    a = set(tokenize(answer, lang))
    s = set()
    for src in sources:
        s |= set(tokenize(src, lang))
    if not a:
        return {"score": 1.0, "unsupported_terms": []}
    unsupported = sorted(a - s)
    return {
        "score": len(a & s) / len(a),
        "unsupported_terms": unsupported[:10],
    }


def coverage_vs_reference(answer, reference, lang):
    """Does this answer carry the same information as its counterpart?

    Run with the EN answer as reference to detect FR omissions — the failure
    mode where the French output is fluent, grounded, and simply says less.
    Bilingual equivalence needs this: neither side may be a reduced edition.
    """
    a = set(tokenize(answer, lang))
    r = set(tokenize(reference, "en" if lang == "fr" else "fr"))
    # Cross-language comparison is only meaningful on language-neutral tokens:
    # numbers and proper nouns survive translation, ordinary vocabulary does not.
    a_keys = {t for t in a if any(c.isdigit() for c in t)}
    r_keys = {t for t in r if any(c.isdigit() for c in t)}
    a_keys |= extract_numbers(answer, lang)
    r_keys |= extract_numbers(reference, "en" if lang == "fr" else "fr")
    if not r_keys:
        return {"score": 1.0, "missing": []}
    missing = sorted(r_keys - a_keys)
    return {"score": len(a_keys & r_keys) / len(r_keys), "missing": missing}
