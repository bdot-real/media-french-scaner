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

# Written-out numerals. Journalistic style spells out numbers under 10 and
# often up to 100, so a grounding check that only reads digits will report
# false hallucinations whenever the source spells a figure the answer digitises.
# Compounds ("ninety-two", "quatre-vingt-douze", "trente et un") are composed
# from these units rather than enumerated, so the table stays small.
_UNITS_EN = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
             "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
             "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
             "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
             "nineteen": 19}
_TENS_EN = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
            "seventy": 70, "eighty": 80, "ninety": 90}

_UNITS_FR = {"zéro": 0, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
             "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
             "onze": 11, "douze": 12, "treize": 13, "quatorze": 14,
             "quinze": 15, "seize": 16}
_TENS_FR = {"vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50,
            "soixante": 60}

# Fractions that carry a real quantity in news copy.
_FRACTIONS = {"quarter": "0.25", "quart": "0.25", "half": "0.5",
              "moitié": "0.5", "third": "0.333", "tiers": "0.333"}


def _word_numbers(text, lang):
    """Extract written-out numerals, including compounds.

    Compound forms are matched first and their spans removed from the text, so
    "ninety-two" yields 92 and not also 90 and 2. Leaving the components in
    would fabricate figures that appear in neither the source nor the answer,
    which is exactly the false-positive the grounding check must not produce.
    """
    found = set()
    units, tens = ((_UNITS_FR, _TENS_FR) if lang == "fr"
                   else (_UNITS_EN, _TENS_EN))
    joiner = r"(?:-|\s+et\s+|\s+)" if lang == "fr" else r"-"

    def consume(pattern, value):
        nonlocal text
        if re.search(pattern, text):
            found.add(str(value))
            text = re.sub(pattern, " ", text)

    # French bases first: "quatre-vingt-douze" must win over "quatre-vingt".
    if lang == "fr":
        for base, bv in (("quatre-vingt", 80), ("soixante", 60)):
            for uw, uv in _UNITS_FR.items():
                if 10 <= uv <= 19:
                    consume(rf"\b{base}-{uw}\b", bv + uv)
        consume(r"\bquatre-vingts?\b", 80)

    # Tens + units compounds. "un"/"one" are excluded from the bare-unit table
    # because they are articles far more often than numerals, but inside a tens
    # compound ("trente et un", "twenty-one") they are unambiguous.
    compound_units = dict(units)
    compound_units["un" if lang == "fr" else "one"] = 1
    for tw, tv in tens.items():
        for uw, uv in compound_units.items():
            if 1 <= uv <= 9:
                consume(rf"\b{tw}{joiner}{uw}\b", tv + uv)

    # Whatever bare forms remain.
    for w, v in {**tens, **units}.items():
        if v:
            consume(rf"\b{w}\b", v)
    # Fractions carry a quantity; the same words used as ordinals do not
    # ("a third consecutive hold", "un troisième maintien"). Exclude the
    # ordinal reading rather than requiring a specific fraction frame, since
    # news copy writes both "a quarter of the fund" and "a quarter reserved".
    _ORDINAL_AFTER = (r"consecutive|straight|time|quarter\b|place|"
                      r"consécutif|consécutive|fois|rang")
    for w, v in _FRACTIONS.items():
        for m in re.finditer(rf"\b{w}\b", text):
            tail = text[m.end():m.end() + 24]
            if re.match(rf"\s+(?:{_ORDINAL_AFTER})", tail):
                continue
            found.add(v)
            break
    return found


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
    for raw in _word_numbers(lowered, lang):
        n = normalize_number(raw)
        if n is not None:
            found.add(n)
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


TRUNCATION_RATIO = 0.72


def coverage_vs_reference(answer, reference, lang):
    """Does this answer carry the same information as its counterpart?

    Two signals, because omissions come in two shapes:

      * numeric  — a figure present in one language and absent in the other.
        Language-neutral, so directly comparable.
      * length   — prose content dropped without dropping a number ("more than
        double", a stated cause, an entire second topic). Cross-language word
        overlap is meaningless, but *relative length* is informative: French
        renders the same content 15-20% longer than English, so a French answer
        materially shorter than its English counterpart has lost content.

    The length signal is deliberately conservative — it only fires well past
    the expected expansion ratio, so ordinary concision is not flagged.
    """
    other = "en" if lang == "fr" else "fr"
    a_keys = extract_numbers(answer, lang)
    r_keys = extract_numbers(reference, other)

    missing = sorted(r_keys - a_keys)
    numeric_score = (len(a_keys & r_keys) / len(r_keys)) if r_keys else 1.0

    # Expected length ratio after stopword-stripped tokenization. The oft-cited
    # 1.15-1.20x French expansion applies to running prose; on terse factual
    # answers with function words removed the content-token counts run close to
    # parity, so 1.0 is the right baseline here.
    a_len = len(tokenize(answer, lang))
    r_len = len(tokenize(reference, other))
    expected = float(r_len)
    length_score = 1.0
    truncated = False
    # TRUNCATION_RATIO is calibrated on this corpus: answers with no planted
    # omission sit at 0.77-0.85 of expected length, planted omissions at
    # 0.53-0.67. 0.72 separates them with margin on both sides. Recalibrate if
    # the corpus or answer style changes materially.
    if expected >= 6:  # too short to judge reliably
        ratio = a_len / expected
        if ratio < TRUNCATION_RATIO:
            length_score = max(0.0, ratio / TRUNCATION_RATIO)
            truncated = True

    return {
        "score": round(min(numeric_score, length_score), 4),
        "numeric_score": round(numeric_score, 4),
        "length_score": round(length_score, 4),
        "missing": missing,
        "truncated": truncated,
        "len_tokens": a_len,
        "ref_len_tokens": r_len,
    }
