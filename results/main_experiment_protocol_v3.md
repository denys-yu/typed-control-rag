# Main experiment — protocol v3 (final, frozen before data collection)

Author: Denys Yuvzhenko
Supersedes: `results/main_experiment_protocol_v2.md` (kept unchanged on disk).
Status: **final for the main run.** Written and frozen before the first provider call of stage 14.

Paper: *The Effect of Typed Control on Retrieval-Failure Propagation in Agentic RAG Systems*.

## 0. What v3 changes

1. **Corrects the outcome partition of v2** (§2.1). v2 defined the ungrounded-answer rate as "anything
   other than `FULLY_SUPPORTED`", which silently swept `UNCLEAR` into the error category while also
   calling it separate. v3 uses four mutually exclusive completed-outcome categories.
2. **Fixes the estimation-based analysis** (§3): question-level aggregation, equal weighting of the
   three defective conditions, paired bootstrap over whole questions, 10,000 resamples, seed 42,
   95% percentile intervals, and an explicit missing-cell rule.
3. **Records the final sample** (§4): 60 questions after the exclusion of eligible question 54, and a
   predeclared 55-question sensitivity subset.
4. **Records the accepted annotation conventions** G-1 and K-1 as explicit operational conventions
   finalized before main data collection — not logical necessities, not retrospectively preregistered.

Everything else in v2 stands: branches, conditions, the one-search-retry limit, prompts, schemas,
generation parameters, the frozen main corpus and index, and the single-model single-dataset limits.

## 1. Design

Four branches (A binary/LLM, B typed/LLM, C binary/rules, D typed/contract) fully crossed with four
initial context conditions (CLEAN, PARTIAL, EMPTY, INCONSISTENT), 3 repeats:

**60 questions × 4 conditions × 4 branches × 3 repeats = 2,880 planned coordinates**, with a ceiling
of **11,520 provider attempts** (the verified four-call maximum trajectory per run; an upper bound,
never an expected count). Model: `gpt-4o-mini-2024-07-18`, `temperature = 0`,
`max_output_tokens = 800`, `max_retries = 0`, `store = false`, Structured Outputs with strict JSON
Schema. Faults affect the **initial context only**; a retry searches the **unchanged** main index.

## 2. Outcome definitions

Unit of analysis: one pipeline run = one (question, condition, branch, repeat) coordinate.
**The question is the independent sampling unit.** Repeats and conditions are dependent observations
within a question.

### 2.1 Completed semantic outcomes — four mutually exclusive categories

For every **completed** run, exactly one of:

1. **Fully supported answer** — an answer labelled `FULLY_SUPPORTED`.
2. **Not-fully-supported answer** — an answer labelled `PARTIALLY_SUPPORTED`, `UNSUPPORTED` or
   `CONFLICTED`.
3. **Unclear answer** — an answer labelled `UNCLEAR`. This is a **separate unresolved category**, not
   an error and not a success. It is never folded into category 2, and any analysis that assigns it
   is reported as a labelled sensitivity check, never as the primary result.
4. **Abstention or escalation** — the run ended without an answer by controller abstention, generator
   abstention or escalation.

### 2.2 Technical statuses — reported separately, never converted

Interrupted runs, technical failures, provider refusals, schema/JSON failures, retry-budget
exhaustion and API-budget stops are **technical statuses**. They are never counted as abstentions,
wrong answers or successes. **Technical missingness is reported against all 2,880 planned
coordinates**; semantic rates are reported against explicitly stated **completed** denominators.

### 2.3 Separate structural measure

**Citation-ID validity** (does a cited `doc_id` belong to the final context?) is reported separately
and never folded into grounding. A citation-invalid answer keeps its semantic label.

### 2.4 Labelling rules

Grounding labels are assigned by human review **against the final context actually supplied to the
generator**, not against the initial context, the gold answer or the model's own explanation. Exact
match with the benchmark answer, citation membership and the generator's explanation are **not**
evidence of grounding. Post-retry contexts get their **own** sufficiency review; an initial-context
label is never copied onto a changed context. Recovery is claimed only where a post-retry context has
an independent reviewed label of OK.

## 3. Analysis plan (fixed before execution)

### 3.1 Primary contrast

**D versus C on initially defective inputs** (the PARTIAL, EMPTY and INCONSISTENT conditions), on the
**not-fully-supported answer rate**, **always reported together with the fully supported answer
rate**, so that refusing more often cannot be presented as an unconditional improvement. Abstention
and unclear rates accompany both.

### 3.2 Aggregation, in this order

1. **Within question × condition × branch:** average the completed repeats (the cell mean of the
   outcome indicator).
2. **Within question × branch, across the three defective conditions:** the **equally weighted** mean
   of the three condition-level cell means (PARTIAL, EMPTY, INCONSISTENT each count 1/3, regardless of
   how many runs completed in each).
3. **Between branches:** the paired per-question difference (for the primary contrast, D − C).

### 3.3 Interval estimation

**Paired bootstrap resampling of whole questions**: 10,000 resamples, `random.Random(42)`, 95%
percentile intervals, resampling questions with replacement and carrying each sampled question's
complete set of cell means. **Individual runs are never resampled as independent observations.**
Estimates are reported as the observed paired mean difference with its interval; no p-value hunting,
no post-hoc non-inferiority margin, and no powered-sample claim is made — 60 questions is a practical
scope decision.

### 3.4 Missing cells

A cell is **available** when it has at least one completed run. If, for a question, either branch of a
pair has no completed observation in a required cell, **that question is unavailable for that paired
aggregate**; it is dropped from that comparison only, and the exclusion and its reason are reported
with the result. Missing cells are never imputed, and a question is never replaced.

### 3.5 CLEAN utility, reported separately

On CLEAN inputs: fully supported answer rate, abstention/escalation rate, unclear rate and
not-fully-supported rate per branch, by the same aggregation (steps 1 and 3, without step 2).

### 3.6 Secondary contrasts

B vs A, C vs A, D vs B, and per-condition breakdowns are **exploratory**. They use the same
estimator, are labelled exploratory, and carry no confirmatory claim.

### 3.7 Predeclared sensitivity analysis

The same analysis, on the same runs, excluding the five questions whose sample membership depends on
the stage 13 conventions or on a single ordinary-reading call:

| Eligible question | question_id |
| --- | --- |
| 20 | `5ae532e955429908b632656f` |
| 23 | `5a7412b655429979e28828a1` |
| 88 | `5a8e4b7c5542990e94052ab7` |
| 90 | `5aba55f25542994dbf0198e0` |
| 132 | `5ab950bd55429970cfb8ea4c` |

This yields a **55-question subset of the same experiment**. It triggers **no additional provider
calls** and **does not replace** the full-sample primary analysis.

## 4. Final sample

60 questions, selected as the first 60 in the **unchanged frozen randomized candidate order** whose
four contexts are approved with `observed_state` equal to the intended state, after the researcher's
correction recorded in `results/stage14_acceptance.json`:

- **Eligible question 54** (`5ab56200554299494045ef88`) is **excluded**, reason
  `ambiguous_question_premise`: the question conflates the beginning of medal awards with the
  beginning of the gold/silver/bronze award tradition, so its CLEAN reading would require repairing
  the premise. Its CLEAN review stays **pending** with `observed_state = null`; its contexts are not
  edited and no replacement state is manufactured.
- **Eligible question 143** (`5a82800855429966c78a6a2f`) enters as the next matching question in the
  same order.

The annotation conventions **G-1** (identifier granularity) and **K-1** (kinship and spouse slots)
are accepted as **explicit operational annotation conventions finalized before main data
collection**. They are not logical necessities and were not preregistered.

The sample excludes all 30 original pilot question ids.

## 5. Execution rules

Deterministic shuffled schedule with the recorded seed; one checkpoint row before and after every
run; resume never repeats a finished, failed or interrupted coordinate; interrupted runs stay
interrupted; every provider attempt, including failures, counts once against the global ceiling of
11,520; `max_retries = 0` (no automatic SDK retries); no provider call outside the frozen
coordinates; no extra call to inspect an interesting case or to obtain a preferred outcome. Bound
components, labels, sample membership and the schedule do not change once execution begins.

## 6. What this protocol does not claim

No effectiveness claim is made before grounding review. Data collection being complete is **not** the
same as semantic outcome annotation being complete; the two are reported separately. Findings will
concern one model, one dataset, one retriever and a reviewed, selected set of questions.
