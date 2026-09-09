"""Dense retrieval through a local embedding model (Ollama).

This is the module that removes the harness's biggest credibility problem.

The BM25 path in `retrieval.py` simulates bilingual divergence with a
hand-authored `LEXICON_COVERAGE` table — which means the divergence it reports
was, in a real sense, asserted rather than measured. This module replaces that
with a real multilingual embedding model: query and documents are embedded, and
retrieval divergence is whatever the model's actual representation produces.

Nothing else in the harness changes. Both retrievers expose `retrieve()` and
`weak_terms()`, so metrics, severity tiers, and the dashboard are identical
either way — the comparison between the two backends is itself informative.

Setup:
    brew install ollama && ollama serve
    ollama pull bge-m3          # multilingual, strong on French

`bge-m3` is the default because it is explicitly multilingual and trained on
substantial French data. `nomic-embed-text` is English-centric and will
overstate divergence for the wrong reason — its French weakness is a property
of the model choice, not of Canadian French. Choosing an English-centric model
and reporting the resulting gap as a finding would be exactly the kind of
motivated measurement this module exists to avoid.
"""
import json
import math
import urllib.error
import urllib.request

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "bge-m3"


class OllamaUnavailable(RuntimeError):
    """Ollama is not reachable, or the requested model is not pulled."""


def _post(host, path, payload, timeout=120):
    req = urllib.request.Request(
        host.rstrip("/") + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        raise OllamaUnavailable(f"HTTP {exc.code} from Ollama: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise OllamaUnavailable(
            f"Cannot reach Ollama at {host}: {exc}. "
            "Start it with `ollama serve`."
        ) from exc


def check_available(host=DEFAULT_HOST, model=DEFAULT_MODEL):
    """Return (ok, message). Never raises — callers use it to decide fallback."""
    try:
        req = urllib.request.Request(host.rstrip("/") + "/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return False, (f"Ollama not reachable at {host} ({exc}). "
                       "Install: brew install ollama && ollama serve")
    names = [m.get("name", "") for m in tags.get("models", [])]
    if not any(n == model or n.startswith(model + ":") for n in names):
        return False, (f"Model '{model}' not pulled. Run: ollama pull {model}. "
                       f"Available: {', '.join(names) or 'none'}")
    return True, f"Ollama ready · {model}"


def embed(texts, host=DEFAULT_HOST, model=DEFAULT_MODEL, batch=8):
    """Embed a list of texts. Returns a list of float vectors."""
    out = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        body = _post(host, "/api/embed", {"model": model, "input": chunk})
        vecs = body.get("embeddings")
        if vecs is None and "embedding" in body:
            vecs = [body["embedding"]]
        if not vecs or len(vecs) != len(chunk):
            raise OllamaUnavailable(
                f"Unexpected embedding response for {len(chunk)} inputs: "
                f"{str(body)[:160]}")
        out.extend(vecs)
    return out


def _norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))


class EmbeddingRetriever:
    """Dense retriever. Same interface as BilingualRetriever.

    Divergence here is *measured*: whatever the multilingual model actually
    represents. There is no coverage table and no per-language adjustment —
    both languages go through the identical code path.
    """

    def __init__(self, documents, lang, host=DEFAULT_HOST, model=DEFAULT_MODEL,
                 cache=None):
        self.lang = lang
        self.host = host
        self.model = model
        self.cache = cache if cache is not None else {}
        self.doc_ids = [d["doc_id"] for d in documents]

        texts, need = [], []
        for d in documents:
            side = d[lang]
            text = side["title"] + ". " + side["body"]
            key = f"{model}|{lang}|doc|{d['doc_id']}"
            if key not in self.cache:
                texts.append(text)
                need.append(key)
        if texts:
            for key, vec in zip(need, embed(texts, host, model)):
                self.cache[key] = _norm(vec)
        self.doc_vecs = {d: self.cache[f"{model}|{lang}|doc|{d}"]
                         for d in self.doc_ids}

    def _query_vec(self, query_text):
        key = f"{self.model}|{self.lang}|q|{query_text}"
        if key not in self.cache:
            self.cache[key] = _norm(embed([query_text], self.host, self.model)[0])
        return self.cache[key]

    def score_query(self, query_text):
        qv = self._query_vec(query_text)
        scored = [(d, cosine(qv, v)) for d, v in self.doc_vecs.items()]
        return sorted(scored, key=lambda kv: (-kv[1], kv[0]))

    def retrieve(self, query_text, k=5):
        return [d for d, _ in self.score_query(query_text)[:k]]

    def weak_terms(self, query_text, doc_ids=None):
        """No lexicon table in this backend — divergence is measured, not modelled.

        Returning nothing is the honest answer: with real embeddings the harness
        can show *that* retrieval diverged but not attribute it to a specific
        term, because the model gives no per-token account of its similarity.
        Term-level attribution is a property of the lexical backend.
        """
        return []
