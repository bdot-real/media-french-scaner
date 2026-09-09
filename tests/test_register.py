"""Adversarial validation of the Canadian French register rules.

The live run scored 1.000 on register across every French answer — zero
violations in 13 generations. That is a good result for the model, but it means
the register subsystem was never exercised: a rule set that never fires is
indistinguishable from a rule set that does not work.

These cases pair metropolitan French against its Canadian equivalent for the
same content. A working rule set flags the first and clears the second. Without
this pairing, a rule that fires on *everything* would look just as good as a
correct one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bqh"))
from metrics.fluency import register_check  # noqa: E402

# (metropolitan / wrong, canadian / correct, what the rule must catch)
PAIRS = [
    ("Le ministre a parlé du chômage partiel durant le week-end.",
     "Le ministre a parlé du travail partagé durant la fin de semaine.",
     "week-end + chomage partiel"),
    ("Envoyez un email à Pôle emploi pour votre dossier.",
     "Envoyez un courriel à Service Canada pour votre dossier.",
     "email + Pole emploi"),
    ("Les administrateurs ont voté sur le budget scolaire.",
     "Les conseillers scolaires ont voté sur le budget scolaire.",
     "administrateur -> conseiller scolaire"),
    ("La ville a haussé les impôts locaux de trois pour cent.",
     "La ville a haussé la taxe foncière de trois pour cent.",
     "impots locaux -> taxe fonciere"),
    ("Le programme d'assurance chômage a été modifié.",
     "Le programme d'assurance-emploi a été modifié.",
     "assurance chomage -> assurance-emploi"),
    ("Les collectivités francophones minoritaires recevront des fonds.",
     "Les communautés de langue officielle en situation minoritaire recevront des fonds.",
     "CLOSM paraphrase"),
    ("Le conseil ouvre des bureaux dans les marchés francophones.",
     "Le conseil ouvre des bureaux dans les milieux de langue officielle en situation minoritaire.",
     "marches francophones -> CLOSM"),
    ("Les municipalités ont ouvert des centres d'hébergement chauffés.",
     "Les municipalités ont ouvert des haltes-chaleur.",
     "centre d'hebergement chauffe -> halte-chaleur"),
    ("La décision est basée sur un rapport et il est en charge de l'enquête.",
     "La décision est fondée sur un rapport et il est responsable de l'enquête.",
     "calques: base sur / en charge de"),
    ("Le plan doit rencontrer les exigences du ministère.",
     "Le plan doit satisfaire aux exigences du ministère.",
     "calque: rencontrer les exigences"),
    ("Il y a un parking près du bureau et il a payé cash.",
     "Il y a un stationnement près du bureau et il a payé en argent comptant.",
     "parking + cash"),
    ("Les navetteurs ont subi des retards ce matin.",
     "Les banlieusards ont subi des retards ce matin.",
     "navetteur -> banlieusard"),
]

# French that is correct and must NOT trigger any rule — the specificity control.
CLEAN = [
    "Le taux de chômage a augmenté de 6,6 à 6,8 pour cent le mois dernier.",
    "Les prestataires de l'assurance-emploi doivent accumuler 420 heures assurables.",
    "Le conseil municipal a déposé un budget de 4,1 milliards de dollars.",
    "Environnement Canada a mesuré 24 millimètres de glace à Kemptville.",
    "Les haltes-chaleur ont fonctionné pendant 71 nuits cet hiver.",
    "Le quota de crabe des neiges a été réduit de 22 pour cent.",
    "Douze avis à long terme sur l'eau potable demeurent en vigueur.",
    "La ponctualité du service ferroviaire s'est établie à 67 pour cent.",
]


def main():
    npass = nfail = 0

    print("\nSENSITIVITY — metropolitan flagged, Canadian clean")
    for bad, good, what in PAIRS:
        rb, rg = register_check(bad, "fr"), register_check(good, "fr")
        ok = rb["score"] < 1.0 and rg["score"] == 1.0
        npass, nfail = (npass + 1, nfail) if ok else (npass, nfail + 1)
        print(f"  {'PASS' if ok else 'FAIL'}  {what}")
        if not ok:
            print(f"          metropolitan={rb['score']:.2f} "
                  f"canadian={rg['score']:.2f} "
                  f"(canadian flagged: {[v['found'] for v in rg['violations']]})")

    print("\nSPECIFICITY — correct Canadian French must not fire")
    for text in CLEAN:
        r = register_check(text, "fr")
        ok = r["score"] == 1.0
        npass, nfail = (npass + 1, nfail) if ok else (npass, nfail + 1)
        print(f"  {'PASS' if ok else 'FAIL'}  {text[:62]}…")
        if not ok:
            print(f"          flagged: {[v['found'] for v in r['violations']]}")

    print("\nENGLISH — rules must not apply to the English side")
    for text in ["The board voted on the school budget during the weekend.",
                 "Send an email about the parking to the city."]:
        r = register_check(text, "en")
        ok = r["score"] == 1.0 and not r["violations"]
        npass, nfail = (npass + 1, nfail) if ok else (npass, nfail + 1)
        print(f"  {'PASS' if ok else 'FAIL'}  {text[:62]}")

    print(f"\n{npass} passed, {nfail} failed")
    return 1 if nfail else 0


if __name__ == "__main__":
    sys.exit(main())
