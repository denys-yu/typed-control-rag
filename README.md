# Typed Control over Retrieval-Failure Propagation

Code, frozen experimental plan, per-run records, accepted semantic annotations and analysis outputs
for the paper **"A Typed Control Contract for Agentic Retrieval-Augmented Generation"** by
Denys Yuvzhenko and Sergii Stirenko. No publication status, venue or DOI is recorded here, because
none has been confirmed.

The software in this repository is authored by Denys Yuvzhenko and released under the MIT licence
(see [LICENSE](LICENSE)); that is separate from the authorship of the paper.

The study asks a narrow question: when the retrieved context is broken, does it matter *how* an
agentic RAG (retrieval-augmented generation) pipeline decides what to do next? Four branches of one
pipeline differ in how the context is assessed and who chooses the next action — the LLM (large
language model) or Python code.

| Branch | Context-sufficiency assessment | Who chooses the next action |
|---|---|---|
| **A** | binary (sufficient / insufficient) | the LLM |
| **B** | typed: `OK` / `EMPTY` / `PARTIAL` / `INCONSISTENT` | the LLM |
| **C** | binary | Python transition rules |
| **D** | typed: `OK` / `EMPTY` / `PARTIAL` / `INCONSISTENT` | a programmatic contract over the type |

### What the branches share, and what they do not

The four branches are **not** prompt-identical, and this README should not be read as claiming that:

- **A and C share one evaluator**: the same binary prompt (`prompts/grade_binary_action.txt`) and the
  same response schema (`context_grade_binary_action`).
- **B and D share one evaluator**: the same typed prompt (`prompts/grade_typed_action.txt`) and the
  same response schema (`context_grade_typed_action`).
- The binary and the typed evaluator therefore use **different** prompts and different schemas from
  each other. A and C differ from B and D at the very first call.
- The **first provider request is byte-identical within each pair** — A matches C, and B matches D.
  The offline gate `tools/stage14_cli.py preflight` checks exactly this
  (`identical_first_request_A_and_C`, `identical_first_request_B_and_D`), so within a pair the only
  difference is who acts on the assessment: the model, or Python.
- Genuinely common to all four branches: the model and its generation parameters, the retriever, the
  corpus and the frozen index, the identical ordered initial context for a given question and
  condition, the query-rewrite node, the answer generator with its own prompt and schema, and the
  retry budget of at most one additional search.
- The evaluator never receives the branch name and never learns whether Python will enforce the
  contract. The generator never receives the branch, the proposed action, the assessment or its
  reason.
- **After the first decision the trajectories diverge.** A rewritten query, a second search, a
  different post-retry context and a different terminal outcome are all expected; only the starting
  point is held fixed.

The primary comparison, fixed in protocol v3 before the first **main-experiment** provider call, is
**D versus C on initially defective inputs**. Provider calls had already been made in earlier
diagnostic and pilot stages; protocol v3 was frozen before any call of the main experiment, not
before any call ever made in the project, and it was not registered with an external registry. Each
of the 60 questions was run under four context conditions (`CLEAN`, `PARTIAL`, `EMPTY`,
`INCONSISTENT`), four branches and three repeats: 2,880 planned runs, one model
(`gpt-4o-mini-2024-07-18`), one dataset (HotpotQA dev/distractor), one retriever.

## What was measured

Throughout, **pp** means percentage points, and all intervals are 95 % percentile bootstrap intervals
over questions produced by the question-level estimator of protocol v3.

### On initially defective inputs (`PARTIAL`, `EMPTY`, `INCONSISTENT`) — the primary result

| D − C on defective inputs | Difference | 95 % interval |
|---|---:|:---:|
| Not fully supported answers (primary) | −12.04 pp | [−18.15, −6.48] |
| Fully supported answers | −19.81 pp | [−27.96, −12.04] |
| Abstention or escalation | +31.85 pp | [+23.70, +40.00] |

Branch D produced fewer not-fully-supported answers than C, **and at the same time** fewer fully
supported ones, while abstaining or escalating far more often. That trade-off, on defective inputs,
is the primary result.

The predeclared 55-question sensitivity subset gives −10.71 pp [−16.57, −5.45] on the primary
measure: same direction, same qualitative reading.

### On `CLEAN` inputs — a separate utility cost, not a repeat of the result above

| D − C on `CLEAN` inputs | Difference | 95 % interval |
|---|---:|:---:|
| Fully supported answers | −8.33 pp | [−16.11, −1.67] |
| Abstention or escalation | +7.22 pp | [+0.56, +15.00] |

This is the cost of the stricter branch when nothing is wrong with the context. **No reduction of
not-fully-supported answers is established for `CLEAN` inputs**: the primary contrast above is
defined on the three defective conditions only, and the CLEAN figures are reported as a utility cost
beside it, never merged into it. Whether that cost is acceptable was **not** established — the
protocol fixed no acceptance threshold and no non-inferiority margin.

`not fully supported` = `PARTIALLY_SUPPORTED` + `UNSUPPORTED` + `CONFLICTED` against the context the
generator received. It is a grounding label, not a claim that an answer is factually wrong or
hallucinated.

Read the numbers in context before quoting them:

- **[results/main_analysis_summary.md](results/main_analysis_summary.md)** — the full narrative
  summary: coverage, the primary contrast, branch levels, the CLEAN utility cost, per-condition
  breakdown, exploratory contrasts, sensitivity analysis, diagnostics and limitations.
- **[results/main_analysis_results.json](results/main_analysis_results.json)** — every estimate,
  interval and diagnostic as machine-readable data.
- Tables: [branch_outcomes.csv](results/main_analysis_tables/branch_outcomes.csv),
  [contrasts.csv](results/main_analysis_tables/contrasts.csv),
  [terminal_outcomes.csv](results/main_analysis_tables/terminal_outcomes.csv).
- Figures: [figure1 — branch outcome composition](results/main_analysis_figures/figure1_branch_outcome_composition.svg),
  [figure2 — effect estimates](results/main_analysis_figures/figure2_effect_estimates.svg).
- **[results/main_experiment_protocol_v3.md](results/main_experiment_protocol_v3.md)** — the protocol
  frozen before the first main-experiment provider call: outcome categories, estimator, bootstrap,
  missing-cell rule.

## Reproducing the published results

One command recomputes the analysis dataset, the estimator, the bootstrap intervals, the tables and
the figures from the per-run records and the accepted annotations, then compares everything with the
reference artefacts. It needs no `OPENAI_API_KEY`, makes no provider call, and does not re-run any
coordinate or change any label. Once the dependencies are installed it makes **no network request**.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-analysis.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe tools\reproduce_analysis.py
```

Verified with **Python 3.12.6 on Windows 11**. [requirements-analysis.txt](requirements-analysis.txt)
pins the exact versions of that environment, including the transitive dependencies, and installs
neither PyTorch nor sentence-transformers: the reproduction reads recorded observations and embeds
nothing, so **no model weights are needed**. On Linux or macOS the same files and commands apply with
`python3 -m venv .venv` and `.venv/bin/python`, but no verification run was performed on those
platforms and none is claimed.

**Outputs are written only to `results/reproduction/`; existing reference artefacts remain
unchanged.** That directory is git-ignored, and the command re-checks the reference files after the
run to confirm they were not modified. It exits non-zero on any mismatch. It checks:

- the 8 regenerated artefacts against the reference ones. Seven are compared byte for byte;
  `main_analysis_results.json` is compared by content with the single field `generated_at_utc`
  excluded, because that timestamp is written afresh on every run.
- the headline numbers against the values fixed at stage 15.1 — 2,880 planned coordinates,
  2,873 completed, 7 technical failures, 1,106 answered runs, 6,049 provider attempts,
  863 answered runs with valid citation-ID membership and 243 answered runs with invalid citation-ID
  membership, the 60-question sample and the 55-question subset, every primary, companion, CLEAN and
  sensitivity estimate with its interval, and 9,458,529 tokens;
- that the question-level (weighted) and the pooled descriptive diagnostics stay distinct;
- the 19 offline checks of `tools/stage15_validate.py`, including the synthetic case in which pooled
  run weighting reverses the sign of the effect.

The expected values in `tools/reproduce_analysis.py` are fixed. If a run disagrees with them, the
packaging is wrong and must be fixed — the expectations are not to be edited to match a new result.

### Unit tests

The tests make no provider call and load no embedding model. `requirements-analysis.txt` already
contains everything they need, including the `openai` and `httpx` versions whose request, response and
error objects the LLM tests construct directly, and `python-dotenv` for the one test that reads a key
from a `.env` file.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

That runs 145 tests and was verified to pass in a clean checkout with exactly the pinned versions of
`requirements-analysis.txt` and the package installed with `--no-deps`. If the `openai`, `httpx` and
`python-dotenv` block of that file is omitted, the two LLM test modules fail to import and 86 of the
145 tests run. `tests/test_retrieval.py` skips anything that needs the embedding model;
`tests/integration_check.py` is the only test that loads the real model and is run explicitly.

## Three levels of verification, and what each one needs

| Level | What it establishes | What it needs |
|---|---|---|
| **1. Recompute the metrics** | that every published estimate, interval, table and figure follows from the recorded per-run observations and the accepted annotations under protocol v3 | this repository only; offline; no model weights; `tools/reproduce_analysis.py` |
| **2. Audit against raw responses** | that those per-run records faithfully represent what the provider actually returned, call by call | the raw run archive, which is **not** in this repository (see below) |
| **3. Run the experiment again** | a fresh sample of model behaviour under the same plan | a paid `OPENAI_API_KEY`, network access, the full dependency set, the embedding weights, and up to 11,520 provider calls |

Level 1 is self-contained here. Level 2 depends on an external archive. Level 3 produces new data and
will not reproduce these numbers exactly: `temperature=0` is a technical setting and is not a
determinism guarantee.

### The raw run archive (level 2)

The raw provider requests and responses of the main experiment — 14,692 files, 121.9 MiB uncompressed,
plan `947b073b30fd…` — are kept outside this repository and have **not** been published anywhere yet.
This README deliberately contains no link to them, because no such link exists. They are packaged
unmodified, with a SHA-256 manifest of every entry, and can be deposited as supplementary material on
request. A hash list of files nobody can obtain is not a reproduction package, so level 2 is honestly
out of reach until that deposit happens.

Note also that `results/main_run_index.jsonl` already carries, per run, the executed and expected
actions, evaluator assessments, returned evidence identifiers, attempt counts, token usage and
latency. What it does not carry is the verbatim provider payloads.

## Running the experiment again (level 3)

This costs money and calls a third-party API. Read
[results/main_experiment_protocol_v3.md](results/main_experiment_protocol_v3.md) first.

The main corpus and the frozen index are tracked here, so **nothing has to be downloaded, rebuilt or
overwritten** first. Plan verification and the offline gates run against the tracked files and need no
embedding weights.

```powershell
# Full environment, pinned to the snapshot the experiment ran on. Install the CPU
# build of PyTorch from the PyTorch index first, then the rest of the snapshot.
.\.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.14.0+cpu
.\.venv\Scripts\python.exe -m pip install -r requirements-frozen.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps

# Verify that the current files still match the frozen plan before spending anything.
.\.venv\Scripts\python.exe tools\stage14_cli.py verify
.\.venv\Scripts\python.exe tools\stage14_cli.py preflight

# Execute; every invocation sizes its own budget and refuses to exceed the global ceiling.
.\.venv\Scripts\python.exe tools\stage14_cli.py run --coordinates 96
```

`verify` and `preflight` are offline and free; both pass on a fresh clone with no API key and no model
weights. Only `run` calls the provider, and only `run` needs the embedding weights, which are fetched
from the Hugging Face Hub at the pinned revision on first use and cached under `artifacts/models/`.

Requirements and guard rails:

- `OPENAI_API_KEY` in the environment or in a `.env` file in the project root (the environment wins).
  The key is never written to logs, reports or stdout; reports record only `configured` / `missing`.
  See [.env.example](.env.example).
- `tools/stage14_cli.py verify` refuses to run if any hash-bound input changed, and names what
  changed. The plan is never re-frozen silently.
- Every provider attempt, including failed ones, counts against the budget. `max_retries=0`; there are
  no automatic API retries. A budget stop inside a trajectory is recorded as such, never as an
  abstention.
- The longest trajectory is four LLM calls (`grade → rewrite → grade → answer`), so
  2,880 × 4 = 11,520 is an **upper bound** from the control flow, not an expected call count. The
  published run used 6,049 attempts.
- Run directories are written under `~/trfp_runs/` — outside the repository, because the Windows
  `MAX_PATH` limit truncated raw-response paths inside the project tree during an earlier attempt.

### Advanced preparation — destructive, not part of any quick start

The following commands **overwrite tracked research inputs**. They are listed only for completeness;
do not run them in a checkout you intend to verify — use a separate working copy.

| Command | What it overwrites | Consequence |
|---|---|---|
| `python tools\stage12_cli.py build-index` | `artifacts/main_retrieval/documents.jsonl` and `embeddings.npy` | downloads the embedding weights and re-embeds the corpus. `documents.jsonl` is a deterministic function of the corpus, but new **embeddings** need not be byte-identical on different hardware, library versions or BLAS backends. If they differ, `stage14_cli.py verify` correctly refuses the frozen plan. |
| `python -m typed_rag --prepare-data` | `data/raw/` and `data/processed/hotpotqa/` | downloads the 46 MB HotpotQA source file and rebuilds the pilot files. |
| `python tools\stage12_cli.py select` | `data/processed/main/` and the candidate pool | redraws the frozen 300-candidate screening pool; a different pool invalidates the recorded selection and the plan. |

## Repository map

```
src/typed_rag/           the pipeline
  config.py              configuration loading and path resolution
  hotpotqa.py            dataset readers, canonical JSON, doc_id hashing
  prepare.py             corpus and question preparation
  retrieval.py           local vector index, exact cosine search
  nodes.py               the single home of every response JSON Schema
  llm.py                 OpenAI Responses API client, error classification
  controller.py          branches A-D, transition rules, one retry search
  fault_cases.py         construction of the four context conditions
  main_study.py          plan freezing, verification, execution of the main study
  evaluate.py, rag_run.py, preview.py, download.py, __main__.py

prompts/                 grade_binary_action (A/C), grade_typed_action (B/D),
                         rewrite_query and answer are hash-bound to the plan;
                         grade_binary.txt belongs to the earlier diagnostic mode
config/experiment.json   model, generation parameters, retry budget, paths (hash-bound)
config/main_inconsistent_edits.json   the 143 hand-drafted INCONSISTENT edits

data/processed/main/     main corpus, questions, gold annotations, candidate pool, manifest
data/processed/hotpotqa/ pilot ids and candidate ids (used to prove the pilot is excluded)
data/processed/fault_cases/  the pilot's context conditions, reused by the unit tests
artifacts/main_retrieval/    the frozen main index: documents, embeddings, manifest

tools/
  reproduce_analysis.py  >>> the offline reproduction command
  stage12_*.py           main-study preparation: corpus, index, eligibility, faults
  stage13_*.py           adjudication of the context reviews and the sample proposal
  stage14_*.py           plan freeze, preflight, execution, audit, review export
  stage15_*.py           acceptance of the labels, the estimator, checks, reporting

tests/                   unit tests; no provider call, no embedding model
results/                 the protocol, the frozen plan, observations, annotations, results
```

### Where the evidence lives in `results/`

Paths in this table are relative to `results/`.

| Path | What it is |
|---|---|
| `main_experiment_protocol_v3.md` | the protocol, frozen before the first main-experiment provider call |
| `main_plan/manifest.json`, `main_plan/runs.jsonl` | the frozen plan: hashes of every bound input, and the 2,880 scheduled coordinates |
| `main_sample_final.json` | the final 60 questions, the sample order and the exclusion record |
| `stage14_acceptance.json` | **the record of acceptance** for the initial-context decisions: counts, reviewer, the excluded and the replacement question, and the hashes of its inputs |
| `main_preparation/selection_rule.json`, `eligibility.json` | the frozen selection rule and the eligibility measurement (143 of 300 candidates) |
| `main_preparation/fault_contexts.jsonl`, `fault_annotations.jsonl` | the 572 candidate initial contexts and their research metadata (condition names, intended states, gold data — never sent to the model) |
| **`main_preparation/fault_reviews.jsonl`** | **the authoritative accepted initial-context reviews** — see the section below |
| `stage14_archive/fault_reviews_pending_d3cd66b0f370.jsonl` | the untouched **pending template** as it existed before acceptance; kept for comparison, not an annotation source |
| `main_fault_review_proposals_v2.jsonl`, `stage13_adjudication.md`, `main_sample_proposal.json`, `stage13_report.json` | the adjudication that **proposed** those decisions, including every rejection and the 19 cases that stayed unresolved inside mismatch questions |
| `main_run_index.jsonl` | **one record per planned coordinate** as executed: status, actions, assessments, evidence ids, attempts, usage, latency |
| `main_post_retry_contexts.jsonl` + `main_post_retry_reviews.jsonl` + `main_post_retry_lookup_augmented.json` | the 335 distinct post-retry contexts, their accepted sufficiency labels, and the map from label to the 1,027 retry instances |
| `main_answer_grounding_cases.jsonl` + `main_answer_grounding_reviews.jsonl` + `main_answer_grounding_lookup.json` | the 347 distinct answer cases, their accepted grounding labels, and the map to all 1,106 answered runs |
| `pilot_post_retry_annotation_rules.md` | the annotation rubric (v1.0, written at the pilot stage, not preregistered) |
| `main_semantic_review_summary.md`, `stage15_acceptance.json` | what was accepted for the post-retry and grounding labels, by whom, when, and under which interpretations |
| `main_analysis.jsonl` | **the analysis dataset**: one row per planned coordinate with its semantic category |
| `main_analysis_results.json`, `main_analysis_summary.md`, `main_analysis_tables/`, `main_analysis_figures/` | the published results |
| `stage15_validation.json` | the 19 offline checks (see the provenance note below) |
| `stage15_1_correction_report.json`, `stage15_1_archive/` | the stage 15.1 reporting corrections and the pre-correction snapshots they replaced |
| `stage14_index_correction.json` | a read-side index defect found after execution and corrected outside the frozen code |
| `stage14_report.json` | the execution record: plan identity, counts, budget use |

### The accepted initial-context reviews, and how they relate to the 60 questions

`results/main_preparation/fault_reviews.jsonl` is the authoritative file. It holds **572 rows**, one
per candidate context, each with a `review_status`, an `observed_state` and a `reviewer`:

| `review_status` | Rows |
|---|---:|
| `approved` | 439 |
| `rejected` | 113 |
| `pending` | 20 |
| **total** | **572** |

552 rows carry `reviewer: "Denys Yuvzhenko"`; the 20 `pending` rows carry no reviewer and no
`observed_state`. Those counts, the reviewer and the acceptance basis are recorded in
[results/stage14_acceptance.json](results/stage14_acceptance.json), and this file's SHA-256
(`ca95e297…`) is bound into the frozen plan as `binding.sources.reviews_sha256`, so the plan verifies
against the **accepted** reviews, not against a template.

Restricted to the 60 questions of the final sample, the file contains exactly **240 rows, all
`approved`**, with 60 each of `observed_state` `OK`, `PARTIAL`, `EMPTY` and `INCONSISTENT` — the four
matched conditions per question that the design requires.

The `_v2` proposals file and `stage13_adjudication.md` are the **proposal** stage that preceded this
acceptance; they are kept because they document every rejection and the cases that stayed unresolved.
They are not themselves accepted annotations, and nothing in the analysis reads them. Rejected and
pending rows are retained on purpose: a selection record that keeps only its successes is not a
selection record.

### When each kind of annotation was accepted

The three annotation layers were accepted at different times, and the difference matters:

| Layer | File | Accepted |
|---|---|---|
| Initial-context states (`OK` / `PARTIAL` / `EMPTY` / `INCONSISTENT`) | `main_preparation/fault_reviews.jsonl` | **before** the main experiment — the sample could not be drawn without them, and the plan binds their hash |
| Post-retry context sufficiency (335 contexts) | `main_post_retry_reviews.jsonl` | **after** data collection |
| Answer grounding (347 cases) | `main_answer_grounding_reviews.jsonl` | **after** data collection |

Initial-context labels were finalized before the main experiment and therefore before its
outcomes were available. The annotation rules had been developed during the pilot. The
post-retry and grounding labels, by contrast, were produced with the run records already in
hand. All three layers were recorded as researcher acceptance of prepared proposals rather
than an independent second review.

### Analysis data schemas

`results/main_analysis.jsonl` — one JSON object per planned coordinate, 2,880 rows:

| Field group | Fields |
|---|---|
| identity | `coordinate` (`question_id\|case_id\|branch\|repeat`), `run_id`, `question_id`, `case_id`, `condition`, `branch`, `repeat`, `sample_position` |
| technical status | `record_status`, `technical_status`, `api_calls`, `api_attempts`, `token_usage`, `latency_seconds` |
| control flow | `searches`, `retried`, `proposed_actions`, `executed_actions`, `expected_actions`, `any_policy_mismatch`, `any_policy_override`, `generator_decision`, `terminal_outcome` |
| assessments | `initial_reviewed_state`, `first_evaluator_assessment`, `second_evaluator_assessment`, `post_retry_reviewed_state`, `post_retry_scope`, `post_retry_context_sha256`, `retrieval_change_after_retry` |
| semantics | `semantic_status`, `semantic_category`, `answer`, `answer_support`, `explanation_support`, `grounding_case_sha256` |
| evidence | `final_context_sha256`, `returned_evidence_doc_ids`, `citation_id_membership_valid` |

`semantic_category` is one of four mutually exclusive values for completed runs —
`fully_supported_answer`, `not_fully_supported_answer`, `unclear_answer`,
`abstention_or_escalation`. The field is always present: for the 7 technical failures it
carries `null`, and those runs are never imputed.

`citation_id_membership_valid` is a per-run field with three possible values — `true`, `false` or
the string `"not_applicable"`. It is `true` when every document identifier the generator returned
as evidence belongs to the final context of that run, `false` when at least one does not, and
`"not_applicable"` when the run produced no answer — which is the case for 1,774 runs.

It is a **structural** check and is reported separately from semantic grounding. Counted over
runs, not over identifiers, there are **863 answered runs with valid citation-ID membership and
243 answered runs with invalid citation-ID membership**. None of the 243 runs is excluded from
any analysis.

`results/main_run_index.jsonl` carries the same coordinates plus `status`, `usage_known`,
`schedule_position`, `final_context_doc_ids`, `generator_explanation`,
`generator_validation_status` and `context_state_after_retry`. It is the input from which
`main_analysis.jsonl` is rebuilt.

## Data, models and provenance

**Dataset.** HotpotQA, `dev` split, `distractor` setting, `v1`. The 46 MB source file is **not**
redistributed here; `python -m typed_rag --prepare-data` downloads it. Its recorded provenance,
including the fact that the official CMU URL was unreachable and a Hugging Face mirror was used
instead, and that identity with the original file was verified only partially, is in
[data/raw/hotpot_dev_distractor_v1.json.source.json](data/raw/hotpot_dev_distractor_v1.json.source.json)
and `data/processed/main/manifest.json`.

**The corpus.** Per `data/processed/main/manifest.json`, the main corpus was built from the contexts
of the **300 screening candidates** drawn for the main study — not from the 60 finally selected
questions. Those candidate contexts contributed 2,994 paragraphs, 13 of which collapsed as duplicates,
leaving **2,981 unique documents**. The corpus stayed fixed at those 2,981 documents when the sample
narrowed to 60 questions, so retrieval always competes against the whole screening pool rather than
against a question's own evidence. This is a **local experimental corpus from the distractor
paragraphs**; it is not the full Wikipedia corpus and this is not the `fullwiki` setting. `doc_id` is
the SHA-256 of the canonical JSON of `title` + `sentences`. Search always runs over the whole corpus.

**Embedding model.** `sentence-transformers/all-MiniLM-L6-v2`, pinned to revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, on CPU, `max_seq_length=256`, L2-normalised float32,
exact cosine search over the whole corpus, `top_k=5`. Weights are fetched from the Hugging Face Hub at
that revision on first use and are not vendored here. The index build rule, ranking rule, truncation
diagnostics (138 of 2,981 documents truncated for embedding only — the stored text is always complete)
and library versions are in
[artifacts/main_retrieval/index_manifest.json](artifacts/main_retrieval/index_manifest.json).

`artifacts/main_retrieval/documents.jsonl` and `embeddings.npy` (8.4 MB together) **are** tracked,
because the frozen plan binds their SHA-256 and `stage14_cli.py verify` cannot check the plan without
them. Model weights and the pilot index are not tracked.

**Generator and evaluator.** `gpt-4o-mini-2024-07-18` through the OpenAI Responses API,
`temperature=0`, `max_output_tokens=800`, strict Structured Outputs, `store=false`,
`max_retries=0`, no `previous_response_id`, no tools, no streaming, no server-side history. Each call
is independent.

## Licensing

- **The original code and documentation written for this project** — the sources under `src/`,
  `tools/`, `tests/`, the prompts, the configuration files, this README and the other Markdown
  authored here — are © 2026 Denys Yuvzhenko and released under the **MIT licence**:
  [LICENSE](LICENSE). The MIT grant covers that original work only. It does **not** extend to
  third-party text quoted or embedded in these files, nor to data derived from HotpotQA, and those
  exceptions apply wherever such material sits — the folder a file lives in and the extension it
  carries decide nothing.
- **HotpotQA-derived material** — `data/processed/`, `results/main_preparation/fault_contexts.jsonl`,
  the context and case exports, and every document text inside the run records and the index — derives
  from HotpotQA and stays under **its** terms. HotpotQA is distributed by its authors under
  CC BY-SA 4.0; consult <https://hotpotqa.github.io/> for the authoritative terms and cite the
  HotpotQA paper when using the data. The MIT licence above does **not** apply to it.
- **The embedding model** is published by its authors under Apache-2.0 and is not redistributed here.
- Model outputs recorded under `results/` are additionally subject to the API provider's terms as they
  stood when the outputs were generated.

The repository is therefore a **mixed-licence set**. Do not treat all of it, or the model, as
MIT-licensed.

## A note on `results/stage15_validation.json`

Three distinct versions of this verification report exist, and the repository contains one of them:

| Version | SHA-256 | Where it is |
|---|---|---|
| The stage 15.1 file, generated `2026-09-21T11:43:43Z` | `73348b7e…` | matches `post_correction_sha256` in `stage15_1_correction_report.json`; a copy was recovered from the `reports/stage15_validation.json` entry of the earlier evidence ZIP, which is held in the private cleanup archive |
| The copy inherited by the publication cleanup | `8fbdaa67…` | its bytes were not preserved and its provenance is unknown; it already differed from the stage 15.1 hash before the cleanup began |
| The file tracked here now | regenerated during the cleanup | `results/stage15_validation.json` |

The recovered stage 15.1 file and the file tracked here were compared field by field. They differ in
**`generated_at_utc` only**. Both contain the same 19 checks with the same names, the same `passed`
flags and the same detail strings, the same `protected_input_hashes` and the same synthetic examples,
and both report `status: ok`. The recovered copy is evidence of the **stage 15.1** state, not of the
state immediately before the cleanup; the inherited `8fbdaa67…` copy is the one whose content was
never established. `stage15_1_correction_report.json` is historical and was not edited.

## Reproducibility boundaries

- **Reproduced and checked here and now:** the analysis dataset, every estimate and interval, the
  tables and the figures, from the tracked observations. Seven of the eight artefacts come back
  byte-identical; `main_analysis_results.json` is identical except for its `generated_at_utc`
  timestamp. Verified by `tools/reproduce_analysis.py`, offline and without model weights.
- **Byte-exact, deterministic to rebuild:** the processed corpus, questions and annotations, and the
  index's `documents.jsonl`, which is a deterministic function of the corpus.
- **Not promised:** byte-identical *embeddings* on different hardware, library versions or BLAS
  backends. The index identity is therefore recorded as hashes and parameters, not asserted as
  reproducible bytes — and rebuilding the index may legitimately make the frozen plan stop verifying.
- **Not promised:** identical model outputs from a new run. `temperature=0` reduces variation; it
  does not guarantee determinism, and the study never claims it does.
- **Not claimed:** verified behaviour on operating systems other than the Windows 11 / Python 3.12.6
  environment in which these commands were run.
- **Requires the external archive:** verifying the per-run records against the verbatim provider
  responses.

## Main limitations

- One model, one dataset, one retriever, one corpus. Branch effects are not separable from this
  model's habits.
- The 60 questions are those whose gold evidence this retriever reaches in the normal top-5 *and*
  whose four fault variants a reviewer approved. 60 is a practical scope decision, not a powered
  sample size. No power calculation was performed.
- The post-retry and answer-grounding labels were accepted **after** data collection; the
  initial-context states were accepted before it. All three were researcher acceptance of prepared
  proposals rather than an independent second review, so no inter-rater reliability is claimed.
- Two annotation conventions (`G-1` identifier granularity, `K-1` kinship and spouse slots) were
  fixed before data collection but after the pilot, and were not preregistered. The predeclared
  55-question subset exists precisely to show how much the conclusions depend on them.
- Seven coordinates failed technically (`incomplete_response: max_output_tokens`); three of those
  failures occurred after a retry. All seven are missing from the semantic analysis and are never
  re-run, replaced or imputed.
- Intervals are **descriptive** bootstrap intervals over questions. No significance test, no
  non-inferiority margin and no power claim is made. Secondary and exploratory contrasts (B−A, C−A,
  D−B, per-condition breakdowns) are reported as exploratory.
- A changed document set after a retry is a retrieval property, not "recovery"; an enforced policy
  action is not evidence that the evaluator's state assessment was correct.
- The evaluator's own predictions are never used to compute "accuracy", "silent failures" or "false
  abstentions". `escalate` is a recorded outcome only — nothing is ever sent to a human or an
  external system.

No claim is made that typed control is generally better, or that it removes hallucination. The
measured effect is a trade-off in this setting.

## A note on file naming

Several filenames still carry the `stage…` prefixes of the incremental process that produced the
study (`stage12_` preparation, `stage13_` adjudication, `stage14_` execution, `stage15_` analysis).
Files whose SHA-256 is bound into the frozen plan, or recorded in the analysis reports, keep their
original names and paths on purpose: renaming them for tidiness would break the hash chain that makes
the plan verifiable. `tools/reproduce_analysis.py` is new packaging around that unchanged code, not a
replacement for it.

## Citation

See [CITATION.cff](CITATION.cff). It describes the **software** only, and records the
repository address <https://github.com/denys-yu/typed-control-rag>. No DOI, venue or
publication date is recorded for the paper, because none has been confirmed — add a
`preferred-citation` entry when those details exist.
