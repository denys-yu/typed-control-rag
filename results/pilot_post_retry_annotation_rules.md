# Post-retry context annotation rules

Version: **post-retry-annotation-rules v1.0**

Author: Denys Yuvzhenko

These are the rules actually used to label the 50 distinct post-retry contexts. They were written
down at Stage 10, **after** the pilot had been executed and after the proposals had been drafted.
They are **not** preregistered, and they are not independent of the pilot: they record and clarify
the conventions the initial annotations had already followed, plus the interpretations accepted in
the Stage 10 instruction. Nothing here was chosen by looking at branch performance or at which
reading improved a result.

## A. Rules already used in the initial annotations

**A1 - the four states.** Source: `results/fault_review_examples.md`, the 'Criteria' paragraph.
OK: the context allows a well-founded answer to the whole question. PARTIAL: useful evidence
exists but a necessary part is missing and is not recoverable from the other documents. EMPTY: no
useful evidence, although documents may be topically close. INCONSISTENT: visibly incompatible
claims about the same relevant fact that are not explained by a different time, object or meaning.

**A2 - necessary identifying relationships must be supported by the context.** Source: the approved
PARTIAL decisions in `data/processed/fault_cases/reviews.jsonl` for the cricket, university,
Groningen, book-series and television questions. Each records PARTIAL because one relation or
constraint stated in the question is unsupported, even where the rest of the chain is present. A
convention read off approved decisions, not a sentence in a rubric document.

**A3 - an indirect association does not recover a missing fact.** Source: the approved PARTIAL
decision for the magazine question, which explicitly declined to recover a magazine's base from an
editor's employment at another publication.

**A4 - editorial and publication locations are evidence of where a magazine is based.** Source: the
approved CLEAN/OK decision for the magazine question, 'Under the ordinary interpretation of the
question about where the magazines are based ...'. This is an ordinary reading of the term 'based',
applied to the same question it was accepted for.

## B. Interpretations accepted in the Stage 10 instruction

**B1 - volume authorship does not establish series authorship.** Knowing that a novel is by an
author, and that the novel belongs to a series, does not establish who wrote the series. Applies to
context #29, which is therefore PARTIAL. This is a gap in the evidence chain and is **not** treated
as the same kind of judgement as A4: A4 reads an ordinary meaning of a term that the documents do
support, whereas here a distinct relation is simply absent from the documents.

**B2 - the A2 requirement applies to the television contexts.** Contexts #34 and #35 carry the
series' broadcast schedule and end date but no document connecting Kent or Kenn Scott to the series.
The question identifies the series through that writing credit, so under A2 the relation must be
supported by the context. Both are PARTIAL. The ground is A2 itself, not an appeal to symmetry with
another case.

**B3 - contexts #1 and #3 remain OK** under A4, the interpretation already accepted for that
question.

## C. Scope

These rules label the **context**: whether the supplied documents support answering the question.
`approved` means the assigned label has been accepted as the right description of that context; it
does not mean the context is OK, and approving a context as PARTIAL is a complete outcome.

A context label is **not** a grounding label for any answer produced from that context. Answer
grounding is assessed separately, under its own rubric.

