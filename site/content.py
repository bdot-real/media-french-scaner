"""Every word on the companion site, in both languages.

The French is Canadian French, for the same reason the report's is: a site
arguing that metropolitan French is a defect cannot be written in it.
`tests/test_site_i18n.py` runs every French string here through the harness's
own register checker and drift detector.

Two kinds of text live here, and the distinction matters to that test:

* `STRINGS` is the site's own voice. It must never use a France-side form.
* The QFCR table's right-hand column is data: what the proofreader wrote,
  read from results.json. "week-end" appears there because the proofreader
  wrote it, not because the site says it. The test checks the voice, not the
  evidence.

Figures are placeholders (`{parity}`, `{qfcr}` ...) filled from results.json by
build.py, so the site cannot drift from the report it links to.
"""

REPO = "https://github.com/bdot-real/media-french-scaner"
SITE = "https://french-drift.melx.buzz"

STRINGS = {
    "en": {
        "lang": "en",
        "other_name": "Français",
        "brand_sub": "Bilingual Quality Harness",
        "title": "French Drift — does your AI answer as well in French?",
        "description": ("An open-source harness that measures whether an AI content "
                        "pipeline performs equivalently in English and Canadian French. "
                        "It reports the gap, not two separate passing grades."),
        "skip": "Skip to content",
        "nav": [("#finding", "The finding"), ("#metrics", "Canadian metrics"),
                ("#report", "The report"), ("#measures", "What it measures"),
                ("#run", "Run it")],
        "nav_report": "Open the report",
        "nav_repo": "GitHub",

        "kicker": "Open source · Python · No dependencies",
        "h1": "Is the French answer as good as the English one?",
        "lede": ("French Drift runs the same corpus, the same questions and the same "
                 "metrics through an AI content pipeline in English and in Canadian "
                 "French, side by side. Then it reports the <em>gap</em>. Two languages "
                 "can each clear a quality bar while the French reader gets a thinner, "
                 "less grounded answer, in a register that reads as foreign. Scoring "
                 "each language on its own can't see that."),
        "cta_report": "Open the live report",
        "cta_repo": "Read the code",
        "hero_alt": ("The report's opening panel: {parity} service parity, and "
                     "{unserved} queries where the French reader was not served."),
        "hero_cap": "The report leads with the worst thing a French reader experienced, not the mean.",

        "stat_parity": "service parity",
        "stat_parity_d": "Queries where the French reader got a substantively equivalent answer.",
        "stat_qfcr": "false corrections",
        "stat_qfcr_d": "Valid Quebec forms a naive “proofread this” pass rewrote.",
        "stat_cov": "coverage gap",
        "stat_cov_d": "French answers carry less than their English counterparts.",
        "stat_media": "media accessible",
        "stat_media_d": "Assets whose French descriptors are complete.",

        "k_finding": "01 · The finding",
        "h_finding": "The hypothesis it was built on didn't survive contact.",
        "p_finding_1": ("The harness started from a plausible argument: Canadian French "
                        "vocabulary is weakly represented in retrieval models, so French "
                        "retrieval diverges. The default backend <em>models</em> that gap "
                        "from a hand-written lexicon table. Then we measured it with a real "
                        "multilingual embedding model, bge-m3, run locally."),
        "th_dim": "Dimension", "th_bm25": "Modelled gap (BM25)",
        "th_embed": "Measured gap (bge-m3)",
        "p_finding_2": ("On precision and nDCG, the sign flipped: French retrieval came "
                        "out marginally <em>ahead</em>. The query the harness was built "
                        "around, “where can people go to keep warm?”, retrieves "
                        "<code>halte-chaleur</code> perfectly under bge-m3."),
        "callout_h": "The divergence is real. It just isn't in retrieval.",
        "callout_p": ("Every generation-side gap is identical under both backends: content "
                      "coverage, register, fabricated figures, localization. The French "
                      "reader loses out in generation, metadata and proofreading. A team "
                      "that fixed retrieval first would be optimizing the wrong stage. "
                      "That result is only visible because the modelled and measured "
                      "backends could be compared directly."),
        "shot_embed_alt": "The same report generated with the bge-m3 embedding backend.",
        "shot_embed_cap": "The same report, bge-m3 backend. Every metric and tier is computed identically.",
        "embed_link": "Open the embedding report",

        "k_metrics": "02 · Two Canadian metrics",
        "h_metrics": "Generic French evaluation can't see these.",
        "mdr_h": "Metropolitan Drift Rate",
        "mdr_p": ("How often a Quebec form in the source is replaced by its France "
                  "counterpart in the answer. It counts substitutions only. When the model "
                  "rephrases around a term, that's verbosity, not drift, so those cases "
                  "leave the denominator entirely. Here, {mdr_sub} of {mdr_n} scored "
                  "opportunities were substituted, with {mdr_reph} rephrasings excluded."),
        "qfcr_h": "Quebec False Correction Rate",
        "qfcr_p": ("Already-correct Canadian French goes through the prompt a team would "
                   "actually write: “Corrige et améliore ce texte en français”. The input "
                   "is correct by construction, so any change is a false correction. "
                   "{qfcr_alt} of {qfcr_n} valid forms were destroyed."),
        "qfcr_th_from": "Valid Quebec form", "qfcr_th_to": "Proofreader wrote",
        "metrics_close": ("Read together, they separate two failures. Good MDR with bad "
                          "QFCR means generation is fine and <strong>the proofreader is "
                          "the problem</strong>: a pipeline can generate perfect Canadian "
                          "French and still ship metropolitan copy."),
        "shot_drift_alt": "The drift and false-correction section of the report.",
        "shot_drift_cap": "Every substitution is listed with the query or probe it came from.",

        "k_report": "03 · The report",
        "h_report": "One self-contained file, in both languages.",
        "p_report": ("The report is a single HTML file with no external requests. It ships "
                     "English and French in the same document, so the two views always "
                     "describe the same run. Its French is checked by the harness's own "
                     "register checker, and so is the French on this site."),
        "shots": [
            ("severity", "Severity first",
             "Every query is classified by its worst outcome for the reader. A refusal "
             "scores perfectly on grounding and register, so without this tier the worst "
             "result would look like a clean pass."),
            ("dimensions", "Ten dimensions, one gap each",
             "Retrieval, grounding, coverage, register, fluency and localization, measured "
             "independently in each language. The line between the dots is the gap."),
            ("media", "Metadata the model never touches",
             "Alt text, captions, credits and transcripts. Untranslated is worse than "
             "missing: it passes the null check in a CMS audit."),
            ("segments", "Where it concentrates",
             "Aggregates say whether the pipeline is failing. Segments by desk, region and "
             "topic say where, which is what routes the fix to an owner."),
        ],

        "k_measures": "04 · What it measures",
        "h_measures": "Each check has a reason.",
        "tiers_h": "Severity tiers, by reader impact",
        "tiers": [
            ("No answer", "French returned nothing usable while English answered."),
            ("Unsupported fact", "French asserted a figure absent from the source."),
            ("Different sources", "The two languages answered from different documents."),
            ("Reduced content", "French was accurate but carried less than English."),
            ("Register", "Accurate and complete, but not Canadian French."),
        ],
        "dims_h": "And beyond the answer itself",
        "dims": [
            ("Grounding, split in two",
             "Against the gold documents and against what retrieval returned. That "
             "separates fabrication from claims that are downstream of a retrieval miss."),
            ("Canadian register",
             "Wrong institutions, wrong statutory terms, metropolitan usage and structural "
             "calques, weighted by severity."),
            ("Localization",
             "<code>$4,100,000</code> where French needs <code>4 100 000 $</code>. A misread "
             "date in a story about a deadline is a factual error no grounding check sees."),
            ("Terminology consistency",
             "Scored one at a time, every answer can look fine while the run names the "
             "same program three ways. French {term_fr} against English {term_en}."),
            ("Answerability",
             "Answered, refused or hedged, per language, with asymmetric cases named."),
            ("Editorial metadata",
             "Tags, SEO descriptions and headlines. {tags} tags dropped in French, "
             "{seo} French SEO descriptions missing."),
        ],

        "k_honest": "05 · Real and modelled",
        "h_honest": "Stated plainly.",
        "real_h": "Real",
        "real_p": ("The BM25 retriever, the bge-m3 embedding backend, every metric, the "
                   "gold labels, EN/FR number normalization, the Canadian French rule set, "
                   "and the validation suite."),
        "model_h": "Modelled",
        "model_p": ("The cause of retrieval divergence in the default BM25 backend, which "
                    "comes from a documented lexicon table. It's also the part the real "
                    "measurement overturned."),
        "frozen_h": "Frozen",
        "frozen_p": ("The generated answers in offline mode, with annotated defects, so "
                     "every detection can be checked against ground truth. "
                     "<code>--live</code> generates them from a real model instead."),

        "k_run": "06 · Run it",
        "h_run": "Python 3.8 or later. Nothing to install.",
        "p_run": ("It runs offline and deterministically. {checks} checks across {suites} "
                  "suites, including a false-positive control on clean French answers."),
        "run_embed": "With real embeddings, via a local Ollama model:",
        "run_live": "With live generation:",
        "cta_repo_2": "Clone it on GitHub",

        "disclaimer": ("All content in the corpus is synthetic. The {docs} news documents, "
                       "their bylines, figures, quotations and media credits were invented "
                       "for evaluation. Nothing reproduces real reporting, real people or any "
                       "organization's output. This is a personal project, not affiliated "
                       "with or endorsed by any broadcaster."),
        "footer_license": "MIT licence",
        "footer_self": "The French on this site passes the harness's own register check.",

        "nf_title": "Not found",
        "nf_h": "That page doesn't exist.",
        "nf_p": "The home page is a good place to start.",
        "nf_home": "Go to the home page",

        "dim_labels": {
            "retrieval_p_at_1": "Retrieval precision@1",
            "retrieval_recall": "Retrieval recall@3",
            "retrieval_ndcg": "Retrieval nDCG@3",
            "grounding_in_context": "Grounding in retrieved context",
            "content_coverage": "Content coverage",
            "fluency_register": "Canadian French register",
            "localization": "Localization",
        },
        # The QFCR table, when the proofreader dropped the form outright.
        "removed_note": "(removed or rephrased)",
    },

    "fr": {
        "lang": "fr",
        "other_name": "English",
        "brand_sub": "Banc d'essai de qualité bilingue",
        "title": "French Drift — votre IA répond-elle aussi bien en français?",
        "description": ("Un banc d'essai à code source ouvert qui mesure si un flux de "
                        "contenu par IA offre un rendement équivalent en anglais et en "
                        "français canadien. Il rend compte de l'écart, et non de deux notes "
                        "de passage distinctes."),
        "skip": "Passer au contenu",
        "nav": [("#finding", "Le constat"), ("#metrics", "Mesures canadiennes"),
                ("#report", "Le rapport"), ("#measures", "Ce qui est mesuré"),
                ("#run", "L'essayer")],
        "nav_report": "Ouvrir le rapport",
        "nav_repo": "GitHub",

        "kicker": "Code source ouvert · Python · Aucune dépendance",
        "h1": "La réponse en français vaut-elle la réponse en anglais?",
        "lede": ("French Drift soumet le même corpus, les mêmes questions et les mêmes "
                 "mesures à un flux de contenu par IA, en anglais et en français canadien, "
                 "en parallèle. Il rend ensuite compte de l'<em>écart</em>. Les deux "
                 "langues peuvent franchir chacune la barre de qualité alors que le "
                 "lectorat francophone reçoit une réponse plus mince, moins fondée, dans un "
                 "registre qui sonne étranger. Noter chaque langue isolément ne permet pas "
                 "de le voir."),
        "cta_report": "Ouvrir le rapport en direct",
        "cta_repo": "Lire le code",
        "hero_alt": ("Le panneau d'ouverture du rapport&nbsp;: une parité de service de "
                     "{parity} et {unserved} requêtes où le lectorat francophone n'a pas "
                     "été servi."),
        "hero_cap": ("Le rapport met en tête le pire résultat vécu par le lectorat "
                     "francophone, et non la moyenne."),

        "stat_parity": "parité de service",
        "stat_parity_d": ("Requêtes où le lectorat francophone a reçu une réponse "
                          "substantiellement équivalente."),
        "stat_qfcr": "fausses corrections",
        "stat_qfcr_d": ("Formes québécoises valides réécrites par une révision "
                        "sommaire («&nbsp;corrige ce texte&nbsp;»)."),
        "stat_cov": "écart de couverture",
        "stat_cov_d": "Les réponses françaises en disent moins que leurs pendants anglais.",
        "stat_media": "médias accessibles",
        "stat_media_d": "Fichiers dont les descriptifs français sont complets.",

        "k_finding": "01 · Le constat",
        "h_finding": "L'hypothèse de départ n'a pas résisté à l'épreuve.",
        "p_finding_1": ("Le banc d'essai partait d'un argument plausible&nbsp;: le "
                        "vocabulaire du français canadien est mal représenté dans les "
                        "modèles de repérage, donc le repérage en français diverge. Le "
                        "moteur par défaut <em>modélise</em> cet écart à partir d'une table "
                        "lexicale rédigée à la main. Nous l'avons ensuite mesuré avec un "
                        "vrai modèle de plongements multilingue, bge-m3, exécuté en local."),
        "th_dim": "Dimension", "th_bm25": "Écart modélisé (BM25)",
        "th_embed": "Écart mesuré (bge-m3)",
        "p_finding_2": ("Pour la précision et le nDCG, le signe s'inverse&nbsp;: le "
                        "repérage en français arrive légèrement <em>en tête</em>. La requête "
                        "autour de laquelle le banc d'essai a été conçu, «&nbsp;où peut-on "
                        "aller pour se réchauffer?&nbsp;», repère parfaitement "
                        "<code>halte-chaleur</code> avec bge-m3."),
        "callout_h": "La divergence est réelle. Elle ne se trouve simplement pas dans le repérage.",
        "callout_p": ("Tous les écarts liés à la génération sont identiques avec les deux "
                      "moteurs&nbsp;: couverture du contenu, registre, chiffres fabriqués, "
                      "localisation. Le lectorat francophone est désavantagé à l'étape de "
                      "la génération, des métadonnées et de la révision. Une équipe qui "
                      "corrigerait d'abord le repérage optimiserait la mauvaise étape. Ce "
                      "résultat n'est visible que parce qu'on a pu comparer directement le "
                      "moteur modélisé et le moteur mesuré."),
        "shot_embed_alt": "Le même rapport, produit avec le moteur de plongements bge-m3.",
        "shot_embed_cap": ("Le même rapport, moteur bge-m3. Chaque mesure et chaque niveau "
                           "sont calculés de la même façon."),
        "embed_link": "Ouvrir le rapport par plongements",

        "k_metrics": "02 · Deux mesures canadiennes",
        "h_metrics": "L'évaluation générique du français ne les voit pas.",
        "mdr_h": "Taux de dérive métropolitaine",
        "mdr_p": ("La fréquence à laquelle une forme québécoise de la source est remplacée "
                  "par son équivalent de France dans la réponse. Seules les substitutions "
                  "comptent. Quand le modèle reformule autour d'un terme, c'est de la "
                  "verbosité, pas de la dérive&nbsp;: ces cas sortent entièrement du "
                  "dénominateur. Ici, {mdr_sub} occasions sur {mdr_n} ont donné lieu à "
                  "une substitution, et {mdr_reph} reformulations ont été exclues."),
        "qfcr_h": "Taux de fausse correction québécoise",
        "qfcr_p": ("Un texte déjà correct en français canadien est soumis à la consigne "
                   "qu'une équipe écrirait vraiment&nbsp;: «&nbsp;Corrige et améliore ce "
                   "texte en français&nbsp;». Le texte de départ est correct par "
                   "construction; toute modification est donc une fausse correction. "
                   "{qfcr_alt} formes valides sur {qfcr_n} ont été détruites."),
        "qfcr_th_from": "Forme québécoise valide", "qfcr_th_to": "Ce qu'a écrit le réviseur",
        "metrics_close": ("Lues ensemble, ces deux mesures distinguent deux défaillances. "
                          "Un bon taux de dérive avec un mauvais taux de fausse correction "
                          "signifie que la génération tient la route et que <strong>c'est la "
                          "révision qui pose problème</strong>&nbsp;: un flux peut produire "
                          "un français canadien impeccable et diffuser malgré tout une copie "
                          "métropolitaine."),
        "shot_drift_alt": "La section du rapport sur la dérive et la fausse correction.",
        "shot_drift_cap": ("Chaque substitution est présentée avec la requête ou la sonde "
                           "dont elle provient."),

        "k_report": "03 · Le rapport",
        "h_report": "Un seul fichier autonome, dans les deux langues.",
        "p_report": ("Le rapport est un fichier HTML unique qui ne fait aucune requête "
                     "externe. L'anglais et le français sont dans le même document, de sorte "
                     "que les deux versions décrivent toujours la même exécution. Son "
                     "français est vérifié par le propre vérificateur de registre du banc "
                     "d'essai, tout comme le français de ce site."),
        "shots": [
            ("severity", "La gravité d'abord",
             "Chaque requête est classée selon son pire résultat pour le lectorat. Un refus "
             "obtient une note parfaite en véracité et en registre; sans ce niveau, le pire "
             "résultat passerait pour une réussite."),
            ("dimensions", "Dix dimensions, un écart chacune",
             "Repérage, véracité, couverture, registre, fluidité et localisation, mesurés "
             "séparément dans chaque langue. Le trait entre les points, c'est l'écart."),
            ("media", "Des métadonnées que le modèle ne touche jamais",
             "Textes de remplacement, légendes, mentions de source et transcriptions. Un "
             "champ non traduit est pire qu'un champ vide&nbsp;: il passe le contrôle de "
             "valeur nulle d'un audit de SGC."),
            ("segments", "Où l'écart se concentre",
             "Les agrégats disent si le flux échoue. La segmentation par pupitre, par région "
             "et par sujet dit où, ce qui permet d'attribuer la correction à un responsable."),
        ],

        "k_measures": "04 · Ce qui est mesuré",
        "h_measures": "Chaque vérification a sa raison d'être.",
        "tiers_h": "Niveaux de gravité, selon l'incidence sur le lectorat",
        "tiers": [
            ("Aucune réponse", "Le français n'a rien fourni d'utilisable alors que l'anglais a répondu."),
            ("Fait non appuyé", "Le français avance un chiffre absent de la source."),
            ("Sources différentes", "Les deux langues ont répondu à partir de documents différents."),
            ("Contenu réduit", "Le français est exact, mais en dit moins que l'anglais."),
            ("Registre", "Exact et complet, mais pas en français canadien."),
        ],
        "dims_h": "Et au-delà de la réponse elle-même",
        "dims": [
            ("La véracité, en deux temps",
             "Par rapport aux documents de référence et par rapport à ce que le repérage a "
             "retourné. On distingue ainsi la fabrication des affirmations qui découlent "
             "d'un repérage manqué."),
            ("Le registre canadien",
             "Mauvaises institutions, mauvais termes législatifs, usages métropolitains et "
             "calques de structure, pondérés selon leur gravité."),
            ("La localisation",
             "<code>$4,100,000</code> là où le français exige <code>4 100 000 $</code>. Une "
             "date mal lue dans un article sur une échéance est une erreur de fait "
             "qu'aucune vérification de véracité ne détecte."),
            ("La constance terminologique",
             "Prise une à une, chaque réponse peut sembler correcte alors que l'exécution "
             "désigne le même programme de trois façons. Français {term_fr} contre "
             "anglais {term_en}."),
            ("La capacité de réponse",
             "Réponse, refus ou réponse évasive, par langue, avec les cas asymétriques "
             "désignés."),
            ("Les métadonnées éditoriales",
             "Mots-clés, descriptions de référencement et titres. {tags} mots-clés perdus en "
             "français, {seo} descriptions de référencement françaises manquantes."),
        ],

        "k_honest": "05 · Réel et modélisé",
        "h_honest": "Dit sans détour.",
        "real_h": "Réel",
        "real_p": ("Le moteur de repérage BM25, le moteur de plongements bge-m3, toutes les "
                   "mesures, les étiquettes de référence, la normalisation des nombres "
                   "EN/FR, les règles du français canadien et la suite de validation."),
        "model_h": "Modélisé",
        "model_p": ("La cause de la divergence du repérage dans le moteur BM25 par défaut, "
                    "tirée d'une table lexicale documentée. C'est aussi la partie que la "
                    "mesure réelle a renversée."),
        "frozen_h": "Figé",
        "frozen_p": ("Les réponses générées en mode hors ligne, avec leurs défauts annotés, "
                     "pour que chaque détection puisse être vérifiée. <code>--live</code> "
                     "les génère plutôt à partir d'un vrai modèle."),

        "k_run": "06 · L'essayer",
        "h_run": "Python 3.8 ou plus récent. Rien à installer.",
        "p_run": ("Il s'exécute hors ligne, de façon déterministe. {checks} vérifications "
                  "réparties en {suites} suites, dont un contrôle des faux positifs sur des "
                  "réponses françaises sans défaut."),
        "run_embed": "Avec de vrais plongements, au moyen d'un modèle Ollama local&nbsp;:",
        "run_live": "Avec génération en direct&nbsp;:",
        "cta_repo_2": "Le cloner sur GitHub",

        "disclaimer": ("Tout le contenu du corpus est fictif. Les {docs} articles, leurs "
                       "signatures, chiffres, citations et mentions de source ont été "
                       "inventés aux fins de l'évaluation. Rien ne reproduit de vrais "
                       "reportages, de vraies personnes ni la production d'une organisation. "
                       "Il s'agit d'un projet personnel, sans lien avec un diffuseur et sans "
                       "l'appui d'aucun diffuseur."),
        "footer_license": "Licence MIT",
        "footer_self": ("Le français de ce site passe le propre contrôle de registre du banc "
                        "d'essai."),

        "nf_title": "Page introuvable",
        "nf_h": "Cette page n'existe pas.",
        "nf_p": "La page d'accueil est un bon point de départ.",
        "nf_home": "Aller à la page d'accueil",

        "dim_labels": {
            "retrieval_p_at_1": "Précision du repérage@1",
            "retrieval_recall": "Rappel du repérage@3",
            "retrieval_ndcg": "nDCG du repérage@3",
            "grounding_in_context": "Véracité dans le contexte repéré",
            "content_coverage": "Couverture du contenu",
            "fluency_register": "Registre du français canadien",
            "localization": "Localisation",
        },
        # The QFCR table, when the proofreader dropped the form outright.
        "removed_note": "(supprimée ou reformulée)",
    },
}
