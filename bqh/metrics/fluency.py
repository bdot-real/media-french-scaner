"""Fluency and register for Canadian French journalistic copy.

This is deliberately *not* a generic French fluency score. A sentence can be
perfectly grammatical metropolitan French and still be wrong for CBC/
Radio-Canada: 'week-end' instead of 'fin de semaine', 'email' instead of
'courriel', 'centre d'hebergement chauffe' instead of 'halte-chaleur'.

Generic multilingual evaluation misses this entirely, which is the whole
argument for a purpose-built harness: the model can score well on French and
still not be publishable in Canadian French.

Rules are drawn from Canadian public-broadcast style conventions and the
federal terminology standard (Termium). Each carries a severity:
  high   - factually or institutionally wrong in Canada (statutory terms)
  medium - reads as foreign to a Canadian audience
  low    - stylistic preference
"""
import re

# (pattern, preferred, severity, note)
REGISTER_RULES = [
    (r"\bweek-?ends?\b", "fin de semaine", "medium",
     "Metropolitan usage; Canadian French uses 'fin de semaine'."),
    (r"\be-?mails?\b", "courriel", "medium",
     "Anglicism; 'courriel' is the standard Canadian term."),
    (r"\bshopping\b", "magasinage", "medium", "Anglicism."),
    (r"\bparking\b", "stationnement", "medium", "Anglicism."),
    (r"\bjob\b", "emploi", "medium", "Anglicism in a news register."),
    (r"\bcash\b", "argent comptant", "medium", "Anglicism."),
    (r"\bnavetteurs?\b", "banlieusard", "low",
     "Metropolitan preference; Canadian copy favours 'banlieusard'."),
    (r"\bchômage\s+partiel\b", "travail partagé", "medium",
     "French administrative term; the Canadian programme is 'travail partagé'."),
    (r"\bpôle\s+emploi\b", "Service Canada", "high",
     "French institution; wrong jurisdiction for Canadian copy."),
    (r"\bsécurité\s+sociale\b", "assurance-emploi / assurance maladie", "high",
     "French institution; Canada has no 'Securite sociale'."),
    (r"\bcentres?\s+d['’]hébergement\s+chauff", "halte-chaleur", "high",
     "Emergency warming facilities are 'haltes-chaleur' in Canadian usage."),
    # Matches the bare noun too: in school-board copy 'administrateur' alone
    # is already the wrong office, with or without a 'scolaire' qualifier.
    (r"\badministrateurs?\b(?!\s+(?:général|délégué))", "conseiller scolaire", "high",
     "The elected school-board office is 'conseiller scolaire' in Canada; "
     "'administrateur' denotes an appointed manager."),
    # CLOSM: flag any loose paraphrase of the statutory term. 'communautes
    # francophones' also silently drops anglophone minority communities in
    # Quebec, which the statutory term covers.
    (r"\b(?:collectivités?|communautés?)\s+francophones?"
     r"(?:\s+(?:minoritaires?|en\s+situation\s+minoritaire))?\b",
     "communauté de langue officielle en situation minoritaire", "high",
     "CLOSM is a statutory term; the paraphrase loses legal precision and "
     "excludes anglophone minority communities."),
    (r"\bimpôts?\s+locaux?\b", "taxe foncière", "medium",
     "Canadian municipal term is 'taxe fonciere'."),
    (r"\bassurance\s+chômage\b", "assurance-emploi", "high",
     "Programme was renamed 'assurance-emploi' in 1996."),
    (r"\bdollars?\s+canadiens?\b", "dollars", "low",
     "Redundant in domestic Canadian copy."),
    (r"\bsoixante-dix\b|\bquatre-vingt-dix\b", "septante/nonante not used; fine",
     "low", "Standard in Canada — informational only."),
]

# Structural anglicisms: English syntax carried into French.
CALQUE_RULES = [
    (r"\bà\s+chaque\s+fois\s+que\b", "chaque fois que", "low", "Calque."),
    (r"\bbasé\s+sur\b", "fondé sur / en fonction de", "medium",
     "Calque of 'based on'."),
    (r"\ben\s+charge\s+de\b", "responsable de", "medium", "Calque of 'in charge of'."),
    (r"\bopportunité\b", "occasion / possibilité", "low",
     "False friend when used for 'opportunity'."),
    (r"\bdéfinitivement\b", "certainement / assurément", "low",
     "False friend for 'definitely'."),
    (r"\brencontrer\s+(?:les\s+)?(?:exigences|besoins|objectifs)\b",
     "satisfaire aux / répondre aux", "medium", "Calque of 'meet requirements'."),
]

SEVERITY_PENALTY = {"high": 1.0, "medium": 0.5, "low": 0.15}


def register_check(text, lang):
    """Canadian-French register violations. EN text returns a clean result."""
    if lang != "fr":
        return {"score": 1.0, "violations": []}
    violations = []
    for pattern, preferred, severity, note in REGISTER_RULES + CALQUE_RULES:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            violations.append({
                "found": m.group().strip(),
                "preferred": preferred,
                "severity": severity,
                "note": note,
            })
    # Normalise by sentence count so long copy is not penalised for length.
    sentences = max(len([s for s in re.split(r"[.!?]+", text) if s.strip()]), 1)
    penalty = sum(SEVERITY_PENALTY[v["severity"]] for v in violations) / sentences
    return {"score": max(0.0, 1.0 - penalty), "violations": violations}


def readability(text, lang):
    """Sentence-length readability, scaled to news-copy norms.

    French runs roughly 15-20% longer than English for the same content, so a
    naive shared threshold would systematically flag French as less readable.
    The target band is language-adjusted to avoid that artefact.
    """
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return {"score": 1.0, "avg_sentence_len": 0.0}
    lengths = [len(s.split()) for s in sentences]
    avg = sum(lengths) / len(lengths)
    target = 26.0 if lang == "fr" else 22.0  # broadcast-news comfortable max
    if avg <= target:
        score = 1.0
    else:
        score = max(0.0, 1.0 - (avg - target) / target)
    return {"score": score, "avg_sentence_len": round(avg, 1),
            "longest": max(lengths)}


def fluency_score(text, lang):
    reg = register_check(text, lang)
    read = readability(text, lang)
    return {
        "score": round(0.7 * reg["score"] + 0.3 * read["score"], 4),
        "register": reg,
        "readability": read,
    }
