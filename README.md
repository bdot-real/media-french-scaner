# Bilingual Quality Harness (BQH)

**Does an AI content workflow perform *equivalently* in English and Canadian French?**

Most multilingual evaluation asks whether a model is *good enough* in each
language, scored separately against separate baselines. That framing can't
detect the failure that matters for a bilingual public broadcaster: both
languages clearing a quality bar while the French output is systematically
thinner, less grounded, or written in a register that reads as foreign to a
Canadian audience.

BQH measures the **gap**. Same corpus, same information needs, same metrics,
run in parallel — and reports where the two languages diverge.

```
  DIMENSION                     EN      FR      GAP   STATUS
  --------------------------------------------------------------
  retrieval_p_at_1           1.000   0.938   +0.062   ok
  retrieval_recall           0.938   0.906   +0.031   ok
  retrieval_ndcg             0.952   0.913   +0.038   ok
  grounding_numeric          1.000   0.938   +0.062   ok
  grounding_in_context       0.922   0.828   +0.094   DIVERGENT
  grounding_entailment       0.843   0.775   +0.068   ok
  content_coverage           1.000   0.833   +0.167   DIVERGENT
  fluency_register           1.000   0.812   +0.188   DIVERGENT
  fluency_overall            0.987   0.848   +0.139   DIVERGENT
  --------------------------------------------------------------
  Equivalence index: 0.906   (1.000 = perfect parity)
```

## Quick start

```bash
python3 bqh/harness.py                          # terminal report
python3 bqh/harness.py --report report.html     # visual dashboard
python3 tests/test_harness.py                   # validation suite
```

No dependencies. Python 3.8+. Runs offline and deterministically.

## What it measures

| Dimension | Question |
|---|---|
| `retrieval_p_at_1` / `recall` / `ndcg` | Does the same question surface the same documents in both languages? |
| `grounding_numeric` | Are there figures in the answer that appear nowhere in the source? |
| `grounding_in_context` | Are claims supported by what retrieval *actually returned*? |
| `grounding_entailment` | Are content words traceable to the source? |
| `content_coverage` | Does the French answer carry the same facts as the English one? |
| `fluency_register` | Is it **Canadian** French, not metropolitan French? |

### Why grounding is split in two

`grounding_numeric` scores against the **gold** documents; `grounding_in_context`
scores against what retrieval **returned**. The difference isolates true
fabrication from unsupported claims that are merely downstream of a retrieval
miss.

This is not a theoretical distinction. In this corpus the English side scores
0.922 on in-context grounding — worse than it looks — purely because a
multi-document query missed one of its two gold documents. Collapsing the two
measures would have reported that as an English hallucination. Retrieval
failures and generation failures need different fixes, so they need different
numbers.

### Why Canadian French, specifically

`fluency_register` encodes Radio-Canada / Termium conventions, not generic
French. It flags:

- **Wrong institution** — `Pôle emploi`, `Sécurité sociale` (French bodies, wrong jurisdiction)
- **Wrong statutory term** — `assurance chômage` for `assurance-emploi`; `communautés francophones` for the CLOSM term, which silently drops anglophone minority communities
- **Wrong office** — `administrateur` for `conseiller scolaire`
- **Metropolitan usage** — `week-end` → `fin de semaine`, `email` → `courriel`
- **Structural calques** — `basé sur`, `en charge de`, `rencontrer les exigences`

A model can score well on French fluency and still be unpublishable in Canadian
French. Severity is weighted: statutory and jurisdictional errors count more
than stylistic preference.

## Root-cause attribution

A red number that doesn't tell you what to fix is not useful. Every retrieval
divergence is attributed to the specific vocabulary responsible:

```
  Lexicon coverage gaps driving retrieval divergence:
    halte-chaleur          coverage 0.20   queries: q03, q11
    banlieusard            coverage 0.30   queries: q06, q09, q12, q16
    assurance-emploi       coverage 0.35   queries: q01, q02
```

That's an actionable finding: these are the terms to add to a synonym map, a
fine-tuning set, or a retrieval-time query expansion.

## What is real and what is modelled

Stated plainly, because an evaluation tool that overclaims is worse than none:

**Real:** the BM25 retriever, all metric computations, the gold relevance
labels, number normalisation across EN/FR conventions, the Canadian French rule
set, the equivalence arithmetic, and the validation suite.

**Modelled:** the *cause* of retrieval divergence. `LEXICON_COVERAGE` in
`bqh/metrics/retrieval.py` assigns a recovery weight to Canadian-French terms
that a metropolitan-tuned embedding space represents weakly. The effect is
simulated from a documented lexicon rather than measured from a live embedding
model.

**Why this is the right trade:** the harness — metrics, thresholds,
attribution, reporting — is what transfers to production. Swapping
`score_query` for a real embedding endpoint changes one method; every number
downstream still computes. The simulation makes the demo deterministic and
offline; it isn't load-bearing for the argument.

**Also frozen:** the generated answers, in offline mode. They carry nine
deliberately planted defects (2 grounding, 3 register, 4 coverage), annotated
in `corpus/generations.json`. `tests/test_harness.py` checks every detection
against those annotations — including a false-positive control on the eight
clean French answers.

```
$ python3 tests/test_harness.py
23 passed, 0 failed
```

## Live mode

```bash
export ANTHROPIC_API_KEY=...
pip install anthropic
python3 bqh/harness.py --live --model claude-sonnet-5 --report report.html
```

Generation moves to the Claude API; retrieval, scoring, and reporting are
unchanged. The French system prompt explicitly requests Canadian French, so
live mode also tests whether prompt-level instruction is sufficient to hold
register — which is itself the interesting question.

## Corpus

12 parallel EN/FR journalistic documents (employment insurance, health
transfers, severe weather, school funding, tolls, arts funding, housing,
courts, monetary policy, fisheries, municipal budget, francophone immigration)
and 16 parallel queries with shared gold labels. French documents are written
in Canadian French. Gold relevance is language-independent by design: a correct
retriever returns the same documents for the English and French form of the
same information need.

Content is synthetic — plausible Canadian news copy with invented figures and
names — so nothing here reproduces real reporting.

## Layout

```
bqh/
  harness.py              runner, aggregation, CLI
  corpus/
    documents.json        12 parallel EN/FR articles
    queries.json          16 parallel queries + gold labels
    generations.json      frozen answers + annotated defects
  metrics/
    retrieval.py          BM25, stemming, lexicon coverage, IR metrics
    grounding.py          numeric grounding, entailment, cross-language coverage
    fluency.py            Canadian French register + readability
  report/
    dashboard.py          self-contained HTML dashboard
tests/
  test_harness.py         detection validation + false-positive control
```

## Limitations

- Lexical retrieval (BM25), not dense embeddings — the divergence *mechanism*
  is modelled rather than measured.
- The register rule set is a curated sample, not the full Termium corpus.
- Cross-language content coverage compares language-neutral tokens (figures,
  proper nouns); it detects dropped facts, not paraphrase-level nuance.
- 16 queries is a demonstration corpus. Threshold calibration at production
  scale needs hundreds.
- Single-annotator gold labels, no inter-annotator agreement.
