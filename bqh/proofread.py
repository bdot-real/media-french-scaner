"""QFCR probe: does a proofreading pass damage correct Canadian French?

QFCR is measured by round-trip. Take French text whose Canadian usage is
already correct, send it through a plain "corrige ce texte" prompt — the kind
of quality step a newsroom would reasonably add — and count how many valid
Quebec forms come back altered.

Because the input is correct by construction, any change to a Quebec form is a
false correction. This isolates the proofreading step: a pipeline can generate
perfect Canadian French and still ship metropolitan copy because a downstream
"improvement" pass rewrote it.

Offline mode uses recorded proofreader outputs so the metric is demonstrable
without a network; --live sends the real prompt.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from metrics.drift import corpus_false_correction, measure_false_correction

PROBE_PATH = Path(__file__).resolve().parent / "corpus" / "proofread_probes.json"

# The prompt deliberately does NOT mention Canadian French. That is the point:
# it is the naive proofreading instruction a team would write by default, and
# QFCR measures what that default costs.
PROOFREAD_PROMPT = (
    "Corrige et améliore ce texte en français. "
    "Réponds uniquement avec le texte corrigé, sans commentaire.\n\n{text}"
)


def load_probes():
    return json.loads(PROBE_PATH.read_text())["probes"]


def run(live=False, provider="openrouter", model=None, verbose=False):
    probes = load_probes()
    pairs = []
    for p in probes:
        original = p["text"]
        if live:
            from harness import PROVIDERS
            out = PROVIDERS[provider](
                PROOFREAD_PROMPT.format(text=original), "fr", [], model)
        else:
            out = p["proofread_offline"]
        if verbose:
            print(f"  {p['probe_id']}: {out[:80]}", file=sys.stderr)
        pairs.append((original, out, p["probe_id"]))
    result = corpus_false_correction(pairs)
    result["n_probes"] = len(probes)
    result["per_probe"] = [
        {"probe_id": tag, **measure_false_correction(o, pr)}
        for o, pr, tag in pairs
    ]
    return result
