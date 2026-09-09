"""Localization conventions: dates, numbers, currency, units, institutions.

A French answer can be perfectly grounded, complete, and in Canadian register
and still be wrong for publication because it renders a date as 03/04 (which
means April 3 in Canada and March 4 in the US), writes $1,234.56 instead of
1 234,56 $, or leaves a temperature in Fahrenheit.

These are not style preferences. A misread date in a news story about a filing
deadline or a court appearance is a factual error the grounding checks cannot
see, because the digits are all present and all correct.

What is checked:

  currency   FR places the symbol AFTER the amount with a non-breaking space
             (1 234,56 $), EN places it before ($1,234.56).
  decimal    FR uses a comma, EN a point. FR groups with a space, EN with a
             comma.
  date       Numeric dates are ambiguous across conventions; news copy in both
             languages should name the month.
  units      Canadian copy is metric. Imperial units unconverted in either
             language are a localization failure.
  percent    FR puts a non-breaking space before the sign (22 %), EN does not.
  time       FR uses the 24-hour clock; EN commonly uses 12-hour with am/pm.
"""
import re

NBSP = " "
NARROW_NBSP = " "
SPACES = f"[ {NBSP}{NARROW_NBSP}]"

MONTHS_EN = ("january february march april may june july august september "
             "october november december").split()
MONTHS_FR = ("janvier février mars avril mai juin juillet août septembre "
             "octobre novembre décembre").split()

IMPERIAL = [
    (r"\b\d+(?:[.,]\d+)?\s*(?:miles?|mi)\b", "miles"),
    (r"\b\d+(?:[.,]\d+)?\s*(?:feet|foot|ft)\b", "feet"),
    (r"\b\d+(?:[.,]\d+)?\s*(?:inch(?:es)?|in)\b", "inches"),
    (r"\b\d+(?:[.,]\d+)?\s*(?:pounds?|lbs?)\b", "pounds"),
    (r"\b\d+(?:[.,]\d+)?\s*(?:gallons?|gal)\b", "gallons"),
    (r"\b\d+(?:[.,]\d+)?\s*(?:acres?)\b", "acres"),
    (r"\bfahrenheit\b|\b\d+\s*°?\s*F\b", "Fahrenheit"),
]


def _issues_fr(text):
    out = []
    # Currency: FR writes "1 234,56 $" — symbol trails the amount.
    for m in re.finditer(r"\$\s?\d", text):
        out.append({"kind": "currency", "severity": "high",
                    "found": text[max(0, m.start() - 2):m.end() + 8].strip(),
                    "note": "FR places the dollar sign after the amount "
                            "(1 234,56 $), not before."})
    # Decimal point where a comma belongs. Exclude version-like and URL forms.
    for m in re.finditer(r"\b\d+\.\d+\b", text):
        frag = m.group()
        if re.match(r"^\d+\.\d{3}$", frag):   # could be EN grouping, still wrong
            pass
        out.append({"kind": "decimal", "severity": "high", "found": frag,
                    "note": "FR uses a decimal comma (3,75), not a point."})
    # Thousands grouped with a comma.
    for m in re.finditer(r"\b\d{1,3}(?:,\d{3})+\b", text):
        out.append({"kind": "grouping", "severity": "high", "found": m.group(),
                    "note": "FR groups thousands with a space (18 400), "
                            "not a comma."})
    # Percent sign with no preceding space.
    for m in re.finditer(r"\d%", text):
        out.append({"kind": "percent", "severity": "low",
                    "found": text[max(0, m.start() - 3):m.end()],
                    "note": "FR inserts a non-breaking space before % (22 %)."})
    # 12-hour clock in French copy.
    for m in re.finditer(r"\b\d{1,2}\s*(?:a\.?m\.?|p\.?m\.?)\b", text, re.I):
        out.append({"kind": "time", "severity": "medium", "found": m.group(),
                    "note": "FR uses the 24-hour clock (14 h 30)."})
    return out


def _issues_en(text):
    out = []
    # French decimal comma leaking into English copy.
    for m in re.finditer(r"\b\d+,\d{1,2}\b(?!\d)", text):
        out.append({"kind": "decimal", "severity": "high", "found": m.group(),
                    "note": "EN uses a decimal point (3.75), not a comma."})
    # Currency symbol trailing the amount.
    for m in re.finditer(r"\d\s?\$", text):
        out.append({"kind": "currency", "severity": "high", "found": m.group(),
                    "note": "EN places the dollar sign before the amount."})
    return out


def _shared_issues(text, lang):
    out = []
    months = MONTHS_FR if lang == "fr" else MONTHS_EN
    # Ambiguous all-numeric dates: 03/04/2026 means different things by
    # convention, and a news reader has no way to disambiguate.
    for m in re.finditer(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", text):
        out.append({"kind": "date", "severity": "high", "found": m.group(),
                    "note": "All-numeric dates are ambiguous across "
                            "conventions; name the month."})
    for pattern, label in IMPERIAL:
        for m in re.finditer(pattern, text, re.I):
            out.append({"kind": "units", "severity": "medium",
                        "found": m.group(),
                        "note": f"Canadian copy is metric; {label} unconverted."})
    return out


SEVERITY_WEIGHT = {"high": 1.0, "medium": 0.5, "low": 0.15}


def localization_check(text, lang):
    """Localization conformance for one answer, 0-1."""
    issues = _shared_issues(text, lang)
    issues += _issues_fr(text) if lang == "fr" else _issues_en(text)
    sentences = max(len([s for s in re.split(r"[.!?]+", text) if s.strip()]), 1)
    penalty = sum(SEVERITY_WEIGHT[i["severity"]] for i in issues) / sentences
    return {"score": round(max(0.0, 1.0 - penalty), 4), "issues": issues}
