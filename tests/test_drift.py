"""Validation for MDR and QFCR.

The defining property of MDR is that it counts substitutions only. These tests
pin that behaviour: a rephrase must not raise MDR, and must not enter the
denominator either — if rephrases were scored as "clean", MDR would be diluted
toward zero by verbose output rather than reported honestly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bqh"))
from metrics.drift import measure_drift, measure_false_correction  # noqa: E402

P, F = [], []


def check(name, cond, detail=""):
    (P if cond else F).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  — {detail}" if detail and not cond else ""))


SRC = ("Les municipalités ont ouvert onze haltes-chaleur durant la fin de "
       "semaine. Envoyez un courriel au conseiller scolaire.")


def main():
    print("\nMDR — substitution counts as drift")
    sub = ("Les municipalités ont ouvert onze centres d'hébergement chauffés "
           "durant le week-end. Envoyez un e-mail à l'administrateur scolaire.")
    r = measure_drift(SRC, sub)
    check("all four forms substituted", r["substituted"] == 4, str(r))
    check("MDR == 1.0", r["mdr"] == 1.0, str(r["mdr"]))
    check("nothing counted as rephrased", r["rephrased"] == 0, str(r))

    print("\nMDR — preservation is clean")
    r = measure_drift(SRC, SRC)
    check("MDR == 0.0 when forms preserved", r["mdr"] == 0.0)
    check("preserved counted", r["preserved"] == 4, str(r))

    print("\nMDR — rephrasing is NOT drift (the defining constraint)")
    reph = ("Les villes ont mis en place des locaux chauffés pour la période. "
            "Communiquez par voie électronique avec la personne responsable.")
    r = measure_drift(SRC, reph)
    check("MDR == 0.0 on rephrase", r["mdr"] == 0.0, str(r["mdr"]))
    check("no substitutions recorded", r["substituted"] == 0, str(r))
    check("rephrases counted separately", r["rephrased"] > 0, str(r))
    check("rephrases excluded from denominator",
          r["scored_opportunities"] == 0, str(r["scored_opportunities"]))

    print("\nMDR — mixed output scores only the substitutions")
    mixed = ("Les municipalités ont ouvert onze haltes-chaleur durant le "
             "week-end. Un message sera transmis à la personne responsable.")
    r = measure_drift(SRC, mixed)
    check("one substitution", r["substituted"] == 1, str(r))
    check("one preserved", r["preserved"] == 1, str(r))
    check("MDR == 0.5 (1 of 2 scored)", r["mdr"] == 0.5, str(r["mdr"]))
    check("rephrased excluded, not counted clean", r["rephrased"] == 2, str(r))

    print("\nMDR — no opportunity means no drift")
    r = measure_drift("Le taux directeur demeure à 3,75 pour cent.",
                      "Le taux directeur demeure à 3,75 pour cent.")
    check("MDR 0.0 with zero opportunities", r["mdr"] == 0.0)
    check("denominator is zero", r["scored_opportunities"] == 0)

    print("\nQFCR — proofreader altering valid Quebec usage")
    proof = ("Les municipalités ont ouvert onze centres d'hébergement chauffés "
             "durant le week-end. Envoyez un e-mail à l'administrateur scolaire.")
    r = measure_false_correction(SRC, proof)
    check("QFCR == 1.0 when all forms altered", r["qfcr"] == 1.0, str(r["qfcr"]))
    check("altered count matches", r["forms_altered"] == 4, str(r))
    check("substitutions flagged as going to France form",
          all(e["to_france_form"] for e in r["events"]), str(r["events"]))

    print("\nQFCR — a faithful proofreader scores zero")
    faithful = SRC.replace("Envoyez", "Veuillez envoyer")
    r = measure_false_correction(SRC, faithful)
    check("QFCR == 0.0 when forms untouched", r["qfcr"] == 0.0, str(r["qfcr"]))
    check("valid forms still counted", r["valid_forms_present"] == 4, str(r))

    print("\nQFCR — partial damage")
    partial = SRC.replace("fin de semaine", "week-end")
    r = measure_false_correction(SRC, partial)
    check("QFCR == 0.25 (1 of 4)", r["qfcr"] == 0.25, str(r["qfcr"]))

    print(f"\n{len(P)} passed, {len(F)} failed")
    return 1 if F else 0


if __name__ == "__main__":
    sys.exit(main())
