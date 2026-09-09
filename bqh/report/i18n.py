"""Bilingual UI strings for the dashboard.

The French here is Canadian French to Radio-Canada conventions — a report about
Canadian French quality written in metropolitan French would undercut its own
argument. `tests/test_i18n.py` runs these strings through the harness's own
register checker, so the tool holds its own copy to the standard it measures.

Terminology notes:
  · "taux d'inoccupation", "taxe fonciere", "conseiller scolaire" — Canadian
    administrative usage, not the France equivalents.
  · "reperage" for retrieval: "recherche d'information" is the broader field;
    "reperage" is the standard Quebec term for the retrieval operation itself.
  · "veracite" for grounding: no settled French term exists, and "ancrage" reads
    as a calque here. "Veracite factuelle" states what is measured.
  · Typography follows Canadian French practice: no space before ":" (unlike
    France), non-breaking space before "%" and inside large numbers.
"""

STRINGS = {
    "en": {
        "lang_name": "English",
        "other_lang": "Français",
        "eyebrow": "Bilingual Quality Harness",
        "title": "EN / FR output equivalence for a journalistic RAG workflow",
        "intro": ("Measures whether an AI content pipeline performs "
                  "<em>equivalently</em> in English and Canadian French — not "
                  "whether it performs adequately in each. The unit of analysis "
                  "is the gap between the two, because that gap is what a "
                  "bilingual public-service mandate actually commits to."),
        "meta_docs": "parallel queries", "meta_docs2": "parallel documents",
        "meta_cf": "Canadian French (Radio-Canada conventions)",
        "meta_mode": "mode", "meta_retr": "retrieval",
        "parity_lab": "Service parity",
        "eq_index": "Equivalence index",
        "hero_tail": ("A mean over all queries understates this: bilingual "
                      "public service is not an average commitment, so the "
                      "harness leads with the worst outcome a reader actually "
                      "experienced."),
        "unserved_one": "query where the French reader was not served",
        "unserved_many": "queries where the French reader was not served",
        "unserved_tail": ("— either no answer was returned, or the answer "
                          "asserted a fact the source does not support. Both "
                          "are mandate failures, not quality deltas."),
        "diverged_mid": "of", "diverged_tail": ("queries diverged between "
                        "English and French, though none left the French reader "
                        "unserved."),
        "no_div": "No divergence detected across the query set.",
        "h_experience": "What the French reader experienced",
        "sub_experience": ("Every query classified by its worst outcome, "
                           "ordered by reader impact."),
        "h_dims": "Quality dimensions",
        "sub_dims": ("Each row is one metric measured independently in both "
                     "languages. The connecting line is the equivalence gap."),
        "h_drift": "Metropolitan drift and false correction",
        "sub_drift": ("Two Canadian-specific metrics generic French evaluation "
                      "does not provide."),
        "mdr_lab": "Metropolitan drift rate",
        "qfcr_lab": "Quebec false correction rate",
        "reph_lab": "Rephrased — not drift",
        "h_media": "Media metadata — images, video, audio",
        "sub_media": ("Alt text, captions, credits, and transcripts. The asset "
                      "is reused across both language sites; the descriptors "
                      "often are not."),
        "a11y_lab": "Accessible in French",
        "h_ed": "Editorial metadata",
        "sub_ed": ("Tags and SEO descriptions drive archive retrieval and topic "
                   "pages — a French story tagged with fewer concepts is less "
                   "discoverable in French."),
        "tags_lab": "Tags dropped in FR", "seo_lab": "Missing FR SEO",
        "edpar_lab": "Editorial parity",
        "h_seg": "Where divergence concentrates",
        "sub_seg": ("An aggregate says whether the pipeline is failing; "
                    "segmentation says where, which is what routes it to an "
                    "owner."),
        "h_lang": "Terminology and answerability",
        "sub_lang": ("Consistency and refusal behaviour across the whole run — "
                     "failures that are invisible when answers are scored one "
                     "at a time."),
        "term_lab": "FR terminology consistency",
        "answer_lab": "FR answer rate",
        "asym_lab": "Answered in one language only",
        "th_concept": "Concept", "th_canonical": "Canonical form",
        "th_uses": "Canonical use", "th_mentions": "Mentions",
        "term_note": ("A pipeline can render the same programme three ways "
                      "across a run and each answer looks fine alone. It breaks "
                      "archive search and house style, and is systematically "
                      "worse in the second language where no single reviewer "
                      "sees all the output."),
        "answer_note": ("A refusal asserts nothing, so it scores perfectly on "
                        "grounding and register. Refusing more often in one "
                        "language is rationing service by language, and "
                        "conventional quality metrics cannot see it."),
        "h_lex": "Root cause — lexicon coverage",
        "sub_lex": ("Canadian French administrative and regional vocabulary the "
                    "retriever represents weakly. This is what converts a red "
                    "number into a fix."),
        "h_detail": "Per-query detail",
        "sub_detail": ("Full result table — the accessible view of every number "
                       "above. Divergent queries first; perfect scores are "
                       "dimmed so the values that differ carry the eye."),
        "th_dim": "Dimension", "th_status": "Status", "th_gap": "Gap",
        "th_query": "Query", "th_class": "Class", "th_issues": "Detected issues",
        "th_note": "Note", "th_asset": "Asset", "th_kind": "Kind",
        "th_fields": "Field states", "th_score": "Score",
        "th_a11y": "Accessibility", "th_doc": "Document", "th_desk": "Desk",
        "th_tags": "FR/EN tags", "th_seo": "SEO description",
        "th_term": "Term (stemmed)", "th_cov": "Model coverage",
        "th_affected": "Affected queries", "th_qform": "Quebec form",
        "th_replaced": "Replaced with", "th_where": "Where", "th_n": "n",
        "th_valid": "Valid Quebec form", "th_changed": "Proofreader changed it to",
        "th_probe": "Probe", "th_en_ans": "EN answer",
        "legend_en": "English", "legend_fr": "Canadian French",
        "legend_scale": "— scale 0 to 1, higher is better",
        "eq_ok": "equivalent", "eq_bad": "divergent",
        "by_desk": "By desk", "by_region": "By region", "by_topic": "By topic",
        "th_div": "Div.", "th_unsvd": "Unsvd", "thin": "thin",
        "mdr_note": ("<strong>MDR</strong> counts substitutions only: {sub} of "
                     "{scored} scored opportunities. {reph} cases where the "
                     "model rephrased around the term are excluded from the "
                     "denominator entirely — verbosity is not drift, and "
                     "scoring it either way would bias the rate."),
        "qfcr_note": ("<strong>QFCR</strong> sends already-correct Canadian "
                      "French through a naive &ldquo;corrige ce texte&rdquo; "
                      "prompt, so any alteration is a false correction by "
                      "construction: {alt} of {present} valid Quebec forms were "
                      "altered. A pipeline can generate perfect Canadian French "
                      "and still ship metropolitan copy because the "
                      "proofreading step rewrote it."),
        "media_note": ("{bad} of {total} assets leave French users without "
                       "access to content English users can reach — missing or "
                       "untranslated alt text, or a missing transcript on timed "
                       "media. Untranslated is worse than missing: it passes a "
                       "null check in a CMS audit."),
        "footer": ("Equivalence threshold {thr} on any dimension. Grounding is "
                   "scored against gold context (fabrication) and against "
                   "retrieved context (in-context support) separately, so a "
                   "retrieval miss is not misreported as a hallucination. "
                   "Offline mode uses a frozen corpus for determinism; "
                   "<code>--live</code> generates answers through a live model."),
        "sev": {"no_answer": "No answer returned", "wrong_fact": "Unsupported fact",
                "wrong_docs": "Different sources", "omission": "Reduced content",
                "register": "Register"},
        "dims": {
            "retrieval_p_at_1": ("Retrieval precision@1", "Top result is a gold document"),
            "retrieval_recall": ("Retrieval recall@3", "Gold documents found in top 3"),
            "retrieval_ndcg": ("Retrieval nDCG@3", "Rank quality of gold documents"),
            "grounding_numeric": ("Grounding — fabrication", "Figures absent from the source document"),
            "grounding_in_context": ("Grounding — in retrieved context", "Figures unsupported by what retrieval returned"),
            "grounding_entailment": ("Grounding — lexical entailment", "Content words traceable to source"),
            "content_coverage": ("Content coverage vs EN", "Does FR carry the same facts as EN"),
            "fluency_register": ("Canadian French register", "Metropolitan forms and anglicisms"),
            "fluency_overall": ("Fluency (composite)", "Register and readability combined"),
            "localization": ("Localization conventions", "Dates, currency, decimals, units"),
        },
    },
    "fr": {
        "lang_name": "Français",
        "other_lang": "English",
        "eyebrow": "Banc d'essai de qualité bilingue",
        "title": "Équivalence des sorties EN/FR pour un flux journalistique à génération augmentée",
        "intro": ("Mesure si un flux de contenu par IA offre un rendement "
                  "<em>équivalent</em> en anglais et en français canadien — et "
                  "non s'il offre un rendement acceptable dans chaque langue. "
                  "L'unité d'analyse est l'écart entre les deux, car c'est cet "
                  "écart que vise un mandat de service public bilingue."),
        "meta_docs": "requêtes parallèles", "meta_docs2": "documents parallèles",
        "meta_cf": "français canadien (normes de Radio-Canada)",
        "meta_mode": "mode", "meta_retr": "repérage",
        "parity_lab": "Parité de service",
        "eq_index": "Indice d'équivalence",
        "hero_tail": ("Une moyenne sur l'ensemble des requêtes en atténue la "
                      "portée&nbsp;: le service public bilingue n'est pas un "
                      "engagement moyen. Le banc d'essai met donc en tête le "
                      "pire résultat vécu par une lectrice ou un lecteur."),
        "unserved_one": "requête où le lectorat francophone n'a pas été servi",
        "unserved_many": "requêtes où le lectorat francophone n'a pas été servi",
        "unserved_tail": ("— soit aucune réponse n'a été fournie, soit la "
                          "réponse avance un fait que la source n'appuie pas. "
                          "Dans les deux cas, il s'agit d'un manquement au "
                          "mandat, et non d'un simple écart de qualité."),
        "diverged_mid": "sur", "diverged_tail": ("requêtes divergent entre "
                        "l'anglais et le français, sans toutefois priver le "
                        "lectorat francophone d'une réponse."),
        "no_div": "Aucune divergence détectée dans l'ensemble des requêtes.",
        "h_experience": "Ce qu'a vécu le lectorat francophone",
        "sub_experience": ("Chaque requête classée selon son pire résultat, en "
                           "ordre d'incidence sur le lectorat."),
        "h_dims": "Dimensions de qualité",
        "sub_dims": ("Chaque ligne présente une mesure évaluée séparément dans "
                     "les deux langues. Le trait de liaison représente l'écart "
                     "d'équivalence."),
        "h_drift": "Dérive métropolitaine et fausse correction",
        "sub_drift": ("Deux mesures propres au contexte canadien que "
                      "l'évaluation générique du français ne fournit pas."),
        "mdr_lab": "Taux de dérive métropolitaine",
        "qfcr_lab": "Taux de fausse correction québécoise",
        "reph_lab": "Reformulations — hors dérive",
        "h_media": "Métadonnées des médias — images, vidéos, audio",
        "sub_media": ("Textes de remplacement, légendes, mentions de source et "
                      "transcriptions. Le fichier est réutilisé dans les deux "
                      "sites linguistiques; les descriptifs, souvent pas."),
        "a11y_lab": "Accessibles en français",
        "h_ed": "Métadonnées éditoriales",
        "sub_ed": ("Les mots-clés et les descriptions de référencement "
                   "alimentent le repérage en archives et les pages "
                   "thématiques&nbsp;: un reportage français comportant moins de "
                   "mots-clés est plus difficile à trouver en français."),
        "tags_lab": "Mots-clés perdus en FR", "seo_lab": "Descriptions FR absentes",
        "edpar_lab": "Parité éditoriale",
        "h_seg": "Où se concentre la divergence",
        "sub_seg": ("Un résultat global indique si le flux échoue; la "
                    "segmentation indique où, ce qui permet d'en confier la "
                    "correction à une équipe."),
        "h_lang": "Terminologie et capacité de réponse",
        "sub_lang": ("Cohérence et comportement de refus sur l'ensemble du "
                     "cycle — des défaillances invisibles lorsque les réponses "
                     "sont évaluées une à une."),
        "term_lab": "Cohérence terminologique FR",
        "answer_lab": "Taux de réponse FR",
        "asym_lab": "Réponse dans une seule langue",
        "th_concept": "Notion", "th_canonical": "Forme retenue",
        "th_uses": "Emploi de la forme retenue", "th_mentions": "Occurrences",
        "term_note": ("Un flux peut rendre un même programme de trois façons "
                      "au cours d'un cycle, et chaque réponse paraît correcte "
                      "isolément. Cela nuit à la recherche en archives et au "
                      "code rédactionnel, et le problème est systématiquement "
                      "plus marqué dans la seconde langue, où personne ne voit "
                      "l'ensemble de la production."),
        "answer_note": ("Un refus n'avance rien; il obtient donc une note "
                        "parfaite en véracité et en registre. Refuser plus "
                        "souvent dans une langue revient à rationner le service "
                        "selon la langue, et les mesures de qualité "
                        "habituelles ne peuvent pas le déceler."),
        "h_lex": "Cause profonde — couverture lexicale",
        "sub_lex": ("Vocabulaire administratif et régional du français canadien "
                    "faiblement représenté par le moteur de repérage. C'est ce "
                    "qui transforme un chiffre en correctif."),
        "h_detail": "Détail par requête",
        "sub_detail": ("Tableau complet des résultats — la version accessible de "
                       "chacun des chiffres ci-dessus. Les requêtes divergentes "
                       "figurent en tête; les résultats parfaits sont atténués "
                       "afin de mettre en évidence les valeurs qui diffèrent."),
        "th_dim": "Dimension", "th_status": "État", "th_gap": "Écart",
        "th_query": "Requête", "th_class": "Catégorie",
        "th_issues": "Problèmes détectés", "th_note": "Remarque",
        "th_asset": "Fichier", "th_kind": "Type",
        "th_fields": "État des champs", "th_score": "Note",
        "th_a11y": "Accessibilité", "th_doc": "Document", "th_desk": "Pupitre",
        "th_tags": "Mots-clés FR/EN", "th_seo": "Description de référencement",
        "th_term": "Terme (radical)", "th_cov": "Couverture du modèle",
        "th_affected": "Requêtes touchées", "th_qform": "Forme québécoise",
        "th_replaced": "Remplacée par", "th_where": "Occurrence", "th_n": "n",
        "th_valid": "Forme québécoise valide",
        "th_changed": "Remplacée par la correction", "th_probe": "Sonde",
        "th_en_ans": "Réponse EN",
        "legend_en": "Anglais", "legend_fr": "Français canadien",
        "legend_scale": "— échelle de 0 à 1; plus le résultat est élevé, mieux c'est",
        "eq_ok": "équivalent", "eq_bad": "divergent",
        "by_desk": "Par pupitre", "by_region": "Par région",
        "by_topic": "Par sujet",
        "th_div": "Div.", "th_unsvd": "Non serv.", "thin": "faible",
        "mdr_note": ("Le <strong>TDM</strong> ne compte que les substitutions&nbsp;: "
                     "{sub} occasions sur {scored} retenues. Les {reph} cas où "
                     "le modèle a reformulé plutôt que de substituer sont exclus "
                     "du dénominateur — la verbosité n'est pas de la dérive, et "
                     "les compter d'une façon ou d'une autre fausserait le taux."),
        "qfcr_note": ("Le <strong>TFCQ</strong> soumet un texte déjà correct en "
                      "français canadien à une consigne de révision sommaire "
                      "(«&nbsp;corrige ce texte&nbsp;»); toute modification "
                      "constitue donc une fausse correction&nbsp;: {alt} formes "
                      "québécoises valides sur {present} ont été altérées. Un "
                      "flux peut produire un français canadien impeccable et "
                      "diffuser malgré tout une copie métropolitaine parce que "
                      "l'étape de révision l'a réécrite."),
        "media_note": ("{bad} fichiers sur {total} privent le public francophone "
                       "d'un contenu accessible au public anglophone — texte de "
                       "remplacement absent ou non traduit, ou transcription "
                       "manquante pour un média chronométré. Un champ non "
                       "traduit est pire qu'un champ vide&nbsp;: il passe le "
                       "contrôle de valeur nulle d'un audit de SGC."),
        "footer": ("Seuil d'équivalence de {thr} pour chaque dimension. La "
                   "véracité est évaluée séparément par rapport au contexte de "
                   "référence (fabrication) et au contexte repéré (appui "
                   "contextuel), de sorte qu'un échec de repérage n'est pas "
                   "rapporté à tort comme une hallucination. Le mode hors ligne "
                   "s'appuie sur un corpus figé, gage de reproductibilité; "
                   "<code>--live</code> génère les réponses au moyen d'un "
                   "modèle en direct."),
        "sev": {"no_answer": "Aucune réponse fournie",
                "wrong_fact": "Fait non appuyé",
                "wrong_docs": "Sources différentes",
                "omission": "Contenu réduit", "register": "Registre"},
        "dims": {
            "retrieval_p_at_1": ("Précision du repérage@1", "Le premier résultat est un document de référence"),
            "retrieval_recall": ("Rappel du repérage@3", "Documents de référence trouvés parmi les 3 premiers"),
            "retrieval_ndcg": ("nDCG du repérage@3", "Qualité du rangement des documents de référence"),
            "grounding_numeric": ("Véracité — fabrication", "Chiffres absents du document source"),
            "grounding_in_context": ("Véracité — contexte repéré", "Chiffres non appuyés par le contexte repéré"),
            "grounding_entailment": ("Véracité — appui lexical", "Mots de contenu attribuables à la source"),
            "content_coverage": ("Couverture du contenu c. EN", "Le français rend-il les mêmes faits que l'anglais"),
            "fluency_register": ("Registre du français canadien", "Formes métropolitaines et anglicismes"),
            "fluency_overall": ("Fluidité (composite)", "Registre et lisibilité combinés"),
            "localization": ("Conventions de localisation", "Dates, devises, décimales, unités"),
        },
    },
}
