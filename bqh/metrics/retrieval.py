"""Bilingual retrieval scoring.

The retriever is a TF-IDF/BM25-style lexical scorer built from scratch (no
sklearn dependency). The bilingual realism comes from `LEXICON_COVERAGE`: a
model tuned predominantly on metropolitan French represents Canadian
administrative and regional vocabulary weakly. We model that as a per-term
recall weight applied at query time on the FR side only.

This is the honest framing to use in conversation: the *effect* is simulated
from a documented lexicon, but the metric computation, the gold labels, and
the divergence arithmetic are real. Swap `score_query` for a call to a real
embedding endpoint and every number downstream still computes.
"""
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict

# Canadian French terms under-represented in metropolitan-tuned embedding
# spaces. Value = fraction of the term's normal retrieval weight the model
# actually recovers. Sourced from the divergence classes annotated in
# corpus/queries.json.
LEXICON_COVERAGE = {
    "assurance-emploi": 0.35,
    "assurable": 0.45,
    "assurables": 0.45,
    "prestataire": 0.50,
    "prestataires": 0.50,
    "halte-chaleur": 0.20,
    "haltes-chaleur": 0.20,
    "conseiller": 0.55,
    "conseillers": 0.55,
    "scolaire": 0.70,
    "scolaires": 0.70,
    "banlieusard": 0.30,
    "banlieusards": 0.30,
    "minoritaire": 0.60,
    "closm": 0.25,
    "foncière": 0.65,
    "poste": 0.75,
    "péage": 0.70,
    "courriel": 0.40,
    "magasinage": 0.30,
    "débosselage": 0.25,
}

# Populated after `stem` is defined; keys the lexicon by stemmed form so
# coverage survives tokenization.
_STEMMED_COVERAGE = {}

STOP_EN = {"the", "a", "an", "of", "to", "in", "for", "on", "and", "is", "are",
           "was", "were", "do", "does", "did", "what", "which", "how", "many",
           "much", "who", "where", "why", "by", "at", "with", "as", "that",
           "from", "its", "their", "it", "be", "has", "have", "will", "can"}
STOP_FR = {"le", "la", "les", "un", "une", "des", "de", "du", "d", "l", "à",
           "au", "aux", "et", "en", "pour", "dans", "sur", "par", "que", "qui",
           "quel", "quelle", "quels", "quelles", "combien", "comment",
           "pourquoi", "où", "est", "sont", "a", "ont", "ce", "cette", "ces",
           "il", "elle", "ils", "elles", "se", "sa", "son", "ses", "leur",
           "leurs", "plus", "pas", "ne", "y", "t", "s", "the", "of"}


def normalize(text):
    text = text.lower()
    text = unicodedata.normalize("NFC", text)
    return text


def tokenize(text, lang):
    text = normalize(text)
    # keep intra-word hyphens (assurance-emploi, halte-chaleur) and apostrophes split
    text = re.sub(r"['’]", " ", text)
    toks = re.findall(r"[a-zà-öø-ÿ0-9]+(?:-[a-zà-öø-ÿ0-9]+)*", text)
    stop = STOP_FR if lang == "fr" else STOP_EN
    return [stem(t, lang) for t in toks if t not in stop and len(t) > 1]


# ---- light morphological stemming ---------------------------------------
# Suffix stripping only. Enough to bridge warming/warm, commuters/commut,
# assurables/assurable, effectifs/effectif — the ordinary inflectional gap
# that would otherwise make BM25 miss an obviously relevant document. Applied
# identically to both languages so it cannot itself create divergence.

_EN_SUFFIXES = ("ingly", "edly", "ing", "ers", "er", "ed", "es", "s", "ly")
_FR_SUFFIXES = ("ements", "ement", "ables", "able", "ions", "ants", "ant",
                "eurs", "euse", "aux", "ales", "ale", "els", "es", "s", "e")


def stem(token, lang):
    if "-" in token:
        return "-".join(stem(part, lang) for part in token.split("-"))
    if token.isdigit():
        return token
    suffixes = _FR_SUFFIXES if lang == "fr" else _EN_SUFFIXES
    for suf in suffixes:
        if token.endswith(suf) and len(token) - len(suf) >= 4:
            return token[: -len(suf)]
    return token


class BilingualRetriever:
    """BM25 retriever with a per-language lexicon-coverage weighting layer."""

    K1 = 1.5
    B = 0.75

    def __init__(self, documents, lang, apply_coverage=True):
        self.lang = lang
        self.apply_coverage = apply_coverage and lang == "fr"
        self.doc_ids = []
        self.doc_tokens = {}
        self.df = Counter()

        for doc in documents:
            side = doc[lang]
            toks = tokenize(side["title"] + " " + side["body"], lang)
            self.doc_ids.append(doc["doc_id"])
            self.doc_tokens[doc["doc_id"]] = Counter(toks)
            for t in set(toks):
                self.df[t] += 1

        self.N = len(self.doc_ids)
        self.avgdl = sum(sum(c.values()) for c in self.doc_tokens.values()) / max(self.N, 1)

    def _idf(self, term):
        n = self.df.get(term, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def coverage(self, term):
        """Fraction of this term's retrieval signal the model actually recovers."""
        if not self.apply_coverage:
            return 1.0
        return _STEMMED_COVERAGE.get(term, LEXICON_COVERAGE.get(term, 1.0))

    def score_query(self, query_text):
        """BM25, with the lexicon-coverage penalty applied to the *matched term*.

        Coverage degrades the query-document association for a term, so it
        applies whether the weak vocabulary sits in the query, the document, or
        both. Applying it to the matched term (rather than query tokens alone)
        is what lets a document whose distinguishing vocabulary is Canadian
        French lose rank to a lexically blander competitor.
        """
        q_toks = tokenize(query_text, self.lang)
        scores = defaultdict(float)
        for term in q_toks:
            idf = self._idf(term)
            cov = self.coverage(term)
            for doc_id in self.doc_ids:
                tf = self.doc_tokens[doc_id].get(term, 0)
                if not tf:
                    continue
                dl = sum(self.doc_tokens[doc_id].values())
                denom = tf + self.K1 * (1 - self.B + self.B * dl / self.avgdl)
                scores[doc_id] += idf * (tf * (self.K1 + 1)) / denom * cov
        # Documents whose distinguishing vocabulary is weakly represented are
        # themselves harder to surface: apply the mean coverage of the doc's
        # high-IDF terms as a retrievability factor.
        for doc_id in list(scores):
            scores[doc_id] *= self._doc_retrievability(doc_id)
        return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))

    def _doc_retrievability(self, doc_id):
        """Mean coverage over the document's weak-lexicon terms (1.0 if none)."""
        if not self.apply_coverage:
            return 1.0
        covs = [self.coverage(t) for t in self.doc_tokens[doc_id]
                if self.coverage(t) < 1.0]
        if not covs:
            return 1.0
        # Dampened: a doc is penalised, but one rare term does not erase it.
        mean_cov = sum(covs) / len(covs)
        return mean_cov ** 0.5

    def retrieve(self, query_text, k=5):
        return [d for d, _ in self.score_query(query_text)[:k]]

    def weak_terms(self, query_text, doc_ids=None):
        """Weak-lexicon terms in the query or in the candidate documents.

        This is the explainability hook: it names the specific Canadian-French
        vocabulary responsible for a divergence, which is what makes a finding
        actionable rather than just a red number on a dashboard.
        """
        terms = set(tokenize(query_text, self.lang))
        for doc_id in (doc_ids or []):
            terms |= set(self.doc_tokens.get(doc_id, {}))
        out = [{"term": display_term(t), "stem": t, "coverage": self.coverage(t)}
               for t in terms if self.coverage(t) < 1.0]
        return sorted(out, key=lambda x: x["coverage"])


# ---- metrics -------------------------------------------------------------

def precision_at_k(retrieved, gold, k):
    top = retrieved[:k]
    if not top:
        return 0.0
    return sum(1 for d in top if d in gold) / len(top)


def recall_at_k(retrieved, gold, k):
    if not gold:
        return 0.0
    return sum(1 for d in retrieved[:k] if d in gold) / len(gold)


def reciprocal_rank(retrieved, gold):
    for i, d in enumerate(retrieved, 1):
        if d in gold:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved, gold, k):
    dcg = sum((1.0 / math.log2(i + 1)) for i, d in enumerate(retrieved[:k], 1) if d in gold)
    ideal = sum((1.0 / math.log2(i + 1)) for i in range(1, min(len(gold), k) + 1))
    return dcg / ideal if ideal else 0.0


_STEMMED_COVERAGE.update(
    {stem(term, "fr"): cov for term, cov in LEXICON_COVERAGE.items()}
)

# Stemming is right for matching but wrong for reading: a report that names
# "assuranc-emploi" as the problem term looks broken. Keep a display form.
_DISPLAY_FORM = {}
for _term in LEXICON_COVERAGE:
    _st = stem(_term, "fr")
    # Prefer the shortest surface form that stems here (the lemma, not a plural).
    if _st not in _DISPLAY_FORM or len(_term) < len(_DISPLAY_FORM[_st]):
        _DISPLAY_FORM[_st] = _term


def display_term(stemmed):
    """Human-readable surface form for a stemmed lexicon key."""
    return _DISPLAY_FORM.get(stemmed, stemmed)
