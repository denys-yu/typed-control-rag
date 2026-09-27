# Main experiment - analysis under protocol v3

Author: Denys Yuvzhenko

Single model (`gpt-4o-mini-2024-07-18`), single dataset (HotpotQA dev/distractor), one retriever and one reviewed, selected sample of 60 questions. Nothing here generalises beyond that. Semantic labels were accepted after data collection under the existing rubric; they are not preregistered.

## 1. Coverage and technical missingness

- Planned coordinates: **2880**; completed: **2873**; technical failures: **7** (all `incomplete_response: max_output_tokens`, left missing, never re-run or replaced).
- Seven coordinates failed technically in total; three of those failures occurred after a retry. Those three contribute retrieval diagnostics only, and their semantic outcomes remain missing like the other four.
- Answered runs: **1106**; provider attempts: **6049**.
- Accepted labels expanded through their lookups: 347 grounding cases -> 1106 answered runs; 335 post-retry contexts -> 1024 completed retry instances and 3 technical-failure retry instances, 1,027 retry instances in total.
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

### Two descriptive conditional views (neither replaces the estimator above)

**Ratio of question/condition-weighted rates - descriptive.** Computed from unrounded question-level aggregates on defective inputs; the denominator is the weighted answer rate (fully supported + not fully supported + unclear).

| Branch | Weighted answer rate (%) | Weighted fully supported share (%) |
| --- | ---: | ---: |
| A | 28.15 | 34.87 |
| B | 10.19 | 25.45 |
| C | 56.11 | 60.40 |
| D | 24.26 | 58.02 |

**Pooled proportions among observed runs - descriptive.** Counts pooled over the completed runs of the three defective conditions, without question-level weighting.

| Branch | Completed runs | Answered runs | Fully supported answers | Answered / completed (%) | Fully supported / answered (%) |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 540 | 152 | 53 | 28.15 | 34.87 |
| B | 538 | 54 | 13 | 10.04 | 24.07 |
| C | 537 | 301 | 181 | 56.05 | 60.13 |
| D | 538 | 131 | 76 | 24.35 | 58.02 |

These are two distinct descriptive diagnostics with different denominators, and neither replaces the protocol-v3 question-level estimator. Branches answer different subsets of runs, so a conditional proportion on its own does not establish equal or superior answer quality. Levels are percentages; contrasts elsewhere are differences in percentage points.

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

On initially defective inputs, branch D (typed state plus a programmatic contract) produced fewer not-fully-supported answers than branch C (binary grade plus rules), -12.04 pp (95% interval [-18.15, -6.48] pp), and fewer fully supported answers, -19.81 pp (95% interval [-27.96, -12.04] pp), alongside more abstentions or escalations, +31.85 pp (95% interval [+23.70, +40.00] pp). The interval for the primary measure stays below zero. This establishes a trade-off in the evaluated setting. Both answer categories are lower under D, and abstention or escalation is higher. Two descriptive conditional views are reported beside it, with different denominators. Pooled over observed runs on defective inputs, 58.02% of D's answers and 60.13% of C's answers are fully supported, while D answered 24.35% of its completed runs against 56.05% for C. Because the branches answer different subsets of runs, these conditional proportions do not establish improved support among emitted answers and do not isolate the mechanism behind the aggregate differences. On CLEAN inputs, D produced -8.33 pp fully supported answers relative to C and abstained or escalated +7.22 pp more often, which is the utility cost of the stricter branch; whether that cost is acceptable was not established, because no acceptance threshold and no non-inferiority margin were specified. The 55-question sensitivity subset gives -10.71 pp [-16.57, -5.45] on the primary measure, the same direction and the same qualitative conclusion as the full sample. The combined category, not-fully-supported, is PARTIALLY_SUPPORTED plus UNSUPPORTED plus CONFLICTED against the context the generator actually received; it does not by itself mean an answer is factually incorrect or hallucinated. No significance test, non-inferiority margin or power claim is made, and these are descriptive interval estimates over 60 selected questions.

## 9. Limitations

- One model (`gpt-4o-mini-2024-07-18`), one dataset (HotpotQA dev/distractor), one retriever and one corpus: branch effects are not separable from this model's habits.
- The 60 questions are those whose gold evidence this retriever reaches in the normal top-5 and whose four fault variants a reviewer accepted; 60 is a practical scope decision, not a powered sample size.
- Semantic labels were accepted after data collection under the existing rubric, by researcher acceptance of prepared proposals rather than an independent second review, so no inter-rater reliability is claimed.
- The CLEAN utility loss is measured but its acceptability is not established: no acceptance threshold and no non-inferiority margin were specified in the protocol.
- Two annotation conventions (G-1 identifier granularity, K-1 kinship and spouse slots) were fixed before data collection but after the pilot; the predeclared 55-question subset exists to show how much the conclusions depend on them.
- Seven coordinates failed technically in total; three of those failures occurred after a retry. All seven are missing from the semantic analysis and are never imputed; the three post-retry ones additionally contribute retrieval diagnostics only.
- Intervals are descriptive bootstrap intervals over questions; repeats and conditions are dependent observations inside a question and are aggregated before any comparison.
- A changed document set after a retry is a retrieval property, not recovery, and an enforced policy action is not evidence that the evaluator's state assessment was correct.

## 10. Reproduction

```powershell
python tools/stage15_accept.py
python tools/stage15_run.py
python tools/stage15_validate.py
```
