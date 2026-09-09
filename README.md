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
python3 tests/test_harness.py                   # detection validation (111 checks)
python3 tests/test_register.py                  # register validation (22 checks)
python3 tests/test_drift.py                     # MDR/QFCR validation (21 checks)
python3 tests/test_i18n.py                      # French UI copy validation (16 checks)
python3 tests/test_newdims.py                   # localization/terminology/answerability (27 checks)
```

The report ships **both languages in one file** with a toggle. The French is
Canadian French to Radio-Canada conventions — a report about Canadian French
quality written in metropolitan French would undercut its own argument — so
`tests/test_i18n.py` runs every French UI string through the harness's own
register checker and drift detector. The tool holds its own copy to the
standard it measures.

Terminology: `repérage` (not `recherche d'information`) for retrieval,
`pupitre` for desk, `véracité` for grounding, `taxe foncière` and `conseiller
scolaire` for the Canadian administrative terms. Typography follows Canadian
practice, including a non-breaking space before `:`. The toggle defaults to the
browser's language, so a francophone reader opening the file cold lands on
French.

No dependencies. Python 3.8+. Runs offline and deterministically.

80 parallel EN/FR documents · 102 parallel queries · 38 annotated defects ·
31 media assets (19 images, 7 videos, 5 audio) · 32 documents with editorial
metadata.

### Real embeddings instead of a modelled gap

The default BM25 backend *simulates* the Canadian-French retrieval gap from a
hand-authored lexicon table. To measure it for real with a local multilingual
model:

```bash
./setup_ollama.sh                    # installs ollama, pulls bge-m3
python3 bqh/harness.py --retriever embedding --report report_embed.html
```

Both backends expose the same interface, so every metric, severity tier, and
dashboard element is identical — which makes the comparison between them
informative in itself.

#### Measured result: the modelled retrieval gap did not survive contact

Run against `bge-m3` (1024-dim, multilingual) on the 60-document corpus:

| Dimension | BM25 gap (modelled) | Embedding gap (measured) |
|---|---|---|
| retrieval precision@1 | +0.026 | **−0.013** |
| retrieval recall@3 | +0.016 | **−0.011** |
| retrieval nDCG@3 | +0.016 | **−0.018** |
| content coverage | +0.112 | +0.112 |
| Canadian French register | +0.077 | +0.077 |
| grounding (fabrication) | +0.030 | +0.030 |

**Queries where French retrieval failed and English succeeded: zero.** The sign
flips — French retrieval is marginally *better* than English under a real
multilingual model.

The clearest case is q04, the `halte-chaleur` query that was the harness's
centrepiece finding under BM25:

```
q04  "Where can people go to keep warm?"   gold: wx-003, hous-024
  BM25 (modelled)  FR → tech-059, hous-050, tech-039    P@1 0.0
  bge-m3 (real)    FR → hous-024, wx-003, wx-049        P@1 1.0
```

`bge-m3` represents `halte-chaleur` perfectly well. The `LEXICON_COVERAGE`
table assumed it would not, and that assumption was wrong.

**This is the most important result in the project, and it corrects the
hypothesis the harness was built on.** The argument was: Canadian French
vocabulary is weakly represented, so retrieval diverges. Measured against a
current multilingual embedding model, that specific claim does not hold. Anyone
planning a bilingual RAG pipeline on the assumption that they must fix
retrieval first would be optimising the wrong stage.

#### What the measurement does not overturn

Every non-retrieval gap is unchanged, because those metrics never depended on
the retrieval backend:

- **content coverage +0.112** — French answers carry less than their English
  counterparts. 14 queries.
- **Canadian French register +0.077** — metropolitan forms and dropped
  statutory terms. 3 queries.
- **grounding +0.030** — 4 fabricated figures.
- **QFCR 80%** — a naive proofreading pass still destroys 12 of 15 valid Quebec
  forms.
- **Media metadata: 58% of assets accessible in French** — this one has nothing
  to do with models at all.

Service parity is 71% under both backends, and the same 4 queries leave the
French reader unserved. **The divergence is real; it just lives in generation,
metadata, and post-processing rather than retrieval.** That is a more useful
finding than the one the harness set out to confirm, and it is only visible
because the modelled and measured backends could be compared directly.

Note that the embedding backend cannot attribute divergence to a specific term —
`weak_terms` returns empty, because a dense model gives no per-token account of
its similarity. Term-level attribution is a property of the lexical backend.

## Localization, terminology, answerability

Three dimensions that grounding and register checks structurally cannot see.

### Localization conventions

A French answer can be grounded, complete, and in correct Canadian register and
still be unpublishable: `$4,100,000` instead of `4 100 000 $`, `3.9` instead of
`3,9`, `03/04` for a date that means April 3 in Canada and March 4 in the US.

These are not style preferences. **A misread date in a story about a filing
deadline is a factual error the grounding checks cannot detect**, because every
digit is present and correct.

### Terminology consistency

Scored one at a time, every answer can look fine while the run as a whole
renders the same programme three ways. Measured here across the full answer
set: **French 0.571 against English 1.000**, and `warming_centre` is **0%
canonical** — every French mention uses a variant rather than `halte-chaleur`.

This breaks archive search and house style, and it is systematically worse in
the second language, where no single reviewer sees all the output.

One implementation note: variant patterns overlap by design (`régime
d'assurance-emploi` contains `assurance-emploi`), so the matcher claims each
character span once, canonical pattern first. Counting each pattern
independently double-counted spans and reported correct copy as inconsistent.

### Readability parity

The often-quoted "French runs 15–20% longer" applies to raw text. This harness
compares content tokens after stopword removal, and the French stoplist is
larger, which cancels most of that expansion.

**Measured across the 68 defect-free answer pairs in this corpus: mean ratio
1.00, stdev 0.115.** The constant is measured, not assumed — two hand-written
guesses (1.05 and 0.85) both produced false "content dropped" verdicts on
faithful French before it was calibrated against the corpus.

### Answerability

A refusal asserts nothing, so it scores *perfectly* on grounding and register.
Without an explicit check, the worst outcome for a reader — no answer at all —
is invisible to conventional quality metrics. Tracked per language as
answered / refused / hedged, with the asymmetric cases named.

## Metropolitan Drift Rate and Quebec False Correction Rate

Two Canadian-specific metrics that generic French evaluation does not provide.

### MDR — Metropolitan Drift Rate

The rate at which a Quebec form is replaced by its France counterpart.

**MDR counts substitutions only.** If the model rephrases *around* a term
rather than substituting the metropolitan form, that is verbosity, not drift.
Rephrased cases are excluded from the denominator entirely — they are neither
evidence for drift nor against it, so scoring them either way biases the rate.

```
MDR = substituted / (substituted + preserved)
```

On this corpus: **50%** — 2 substituted of 4 scored opportunities, with **13
rephrased cases excluded**. A naive implementation counting rephrases as clean
would have reported 2/17 ≈ 12%, understating substitution behaviour by 4×. The
constraint is pinned by tests in `tests/test_drift.py`.

### QFCR — Quebec False Correction Rate

The rate at which a "proofread this" prompt incorrectly *fixes* valid regional
usage.

```
QFCR = valid Quebec forms altered / valid Quebec forms present
```

`bqh/proofread.py` sends already-correct Canadian French through a naive
`"Corrige et améliore ce texte en français"` prompt — deliberately not
mentioning Canadian French, because that is the default instruction a team
would write. Since the input is correct by construction, any alteration is a
false correction.

On the probe set: **QFCR 80%** — 12 of 15 valid Quebec forms destroyed.

```
fin de semaine    → week-end
courriel          → email
halte-chaleur     → centre d'hébergement chauffé
conseiller scolaire → administrateur scolaire
assurance-emploi  → assurance chômage
banlieusard       → navetteur
présentement      → actuellement
dépanneur         → épicerie de nuit
```

This is the most actionable finding in the harness. A pipeline can generate
perfect Canadian French and still ship metropolitan copy, because a downstream
"quality improvement" step rewrote it. MDR and QFCR separate those two
failures: good MDR with bad QFCR means generation is fine and **the proofreader
is the problem**.

## Metadata: media, editorial, provenance

The article body is not the only thing a bilingual newsroom publishes.

### Media — images, video, audio

Every asset carries descriptors: alt text, captions, credits, transcripts. The
*asset* is reused across both language sites; the descriptors often are not.

| State | Meaning |
|---|---|
| `missing` | FR descriptor absent while EN is present |
| `untranslated` | FR byte-identical to EN — **worse than missing**, because it passes a null check in a CMS audit |
| `truncated` | FR present but under half the English length |

Two costs compound: **accessibility** (a French screen-reader user gets nothing
where an English one gets a description) and **discovery** (alt text and
captions feed archive retrieval, so an undescribed French asset is
unfindable).

On this corpus: **55% of assets accessible in French**, 5 of 11 failing. Both
videos are missing French transcripts — for timed media that removes the only
text representation of the content, so it is treated as a hard accessibility
failure rather than a metadata gap.

### Editorial — tags, SEO descriptions, headlines

Tags drive archive retrieval, related-story modules, and topic pages, so a
French story tagged with fewer concepts is less discoverable in French — the
same divergence the retrieval metrics measure, arriving through the CMS instead
of the model. Tags are translated, so only the *count* of concepts carried is
comparable across languages.

On this corpus: **6 tags dropped**, 2 missing French SEO descriptions. Both arts
documents dropped the CLOSM tag specifically.

### Segmentation — desk, region, topic

An aggregate says *whether* the pipeline is failing; segmentation says *where*,
which is what routes it to an owner. Queries inherit the metadata of the
documents their gold set points at. Segments below 2 queries are reported but
flagged `thin`, because a one-query segment is an anecdote.

## Leading with severity, not the mean

The first live run reported *"equivalence 0.958, all dimensions pass"* while a
French reader asking where to warm up during a power outage received no answer
at all. Averaged across queries, a total service failure became a rounding error.

Every query is now classified by its worst outcome, ordered by reader impact:

| Tier | What happened |
|---|---|
| `no_answer` | French returned nothing usable while English answered |
| `wrong_fact` | French asserted a figure absent from the source |
| `wrong_docs` | Retrieval diverged; the two languages answered from different sources |
| `omission` | French accurate but carrying less than the English |
| `register` | Accurate and complete, but not Canadian French |

The headline is **service parity** — the share of queries where the French
reader got a substantively equivalent answer.

Refusal detection matters specifically here: a refusal scores *well* on
grounding (nothing asserted, nothing to contradict) and on register (no
violations possible). Without an explicit check, the worst outcome for a reader
looks like a clean pass.

## What it measures

| Dimension | Question |
|---|---|
| `retrieval_p_at_1` / `recall` / `ndcg` | Does the same question surface the same documents in both languages? |
| `grounding_numeric` | Are there figures in the answer that appear nowhere in the source? |
| `grounding_in_context` | Are claims supported by what retrieval *actually returned*? |
| `grounding_entailment` | Are content words traceable to the source? |
| `content_coverage` | Does the French answer carry the same facts as the English one? |
| `fluency_register` | Is it **Canadian** French, not metropolitan French? |
| `localization` | Dates, currency, decimals, units — Canadian conventions? |

Plus three corpus-level measures that cannot be computed per answer:

| Measure | Question |
|---|---|
| terminology consistency | Is the same programme named the same way all run? |
| readability parity | Is the FR/EN length relationship stable? |
| answerability | Does each language get an answer *at all*? |

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

Offline mode is deterministic and frozen. Live mode generates the answers from a
real model and scores those instead — retrieval, metrics, and reporting are
unchanged.

**OpenRouter** (no SDK required — stdlib HTTP only):

```bash
export OPENROUTER_API_KEY=sk-or-...
python3 bqh/harness.py --live --provider openrouter --report report_live.html
```

Defaults to `nex-agi/nex-n2.5-pro:free`. Override with `--model`; add `-v` to log
each call. 32 sequential calls (16 queries × 2 languages), so expect a few
minutes on free-tier endpoints.

**Anthropic API:**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pip install anthropic
python3 bqh/harness.py --live --provider anthropic --model claude-sonnet-5
```

### What live mode actually tests

The French system prompt explicitly asks for Canadian French to Radio-Canada
conventions. So a live run answers a sharper question than the frozen corpus can:
**is prompt-level instruction enough to hold register?**

**Measured result** (`nex-agi/nex-n2.5-pro:free` via OpenRouter, 13 query pairs):

```
  DIMENSION                     EN      FR      GAP   STATUS
  retrieval_p_at_1           1.000   0.923   +0.077   ok
  grounding_numeric          1.000   1.000   +0.000   ok
  fluency_register           1.000   1.000   +0.000   ok
  content_coverage           1.000   0.923   +0.077   ok
  --------------------------------------------------------------
  Equivalence index: 0.958
```

Two findings, and they point in opposite directions:

**Generation held up.** Register scored a perfect 1.000 — the model used
`conseillers scolaires`, not `administrateurs`; `communautés de langue
officielle`, not the loose paraphrase. Grounding was clean in both languages: no
fabricated figures. Prompt-level instruction *was* sufficient here, which is a
real (and encouraging) result worth reporting honestly rather than assuming the
worst.

**Retrieval still failed — and the consequence got worse, not better.** Query
q04 ("where can people go to keep warm?"):

| | Answer |
|---|---|
| **EN** | "People can go to one of the eleven warming centres opened by municipalities." |
| **FR** | *"Les sources fournies ne mentionnent aucune panne ni aucun endroit où les gens peuvent aller se réchauffer."* |

The French user gets **no answer at all** to a question the English user gets
answered — same corpus, same model, same prompt. The retrieval layer never
surfaced the document, because `halte-chaleur` is weakly represented, so a
well-behaved model correctly declined to answer.

This is the argument the harness exists to make. A good model does not rescue a
retrieval layer with uneven language coverage — it faithfully reports that it
has nothing to say. The failure moves from *visible* (a bad French answer) to
*invisible* (a polite refusal), which is harder to catch in production and
worse for the reader. **Fixing the generator would not have fixed this.**

### Note on the live numbers

The live run covers 13 of 16 query pairs. The three multi-document queries
(q14–q16) are missing: OpenRouter's free tier caps at 50 requests/day and the
run exhausted it. `--limit 13` scores the complete subset rather than comparing
uneven query sets across languages. Live generations are checkpointed to
`live_cache.json` after every call, so a re-run resumes instead of re-paying.

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
