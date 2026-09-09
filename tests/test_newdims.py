"""Validation for the localization, terminology, readability and answerability
dimensions.

Each has a sensitivity case (a real defect must be flagged) and a specificity
control (correct copy must not be). Without the paired control, a rule that
fires on everything scores the same as a correct one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bqh"))
from metrics.localization import localization_check  # noqa: E402
from metrics.consistency import terminology_consistency, readability_parity  # noqa: E402
from metrics.answerability import classify_answer, answerability  # noqa: E402

P, F = [], []


def check(name, cond, detail=""):
    (P if cond else F).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not cond else ""))


def main():
    print("\n1. Localization — French conventions")
    cases = [
        ("$4,100,000 before amount", "Le budget de $4,100,000 a été déposé.", "currency"),
        ("decimal point", "La hausse est de 3.9 pour cent.", "decimal"),
        ("comma grouping", "Le quota est de 18,400 tonnes.", "grouping"),
        ("ambiguous date", "Déposé le 03/04 dernier.", "date"),
        ("imperial units", "La route couvre 12 miles.", "units"),
    ]
    for label, text, kind in cases:
        r = localization_check(text, "fr")
        kinds = [i["kind"] for i in r["issues"]]
        check(f"FR flags {label}", kind in kinds, str(kinds))

    print("\n2. Localization — correct French is not flagged")
    clean_fr = [
        "Le budget de 4 100 000 $ a été déposé le 3 avril.",
        "La hausse est de 3,9 %.",
        "Le quota est de 18 400 tonnes.",
        "Environnement Canada a mesuré 24 millimètres à Kemptville.",
        "Le taux directeur demeure à 3,75 pour cent.",
    ]
    for t in clean_fr:
        r = localization_check(t, "fr")
        check(f"clean: {t[:44]}…", r["score"] == 1.0,
              str([i["kind"] for i in r["issues"]]))

    print("\n3. Localization — English conventions")
    r = localization_check("The budget of 4 100 000 $ was tabled.", "en")
    check("EN flags trailing currency symbol",
          "currency" in [i["kind"] for i in r["issues"]])
    r = localization_check("The $4,100,000 budget rose 3.9%.", "en")
    check("EN clean copy scores 1.0", r["score"] == 1.0,
          str([i["kind"] for i in r["issues"]]))

    print("\n4. Terminology consistency")
    mixed = ["Les prestataires de l'assurance-emploi.",
             "Le régime d'assurance-emploi change.",
             "L'assurance chômage sera revue."]
    r = terminology_consistency(mixed, "fr")
    check("mixed variants score below 1.0", r["score"] < 1.0, str(r["score"]))
    consistent = ["Les prestataires de l'assurance-emploi.",
                  "Le régime d'assurance-emploi change.",
                  "L'assurance-emploi sera revue."]
    r = terminology_consistency(consistent, "fr")
    check("consistent usage scores 1.0", r["score"] == 1.0, str(r["score"]))
    check("no concepts found in unrelated text",
          terminology_consistency(["Le temps est beau."], "fr")["score"] == 1.0)

    print("\n5. Readability parity")
    en = ["The city tabled a $4.1 billion budget with a 3.9 per cent tax increase."] * 4
    fr_ok = ["La ville a déposé un budget de 4,1 milliards de dollars comportant "
             "une hausse de taxe de 3,9 pour cent."] * 4
    r = readability_parity(en, fr_ok)
    # The verdict is the actionable output; the score is a continuous distance
    # from parity that a single sentence pair cannot pin precisely.
    check("faithful French reads as within expected expansion",
          r["verdict"] == "within expected expansion", r["verdict"])
    fr_short = ["Le budget a augmenté."] * 4
    r = readability_parity(en, fr_short)
    check("truncated French scores lower", r["score"] < 0.6, str(r["ratio"]))
    check("faithful scores above truncated",
          readability_parity(en, fr_ok)["score"] > r["score"])
    check("verdict names the direction", "shorter" in r["verdict"], r["verdict"])

    print("\n6. Answerability")
    check("FR refusal detected",
          classify_answer("Les sources ne mentionnent aucune panne.", "fr")[0] == "refused")
    check("FR hedge detected",
          classify_answer("Il semblerait que le budget soit de 4 milliards.", "fr")[0] == "hedged")
    check("FR answer detected",
          classify_answer("Le budget est de 4,1 milliards de dollars.", "fr")[0] == "answered")
    check("EN refusal detected",
          classify_answer("The sources do not mention any outage.", "en")[0] == "refused")
    check("EN hedge detected",
          classify_answer("It appears the budget might be $4 billion.", "en")[0] == "hedged")

    print("\n7. Answerability asymmetry is the finding")
    rows = [{"query_id": "qA", "langs": {
                "en": {"answer": "Municipalities opened eleven warming centres."},
                "fr": {"answer": "Les sources ne mentionnent aucun endroit."}}},
            {"query_id": "qB", "langs": {
                "en": {"answer": "The budget is $4.1 billion."},
                "fr": {"answer": "Le budget est de 4,1 milliards de dollars."}}}]
    a = answerability(rows)
    check("one asymmetric query found", a["n_asymmetric"] == 1, str(a["n_asymmetric"]))
    check("served/denied languages named",
          a["asymmetric"][0] == {"query_id": "qA", "served": "en", "denied": "fr"},
          str(a["asymmetric"]))
    check("refusal gap is positive for FR", a["refusal_gap"] > 0, str(a["refusal_gap"]))

    print(f"\n{len(P)} passed, {len(F)} failed")
    return 1 if F else 0


if __name__ == "__main__":
    sys.exit(main())
