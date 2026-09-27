# Main experiment - analysis under protocol v3

Author: Denys Yuvzhenko

Single model (`gpt-4o-mini-2024-07-18`), single dataset (HotpotQA dev/distractor), one retriever and one reviewed, selected sample of 60 questions. Nothing here generalises beyond that. Semantic labels were accepted after data collection under the existing rubric; they are not preregistered.

## 1. Coverage and technical missingness

- Planned coordinates: **2880**; completed: **2873**; technical failures: **7** (all `incomplete_response: max_output_tokens`, left missing, never re-run or replaced).
- Answered runs: **1106**; provider attempts: **6049**.
- Accepted labels expanded through their lookups: 347 grounding cases -> 1106 answered runs; 335 post-retry contexts -> 1024 completed retried runs (plus 3 technically failed retried runs, retrieval coverage only).
- Semantic rates below use **completed runs** as their denominator; technical missingness is reported against all planned coordinates.
- The accepted grounding labels contain no `UNCLEAR` case, so the unclear-answer category is defined by the protocol but empty in this dataset; it is still reported as its own column rather than folded into any other category.

## 2. Primary contrast: D versus C on initially defective inputs

Question-level estimator: repeats averaged within each question x condition x branch cell, the three defective conditions weighted one third each, then paired per-question differences averaged over questions. Intervals are 95% percentile bootstrap intervals from 10,000 resamples of whole questions (seed 42).

| Contrast (D - C, defective inputs) | Difference (pp) | 95% interval | Questions |
| --- | ---: | :---: | ---: |
| Not fully supported answers (primary) | -12.04 | [-18.15, -6.48] | 60 |
| Fully supported answers | -19.81 | [-27.96, -12.04] | 60 |
| Abstention or escalation | +31.85 | [+23.70, +40.00] | 60 |
| Unclear answers | +0.00 | [+0.00, +0.00] | 60 |

Branch levels on defective inputs (same aggregation, percentage points):

| Branch | Fully supported | Not fully supported | Unclear | Abstention/escalation |
| --- | ---: | ---: | ---: | ---: |
| A | 9.81 | 18.33 | 0.00 | 71.85 |
| B | 2.59 | 7.59 | 0.00 | 89.81 |
| C | 33.89 | 22.22 | 0.00 | 43.89 |
| D | 14.07 | 10.19 | 0.00 | 75.74 |

Answer-conditional view (different denominator: answered runs, not all completed runs):

| Branch | Answered (pp of completed) | Fully supported share of answers (pp) |
| --- | ---: | ---: |
| A | 28.14 | 34.86 |
| B | 10.18 | 25.44 |
| C | 56.11 | 60.40 |
| D | 24.26 | 58.00 |

## 3. CLEAN utility

| Branch | Fully supported | Not fully supported | Unclear | Abstention/escalation |
| --- | ---: | ---: | ---: | ---: |
| A | 66.11 | 3.33 | 0.00 | 30.56 |
| B | 53.89 | 1.67 | 0.00 | 44.44 |
| C | 68.33 | 2.78 | 0.00 | 28.89 |
| D | 60.00 | 3.89 | 0.00 | 36.11 |

| Contrast (D - C, CLEAN inputs) | Difference (pp) | 95% interval | Questions |
| --- | ---: | :---: | ---: |
| Fully supported answers | -8.33 | [-16.11, -1.67] | 60 |
| Abstention or escalation | +7.22 | [+0.56, +15.00] | 60 |
| Not fully supported answers | +1.11 | [-2.78, +5.56] | 60 |

## 4. Per-condition breakdown (D - C)

| Condition | Not fully supported (pp) | Fully supported (pp) | Abstention/escalation (pp) |
| --- | ---: | ---: | ---: |
| CLEAN | +1.11 [-2.78, +5.56] | -8.33 | +7.22 |
| PARTIAL | -10.00 [-19.44, -1.11] | -8.33 | +18.33 |
| EMPTY | -8.89 [-16.12, -2.78] | -37.22 | +46.11 |
| INCONSISTENT | -17.22 [-26.67, -8.89] | -13.89 | +31.11 |

## 5. Exploratory contrasts (defective inputs)

Labelled exploratory: they carry no confirmatory claim.

| Contrast | Not fully supported (pp) | Fully supported (pp) | Abstention/escalation (pp) |
| --- | ---: | ---: | ---: |
| B - A | -10.74 [-16.48, -5.74] | -7.22 | +17.96 |
| C - A | +3.89 [+0.74, +7.59] | +24.07 | -27.96 |
| D - B | +2.59 [+0.19, +5.56] | +11.48 | -14.07 |

## 6. Predeclared sensitivity analysis (55 questions)

The same runs, excluding the five questions whose sample membership depends on the stage 13 conventions G-1 and K-1 or on a single ordinary-reading call.

| Contrast (D - C, defective inputs) | Difference (pp) | 95% interval | Questions |
| --- | ---: | :---: | ---: |
| Not fully supported answers (primary) | -10.71 | [-16.57, -5.45] | 55 |
| Fully supported answers | -21.62 | [-30.10, -13.33] | 55 |
| Abstention or escalation | +32.32 | [+24.04, +41.01] | 55 |

## 7. Diagnostics

- Retry: 1024 completed runs retried (35.64% of completed runs). Document-set change after retry: {'set_changed': 1004, 'order_only': 16, 'identical': 4}. A changed document set is a retrieval change, not recovery.
- Reviewed post-retry states and what the run then produced: {'post_retry_OK': 747, 'post_retry_OK_then_abstention_or_escalation': 400, 'post_retry_OK_then_fully_supported_answer': 332, 'post_retry_PARTIAL': 263, 'post_retry_OK_then_not_fully_supported_answer': 15, 'post_retry_EMPTY': 14}. Context restoration to OK is reported separately from producing a fully supported answer.
- Policy: 1357 proposed-action mismatches over 3897 steps with a proposal. 665 executions diverged from the policy action in A and B, which is those branches' design, and 0 contract violations occurred in C and D. Enforced compliance is not evidence that the evaluator's state assessment was correct.
- Citation-ID validity, independent of grounding: {'False': 243, 'not_applicable': 1774, 'True': 863}. All invalid-citation answers are retained with their accepted labels.
- Usage: 6049 provider attempts, 6049 logged calls, 9458529 tokens (8815546 input, 642983 output, 108288 cached); mean recorded run latency 3.317 s. No monetary estimate is given.

Initial evaluator against the accepted reviewed state of the initial context:

- typed grader (B, D): {'OK': {'OK': 189, 'PARTIAL': 166, 'INCONSISTENT': 5}, 'EMPTY': {'EMPTY': 292, 'PARTIAL': 68}, 'PARTIAL': {'PARTIAL': 280, 'OK': 48, 'EMPTY': 32}, 'INCONSISTENT': {'PARTIAL': 171, 'OK': 31, 'INCONSISTENT': 154}}
- binary grader (A, C): {'OK': {'True': 249, 'False': 111}, 'non-OK': {'False': 893, 'True': 184}}

## 8. What this means

On initially defective inputs, branch D (typed state plus a programmatic contract) and branch C (binary grade plus rules) differ by -12.04 pp in the rate of answers their final context does not fully support (95% interval [-18.15, -6.48] pp), and by -19.81 pp in the rate of fully supported answers (95% interval [-27.96, -12.04] pp). D produced fewer not-fully-supported answers than C, and the interval stays below zero. The two figures belong together: D lowers both kinds of answer, so any reduction in unsupported answers is bought by answering less often rather than by answering better. Conditional on answering at all, the share of fully supported answers is 58.0% for D and 60.4% for C, while D answers 24.3% of completed runs against 56.1% for C, so the difference is mostly in how often each branch answers rather than in how well it answers when it does. On CLEAN inputs, D produces -8.33 pp fully supported answers relative to C and abstains or escalates +7.22 pp more often, which is the utility cost of the stricter branch. The 55-question sensitivity subset gives -10.71 pp [-16.57, -5.45] on the primary measure, the same direction and the same qualitative conclusion as the full sample. No significance test, non-inferiority margin or power claim is made, and these are descriptive interval estimates over 60 selected questions.

## 9. Limitations

- One model (`gpt-4o-mini-2024-07-18`), one dataset (HotpotQA dev/distractor), one retriever and one corpus: branch effects are not separable from this model's habits.
- The 60 questions are those whose gold evidence this retriever reaches in the normal top-5 and whose four fault variants a reviewer accepted; 60 is a practical scope decision, not a powered sample size.
- Semantic labels were accepted after data collection under the existing rubric, by researcher acceptance of prepared proposals rather than an independent second review, so no inter-rater reliability is claimed.
- Two annotation conventions (G-1 identifier granularity, K-1 kinship and spouse slots) were fixed before data collection but after the pilot; the predeclared 55-question subset exists to show how much the conclusions depend on them.
- 7 of 2,880 coordinates are missing as recorded technical failures and are never imputed; three further runs failed technically after a retry and contribute retrieval coverage only.
- Intervals are descriptive bootstrap intervals over questions; repeats and conditions are dependent observations inside a question and are aggregated before any comparison.
- A changed document set after a retry is a retrieval property, not recovery, and an enforced policy action is not evidence that the evaluator's state assessment was correct.

## 10. Reproduction

```powershell
python tools/stage15_accept.py
python tools/stage15_run.py
python tools/stage15_validate.py
```
