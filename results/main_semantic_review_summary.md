# Main semantic review proposals

Status: proposals for researcher acceptance; not accepted annotations and not an independent second human review.

## What is supplied

- `main_post_retry_review_proposals.jsonl`: 335 context-state proposals.
- `main_answer_grounding_review_proposals.jsonl`: 347 answer and explanation proposals.
- `main_post_retry_lookup_additions.json`: three proposed supplemental mappings for technically failed runs after retrieval.
- `main_semantic_review_manifest.json`: source hashes, checks and unweighted unique-case counts.

All notes are English and refer to full document IDs. Original review templates, run index, frozen protocol, execution records and observations are unchanged. No model-provider calls or coordinate reruns were performed. Review IDs PR/AG follow the order of the supplied context/case files; content hashes are the join keys.

`proposed_review_status: approved` means that the proposed semantic judgement is ready for researcher consideration. It does not mean that the researcher has accepted it or that the context/answer is good. No reviewer name or acceptance timestamp is assigned in these proposal files.

## Method and scope

The supplied protocol v3 hash matches Stage 14's recorded hash. Judgements use the supplied question and document content, applying the context rules, the grounding rubric, and accepted G-1/K-1 conventions. Answers and explanations are judged separately. Benchmark answers, outside fact lookup, citation-ID validity and the model's explanation are not evidence for the answer.

Evidence was organized by question and identical document sets for inspection (314 groups), retaining all 335 ordered-context hashes and 347 complete-output hashes in the deliverables. Document-set equivalence was only an inspection aid: an answer label was not inferred from its context-state label. No case was merged out of the source inventory. The prose was read in full; score/branch/condition/repeat/frequency metadata were excluded from the semantic inspection view. Earlier technical reconciliation inspected mappings, so this is not a claim of fully blinded or independent annotation. No branch effect estimates were used to choose labels or calculated from these unaccepted proposals.

Eight ordered post-retry contexts also match recorded initial contexts; the proposals agree with their frozen states. A broader same-document-set consistency check was used to apply the existing identifying-qualification convention, not to alter frozen labels. In particular, an early draft overlooked the required mob-assassin qualifier in the Philip Carlo cases; this was corrected before delivery. No new sampling or execution rule is introduced.

## Proposed label counts

Counts below are **unique reviewed cases**, not pipeline-run rates, branch comparisons, or independent observations.

### Post Retry States

| Label | Cases |
| --- | ---: |
| EMPTY | 3 |
| OK | 250 |
| PARTIAL | 82 |

### Answer Support

| Label | Cases |
| --- | ---: |
| CONFLICTED | 25 |
| FULLY_SUPPORTED | 249 |
| PARTIALLY_SUPPORTED | 67 |
| UNSUPPORTED | 6 |

### Explanation Support

| Label | Cases |
| --- | ---: |
| CONFLICTED | 18 |
| FULLY_SUPPORTED | 292 |
| PARTIALLY_SUPPORTED | 37 |

## Decisions worth confirming first

These are explicit readings of the supplied evidence and existing rubric. They are not additional model calls, a revised sample, or post-hoc exclusions. If a reading is rejected, revise the affected proposals consistently and record the decision before the primary analysis. Do not choose a reading based on the resulting branch contrast.

### Mission identifier versus shuttle name

G-1 requires a mission designator. Challenger is supported as a vehicle but remains a partial answer, including when STS-51-L is available in the context. Explanations that only state the shuttle and honoree are fully supported.

Affected review IDs: PR-0002, PR-0118, PR-0184, PR-0221, PR-0236, PR-0309, AG-0035, AG-0046, AG-0069, AG-0159, AG-0195, AG-0238, AG-0300, AG-0334.

### General answer survives a narrower conflict

Panthers/tigers remain supported despite conflicting island ranges for one leopard subspecies. Brooklyn/New York City is shared by both conflicting neighborhood accounts. An INCONSISTENT context does not mechanically imply a CONFLICTED answer.

Affected review IDs: AG-0076, AG-0094, AG-0133, AG-0198, AG-0201, AG-0268, AG-0298, AG-0343.

### Identifying qualifications remain required

The Snatch cases lack the 2000 British-film identification; the Philip Carlo cases lack the mob-assassin description of Kuklinski. Proposed PARTIAL/PARTIALLY_SUPPORTED follows A2 rather than treating these qualifications as dispensable. K273 matches the frozen initial PARTIAL reading.

Affected review IDs: PR-0081, AG-0040, AG-0065, AG-0163, AG-0253, AG-0288.

### Positive single-species property

The text explicitly calls Chilopsis monotypic. Proposed OK treats the question as selecting an option positively satisfying that property, not as requiring proof that Cunninghamia cannot also have one species. Cunninghamia counts are not invented.

Affected review IDs: PR-0062, PR-0115, PR-0182.

### Mall in a different city

Winter Haven is the specified second-ranked city, but Eagle Ridge Mall is explicitly in Lake Wales; the answer is CONFLICTED. Its explanation does not supply the needed city-to-mall link.

Affected review IDs: PR-0219, AG-0024, AG-0123, AG-0127.

### Calendar date not in evidence

Review AG-0102 specifically: October 21, 2009 is not given in the supplied context, although the debut season and episode are. The answer is UNSUPPORTED; the explanation is partly supported.

Affected review IDs: AG-0102.

### Film nationality versus language

Review AG-0180 and AG-0283 specifically: Italian English-language identifies nationality plus language, not evidence of two spoken languages. The extra Italian language claim makes the answer partly supported; the explanations are assessed separately.

Affected review IDs: AG-0180, AG-0283.

### Honors selection versus coached team

Helfrich is fully supported as the Oregon coach. Explanations saying he coached the All-Pac-12 honors selection are only partly supported. AG-0272 correctly describes the selection as featuring players and is fully supported.

Affected review IDs: PR-0206, AG-0057, AG-0068, AG-0106, AG-0124, AG-0153, AG-0269, AG-0272, AG-0301.

### Wrong-looking candidate without a proved contradiction

The Cypress Hill passage supports South Gate as that group's origin, but supplies no connection to RedEye to Paris. Proposed PARTIALLY_SUPPORTED records the missing identifying relationship; no remembered artist identity is used to manufacture a contradiction.

Affected review IDs: AG-0337.

### Cooking method for a different dumpling category

Boiling of potato/plum or chicken dumplings does not establish how the bread dumplings served with Svickova are prepared. The method answer is UNSUPPORTED while the explanation contains a supported serving relationship.

Affected review IDs: AG-0156.

## The three extra retrieval mappings

The exported post-retry lookup covers 1,024 completed runs. The run index contains 1,027 retried runs, including three that failed technically after retrieval. All three match one already exported context by question, ordered document IDs, and the run-level context hash shared with completed counterparts. They therefore require no additional context annotation, subject to the local raw-content check in the supplement.

Preserve the original completed-run lookup. If needed, create an augmented lookup with explicit completed/technical scopes. Adding these mappings must not turn the three missing semantic outcomes into completed cases, recovery successes, or answers. Primary completed-outcome denominators remain unchanged. A reviewed OK context can be reported as a retrieval property separately from a technically failed pipeline outcome.

## How to accept and use the proposals

1. Copy these five files to the project's `results` folder. Do not overwrite either original `*_reviews.jsonl` with a proposal file: their schemas intentionally differ.
2. Review the decisions above and accept or amend the proposals. No additional paid experiment is needed for this step.
3. After explicit researcher acceptance, archive the current pending review files with hashes. Join contexts by `context_sha256` and answers by `case_sha256`; require exact one-to-one coverage and matching source hashes.
4. Copy `proposed_observed_state` to `observed_state`; copy `proposed_answer_support`/`proposed_explanation_support` to their corresponding review fields; set the accepted `review_status`, `reviewer: Denys Yuvzhenko`, and the English note. Preserve the original five-field context and six-field answer schemas. Record the actual acceptance time and scope in a separate acceptance record. Do not backdate annotations or describe the proposals as an independent human review.
5. Keep all 7 technical failures missing; keep all 243 invalid citation-ID answers. Expand accepted labels through their appropriate lookups, without dropping rows, repairing answers, changing citation IDs, or repeating runs.
6. Analyze under protocol v3: completed outcomes in four separate categories; whole-question paired bootstrap; the D-versus-C contrast paired with fully supported answers; CLEAN utility; equal weighting of the three defective conditions; the predeclared 55-question sensitivity subset. Keep answer grounding, explanation grounding, citation validity, context restoration and technical status separate. Do not substitute pooled run rates for the specified question-level estimator.

No author or coauthor attribution is introduced by this package. Researcher approval of semantic labels remains a separate action.
