# Answer-grounding review

Author: Denys Yuvzhenko

76 distinct cases. Each one is a question, the exact ordered context the generator was given,
and the complete answer it returned. Decide whether the answer to the question is supported by that
context.

## Rubric

Record a primary label in `results/pilot_answer_grounding_reviews.jsonl` under `answer_support`, by
`review_id`:

* **FULLY_SUPPORTED** - the complete answer, including the identifying relationships the question
  requires, follows from the supplied evidence, with no unresolved relevant contradiction.
* **PARTIALLY_SUPPORTED** - some required claims or relationships are supported, others lack evidence.
* **UNSUPPORTED** - the evidence does not support the substantive answer.
* **CONFLICTED** - relevant supplied evidence contradicts the answer, or contains an unresolved conflict
  that the answer depends on.
* **UNCLEAR** - the case cannot be resolved reliably under this rubric. An explanation is required.

Every label needs a justification in `note`, referring to the documents you relied on by their number or
`doc_id`.

If the generator supplied an explanation, also record `explanation_support` using the same five labels,
judging the explanation's own claims. Leave it `null` when there is no explanation. This keeps an
unsupported rationale distinguishable from an unsupported answer.

Ordinary reasoning over the supplied documents is expected. Do not add facts from your own knowledge:
if the context does not contain it, it is not evidence here.

### What does not count as grounding

* Agreement with a benchmark answer is **not** evidence of grounding, and benchmark answers are not shown.
* A correct-looking value without the identifying relationship the question requires may still be
  insufficient - for example a school count for a university the context never links to the named person.
* A `doc_id` being valid does **not** prove that the document supports the answer. Membership is checked
  structurally; whether the content supports the claim is your judgement.
* The generator's explanation is a claim to inspect, not independent evidence.
* A context's own state label does **not** determine the grounding label of an answer drawn from it.

Deliberately not shown: branch, injected condition, repeat number, evaluator decisions, controller
actions, context state labels, benchmark answers, correctness scores, and how many runs produced each
case. The run mapping is in `results/pilot_answer_grounding_lookup.json`.

---

## AG-0001

* `case_sha256`: `076c42d063245752c2542875499f4067e9a1cae8f2e3c9a2c28b0d5dc1ca9e86`

**Question:** A Wind in the Door is part of a series written by who?

**Context supplied to the generator (5 documents, in order):**

### [1] A Wind in the Door

`doc_id: a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85`

A Wind in the Door is a young adult science fantasy novel by Madeleine L'Engle.
 It is a companion book to "A Wrinkle in Time", and part of the Time Quintet.

### [2] The Four Winds of Love

`doc_id: f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c`

The Four Winds of Love is the overall title for a series of six novels written by Compton Mackenzie, "The East Wind of Love" (1937), "The South Wind of Love" (1938), "The West Wind of Love" (1940), "West to North" (1942), "The North Wind of Love, Book 1" (1944) and "The North Wind of Love, Book 2" (1945), which taken together constitute a major fictional chronicle of the first forty years of the twentieth century.
 The main protagonist of the hexalogy is the semi-autobiographical character of John Ogilvie.

### [3] Close the Last Door

`doc_id: d427b4d61dfd5c4d1e6687dd9fa717ad4ba0aee031db3e78c2251c020fc5cb9f`

Close the Last Door (Japanese: 最後のドアを閉めろ!
 , Hepburn: Saigo no Door wo Shimero! )
 is a yaoi manga series written by Yugi Yamada.
 It has been adapted into an OVA directed by Tama.
 It is licensed in North America by Digital Manga Publishing, which published the first volume in 2006.

### [4] Door to Door (Modern Family)

`doc_id: 1b07bca2974914aecee772e6c82b10981c64d46bdb758a546f87fd251f584d4f`

"Door to Door" is the fourth episode of the third season of the American sitcom "Modern Family", and the series' 52nd episode overall.
 "Door to Door" first aired on October 5, 2011, on ABC.
 The episode was written by Bill Wrubel and directed by Chris Koch.

### [5] Time Quintet

`doc_id: 09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de`

The Time Quintet is a fantasy/science fiction series of five young adult novels written by Madeleine L'Engle.

### Generator output

**Answer:** Madeleine L'Engle

**Explanation given by the generator:** The documents clearly state that 'A Wind in the Door' is written by Madeleine L'Engle and is part of the Time Quintet series.

**Documents the generator cited (its own citations, not a verified list):**

* `a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85` - [1] A Wind in the Door
* `5b07bca2974914aecee772e6c82b10981c64d46bdb758a546f87fd251f584d4f` - not among the documents supplied above

---

## AG-0002

* `case_sha256`: `1e097757d7d812b1e5aa25cfb44c982b581f74350269741a6c2689908f8df5b9`

**Question:** A Wind in the Door is part of a series written by who?

**Context supplied to the generator (5 documents, in order):**

### [1] A Wind in the Door

`doc_id: a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85`

A Wind in the Door is a young adult science fantasy novel by Madeleine L'Engle.
 It is a companion book to "A Wrinkle in Time", and part of the Time Quintet.

### [2] The Four Winds of Love

`doc_id: f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c`

The Four Winds of Love is the overall title for a series of six novels written by Compton Mackenzie, "The East Wind of Love" (1937), "The South Wind of Love" (1938), "The West Wind of Love" (1940), "West to North" (1942), "The North Wind of Love, Book 1" (1944) and "The North Wind of Love, Book 2" (1945), which taken together constitute a major fictional chronicle of the first forty years of the twentieth century.
 The main protagonist of the hexalogy is the semi-autobiographical character of John Ogilvie.

### [3] Close the Last Door

`doc_id: d427b4d61dfd5c4d1e6687dd9fa717ad4ba0aee031db3e78c2251c020fc5cb9f`

Close the Last Door (Japanese: 最後のドアを閉めろ!
 , Hepburn: Saigo no Door wo Shimero! )
 is a yaoi manga series written by Yugi Yamada.
 It has been adapted into an OVA directed by Tama.
 It is licensed in North America by Digital Manga Publishing, which published the first volume in 2006.

### [4] Door to Door (Modern Family)

`doc_id: 1b07bca2974914aecee772e6c82b10981c64d46bdb758a546f87fd251f584d4f`

"Door to Door" is the fourth episode of the third season of the American sitcom "Modern Family", and the series' 52nd episode overall.
 "Door to Door" first aired on October 5, 2011, on ABC.
 The episode was written by Bill Wrubel and directed by Chris Koch.

### [5] Time Quintet

`doc_id: 09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de`

The Time Quintet is a fantasy/science fiction series of five young adult novels written by Madeleine L'Engle.

### Generator output

**Answer:** Madeleine L'Engle

**Explanation given by the generator:** The documents clearly state that 'A Wind in the Door' is written by Madeleine L'Engle and is part of the Time Quintet series.

**Documents the generator cited (its own citations, not a verified list):**

* `a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85` - [1] A Wind in the Door
* `5e4b2e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de` - not among the documents supplied above

---

## AG-0003

* `case_sha256`: `291b4a59502bd39cfc67b5ae3386d84ebb630ed0d8af89d4031193d2a0232630`

**Question:** A Wind in the Door is part of a series written by who?

**Context supplied to the generator (5 documents, in order):**

### [1] A Wind in the Door

`doc_id: a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85`

A Wind in the Door is a young adult science fantasy novel by Madeleine L'Engle.
 It is a companion book to "A Wrinkle in Time", and part of the Time Quintet.

### [2] The Four Winds of Love

`doc_id: f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c`

The Four Winds of Love is the overall title for a series of six novels written by Compton Mackenzie, "The East Wind of Love" (1937), "The South Wind of Love" (1938), "The West Wind of Love" (1940), "West to North" (1942), "The North Wind of Love, Book 1" (1944) and "The North Wind of Love, Book 2" (1945), which taken together constitute a major fictional chronicle of the first forty years of the twentieth century.
 The main protagonist of the hexalogy is the semi-autobiographical character of John Ogilvie.

### [3] Close the Last Door

`doc_id: d427b4d61dfd5c4d1e6687dd9fa717ad4ba0aee031db3e78c2251c020fc5cb9f`

Close the Last Door (Japanese: 最後のドアを閉めろ!
 , Hepburn: Saigo no Door wo Shimero! )
 is a yaoi manga series written by Yugi Yamada.
 It has been adapted into an OVA directed by Tama.
 It is licensed in North America by Digital Manga Publishing, which published the first volume in 2006.

### [4] John Kuenster

`doc_id: 76370702233eba20a2a2d6db40c7386c05bcd0f8a53536e9ddd093c93e9ca79d`

John Kuenster (June 18, 1924 – April 2, 2012) was a sportswriter for the "Chicago Daily News" and most notably, was the editor of the periodical "Baseball Digest".
 He also wrote the books "To Sleep with the Angels" (1990), "Heartbreakers" (2002) and "At Home and Away" (2003), among others.

### [5] Dan Angel

`doc_id: 7f178e2bf31b623def96e59d1fe244677e794f67c6a614c15c5f9bdf6077c521`

Dan Angel is an American film and television producer, screenwriter, story editor and showrunner.
 He has written and produced a number of television series and movies, often with his writing partner Billy Brown, including "The X-Files", "Goosebumps", "Animorphs", "", "Door to Door", "", "Christmas in Canaan", "" and "Dan Vs.".
 His work has won numerous awards, including a Primetime Emmy Award for Outstanding Made for Television Movie and Peabody Award recognizing his work executive producing "Door to Door".
 and another Emmy Award for Outstanding Children's Series in his work on .

### Generator output

**Answer:** Madeleine L'Engle

**Explanation given by the generator:** The document explicitly states that 'A Wind in the Door' is written by Madeleine L'Engle.

**Documents the generator cited (its own citations, not a verified list):**

* `a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85` - [1] A Wind in the Door

---

## AG-0004

* `case_sha256`: `2d40f3ff4a3d93eaca712f16afb5b400fea2ba7366bb3f4272d27b7938c92502`

**Question:** A Wind in the Door is part of a series written by who?

**Context supplied to the generator (5 documents, in order):**

### [1] A Wind in the Door

`doc_id: a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85`

A Wind in the Door is a young adult science fantasy novel by Madeleine L'Engle.
 It is a companion book to "A Wrinkle in Time", and part of the Time Quintet.

### [2] The Four Winds of Love

`doc_id: f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c`

The Four Winds of Love is the overall title for a series of six novels written by Compton Mackenzie, "The East Wind of Love" (1937), "The South Wind of Love" (1938), "The West Wind of Love" (1940), "West to North" (1942), "The North Wind of Love, Book 1" (1944) and "The North Wind of Love, Book 2" (1945), which taken together constitute a major fictional chronicle of the first forty years of the twentieth century.
 The main protagonist of the hexalogy is the semi-autobiographical character of John Ogilvie.

### [3] Close the Last Door

`doc_id: d427b4d61dfd5c4d1e6687dd9fa717ad4ba0aee031db3e78c2251c020fc5cb9f`

Close the Last Door (Japanese: 最後のドアを閉めろ!
 , Hepburn: Saigo no Door wo Shimero! )
 is a yaoi manga series written by Yugi Yamada.
 It has been adapted into an OVA directed by Tama.
 It is licensed in North America by Digital Manga Publishing, which published the first volume in 2006.

### [4] Door to Door (Modern Family)

`doc_id: 1b07bca2974914aecee772e6c82b10981c64d46bdb758a546f87fd251f584d4f`

"Door to Door" is the fourth episode of the third season of the American sitcom "Modern Family", and the series' 52nd episode overall.
 "Door to Door" first aired on October 5, 2011, on ABC.
 The episode was written by Bill Wrubel and directed by Chris Koch.

### [5] Time Quintet

`doc_id: 09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de`

The Time Quintet is a fantasy/science fiction series of five young adult novels written by Madeleine L'Engle.

### Generator output

**Answer:** Madeleine L'Engle

**Explanation given by the generator:** The documents clearly state that 'A Wind in the Door' is written by Madeleine L'Engle and is part of the Time Quintet series.

**Documents the generator cited (its own citations, not a verified list):**

* `a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85` - [1] A Wind in the Door
* `f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c` - [2] The Four Winds of Love
* `09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de` - [5] Time Quintet

---

## AG-0005

* `case_sha256`: `324338234c94d5612075af53c27cf6726dc74e9581dc54cf345526dac9c558ef`

**Question:** A Wind in the Door is part of a series written by who?

**Context supplied to the generator (5 documents, in order):**

### [1] A Wind in the Door

`doc_id: a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85`

A Wind in the Door is a young adult science fantasy novel by Madeleine L'Engle.
 It is a companion book to "A Wrinkle in Time", and part of the Time Quintet.

### [2] The Four Winds of Love

`doc_id: f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c`

The Four Winds of Love is the overall title for a series of six novels written by Compton Mackenzie, "The East Wind of Love" (1937), "The South Wind of Love" (1938), "The West Wind of Love" (1940), "West to North" (1942), "The North Wind of Love, Book 1" (1944) and "The North Wind of Love, Book 2" (1945), which taken together constitute a major fictional chronicle of the first forty years of the twentieth century.
 The main protagonist of the hexalogy is the semi-autobiographical character of John Ogilvie.

### [3] Close the Last Door

`doc_id: d427b4d61dfd5c4d1e6687dd9fa717ad4ba0aee031db3e78c2251c020fc5cb9f`

Close the Last Door (Japanese: 最後のドアを閉めろ!
 , Hepburn: Saigo no Door wo Shimero! )
 is a yaoi manga series written by Yugi Yamada.
 It has been adapted into an OVA directed by Tama.
 It is licensed in North America by Digital Manga Publishing, which published the first volume in 2006.

### [4] Time Quintet

`doc_id: bbfb2e6e8d4dc46867bcf5946d36658c780bca6cc7c13c3fd87485b23120e6ec`

The Time Quintet is a fantasy/science fiction series of five young adult novels written by Ursula K. Le Guin.

### [5] Time Quintet

`doc_id: 09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de`

The Time Quintet is a fantasy/science fiction series of five young adult novels written by Madeleine L'Engle.

### Generator output

**Answer:** Madeleine L'Engle

**Explanation given by the generator:** The documents clearly state that 'A Wind in the Door' is written by Madeleine L'Engle and is part of the Time Quintet series.

**Documents the generator cited (its own citations, not a verified list):**

* `a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85` - [1] A Wind in the Door
* `09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de` - [5] Time Quintet

---

## AG-0006

* `case_sha256`: `347c9989c5970618643860fb44378c8d05a4081959bd7522ea14253ecbc1719e`

**Question:** A Wind in the Door is part of a series written by who?

**Context supplied to the generator (5 documents, in order):**

### [1] A Wind in the Door

`doc_id: a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85`

A Wind in the Door is a young adult science fantasy novel by Madeleine L'Engle.
 It is a companion book to "A Wrinkle in Time", and part of the Time Quintet.

### [2] The Four Winds of Love

`doc_id: f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c`

The Four Winds of Love is the overall title for a series of six novels written by Compton Mackenzie, "The East Wind of Love" (1937), "The South Wind of Love" (1938), "The West Wind of Love" (1940), "West to North" (1942), "The North Wind of Love, Book 1" (1944) and "The North Wind of Love, Book 2" (1945), which taken together constitute a major fictional chronicle of the first forty years of the twentieth century.
 The main protagonist of the hexalogy is the semi-autobiographical character of John Ogilvie.

### [3] Close the Last Door

`doc_id: d427b4d61dfd5c4d1e6687dd9fa717ad4ba0aee031db3e78c2251c020fc5cb9f`

Close the Last Door (Japanese: 最後のドアを閉めろ!
 , Hepburn: Saigo no Door wo Shimero! )
 is a yaoi manga series written by Yugi Yamada.
 It has been adapted into an OVA directed by Tama.
 It is licensed in North America by Digital Manga Publishing, which published the first volume in 2006.

### [4] Time Quintet

`doc_id: bbfb2e6e8d4dc46867bcf5946d36658c780bca6cc7c13c3fd87485b23120e6ec`

The Time Quintet is a fantasy/science fiction series of five young adult novels written by Ursula K. Le Guin.

### [5] Time Quintet

`doc_id: 09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de`

The Time Quintet is a fantasy/science fiction series of five young adult novels written by Madeleine L'Engle.

### Generator output

**Answer:** Madeleine L'Engle

**Explanation given by the generator:** The documents clearly state that 'A Wind in the Door' is written by Madeleine L'Engle and is part of the Time Quintet series.

**Documents the generator cited (its own citations, not a verified list):**

* `a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85` - [1] A Wind in the Door
* `f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c` - [2] The Four Winds of Love
* `09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de` - [5] Time Quintet

---

## AG-0007

* `case_sha256`: `7198af3ba9fb39677145a552f4b953f16db9b9c64632e391423fbd25a1056323`

**Question:** A Wind in the Door is part of a series written by who?

**Context supplied to the generator (5 documents, in order):**

### [1] A Wind in the Door

`doc_id: a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85`

A Wind in the Door is a young adult science fantasy novel by Madeleine L'Engle.
 It is a companion book to "A Wrinkle in Time", and part of the Time Quintet.

### [2] The Four Winds of Love

`doc_id: f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c`

The Four Winds of Love is the overall title for a series of six novels written by Compton Mackenzie, "The East Wind of Love" (1937), "The South Wind of Love" (1938), "The West Wind of Love" (1940), "West to North" (1942), "The North Wind of Love, Book 1" (1944) and "The North Wind of Love, Book 2" (1945), which taken together constitute a major fictional chronicle of the first forty years of the twentieth century.
 The main protagonist of the hexalogy is the semi-autobiographical character of John Ogilvie.

### [3] Close the Last Door

`doc_id: d427b4d61dfd5c4d1e6687dd9fa717ad4ba0aee031db3e78c2251c020fc5cb9f`

Close the Last Door (Japanese: 最後のドアを閉めろ!
 , Hepburn: Saigo no Door wo Shimero! )
 is a yaoi manga series written by Yugi Yamada.
 It has been adapted into an OVA directed by Tama.
 It is licensed in North America by Digital Manga Publishing, which published the first volume in 2006.

### [4] Door to Door (Modern Family)

`doc_id: 1b07bca2974914aecee772e6c82b10981c64d46bdb758a546f87fd251f584d4f`

"Door to Door" is the fourth episode of the third season of the American sitcom "Modern Family", and the series' 52nd episode overall.
 "Door to Door" first aired on October 5, 2011, on ABC.
 The episode was written by Bill Wrubel and directed by Chris Koch.

### [5] Time Quintet

`doc_id: 09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de`

The Time Quintet is a fantasy/science fiction series of five young adult novels written by Madeleine L'Engle.

### Generator output

**Answer:** Madeleine L'Engle

**Explanation given by the generator:** The documents clearly state that 'A Wind in the Door' is written by Madeleine L'Engle and is part of the Time Quintet series.

**Documents the generator cited (its own citations, not a verified list):**

* `a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85` - [1] A Wind in the Door
* `09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de` - [5] Time Quintet

---

## AG-0008

* `case_sha256`: `7a62f9fd221fb88a22c521ffec00a42c7081c17c7fda335341b2117f55ffb256`

**Question:** A Wind in the Door is part of a series written by who?

**Context supplied to the generator (5 documents, in order):**

### [1] A Wind in the Door

`doc_id: a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85`

A Wind in the Door is a young adult science fantasy novel by Madeleine L'Engle.
 It is a companion book to "A Wrinkle in Time", and part of the Time Quintet.

### [2] The Four Winds of Love

`doc_id: f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c`

The Four Winds of Love is the overall title for a series of six novels written by Compton Mackenzie, "The East Wind of Love" (1937), "The South Wind of Love" (1938), "The West Wind of Love" (1940), "West to North" (1942), "The North Wind of Love, Book 1" (1944) and "The North Wind of Love, Book 2" (1945), which taken together constitute a major fictional chronicle of the first forty years of the twentieth century.
 The main protagonist of the hexalogy is the semi-autobiographical character of John Ogilvie.

### [3] Close the Last Door

`doc_id: d427b4d61dfd5c4d1e6687dd9fa717ad4ba0aee031db3e78c2251c020fc5cb9f`

Close the Last Door (Japanese: 最後のドアを閉めろ!
 , Hepburn: Saigo no Door wo Shimero! )
 is a yaoi manga series written by Yugi Yamada.
 It has been adapted into an OVA directed by Tama.
 It is licensed in North America by Digital Manga Publishing, which published the first volume in 2006.

### [4] Door to Door (Modern Family)

`doc_id: 1b07bca2974914aecee772e6c82b10981c64d46bdb758a546f87fd251f584d4f`

"Door to Door" is the fourth episode of the third season of the American sitcom "Modern Family", and the series' 52nd episode overall.
 "Door to Door" first aired on October 5, 2011, on ABC.
 The episode was written by Bill Wrubel and directed by Chris Koch.

### [5] Time Quintet

`doc_id: 09772e4b22159225093e3843c45e1db28de14c89e3e8216a0deccbffc491e7de`

The Time Quintet is a fantasy/science fiction series of five young adult novels written by Madeleine L'Engle.

### Generator output

**Answer:** Madeleine L'Engle

**Explanation given by the generator:** The documents clearly state that 'A Wind in the Door' is written by Madeleine L'Engle and is part of the Time Quintet series.

**Documents the generator cited (its own citations, not a verified list):**

* `a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85` - [1] A Wind in the Door
* `5` - not among the documents supplied above

---

## AG-0009

* `case_sha256`: `f1ff2d00a887a5240e984432f69496614eeb37b7f8582e6a35563fa1984f109f`

**Question:** A Wind in the Door is part of a series written by who?

**Context supplied to the generator (5 documents, in order):**

### [1] A Wind in the Door

`doc_id: a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85`

A Wind in the Door is a young adult science fantasy novel by Madeleine L'Engle.
 It is a companion book to "A Wrinkle in Time", and part of the Time Quintet.

### [2] The Four Winds of Love

`doc_id: f1cd50819103fbfd90f02222b0e41d3092c4638ca7dff7ab6987a5017054040c`

The Four Winds of Love is the overall title for a series of six novels written by Compton Mackenzie, "The East Wind of Love" (1937), "The South Wind of Love" (1938), "The West Wind of Love" (1940), "West to North" (1942), "The North Wind of Love, Book 1" (1944) and "The North Wind of Love, Book 2" (1945), which taken together constitute a major fictional chronicle of the first forty years of the twentieth century.
 The main protagonist of the hexalogy is the semi-autobiographical character of John Ogilvie.

### [3] Close the Last Door

`doc_id: d427b4d61dfd5c4d1e6687dd9fa717ad4ba0aee031db3e78c2251c020fc5cb9f`

Close the Last Door (Japanese: 最後のドアを閉めろ!
 , Hepburn: Saigo no Door wo Shimero! )
 is a yaoi manga series written by Yugi Yamada.
 It has been adapted into an OVA directed by Tama.
 It is licensed in North America by Digital Manga Publishing, which published the first volume in 2006.

### [4] John Kuenster

`doc_id: 76370702233eba20a2a2d6db40c7386c05bcd0f8a53536e9ddd093c93e9ca79d`

John Kuenster (June 18, 1924 – April 2, 2012) was a sportswriter for the "Chicago Daily News" and most notably, was the editor of the periodical "Baseball Digest".
 He also wrote the books "To Sleep with the Angels" (1990), "Heartbreakers" (2002) and "At Home and Away" (2003), among others.

### [5] Dan Angel

`doc_id: 7f178e2bf31b623def96e59d1fe244677e794f67c6a614c15c5f9bdf6077c521`

Dan Angel is an American film and television producer, screenwriter, story editor and showrunner.
 He has written and produced a number of television series and movies, often with his writing partner Billy Brown, including "The X-Files", "Goosebumps", "Animorphs", "", "Door to Door", "", "Christmas in Canaan", "" and "Dan Vs.".
 His work has won numerous awards, including a Primetime Emmy Award for Outstanding Made for Television Movie and Peabody Award recognizing his work executive producing "Door to Door".
 and another Emmy Award for Outstanding Children's Series in his work on .

### Generator output

**Answer:** Madeleine L'Engle

**Explanation given by the generator:** The document explicitly states that 'A Wind in the Door' is a novel by Madeleine L'Engle.

**Documents the generator cited (its own citations, not a verified list):**

* `a81ef98f92d9bb197d45462fc7181a659787c8b5aae9ccb23afbc2e13ad38f85` - [1] A Wind in the Door

---

## AG-0010

* `case_sha256`: `07c8f87b401f9c0e74bc143dd67777124e2ee22cd2190579a00e1b4239bd10eb`

**Question:** Bill Woodfull opened pairing with what cricketer who died in April of 1991?

**Context supplied to the generator (5 documents, in order):**

### [1] Bill Woodfull

`doc_id: b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b`

William Maldon "Bill" Woodfull OBE (22 August 1897 – 11 August 1965) was an Australian cricketer of the 1920s and 1930s.
 He captained both Victoria and Australia, and was best known for his dignified and moral conduct during the tumultuous bodyline series in 1932–33 that almost saw the end of Anglo-Australian cricketing ties.
 Trained as a schoolteacher, Woodfull was known for his benevolent attitude towards his players, and his patience and defensive technique as an opening batsman.
 Woodfull was not a flamboyant player, but was known for his calm, unruffled style and his reliability in difficult situations.
 His opening pairing with fellow Victorian Bill Ponsford for both his state and Australia remains one of the most successful in history.
 While not known for his tactical skills, Woodfull was widely admired by his players and observers for his sportsmanship and ability to mould a successful and loyal team through the strength of his character.

### [2] Murray Hedgcock

`doc_id: eded850f5f431035715ba5292c5eca5d45cd9010dfab306b02caf6b4063664db`

Murray Hedgcock (born 23 February 1931) is an Australian cricket writer and journalist.
 He was born in south Melbourne and grew up in various country towns in Victoria.
 The test cricketer Bill Woodfull was the headmaster of one of his schools.
 After leaving school, he worked briefly in a bank before becoming a journalist.
 From 1966 until his retirement in 1991, he was posted to London.
 He wrote regularly for "The Australian", Wisden and "The Cricketer".

### [3] Jack Fingleton

`doc_id: 2dd07053467e3574ac11d0ee371e43ab80098a4fb2432e71afce045407dfcfa8`

John "Jack" Henry Webb Fingleton OBE (28 April 190822 November 1981) was an Australian cricketer who was trained as a journalist and became a political and cricket commentator after the end of his playing career.
 A stubborn opening batsman known for his dour defensive approach, he scored five Test centuries, representing Australia in 18 Tests between 1932 and 1938.
 He was also known for his involvement in several cricket diplomacy incidents in his career, accused of leaking the infamous verbal exchange between Australian captain Bill Woodfull and English manager Plum Warner during the acrimonious Bodyline series, and later of causing sectarian tension within the team by leading a group of players of Irish Catholic descent in undermining the leadership of the Protestant Don Bradman.
 In retirement, Fingleton became a prominent political commentator in Canberra, with links to Australian prime ministers.
 The author of many cricket books, he is regarded as one of Australia's finest cricket writers, with a perceptive and occasionally sardonic style, marked by persistent criticisms of Bradman.

### [4] Bill Ponsford

`doc_id: a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4`

William Harold "Bill" Ponsford (19 October 1900 – 6 April 1991) was an Australian cricketer.
 Usually playing as an opening batsman, he formed a successful and long-lived partnership opening the batting for Victoria and Australia with Bill Woodfull, his friend and state and national captain.
 Ponsford is the only player to twice break the world record for the highest individual score in first-class cricket; Ponsford and Brian Lara are the only cricketers to twice score 400 runs in an innings.
 Ponsford holds the Australian record for a partnership in Test cricket, set in 1934 in combination with Donald Bradman(451 for 2nd wicket)—the man who broke many of Ponsford's other individual records.In fact,he along with Don Bradman set the record for the highest partnership ever for any wicket in Test cricket history when playing in away soil (451 runs for the second wicket)

### [5] Adelaide leak

`doc_id: 5c4083d0cb34e9a9e5db935c3f0c67bd1b6fcc6bd78e6459c2f98e1e571220a7`

The Adelaide leak was the revelation to the press of a dressing-room incident during the third Test, a cricket match played during the 1932–33 Ashes series between Australia and England, more commonly known as the Bodyline series.
 During the course of play on 14 January 1933, the Australian Test captain Bill Woodfull was struck over the heart by a ball delivered by Harold Larwood.
 Although not badly hurt, Woodfull was shaken and dismissed shortly afterwards.
 On his return to the Australian dressing room, Woodfull was visited by the managers of the Marylebone Cricket Club (MCC) team, Pelham Warner and Richard Palairet.
 Warner enquired after Woodfull's health, but the latter dismissed his concerns in brusque fashion.
 He said he did not want to speak to the Englishman owing to the Bodyline tactics England were using, leaving Warner embarrassed and shaken.
 The matter became public knowledge when someone present leaked the exchange to the press and it was widely reported on 16 January.
 Such leaks to the press were practically unknown at the time, and the players were horrified that the confrontation became public knowledge.

### Generator output

**Answer:** Bill Ponsford

**Explanation given by the generator:** Bill Woodfull opened pairing with Bill Ponsford, who died in April 1991.

**Documents the generator cited (its own citations, not a verified list):**

* `b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b` - [1] Bill Woodfull
* `a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4` - [4] Bill Ponsford

---

## AG-0011

* `case_sha256`: `33495bfb795d0f9667e45fb4860fc43d4e702af18da0e79136f163521ed4936f`

**Question:** Bill Woodfull opened pairing with what cricketer who died in April of 1991?

**Context supplied to the generator (5 documents, in order):**

### [1] Bill Woodfull

`doc_id: b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b`

William Maldon "Bill" Woodfull OBE (22 August 1897 – 11 August 1965) was an Australian cricketer of the 1920s and 1930s.
 He captained both Victoria and Australia, and was best known for his dignified and moral conduct during the tumultuous bodyline series in 1932–33 that almost saw the end of Anglo-Australian cricketing ties.
 Trained as a schoolteacher, Woodfull was known for his benevolent attitude towards his players, and his patience and defensive technique as an opening batsman.
 Woodfull was not a flamboyant player, but was known for his calm, unruffled style and his reliability in difficult situations.
 His opening pairing with fellow Victorian Bill Ponsford for both his state and Australia remains one of the most successful in history.
 While not known for his tactical skills, Woodfull was widely admired by his players and observers for his sportsmanship and ability to mould a successful and loyal team through the strength of his character.

### [2] Murray Hedgcock

`doc_id: eded850f5f431035715ba5292c5eca5d45cd9010dfab306b02caf6b4063664db`

Murray Hedgcock (born 23 February 1931) is an Australian cricket writer and journalist.
 He was born in south Melbourne and grew up in various country towns in Victoria.
 The test cricketer Bill Woodfull was the headmaster of one of his schools.
 After leaving school, he worked briefly in a bank before becoming a journalist.
 From 1966 until his retirement in 1991, he was posted to London.
 He wrote regularly for "The Australian", Wisden and "The Cricketer".

### [3] Adelaide leak

`doc_id: 5c4083d0cb34e9a9e5db935c3f0c67bd1b6fcc6bd78e6459c2f98e1e571220a7`

The Adelaide leak was the revelation to the press of a dressing-room incident during the third Test, a cricket match played during the 1932–33 Ashes series between Australia and England, more commonly known as the Bodyline series.
 During the course of play on 14 January 1933, the Australian Test captain Bill Woodfull was struck over the heart by a ball delivered by Harold Larwood.
 Although not badly hurt, Woodfull was shaken and dismissed shortly afterwards.
 On his return to the Australian dressing room, Woodfull was visited by the managers of the Marylebone Cricket Club (MCC) team, Pelham Warner and Richard Palairet.
 Warner enquired after Woodfull's health, but the latter dismissed his concerns in brusque fashion.
 He said he did not want to speak to the Englishman owing to the Bodyline tactics England were using, leaving Warner embarrassed and shaken.
 The matter became public knowledge when someone present leaked the exchange to the press and it was widely reported on 16 January.
 Such leaks to the press were practically unknown at the time, and the players were horrified that the confrontation became public knowledge.

### [4] Bill Ponsford

`doc_id: adc806096baaa4aff6bf16e1cc7c15a9a0a20ec07895851ce870b09a58d09910`

William Harold "Bill" Ponsford (19 October 1900 – 6 April 1990) was an Australian cricketer.
 Usually playing as an opening batsman, he formed a successful and long-lived partnership opening the batting for Victoria and Australia with Bill Woodfull, his friend and state and national captain.
 Ponsford is the only player to twice break the world record for the highest individual score in first-class cricket; Ponsford and Brian Lara are the only cricketers to twice score 400 runs in an innings.
 Ponsford holds the Australian record for a partnership in Test cricket, set in 1934 in combination with Donald Bradman(451 for 2nd wicket)—the man who broke many of Ponsford's other individual records.In fact,he along with Don Bradman set the record for the highest partnership ever for any wicket in Test cricket history when playing in away soil (451 runs for the second wicket)

### [5] Bill Ponsford

`doc_id: a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4`

William Harold "Bill" Ponsford (19 October 1900 – 6 April 1991) was an Australian cricketer.
 Usually playing as an opening batsman, he formed a successful and long-lived partnership opening the batting for Victoria and Australia with Bill Woodfull, his friend and state and national captain.
 Ponsford is the only player to twice break the world record for the highest individual score in first-class cricket; Ponsford and Brian Lara are the only cricketers to twice score 400 runs in an innings.
 Ponsford holds the Australian record for a partnership in Test cricket, set in 1934 in combination with Donald Bradman(451 for 2nd wicket)—the man who broke many of Ponsford's other individual records.In fact,he along with Don Bradman set the record for the highest partnership ever for any wicket in Test cricket history when playing in away soil (451 runs for the second wicket)

### Generator output

**Answer:** Bill Ponsford

**Explanation given by the generator:** Bill Ponsford, who opened the batting with Bill Woodfull, died in April 1991.

**Documents the generator cited (its own citations, not a verified list):**

* `b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b` - [1] Bill Woodfull
* `5c4083d0cb34e9a9e5db935c3f0c67bd1b6fcc6bd78e6459c2f98e1e571220a7` - [3] Adelaide leak
* `adc806096baaa4aff6bf16e1cc7c15a9a0a20ec07895851ce870b09a58d09910` - [4] Bill Ponsford
* `a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4` - [5] Bill Ponsford

---

## AG-0012

* `case_sha256`: `7017101ce6689232cc89b459bf9efdf2850b43f23200c03942ccc68cc0b92d01`

**Question:** Bill Woodfull opened pairing with what cricketer who died in April of 1991?

**Context supplied to the generator (5 documents, in order):**

### [1] Bill Woodfull

`doc_id: b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b`

William Maldon "Bill" Woodfull OBE (22 August 1897 – 11 August 1965) was an Australian cricketer of the 1920s and 1930s.
 He captained both Victoria and Australia, and was best known for his dignified and moral conduct during the tumultuous bodyline series in 1932–33 that almost saw the end of Anglo-Australian cricketing ties.
 Trained as a schoolteacher, Woodfull was known for his benevolent attitude towards his players, and his patience and defensive technique as an opening batsman.
 Woodfull was not a flamboyant player, but was known for his calm, unruffled style and his reliability in difficult situations.
 His opening pairing with fellow Victorian Bill Ponsford for both his state and Australia remains one of the most successful in history.
 While not known for his tactical skills, Woodfull was widely admired by his players and observers for his sportsmanship and ability to mould a successful and loyal team through the strength of his character.

### [2] Murray Hedgcock

`doc_id: eded850f5f431035715ba5292c5eca5d45cd9010dfab306b02caf6b4063664db`

Murray Hedgcock (born 23 February 1931) is an Australian cricket writer and journalist.
 He was born in south Melbourne and grew up in various country towns in Victoria.
 The test cricketer Bill Woodfull was the headmaster of one of his schools.
 After leaving school, he worked briefly in a bank before becoming a journalist.
 From 1966 until his retirement in 1991, he was posted to London.
 He wrote regularly for "The Australian", Wisden and "The Cricketer".

### [3] Jack Fingleton

`doc_id: 2dd07053467e3574ac11d0ee371e43ab80098a4fb2432e71afce045407dfcfa8`

John "Jack" Henry Webb Fingleton OBE (28 April 190822 November 1981) was an Australian cricketer who was trained as a journalist and became a political and cricket commentator after the end of his playing career.
 A stubborn opening batsman known for his dour defensive approach, he scored five Test centuries, representing Australia in 18 Tests between 1932 and 1938.
 He was also known for his involvement in several cricket diplomacy incidents in his career, accused of leaking the infamous verbal exchange between Australian captain Bill Woodfull and English manager Plum Warner during the acrimonious Bodyline series, and later of causing sectarian tension within the team by leading a group of players of Irish Catholic descent in undermining the leadership of the Protestant Don Bradman.
 In retirement, Fingleton became a prominent political commentator in Canberra, with links to Australian prime ministers.
 The author of many cricket books, he is regarded as one of Australia's finest cricket writers, with a perceptive and occasionally sardonic style, marked by persistent criticisms of Bradman.

### [4] Adelaide leak

`doc_id: 5c4083d0cb34e9a9e5db935c3f0c67bd1b6fcc6bd78e6459c2f98e1e571220a7`

The Adelaide leak was the revelation to the press of a dressing-room incident during the third Test, a cricket match played during the 1932–33 Ashes series between Australia and England, more commonly known as the Bodyline series.
 During the course of play on 14 January 1933, the Australian Test captain Bill Woodfull was struck over the heart by a ball delivered by Harold Larwood.
 Although not badly hurt, Woodfull was shaken and dismissed shortly afterwards.
 On his return to the Australian dressing room, Woodfull was visited by the managers of the Marylebone Cricket Club (MCC) team, Pelham Warner and Richard Palairet.
 Warner enquired after Woodfull's health, but the latter dismissed his concerns in brusque fashion.
 He said he did not want to speak to the Englishman owing to the Bodyline tactics England were using, leaving Warner embarrassed and shaken.
 The matter became public knowledge when someone present leaked the exchange to the press and it was widely reported on 16 January.
 Such leaks to the press were practically unknown at the time, and the players were horrified that the confrontation became public knowledge.

### [5] Bill Ponsford

`doc_id: a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4`

William Harold "Bill" Ponsford (19 October 1900 – 6 April 1991) was an Australian cricketer.
 Usually playing as an opening batsman, he formed a successful and long-lived partnership opening the batting for Victoria and Australia with Bill Woodfull, his friend and state and national captain.
 Ponsford is the only player to twice break the world record for the highest individual score in first-class cricket; Ponsford and Brian Lara are the only cricketers to twice score 400 runs in an innings.
 Ponsford holds the Australian record for a partnership in Test cricket, set in 1934 in combination with Donald Bradman(451 for 2nd wicket)—the man who broke many of Ponsford's other individual records.In fact,he along with Don Bradman set the record for the highest partnership ever for any wicket in Test cricket history when playing in away soil (451 runs for the second wicket)

### Generator output

**Answer:** Bill Ponsford

**Explanation given by the generator:** Bill Woodfull opened pairing with Bill Ponsford, who died in April 1991.

**Documents the generator cited (its own citations, not a verified list):**

* `b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b` - [1] Bill Woodfull
* `5c4083d0cb34e9a9e5db935c3f0c67bd1b6fcc6bd78e6459c2f98e1e571220a7` - [4] Adelaide leak
* `a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4` - [5] Bill Ponsford

---

## AG-0013

* `case_sha256`: `8e25af6a4365ff0bf37a537f6fd98ad7566b8165de847c67cf8925728b9e2146`

**Question:** Bill Woodfull opened pairing with what cricketer who died in April of 1991?

**Context supplied to the generator (5 documents, in order):**

### [1] Bill Woodfull

`doc_id: b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b`

William Maldon "Bill" Woodfull OBE (22 August 1897 – 11 August 1965) was an Australian cricketer of the 1920s and 1930s.
 He captained both Victoria and Australia, and was best known for his dignified and moral conduct during the tumultuous bodyline series in 1932–33 that almost saw the end of Anglo-Australian cricketing ties.
 Trained as a schoolteacher, Woodfull was known for his benevolent attitude towards his players, and his patience and defensive technique as an opening batsman.
 Woodfull was not a flamboyant player, but was known for his calm, unruffled style and his reliability in difficult situations.
 His opening pairing with fellow Victorian Bill Ponsford for both his state and Australia remains one of the most successful in history.
 While not known for his tactical skills, Woodfull was widely admired by his players and observers for his sportsmanship and ability to mould a successful and loyal team through the strength of his character.

### [2] Bill Ponsford

`doc_id: a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4`

William Harold "Bill" Ponsford (19 October 1900 – 6 April 1991) was an Australian cricketer.
 Usually playing as an opening batsman, he formed a successful and long-lived partnership opening the batting for Victoria and Australia with Bill Woodfull, his friend and state and national captain.
 Ponsford is the only player to twice break the world record for the highest individual score in first-class cricket; Ponsford and Brian Lara are the only cricketers to twice score 400 runs in an innings.
 Ponsford holds the Australian record for a partnership in Test cricket, set in 1934 in combination with Donald Bradman(451 for 2nd wicket)—the man who broke many of Ponsford's other individual records.In fact,he along with Don Bradman set the record for the highest partnership ever for any wicket in Test cricket history when playing in away soil (451 runs for the second wicket)

### [3] Murray Hedgcock

`doc_id: eded850f5f431035715ba5292c5eca5d45cd9010dfab306b02caf6b4063664db`

Murray Hedgcock (born 23 February 1931) is an Australian cricket writer and journalist.
 He was born in south Melbourne and grew up in various country towns in Victoria.
 The test cricketer Bill Woodfull was the headmaster of one of his schools.
 After leaving school, he worked briefly in a bank before becoming a journalist.
 From 1966 until his retirement in 1991, he was posted to London.
 He wrote regularly for "The Australian", Wisden and "The Cricketer".

### [4] Jack Fingleton

`doc_id: 2dd07053467e3574ac11d0ee371e43ab80098a4fb2432e71afce045407dfcfa8`

John "Jack" Henry Webb Fingleton OBE (28 April 190822 November 1981) was an Australian cricketer who was trained as a journalist and became a political and cricket commentator after the end of his playing career.
 A stubborn opening batsman known for his dour defensive approach, he scored five Test centuries, representing Australia in 18 Tests between 1932 and 1938.
 He was also known for his involvement in several cricket diplomacy incidents in his career, accused of leaking the infamous verbal exchange between Australian captain Bill Woodfull and English manager Plum Warner during the acrimonious Bodyline series, and later of causing sectarian tension within the team by leading a group of players of Irish Catholic descent in undermining the leadership of the Protestant Don Bradman.
 In retirement, Fingleton became a prominent political commentator in Canberra, with links to Australian prime ministers.
 The author of many cricket books, he is regarded as one of Australia's finest cricket writers, with a perceptive and occasionally sardonic style, marked by persistent criticisms of Bradman.

### [5] James MacLaren (cricketer)

`doc_id: 47f2e416002a5b5b60152e1efe8da76d75bbc13728dcdd1c0916ac47e7728b64`

James Alexander MacLaren (4 January 1870 – 8 July 1952) was an English cricketer who played first-class cricket for Lancashire County Cricket Club between 1891 and 1894.
 Born in Whalley Range, Manchester, and the eldest of seven brothers, MacLaren was a keen cricketer from his youngest days.
 He was particularly close to his younger brother Archie, who later captained England.
 He attended Elstree School and Harrow School, where he coached as a cricketer and was later joined by Archie.
 He also received coaching at Old Trafford Cricket Ground, where his father was treasurer of Lancashire County Cricket Club.
 He played in the Harrow first team between 1886 and 1888, and was appointed captain in his final year.
 Upon leaving Harrow, he played on four occasions for Lancashire between 1891 and 1894 but had little success.
 On one occasion in 1894, he opened the batting with his brother Archie, who was captain of Lancashire by that stage.
 In 1900, he qualified as a doctor of medicine.
 He died at the age of 82 following a fall.

### Generator output

**Answer:** Bill Ponsford

**Explanation given by the generator:** Bill Woodfull opened pairing with Bill Ponsford, who died in April 1991.

**Documents the generator cited (its own citations, not a verified list):**

* `b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b` - [1] Bill Woodfull
* `a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4` - [2] Bill Ponsford

---

## AG-0014

* `case_sha256`: `bac2792b765054115fe26961fa74dbd49bfcea87e7b33c38cd38a94b0ce358b3`

**Question:** Bill Woodfull opened pairing with what cricketer who died in April of 1991?

**Context supplied to the generator (5 documents, in order):**

### [1] Bill Woodfull

`doc_id: b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b`

William Maldon "Bill" Woodfull OBE (22 August 1897 – 11 August 1965) was an Australian cricketer of the 1920s and 1930s.
 He captained both Victoria and Australia, and was best known for his dignified and moral conduct during the tumultuous bodyline series in 1932–33 that almost saw the end of Anglo-Australian cricketing ties.
 Trained as a schoolteacher, Woodfull was known for his benevolent attitude towards his players, and his patience and defensive technique as an opening batsman.
 Woodfull was not a flamboyant player, but was known for his calm, unruffled style and his reliability in difficult situations.
 His opening pairing with fellow Victorian Bill Ponsford for both his state and Australia remains one of the most successful in history.
 While not known for his tactical skills, Woodfull was widely admired by his players and observers for his sportsmanship and ability to mould a successful and loyal team through the strength of his character.

### [2] Murray Hedgcock

`doc_id: eded850f5f431035715ba5292c5eca5d45cd9010dfab306b02caf6b4063664db`

Murray Hedgcock (born 23 February 1931) is an Australian cricket writer and journalist.
 He was born in south Melbourne and grew up in various country towns in Victoria.
 The test cricketer Bill Woodfull was the headmaster of one of his schools.
 After leaving school, he worked briefly in a bank before becoming a journalist.
 From 1966 until his retirement in 1991, he was posted to London.
 He wrote regularly for "The Australian", Wisden and "The Cricketer".

### [3] Bill Ponsford

`doc_id: a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4`

William Harold "Bill" Ponsford (19 October 1900 – 6 April 1991) was an Australian cricketer.
 Usually playing as an opening batsman, he formed a successful and long-lived partnership opening the batting for Victoria and Australia with Bill Woodfull, his friend and state and national captain.
 Ponsford is the only player to twice break the world record for the highest individual score in first-class cricket; Ponsford and Brian Lara are the only cricketers to twice score 400 runs in an innings.
 Ponsford holds the Australian record for a partnership in Test cricket, set in 1934 in combination with Donald Bradman(451 for 2nd wicket)—the man who broke many of Ponsford's other individual records.In fact,he along with Don Bradman set the record for the highest partnership ever for any wicket in Test cricket history when playing in away soil (451 runs for the second wicket)

### [4] Jack Fingleton

`doc_id: 2dd07053467e3574ac11d0ee371e43ab80098a4fb2432e71afce045407dfcfa8`

John "Jack" Henry Webb Fingleton OBE (28 April 190822 November 1981) was an Australian cricketer who was trained as a journalist and became a political and cricket commentator after the end of his playing career.
 A stubborn opening batsman known for his dour defensive approach, he scored five Test centuries, representing Australia in 18 Tests between 1932 and 1938.
 He was also known for his involvement in several cricket diplomacy incidents in his career, accused of leaking the infamous verbal exchange between Australian captain Bill Woodfull and English manager Plum Warner during the acrimonious Bodyline series, and later of causing sectarian tension within the team by leading a group of players of Irish Catholic descent in undermining the leadership of the Protestant Don Bradman.
 In retirement, Fingleton became a prominent political commentator in Canberra, with links to Australian prime ministers.
 The author of many cricket books, he is regarded as one of Australia's finest cricket writers, with a perceptive and occasionally sardonic style, marked by persistent criticisms of Bradman.

### [5] Adelaide leak

`doc_id: 5c4083d0cb34e9a9e5db935c3f0c67bd1b6fcc6bd78e6459c2f98e1e571220a7`

The Adelaide leak was the revelation to the press of a dressing-room incident during the third Test, a cricket match played during the 1932–33 Ashes series between Australia and England, more commonly known as the Bodyline series.
 During the course of play on 14 January 1933, the Australian Test captain Bill Woodfull was struck over the heart by a ball delivered by Harold Larwood.
 Although not badly hurt, Woodfull was shaken and dismissed shortly afterwards.
 On his return to the Australian dressing room, Woodfull was visited by the managers of the Marylebone Cricket Club (MCC) team, Pelham Warner and Richard Palairet.
 Warner enquired after Woodfull's health, but the latter dismissed his concerns in brusque fashion.
 He said he did not want to speak to the Englishman owing to the Bodyline tactics England were using, leaving Warner embarrassed and shaken.
 The matter became public knowledge when someone present leaked the exchange to the press and it was widely reported on 16 January.
 Such leaks to the press were practically unknown at the time, and the players were horrified that the confrontation became public knowledge.

### Generator output

**Answer:** Bill Ponsford

**Explanation given by the generator:** Bill Woodfull opened pairing with Bill Ponsford, who died in April 1991.

**Documents the generator cited (its own citations, not a verified list):**

* `b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b` - [1] Bill Woodfull
* `a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4` - [3] Bill Ponsford

---

## AG-0015

* `case_sha256`: `beb9bfe1be8146616b8ec6e93052e5b9bd55792ec49c73dd2213af4519ab994f`

**Question:** Bill Woodfull opened pairing with what cricketer who died in April of 1991?

**Context supplied to the generator (5 documents, in order):**

### [1] Bill Woodfull

`doc_id: b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b`

William Maldon "Bill" Woodfull OBE (22 August 1897 – 11 August 1965) was an Australian cricketer of the 1920s and 1930s.
 He captained both Victoria and Australia, and was best known for his dignified and moral conduct during the tumultuous bodyline series in 1932–33 that almost saw the end of Anglo-Australian cricketing ties.
 Trained as a schoolteacher, Woodfull was known for his benevolent attitude towards his players, and his patience and defensive technique as an opening batsman.
 Woodfull was not a flamboyant player, but was known for his calm, unruffled style and his reliability in difficult situations.
 His opening pairing with fellow Victorian Bill Ponsford for both his state and Australia remains one of the most successful in history.
 While not known for his tactical skills, Woodfull was widely admired by his players and observers for his sportsmanship and ability to mould a successful and loyal team through the strength of his character.

### [2] Murray Hedgcock

`doc_id: eded850f5f431035715ba5292c5eca5d45cd9010dfab306b02caf6b4063664db`

Murray Hedgcock (born 23 February 1931) is an Australian cricket writer and journalist.
 He was born in south Melbourne and grew up in various country towns in Victoria.
 The test cricketer Bill Woodfull was the headmaster of one of his schools.
 After leaving school, he worked briefly in a bank before becoming a journalist.
 From 1966 until his retirement in 1991, he was posted to London.
 He wrote regularly for "The Australian", Wisden and "The Cricketer".

### [3] Adelaide leak

`doc_id: 5c4083d0cb34e9a9e5db935c3f0c67bd1b6fcc6bd78e6459c2f98e1e571220a7`

The Adelaide leak was the revelation to the press of a dressing-room incident during the third Test, a cricket match played during the 1932–33 Ashes series between Australia and England, more commonly known as the Bodyline series.
 During the course of play on 14 January 1933, the Australian Test captain Bill Woodfull was struck over the heart by a ball delivered by Harold Larwood.
 Although not badly hurt, Woodfull was shaken and dismissed shortly afterwards.
 On his return to the Australian dressing room, Woodfull was visited by the managers of the Marylebone Cricket Club (MCC) team, Pelham Warner and Richard Palairet.
 Warner enquired after Woodfull's health, but the latter dismissed his concerns in brusque fashion.
 He said he did not want to speak to the Englishman owing to the Bodyline tactics England were using, leaving Warner embarrassed and shaken.
 The matter became public knowledge when someone present leaked the exchange to the press and it was widely reported on 16 January.
 Such leaks to the press were practically unknown at the time, and the players were horrified that the confrontation became public knowledge.

### [4] Jack Fingleton

`doc_id: 2dd07053467e3574ac11d0ee371e43ab80098a4fb2432e71afce045407dfcfa8`

John "Jack" Henry Webb Fingleton OBE (28 April 190822 November 1981) was an Australian cricketer who was trained as a journalist and became a political and cricket commentator after the end of his playing career.
 A stubborn opening batsman known for his dour defensive approach, he scored five Test centuries, representing Australia in 18 Tests between 1932 and 1938.
 He was also known for his involvement in several cricket diplomacy incidents in his career, accused of leaking the infamous verbal exchange between Australian captain Bill Woodfull and English manager Plum Warner during the acrimonious Bodyline series, and later of causing sectarian tension within the team by leading a group of players of Irish Catholic descent in undermining the leadership of the Protestant Don Bradman.
 In retirement, Fingleton became a prominent political commentator in Canberra, with links to Australian prime ministers.
 The author of many cricket books, he is regarded as one of Australia's finest cricket writers, with a perceptive and occasionally sardonic style, marked by persistent criticisms of Bradman.

### [5] Bill Ponsford

`doc_id: a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4`

William Harold "Bill" Ponsford (19 October 1900 – 6 April 1991) was an Australian cricketer.
 Usually playing as an opening batsman, he formed a successful and long-lived partnership opening the batting for Victoria and Australia with Bill Woodfull, his friend and state and national captain.
 Ponsford is the only player to twice break the world record for the highest individual score in first-class cricket; Ponsford and Brian Lara are the only cricketers to twice score 400 runs in an innings.
 Ponsford holds the Australian record for a partnership in Test cricket, set in 1934 in combination with Donald Bradman(451 for 2nd wicket)—the man who broke many of Ponsford's other individual records.In fact,he along with Don Bradman set the record for the highest partnership ever for any wicket in Test cricket history when playing in away soil (451 runs for the second wicket)

### Generator output

**Answer:** Bill Ponsford

**Explanation given by the generator:** The documents indicate that Bill Woodfull opened pairing with Bill Ponsford, who died in April 1991.

**Documents the generator cited (its own citations, not a verified list):**

* `b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b` - [1] Bill Woodfull
* `a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4` - [5] Bill Ponsford

---

## AG-0016

* `case_sha256`: `c0bf014e459bad02bbac95e72a33a813cdcf135411aa3563b6af14686c8c6068`

**Question:** Bill Woodfull opened pairing with what cricketer who died in April of 1991?

**Context supplied to the generator (5 documents, in order):**

### [1] Bill Woodfull

`doc_id: b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b`

William Maldon "Bill" Woodfull OBE (22 August 1897 – 11 August 1965) was an Australian cricketer of the 1920s and 1930s.
 He captained both Victoria and Australia, and was best known for his dignified and moral conduct during the tumultuous bodyline series in 1932–33 that almost saw the end of Anglo-Australian cricketing ties.
 Trained as a schoolteacher, Woodfull was known for his benevolent attitude towards his players, and his patience and defensive technique as an opening batsman.
 Woodfull was not a flamboyant player, but was known for his calm, unruffled style and his reliability in difficult situations.
 His opening pairing with fellow Victorian Bill Ponsford for both his state and Australia remains one of the most successful in history.
 While not known for his tactical skills, Woodfull was widely admired by his players and observers for his sportsmanship and ability to mould a successful and loyal team through the strength of his character.

### [2] Bill Ponsford

`doc_id: a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4`

William Harold "Bill" Ponsford (19 October 1900 – 6 April 1991) was an Australian cricketer.
 Usually playing as an opening batsman, he formed a successful and long-lived partnership opening the batting for Victoria and Australia with Bill Woodfull, his friend and state and national captain.
 Ponsford is the only player to twice break the world record for the highest individual score in first-class cricket; Ponsford and Brian Lara are the only cricketers to twice score 400 runs in an innings.
 Ponsford holds the Australian record for a partnership in Test cricket, set in 1934 in combination with Donald Bradman(451 for 2nd wicket)—the man who broke many of Ponsford's other individual records.In fact,he along with Don Bradman set the record for the highest partnership ever for any wicket in Test cricket history when playing in away soil (451 runs for the second wicket)

### [3] Murray Hedgcock

`doc_id: eded850f5f431035715ba5292c5eca5d45cd9010dfab306b02caf6b4063664db`

Murray Hedgcock (born 23 February 1931) is an Australian cricket writer and journalist.
 He was born in south Melbourne and grew up in various country towns in Victoria.
 The test cricketer Bill Woodfull was the headmaster of one of his schools.
 After leaving school, he worked briefly in a bank before becoming a journalist.
 From 1966 until his retirement in 1991, he was posted to London.
 He wrote regularly for "The Australian", Wisden and "The Cricketer".

### [4] Adelaide leak

`doc_id: 5c4083d0cb34e9a9e5db935c3f0c67bd1b6fcc6bd78e6459c2f98e1e571220a7`

The Adelaide leak was the revelation to the press of a dressing-room incident during the third Test, a cricket match played during the 1932–33 Ashes series between Australia and England, more commonly known as the Bodyline series.
 During the course of play on 14 January 1933, the Australian Test captain Bill Woodfull was struck over the heart by a ball delivered by Harold Larwood.
 Although not badly hurt, Woodfull was shaken and dismissed shortly afterwards.
 On his return to the Australian dressing room, Woodfull was visited by the managers of the Marylebone Cricket Club (MCC) team, Pelham Warner and Richard Palairet.
 Warner enquired after Woodfull's health, but the latter dismissed his concerns in brusque fashion.
 He said he did not want to speak to the Englishman owing to the Bodyline tactics England were using, leaving Warner embarrassed and shaken.
 The matter became public knowledge when someone present leaked the exchange to the press and it was widely reported on 16 January.
 Such leaks to the press were practically unknown at the time, and the players were horrified that the confrontation became public knowledge.

### [5] James MacLaren (cricketer)

`doc_id: 47f2e416002a5b5b60152e1efe8da76d75bbc13728dcdd1c0916ac47e7728b64`

James Alexander MacLaren (4 January 1870 – 8 July 1952) was an English cricketer who played first-class cricket for Lancashire County Cricket Club between 1891 and 1894.
 Born in Whalley Range, Manchester, and the eldest of seven brothers, MacLaren was a keen cricketer from his youngest days.
 He was particularly close to his younger brother Archie, who later captained England.
 He attended Elstree School and Harrow School, where he coached as a cricketer and was later joined by Archie.
 He also received coaching at Old Trafford Cricket Ground, where his father was treasurer of Lancashire County Cricket Club.
 He played in the Harrow first team between 1886 and 1888, and was appointed captain in his final year.
 Upon leaving Harrow, he played on four occasions for Lancashire between 1891 and 1894 but had little success.
 On one occasion in 1894, he opened the batting with his brother Archie, who was captain of Lancashire by that stage.
 In 1900, he qualified as a doctor of medicine.
 He died at the age of 82 following a fall.

### Generator output

**Answer:** Bill Ponsford

**Explanation given by the generator:** The documents indicate that Bill Woodfull opened pairing with Bill Ponsford, who died in April 1991.

**Documents the generator cited (its own citations, not a verified list):**

* `b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b` - [1] Bill Woodfull
* `a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4` - [2] Bill Ponsford

---

## AG-0017

* `case_sha256`: `e9745b25666a76eb4ad4079a88424a753148568d6fb992a1fdfaba7d9e48ae89`

**Question:** Bill Woodfull opened pairing with what cricketer who died in April of 1991?

**Context supplied to the generator (5 documents, in order):**

### [1] Bill Woodfull

`doc_id: b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b`

William Maldon "Bill" Woodfull OBE (22 August 1897 – 11 August 1965) was an Australian cricketer of the 1920s and 1930s.
 He captained both Victoria and Australia, and was best known for his dignified and moral conduct during the tumultuous bodyline series in 1932–33 that almost saw the end of Anglo-Australian cricketing ties.
 Trained as a schoolteacher, Woodfull was known for his benevolent attitude towards his players, and his patience and defensive technique as an opening batsman.
 Woodfull was not a flamboyant player, but was known for his calm, unruffled style and his reliability in difficult situations.
 His opening pairing with fellow Victorian Bill Ponsford for both his state and Australia remains one of the most successful in history.
 While not known for his tactical skills, Woodfull was widely admired by his players and observers for his sportsmanship and ability to mould a successful and loyal team through the strength of his character.

### [2] Murray Hedgcock

`doc_id: eded850f5f431035715ba5292c5eca5d45cd9010dfab306b02caf6b4063664db`

Murray Hedgcock (born 23 February 1931) is an Australian cricket writer and journalist.
 He was born in south Melbourne and grew up in various country towns in Victoria.
 The test cricketer Bill Woodfull was the headmaster of one of his schools.
 After leaving school, he worked briefly in a bank before becoming a journalist.
 From 1966 until his retirement in 1991, he was posted to London.
 He wrote regularly for "The Australian", Wisden and "The Cricketer".

### [3] Adelaide leak

`doc_id: 5c4083d0cb34e9a9e5db935c3f0c67bd1b6fcc6bd78e6459c2f98e1e571220a7`

The Adelaide leak was the revelation to the press of a dressing-room incident during the third Test, a cricket match played during the 1932–33 Ashes series between Australia and England, more commonly known as the Bodyline series.
 During the course of play on 14 January 1933, the Australian Test captain Bill Woodfull was struck over the heart by a ball delivered by Harold Larwood.
 Although not badly hurt, Woodfull was shaken and dismissed shortly afterwards.
 On his return to the Australian dressing room, Woodfull was visited by the managers of the Marylebone Cricket Club (MCC) team, Pelham Warner and Richard Palairet.
 Warner enquired after Woodfull's health, but the latter dismissed his concerns in brusque fashion.
 He said he did not want to speak to the Englishman owing to the Bodyline tactics England were using, leaving Warner embarrassed and shaken.
 The matter became public knowledge when someone present leaked the exchange to the press and it was widely reported on 16 January.
 Such leaks to the press were practically unknown at the time, and the players were horrified that the confrontation became public knowledge.

### [4] Jack Fingleton

`doc_id: 2dd07053467e3574ac11d0ee371e43ab80098a4fb2432e71afce045407dfcfa8`

John "Jack" Henry Webb Fingleton OBE (28 April 190822 November 1981) was an Australian cricketer who was trained as a journalist and became a political and cricket commentator after the end of his playing career.
 A stubborn opening batsman known for his dour defensive approach, he scored five Test centuries, representing Australia in 18 Tests between 1932 and 1938.
 He was also known for his involvement in several cricket diplomacy incidents in his career, accused of leaking the infamous verbal exchange between Australian captain Bill Woodfull and English manager Plum Warner during the acrimonious Bodyline series, and later of causing sectarian tension within the team by leading a group of players of Irish Catholic descent in undermining the leadership of the Protestant Don Bradman.
 In retirement, Fingleton became a prominent political commentator in Canberra, with links to Australian prime ministers.
 The author of many cricket books, he is regarded as one of Australia's finest cricket writers, with a perceptive and occasionally sardonic style, marked by persistent criticisms of Bradman.

### [5] Bill Ponsford

`doc_id: a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4`

William Harold "Bill" Ponsford (19 October 1900 – 6 April 1991) was an Australian cricketer.
 Usually playing as an opening batsman, he formed a successful and long-lived partnership opening the batting for Victoria and Australia with Bill Woodfull, his friend and state and national captain.
 Ponsford is the only player to twice break the world record for the highest individual score in first-class cricket; Ponsford and Brian Lara are the only cricketers to twice score 400 runs in an innings.
 Ponsford holds the Australian record for a partnership in Test cricket, set in 1934 in combination with Donald Bradman(451 for 2nd wicket)—the man who broke many of Ponsford's other individual records.In fact,he along with Don Bradman set the record for the highest partnership ever for any wicket in Test cricket history when playing in away soil (451 runs for the second wicket)

### Generator output

**Answer:** Bill Ponsford

**Explanation given by the generator:** Bill Ponsford was the cricketer who opened pairing with Bill Woodfull and he died in April 1991.

**Documents the generator cited (its own citations, not a verified list):**

* `b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b` - [1] Bill Woodfull
* `a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4` - [5] Bill Ponsford

---

## AG-0018

* `case_sha256`: `eb69f12cd5acc9f50adf6f4e9ec4ef47d52e191e2f555bbcf277c91b7ab277c0`

**Question:** Bill Woodfull opened pairing with what cricketer who died in April of 1991?

**Context supplied to the generator (5 documents, in order):**

### [1] Bill Woodfull

`doc_id: b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b`

William Maldon "Bill" Woodfull OBE (22 August 1897 – 11 August 1965) was an Australian cricketer of the 1920s and 1930s.
 He captained both Victoria and Australia, and was best known for his dignified and moral conduct during the tumultuous bodyline series in 1932–33 that almost saw the end of Anglo-Australian cricketing ties.
 Trained as a schoolteacher, Woodfull was known for his benevolent attitude towards his players, and his patience and defensive technique as an opening batsman.
 Woodfull was not a flamboyant player, but was known for his calm, unruffled style and his reliability in difficult situations.
 His opening pairing with fellow Victorian Bill Ponsford for both his state and Australia remains one of the most successful in history.
 While not known for his tactical skills, Woodfull was widely admired by his players and observers for his sportsmanship and ability to mould a successful and loyal team through the strength of his character.

### [2] Bill Ponsford

`doc_id: a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4`

William Harold "Bill" Ponsford (19 October 1900 – 6 April 1991) was an Australian cricketer.
 Usually playing as an opening batsman, he formed a successful and long-lived partnership opening the batting for Victoria and Australia with Bill Woodfull, his friend and state and national captain.
 Ponsford is the only player to twice break the world record for the highest individual score in first-class cricket; Ponsford and Brian Lara are the only cricketers to twice score 400 runs in an innings.
 Ponsford holds the Australian record for a partnership in Test cricket, set in 1934 in combination with Donald Bradman(451 for 2nd wicket)—the man who broke many of Ponsford's other individual records.In fact,he along with Don Bradman set the record for the highest partnership ever for any wicket in Test cricket history when playing in away soil (451 runs for the second wicket)

### [3] Murray Hedgcock

`doc_id: eded850f5f431035715ba5292c5eca5d45cd9010dfab306b02caf6b4063664db`

Murray Hedgcock (born 23 February 1931) is an Australian cricket writer and journalist.
 He was born in south Melbourne and grew up in various country towns in Victoria.
 The test cricketer Bill Woodfull was the headmaster of one of his schools.
 After leaving school, he worked briefly in a bank before becoming a journalist.
 From 1966 until his retirement in 1991, he was posted to London.
 He wrote regularly for "The Australian", Wisden and "The Cricketer".

### [4] James MacLaren (cricketer)

`doc_id: 47f2e416002a5b5b60152e1efe8da76d75bbc13728dcdd1c0916ac47e7728b64`

James Alexander MacLaren (4 January 1870 – 8 July 1952) was an English cricketer who played first-class cricket for Lancashire County Cricket Club between 1891 and 1894.
 Born in Whalley Range, Manchester, and the eldest of seven brothers, MacLaren was a keen cricketer from his youngest days.
 He was particularly close to his younger brother Archie, who later captained England.
 He attended Elstree School and Harrow School, where he coached as a cricketer and was later joined by Archie.
 He also received coaching at Old Trafford Cricket Ground, where his father was treasurer of Lancashire County Cricket Club.
 He played in the Harrow first team between 1886 and 1888, and was appointed captain in his final year.
 Upon leaving Harrow, he played on four occasions for Lancashire between 1891 and 1894 but had little success.
 On one occasion in 1894, he opened the batting with his brother Archie, who was captain of Lancashire by that stage.
 In 1900, he qualified as a doctor of medicine.
 He died at the age of 82 following a fall.

### [5] Jack Fingleton

`doc_id: 2dd07053467e3574ac11d0ee371e43ab80098a4fb2432e71afce045407dfcfa8`

John "Jack" Henry Webb Fingleton OBE (28 April 190822 November 1981) was an Australian cricketer who was trained as a journalist and became a political and cricket commentator after the end of his playing career.
 A stubborn opening batsman known for his dour defensive approach, he scored five Test centuries, representing Australia in 18 Tests between 1932 and 1938.
 He was also known for his involvement in several cricket diplomacy incidents in his career, accused of leaking the infamous verbal exchange between Australian captain Bill Woodfull and English manager Plum Warner during the acrimonious Bodyline series, and later of causing sectarian tension within the team by leading a group of players of Irish Catholic descent in undermining the leadership of the Protestant Don Bradman.
 In retirement, Fingleton became a prominent political commentator in Canberra, with links to Australian prime ministers.
 The author of many cricket books, he is regarded as one of Australia's finest cricket writers, with a perceptive and occasionally sardonic style, marked by persistent criticisms of Bradman.

### Generator output

**Answer:** Bill Ponsford

**Explanation given by the generator:** Bill Woodfull opened pairing with Bill Ponsford, who died in April 1991.

**Documents the generator cited (its own citations, not a verified list):**

* `b2fc1577b1942daeb0059d4d529e07a4f72f3079ce96b2875ef9606809cd6f2b` - [1] Bill Woodfull
* `a898ec065ae53af94962564f9fd202c9885e3357d41bd0417fdb66531ad3c2d4` - [2] Bill Ponsford

---

## AG-0019

* `case_sha256`: `28bec664ca6089b8e4099294503fbc3c761dea705afafd239bc8fa9bf23dce08`

**Question:** Gerald Grosvenor, 6th Duke of Westminster was succeeded by the British aristocrat who is estimated to be worth how much?

**Context supplied to the generator (5 documents, in order):**

### [1] Gerald Grosvenor, 6th Duke of Westminster

`doc_id: 9736928ea325808e8016c56da3727a16bdb09ad27ad3672e587b48991344b199`

Major General Gerald Cavendish Grosvenor, 6th Duke of Westminster, (22 December 1951 – 9 August 2016) was a British landowner, businessman, philanthropist, Territorial Army general and hereditary peer.
 He was the son of Robert George Grosvenor, 5th Duke of Westminster and Viola Grosvenor.
 He was Chairman of the property company Grosvenor Group.
 He is succeeded by his son, Hugh Grosvenor, 7th Duke of Westminster.

### [2] Hugh Grosvenor, 7th Duke of Westminster

`doc_id: d79a417280842b668ec89630d8d84529bd5fd91e71bcf4a80b4a89d70cd8d5d8`

Hugh Richard Louis Grosvenor, 7th Duke of Westminster (born 29 January 1991), styled as Earl Grosvenor until August 2016, is a British aristocrat, billionaire, businessman and landowner.
 He is the third child and only son of Gerald Grosvenor, 6th Duke of Westminster and his wife Natalia Phillips Grosvenor, Duchess of Westminster.
 He inherited the title of Duke of Westminster on 9 August 2016, on the death of his father.
 The duke is estimated to be worth US$13 billion, making him the world's richest person aged under 30.

### [3] Gerald Grosvenor, 4th Duke of Westminster

`doc_id: 7965e607af0a9a628e93769b57abf8bdbd00c3fc047e6bfcc87698ab24d2ea61`

Colonel Gerald Hugh Grosvenor, 4th Duke of Westminster {'1': ", '2': ", '3': ", '4': "} (13 February 1907 – 25 February 1967) was the son of Captain Lord Hugh William Grosvenor and Lady Mabel Crichton and a grandson of Hugh Grosvenor, 1st Duke of Westminster.

### [4] Sally Grosvenor, Duchess of Westminster

`doc_id: 59d785c27fc7c8f8f60b21d519ae27236a035b6555cb042dfea7005c7b820976`

Sally Grosvenor, Duchess of Westminster, née Perry (1909 – 30 May 1990), was the wife of Gerald Grosvenor, 4th Duke of Westminster.

### [5] Natalia Grosvenor, Duchess of Westminster

`doc_id: f4ec6705fc07323ddaaa78620b1c459473cfcee5b4177601a9f508280c17f5df`

Natalia Ayesha Grosvenor, Duchess of Westminster ("née" Phillips; born 8 May 1959) is the widow of Gerald Grosvenor, 6th Duke of Westminster.
 The Duchess will assume the style of Dowager Duchess only upon the marriage of her son.
 At the time of her husband's succession to the title, there were four Duchesses of Westminster, the current Duchess, Sally Grosvenor, Duchess of Westminster, Anne Grosvenor, Duchess of Westminster and Viola Grosvenor, Duchess of Westminster.

### Generator output

**Answer:** US$13 billion

**Explanation given by the generator:** The documents specify that Hugh Grosvenor, 7th Duke of Westminster, is estimated to be worth US$13 billion.

**Documents the generator cited (its own citations, not a verified list):**

* `9736928ea325808e8016c56da3727a16bdb09ad27ad3672e587b48991344b199` - [1] Gerald Grosvenor, 6th Duke of Westminster
* `d79a417280842b668ec89630d8d84529bd5fd91e71bcf4a80b4a89d70cd8d5d8` - [2] Hugh Grosvenor, 7th Duke of Westminster

---

## AG-0020

* `case_sha256`: `7ef2aa53c04c6297c47e8aa00dacefd56f43de950142aebe4764dcbdbec89edc`

**Question:** Gerald Grosvenor, 6th Duke of Westminster was succeeded by the British aristocrat who is estimated to be worth how much?

**Context supplied to the generator (5 documents, in order):**

### [1] Hugh Grosvenor, 7th Duke of Westminster

`doc_id: d79a417280842b668ec89630d8d84529bd5fd91e71bcf4a80b4a89d70cd8d5d8`

Hugh Richard Louis Grosvenor, 7th Duke of Westminster (born 29 January 1991), styled as Earl Grosvenor until August 2016, is a British aristocrat, billionaire, businessman and landowner.
 He is the third child and only son of Gerald Grosvenor, 6th Duke of Westminster and his wife Natalia Phillips Grosvenor, Duchess of Westminster.
 He inherited the title of Duke of Westminster on 9 August 2016, on the death of his father.
 The duke is estimated to be worth US$13 billion, making him the world's richest person aged under 30.

### [2] Gerald Grosvenor, 6th Duke of Westminster

`doc_id: 9736928ea325808e8016c56da3727a16bdb09ad27ad3672e587b48991344b199`

Major General Gerald Cavendish Grosvenor, 6th Duke of Westminster, (22 December 1951 – 9 August 2016) was a British landowner, businessman, philanthropist, Territorial Army general and hereditary peer.
 He was the son of Robert George Grosvenor, 5th Duke of Westminster and Viola Grosvenor.
 He was Chairman of the property company Grosvenor Group.
 He is succeeded by his son, Hugh Grosvenor, 7th Duke of Westminster.

### [3] Gerald Grosvenor, 4th Duke of Westminster

`doc_id: 7965e607af0a9a628e93769b57abf8bdbd00c3fc047e6bfcc87698ab24d2ea61`

Colonel Gerald Hugh Grosvenor, 4th Duke of Westminster {'1': ", '2': ", '3': ", '4': "} (13 February 1907 – 25 February 1967) was the son of Captain Lord Hugh William Grosvenor and Lady Mabel Crichton and a grandson of Hugh Grosvenor, 1st Duke of Westminster.

### [4] Francis Grosvenor, 8th Earl of Wilton

`doc_id: 16c5791e93e47a993132f82dd57bad9e264f88be5420a2f4b3474e17339c2ec4`

Francis Egerton Grosvenor, 8th Earl of Wilton (born 8 February 1934) is a British aristocrat, financier and academic.
 He is the eldest son of Robert Egerton Grosvenor, 5th Baron Ebury and his first wife Anne Acland-Troyte.
 He succeeded his father as 6th Baron Ebury in 1957, and his fourth cousin, Seymour William Arthur John Egerton, 7th Earl of Wilton, to the earldom in 1999.

### [5] Natalia Grosvenor, Duchess of Westminster

`doc_id: f4ec6705fc07323ddaaa78620b1c459473cfcee5b4177601a9f508280c17f5df`

Natalia Ayesha Grosvenor, Duchess of Westminster ("née" Phillips; born 8 May 1959) is the widow of Gerald Grosvenor, 6th Duke of Westminster.
 The Duchess will assume the style of Dowager Duchess only upon the marriage of her son.
 At the time of her husband's succession to the title, there were four Duchesses of Westminster, the current Duchess, Sally Grosvenor, Duchess of Westminster, Anne Grosvenor, Duchess of Westminster and Viola Grosvenor, Duchess of Westminster.

### Generator output

**Answer:** US$13 billion

**Explanation given by the generator:** The documents state that Hugh Grosvenor, 7th Duke of Westminster, is estimated to be worth US$13 billion.

**Documents the generator cited (its own citations, not a verified list):**

* `d79a417280842b668ec89630d8d84529bd5fd91e71bcf4a80b4a89d70cd8d5d8` - [1] Hugh Grosvenor, 7th Duke of Westminster
* `9736928ea325808e8016c56da3727a16bdb09ad27ad3672e587b48991344b199` - [2] Gerald Grosvenor, 6th Duke of Westminster

---

## AG-0021

* `case_sha256`: `e2a656c8462c47575182aa033ab9fc8656be31737a18bad5e8639bf118ff3fc8`

**Question:** Gerald Grosvenor, 6th Duke of Westminster was succeeded by the British aristocrat who is estimated to be worth how much?

**Context supplied to the generator (5 documents, in order):**

### [1] Gerald Grosvenor, 6th Duke of Westminster

`doc_id: 9736928ea325808e8016c56da3727a16bdb09ad27ad3672e587b48991344b199`

Major General Gerald Cavendish Grosvenor, 6th Duke of Westminster, (22 December 1951 – 9 August 2016) was a British landowner, businessman, philanthropist, Territorial Army general and hereditary peer.
 He was the son of Robert George Grosvenor, 5th Duke of Westminster and Viola Grosvenor.
 He was Chairman of the property company Grosvenor Group.
 He is succeeded by his son, Hugh Grosvenor, 7th Duke of Westminster.

### [2] Hugh Grosvenor, 7th Duke of Westminster

`doc_id: d79a417280842b668ec89630d8d84529bd5fd91e71bcf4a80b4a89d70cd8d5d8`

Hugh Richard Louis Grosvenor, 7th Duke of Westminster (born 29 January 1991), styled as Earl Grosvenor until August 2016, is a British aristocrat, billionaire, businessman and landowner.
 He is the third child and only son of Gerald Grosvenor, 6th Duke of Westminster and his wife Natalia Phillips Grosvenor, Duchess of Westminster.
 He inherited the title of Duke of Westminster on 9 August 2016, on the death of his father.
 The duke is estimated to be worth US$13 billion, making him the world's richest person aged under 30.

### [3] Gerald Grosvenor, 4th Duke of Westminster

`doc_id: 7965e607af0a9a628e93769b57abf8bdbd00c3fc047e6bfcc87698ab24d2ea61`

Colonel Gerald Hugh Grosvenor, 4th Duke of Westminster {'1': ", '2': ", '3': ", '4': "} (13 February 1907 – 25 February 1967) was the son of Captain Lord Hugh William Grosvenor and Lady Mabel Crichton and a grandson of Hugh Grosvenor, 1st Duke of Westminster.

### [4] Natalia Grosvenor, Duchess of Westminster

`doc_id: f4ec6705fc07323ddaaa78620b1c459473cfcee5b4177601a9f508280c17f5df`

Natalia Ayesha Grosvenor, Duchess of Westminster ("née" Phillips; born 8 May 1959) is the widow of Gerald Grosvenor, 6th Duke of Westminster.
 The Duchess will assume the style of Dowager Duchess only upon the marriage of her son.
 At the time of her husband's succession to the title, there were four Duchesses of Westminster, the current Duchess, Sally Grosvenor, Duchess of Westminster, Anne Grosvenor, Duchess of Westminster and Viola Grosvenor, Duchess of Westminster.

### [5] Sally Grosvenor, Duchess of Westminster

`doc_id: 59d785c27fc7c8f8f60b21d519ae27236a035b6555cb042dfea7005c7b820976`

Sally Grosvenor, Duchess of Westminster, née Perry (1909 – 30 May 1990), was the wife of Gerald Grosvenor, 4th Duke of Westminster.

### Generator output

**Answer:** US$13 billion

**Explanation given by the generator:** The documents specify that Hugh Grosvenor, 7th Duke of Westminster, is estimated to be worth US$13 billion.

**Documents the generator cited (its own citations, not a verified list):**

* `9736928ea325808e8016c56da3727a16bdb09ad27ad3672e587b48991344b199` - [1] Gerald Grosvenor, 6th Duke of Westminster
* `d79a417280842b668ec89630d8d84529bd5fd91e71bcf4a80b4a89d70cd8d5d8` - [2] Hugh Grosvenor, 7th Duke of Westminster

---

## AG-0022

* `case_sha256`: `ed47e3417a9a9abe767afedfc76d79e858621d56cb8ba9e0b4e476fb3be96af6`

**Question:** Gerald Grosvenor, 6th Duke of Westminster was succeeded by the British aristocrat who is estimated to be worth how much?

**Context supplied to the generator (5 documents, in order):**

### [1] Gerald Grosvenor, 6th Duke of Westminster

`doc_id: 9736928ea325808e8016c56da3727a16bdb09ad27ad3672e587b48991344b199`

Major General Gerald Cavendish Grosvenor, 6th Duke of Westminster, (22 December 1951 – 9 August 2016) was a British landowner, businessman, philanthropist, Territorial Army general and hereditary peer.
 He was the son of Robert George Grosvenor, 5th Duke of Westminster and Viola Grosvenor.
 He was Chairman of the property company Grosvenor Group.
 He is succeeded by his son, Hugh Grosvenor, 7th Duke of Westminster.

### [2] Hugh Grosvenor, 7th Duke of Westminster

`doc_id: d79a417280842b668ec89630d8d84529bd5fd91e71bcf4a80b4a89d70cd8d5d8`

Hugh Richard Louis Grosvenor, 7th Duke of Westminster (born 29 January 1991), styled as Earl Grosvenor until August 2016, is a British aristocrat, billionaire, businessman and landowner.
 He is the third child and only son of Gerald Grosvenor, 6th Duke of Westminster and his wife Natalia Phillips Grosvenor, Duchess of Westminster.
 He inherited the title of Duke of Westminster on 9 August 2016, on the death of his father.
 The duke is estimated to be worth US$13 billion, making him the world's richest person aged under 30.

### [3] Gerald Grosvenor, 4th Duke of Westminster

`doc_id: 7965e607af0a9a628e93769b57abf8bdbd00c3fc047e6bfcc87698ab24d2ea61`

Colonel Gerald Hugh Grosvenor, 4th Duke of Westminster {'1': ", '2': ", '3': ", '4': "} (13 February 1907 – 25 February 1967) was the son of Captain Lord Hugh William Grosvenor and Lady Mabel Crichton and a grandson of Hugh Grosvenor, 1st Duke of Westminster.

### [4] Sally Grosvenor, Duchess of Westminster

`doc_id: 59d785c27fc7c8f8f60b21d519ae27236a035b6555cb042dfea7005c7b820976`

Sally Grosvenor, Duchess of Westminster, née Perry (1909 – 30 May 1990), was the wife of Gerald Grosvenor, 4th Duke of Westminster.

### [5] Natalia Grosvenor, Duchess of Westminster

`doc_id: f4ec6705fc07323ddaaa78620b1c459473cfcee5b4177601a9f508280c17f5df`

Natalia Ayesha Grosvenor, Duchess of Westminster ("née" Phillips; born 8 May 1959) is the widow of Gerald Grosvenor, 6th Duke of Westminster.
 The Duchess will assume the style of Dowager Duchess only upon the marriage of her son.
 At the time of her husband's succession to the title, there were four Duchesses of Westminster, the current Duchess, Sally Grosvenor, Duchess of Westminster, Anne Grosvenor, Duchess of Westminster and Viola Grosvenor, Duchess of Westminster.

### Generator output

**Answer:** US$13 billion

**Explanation given by the generator:** The documents state that Hugh Grosvenor, 7th Duke of Westminster, is estimated to be worth US$13 billion.

**Documents the generator cited (its own citations, not a verified list):**

* `9736928ea325808e8016c56da3727a16bdb09ad27ad3672e587b48991344b199` - [1] Gerald Grosvenor, 6th Duke of Westminster
* `d79a417280842b668ec89630d8d84529bd5fd91e71bcf4a80b4a89d70cd8d5d8` - [2] Hugh Grosvenor, 7th Duke of Westminster

---

## AG-0023

* `case_sha256`: `0b1009d96293814664e2acaf02a74235b13018eb23b19cab9917e47002b9dfc0`

**Question:** How many different schools does the university, in which Andrew J. Elliot is a professor of psychology, have?

**Context supplied to the generator (5 documents, in order):**

### [1] Andrew J. Elliot

`doc_id: f3df15bf00898a0b19d479781dac4a339e253abff5430d015597640256b9c651`

Andrew J. Elliot (born 1962) is a professor of psychology at the University of Rochester.
 His research on the hierarchical model of approach and avoidance motivation focuses on combining classic and contemporary methods to test various theories.
 Elliot's work in social psychology is cited frequently by those in the field, causing him to be named one of Thomson Reuters' ISI Highly Cited for the Social Sciences in 2010.

### [2] University of Rochester

`doc_id: 99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf`

The University of Rochester ( U of R or UR) frequently referred to simply as Rochester, is a private, nonsectarian, research university in Rochester, New York.
 The university grants undergraduate and graduate degrees, including doctoral and professional degrees.
 The university has six schools and various interdisciplinary programs.

### [3] Andrew J. Offutt

`doc_id: 99604228a4708b0cb0e09569b1b92c482a72740d04dd91b7b6a3e1e1f6fe1ea6`

Andrew Jefferson Offutt (August 16, 1934 – April 30, 2013) was an American science fiction and fantasy author.
 He wrote as Andrew J. Offutt, A. J. Offutt, and Andy Offutt.
 His normal byline, andrew j. offutt, has all his name in lower-case letters.
 He also wrote erotica under seventeen different pseudonyms, principally John Cleve, John Denis, Jeff Morehead, and Turk Winter.
 He is the father of novelist Chris Offutt and professor Jeff Offutt.

### [4] Florida International University

`doc_id: bb755ce211b54acee77d26462f231c64ac235287912134467cfc71c509655317`

Florida International University (FIU) is an American metropolitan public research university in Greater Miami, Florida, United States.
 FIU has two major campuses in Miami-Dade County, with its main campus in University Park.
 Florida International University is classified as a research university with highest research activity by the Carnegie Foundation and a research university by the Florida Legislature.

### [5] Simon Wiesenthal

`doc_id: b85fc181ca723d3120b61d5e98f1de7098e944996d67242e9f183b87b7640d92`

Simon Wiesenthal (31 December 1908 – 20 September 2005) was a Jewish Austrian Holocaust survivor, Nazi hunter, and writer.

### Generator output

**Answer:** six

**Explanation given by the generator:** The University of Rochester has six schools, as stated in the retrieved documents.

**Documents the generator cited (its own citations, not a verified list):**

* `f3df15bf00898a0b19d479781dac4a339e253abff5430d015597640256b9c651` - [1] Andrew J. Elliot
* `99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf` - [2] University of Rochester

---

## AG-0024

* `case_sha256`: `0eb0053158d54ccb752fbff89d1ebc454345b3262537f32fc7ee46e04e8ecf31`

**Question:** How many different schools does the university, in which Andrew J. Elliot is a professor of psychology, have?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Rochester

`doc_id: 99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf`

The University of Rochester ( U of R or UR) frequently referred to simply as Rochester, is a private, nonsectarian, research university in Rochester, New York.
 The university grants undergraduate and graduate degrees, including doctoral and professional degrees.
 The university has six schools and various interdisciplinary programs.

### [2] Sampaloc, Manila

`doc_id: 3dd72fa8bb1b18ed68a684e8dfdf850cc1125eed3236b5eaffa64d9b52216792`

Sampaloc is one of the city districts that comprise Manila, Philippines.
 It is known as Metropolitan Manila's "University Belt", after the clusters of prominent higher educational institutions located there.
 Among the universities in Sampaloc are the University of Santo Tomas (1611, moved to Sampaloc in 1927), a by-product of the 333-year Hispanic colonization of the Philippines; National University (Philippines) (1900), as the first private nonsectarian and coeducational institution in the Philippines and also, the first university to use English as its medium of instruction, replacing Spanish language; Far Eastern University (1928), known for its Art Deco campus awarded as a cultural heritage site of the Philippines; and University of the East (1946), once dubbed as the largest university in Asia in terms of enrollment.
 The district is bordered by Quiapo and San Miguel districts in the south, Santa Mesa district in the south and east, Santa Cruz district in the west and north, and Quezon City in the northeast.

### [3] La Salle University (Ozamiz)

`doc_id: 9ac29e3caf04c0673e0250bd9124fa1253acb3c17aba6f59c1d84a3211360e37`

La Salle University (LSU), formerly known as Immaculate Conception College-La Salle, is a member school of De La Salle Philippines located in Ozamiz City, Misamis Occidental, Philippines.
 It was formally opened in 1929 by the Society of Jesus in the Philippines.
 It was formally turned over to the De La Salle Brothers in the Philippines in 1994 and was granted university status in 2006 and was renamed La Salle University.

### [4] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [5] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### Generator output

**Answer:** six

**Explanation given by the generator:** The University of Rochester has six schools as stated in the document.

**Documents the generator cited (its own citations, not a verified list):**

* `99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf` - [1] University of Rochester

---

## AG-0025

* `case_sha256`: `291650b719757755a7b5811d95111e0bde954546d123e3ce6a95ced69f8f977f`

**Question:** How many different schools does the university, in which Andrew J. Elliot is a professor of psychology, have?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Rochester

`doc_id: 99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf`

The University of Rochester ( U of R or UR) frequently referred to simply as Rochester, is a private, nonsectarian, research university in Rochester, New York.
 The university grants undergraduate and graduate degrees, including doctoral and professional degrees.
 The university has six schools and various interdisciplinary programs.

### [2] Sampaloc, Manila

`doc_id: 3dd72fa8bb1b18ed68a684e8dfdf850cc1125eed3236b5eaffa64d9b52216792`

Sampaloc is one of the city districts that comprise Manila, Philippines.
 It is known as Metropolitan Manila's "University Belt", after the clusters of prominent higher educational institutions located there.
 Among the universities in Sampaloc are the University of Santo Tomas (1611, moved to Sampaloc in 1927), a by-product of the 333-year Hispanic colonization of the Philippines; National University (Philippines) (1900), as the first private nonsectarian and coeducational institution in the Philippines and also, the first university to use English as its medium of instruction, replacing Spanish language; Far Eastern University (1928), known for its Art Deco campus awarded as a cultural heritage site of the Philippines; and University of the East (1946), once dubbed as the largest university in Asia in terms of enrollment.
 The district is bordered by Quiapo and San Miguel districts in the south, Santa Mesa district in the south and east, Santa Cruz district in the west and north, and Quezon City in the northeast.

### [3] La Salle University (Ozamiz)

`doc_id: 9ac29e3caf04c0673e0250bd9124fa1253acb3c17aba6f59c1d84a3211360e37`

La Salle University (LSU), formerly known as Immaculate Conception College-La Salle, is a member school of De La Salle Philippines located in Ozamiz City, Misamis Occidental, Philippines.
 It was formally opened in 1929 by the Society of Jesus in the Philippines.
 It was formally turned over to the De La Salle Brothers in the Philippines in 1994 and was granted university status in 2006 and was renamed La Salle University.

### [4] Florida International University

`doc_id: bb755ce211b54acee77d26462f231c64ac235287912134467cfc71c509655317`

Florida International University (FIU) is an American metropolitan public research university in Greater Miami, Florida, United States.
 FIU has two major campuses in Miami-Dade County, with its main campus in University Park.
 Florida International University is classified as a research university with highest research activity by the Carnegie Foundation and a research university by the Florida Legislature.

### [5] University of the Philippines Cebu

`doc_id: 80734d512d4aae397931b1befb71e6716d633009af22212ecfb35ec4f825c404`

The University of the Philippines Cebu (Cebuano: "Unibersidad sa Pilipinas sa Sugbo" ; Filipino: "Unibersidad ng Pilipinas sa Cebu" ; also referred to as UPC or UP Cebu) is a public research university and the youngest constituent university of the University of the Philippines System located in Cebu City, the capital city of Cebu province in the Philippines.
 It was founded on May 3, 1918, ten years after the founding of UP in 1908.
 It is considered as the University's flagship campus in Central Visayas.

### Generator output

**Answer:** six

**Explanation given by the generator:** The University of Rochester has six schools as stated in the document.

**Documents the generator cited (its own citations, not a verified list):**

* `99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf` - [1] University of Rochester

---

## AG-0026

* `case_sha256`: `425c88f51bcba91978f5635f1ba46b995328e0b0762cf4c34320139c34388cd7`

**Question:** How many different schools does the university, in which Andrew J. Elliot is a professor of psychology, have?

**Context supplied to the generator (5 documents, in order):**

### [1] Andrew J. Elliot

`doc_id: f3df15bf00898a0b19d479781dac4a339e253abff5430d015597640256b9c651`

Andrew J. Elliot (born 1962) is a professor of psychology at the University of Rochester.
 His research on the hierarchical model of approach and avoidance motivation focuses on combining classic and contemporary methods to test various theories.
 Elliot's work in social psychology is cited frequently by those in the field, causing him to be named one of Thomson Reuters' ISI Highly Cited for the Social Sciences in 2010.

### [2] Archives of Scientific Psychology

`doc_id: 4157c3bd4a0099c60c12ffde7a30b881f2543b36dc5b7a246dd177607b33e0cc`

Archives of Scientific Psychology is an open access academic journal published by the American Psychological Association.
 The journal publishes a wide variety of articles pertaining to the many different sub-fields of psychology, such as neuroscience and political psychology.
 The journal includes articles that cover the many different research methodologies employed by psychologists.
 The current editors-in-chief are Cecil R. Reynolds (Texas A&M University) and Gary R. VandenBos (American Psychological Association).

### [3] University of Rochester

`doc_id: 99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf`

The University of Rochester ( U of R or UR) frequently referred to simply as Rochester, is a private, nonsectarian, research university in Rochester, New York.
 The university grants undergraduate and graduate degrees, including doctoral and professional degrees.
 The university has six schools and various interdisciplinary programs.

### [4] Florida International University

`doc_id: bb755ce211b54acee77d26462f231c64ac235287912134467cfc71c509655317`

Florida International University (FIU) is an American metropolitan public research university in Greater Miami, Florida, United States.
 FIU has two major campuses in Miami-Dade County, with its main campus in University Park.
 Florida International University is classified as a research university with highest research activity by the Carnegie Foundation and a research university by the Florida Legislature.

### [5] Andrew J. Offutt

`doc_id: 99604228a4708b0cb0e09569b1b92c482a72740d04dd91b7b6a3e1e1f6fe1ea6`

Andrew Jefferson Offutt (August 16, 1934 – April 30, 2013) was an American science fiction and fantasy author.
 He wrote as Andrew J. Offutt, A. J. Offutt, and Andy Offutt.
 His normal byline, andrew j. offutt, has all his name in lower-case letters.
 He also wrote erotica under seventeen different pseudonyms, principally John Cleve, John Denis, Jeff Morehead, and Turk Winter.
 He is the father of novelist Chris Offutt and professor Jeff Offutt.

### Generator output

**Answer:** six

**Explanation given by the generator:** The University of Rochester has six schools, as stated in the documents.

**Documents the generator cited (its own citations, not a verified list):**

* `f3df15bf00898a0b19d479781dac4a339e253abff5430d015597640256b9c651` - [1] Andrew J. Elliot
* `99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf` - [3] University of Rochester

---

## AG-0027

* `case_sha256`: `70ef2d09d224586f6974db29982da0d12df98332f9935d90e1a75e4aa3171496`

**Question:** How many different schools does the university, in which Andrew J. Elliot is a professor of psychology, have?

**Context supplied to the generator (5 documents, in order):**

### [1] Andrew J. Elliot

`doc_id: f3df15bf00898a0b19d479781dac4a339e253abff5430d015597640256b9c651`

Andrew J. Elliot (born 1962) is a professor of psychology at the University of Rochester.
 His research on the hierarchical model of approach and avoidance motivation focuses on combining classic and contemporary methods to test various theories.
 Elliot's work in social psychology is cited frequently by those in the field, causing him to be named one of Thomson Reuters' ISI Highly Cited for the Social Sciences in 2010.

### [2] Archives of Scientific Psychology

`doc_id: 4157c3bd4a0099c60c12ffde7a30b881f2543b36dc5b7a246dd177607b33e0cc`

Archives of Scientific Psychology is an open access academic journal published by the American Psychological Association.
 The journal publishes a wide variety of articles pertaining to the many different sub-fields of psychology, such as neuroscience and political psychology.
 The journal includes articles that cover the many different research methodologies employed by psychologists.
 The current editors-in-chief are Cecil R. Reynolds (Texas A&M University) and Gary R. VandenBos (American Psychological Association).

### [3] University of Rochester

`doc_id: 99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf`

The University of Rochester ( U of R or UR) frequently referred to simply as Rochester, is a private, nonsectarian, research university in Rochester, New York.
 The university grants undergraduate and graduate degrees, including doctoral and professional degrees.
 The university has six schools and various interdisciplinary programs.

### [4] Florida International University

`doc_id: bb755ce211b54acee77d26462f231c64ac235287912134467cfc71c509655317`

Florida International University (FIU) is an American metropolitan public research university in Greater Miami, Florida, United States.
 FIU has two major campuses in Miami-Dade County, with its main campus in University Park.
 Florida International University is classified as a research university with highest research activity by the Carnegie Foundation and a research university by the Florida Legislature.

### [5] Andrew J. Offutt

`doc_id: 99604228a4708b0cb0e09569b1b92c482a72740d04dd91b7b6a3e1e1f6fe1ea6`

Andrew Jefferson Offutt (August 16, 1934 – April 30, 2013) was an American science fiction and fantasy author.
 He wrote as Andrew J. Offutt, A. J. Offutt, and Andy Offutt.
 His normal byline, andrew j. offutt, has all his name in lower-case letters.
 He also wrote erotica under seventeen different pseudonyms, principally John Cleve, John Denis, Jeff Morehead, and Turk Winter.
 He is the father of novelist Chris Offutt and professor Jeff Offutt.

### Generator output

**Answer:** six

**Explanation given by the generator:** The University of Rochester, where Andrew J. Elliot is a professor, has six schools.

**Documents the generator cited (its own citations, not a verified list):**

* `f3df15bf00898a0b19d479781dac4a339e253abff5430d015597640256b9c651` - [1] Andrew J. Elliot
* `99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf` - [3] University of Rochester

---

## AG-0028

* `case_sha256`: `7646b3c9b55abc6e3afbed1494083b9bdb1080f99ec37c4ceb9d069cfddb4966`

**Question:** How many different schools does the university, in which Andrew J. Elliot is a professor of psychology, have?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Rochester

`doc_id: 99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf`

The University of Rochester ( U of R or UR) frequently referred to simply as Rochester, is a private, nonsectarian, research university in Rochester, New York.
 The university grants undergraduate and graduate degrees, including doctoral and professional degrees.
 The university has six schools and various interdisciplinary programs.

### [2] Sampaloc, Manila

`doc_id: 3dd72fa8bb1b18ed68a684e8dfdf850cc1125eed3236b5eaffa64d9b52216792`

Sampaloc is one of the city districts that comprise Manila, Philippines.
 It is known as Metropolitan Manila's "University Belt", after the clusters of prominent higher educational institutions located there.
 Among the universities in Sampaloc are the University of Santo Tomas (1611, moved to Sampaloc in 1927), a by-product of the 333-year Hispanic colonization of the Philippines; National University (Philippines) (1900), as the first private nonsectarian and coeducational institution in the Philippines and also, the first university to use English as its medium of instruction, replacing Spanish language; Far Eastern University (1928), known for its Art Deco campus awarded as a cultural heritage site of the Philippines; and University of the East (1946), once dubbed as the largest university in Asia in terms of enrollment.
 The district is bordered by Quiapo and San Miguel districts in the south, Santa Mesa district in the south and east, Santa Cruz district in the west and north, and Quezon City in the northeast.

### [3] La Salle University (Ozamiz)

`doc_id: 9ac29e3caf04c0673e0250bd9124fa1253acb3c17aba6f59c1d84a3211360e37`

La Salle University (LSU), formerly known as Immaculate Conception College-La Salle, is a member school of De La Salle Philippines located in Ozamiz City, Misamis Occidental, Philippines.
 It was formally opened in 1929 by the Society of Jesus in the Philippines.
 It was formally turned over to the De La Salle Brothers in the Philippines in 1994 and was granted university status in 2006 and was renamed La Salle University.

### [4] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [5] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### Generator output

**Answer:** six

**Explanation given by the generator:** The University of Rochester has six schools, as stated in the provided document.

**Documents the generator cited (its own citations, not a verified list):**

* `99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf` - [1] University of Rochester

---

## AG-0029

* `case_sha256`: `ca7b789026d15aaf8a9e9ab2c6d7d6e9e89be04094d2f0ac75b62fd052254644`

**Question:** How many different schools does the university, in which Andrew J. Elliot is a professor of psychology, have?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Rochester

`doc_id: 99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf`

The University of Rochester ( U of R or UR) frequently referred to simply as Rochester, is a private, nonsectarian, research university in Rochester, New York.
 The university grants undergraduate and graduate degrees, including doctoral and professional degrees.
 The university has six schools and various interdisciplinary programs.

### [2] Sampaloc, Manila

`doc_id: 3dd72fa8bb1b18ed68a684e8dfdf850cc1125eed3236b5eaffa64d9b52216792`

Sampaloc is one of the city districts that comprise Manila, Philippines.
 It is known as Metropolitan Manila's "University Belt", after the clusters of prominent higher educational institutions located there.
 Among the universities in Sampaloc are the University of Santo Tomas (1611, moved to Sampaloc in 1927), a by-product of the 333-year Hispanic colonization of the Philippines; National University (Philippines) (1900), as the first private nonsectarian and coeducational institution in the Philippines and also, the first university to use English as its medium of instruction, replacing Spanish language; Far Eastern University (1928), known for its Art Deco campus awarded as a cultural heritage site of the Philippines; and University of the East (1946), once dubbed as the largest university in Asia in terms of enrollment.
 The district is bordered by Quiapo and San Miguel districts in the south, Santa Mesa district in the south and east, Santa Cruz district in the west and north, and Quezon City in the northeast.

### [3] La Salle University (Ozamiz)

`doc_id: 9ac29e3caf04c0673e0250bd9124fa1253acb3c17aba6f59c1d84a3211360e37`

La Salle University (LSU), formerly known as Immaculate Conception College-La Salle, is a member school of De La Salle Philippines located in Ozamiz City, Misamis Occidental, Philippines.
 It was formally opened in 1929 by the Society of Jesus in the Philippines.
 It was formally turned over to the De La Salle Brothers in the Philippines in 1994 and was granted university status in 2006 and was renamed La Salle University.

### [4] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [5] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### Generator output

**Answer:** six

**Explanation given by the generator:** The document specifically states that the University of Rochester has six schools.

**Documents the generator cited (its own citations, not a verified list):**

* `99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf` - [1] University of Rochester

---

## AG-0030

* `case_sha256`: `cef5a886451d6a020cb33b6e23a523e4eb810f9dbb7ee431ab0a8f740924679a`

**Question:** How many different schools does the university, in which Andrew J. Elliot is a professor of psychology, have?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Rochester

`doc_id: 99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf`

The University of Rochester ( U of R or UR) frequently referred to simply as Rochester, is a private, nonsectarian, research university in Rochester, New York.
 The university grants undergraduate and graduate degrees, including doctoral and professional degrees.
 The university has six schools and various interdisciplinary programs.

### [2] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [3] La Salle University (Ozamiz)

`doc_id: 9ac29e3caf04c0673e0250bd9124fa1253acb3c17aba6f59c1d84a3211360e37`

La Salle University (LSU), formerly known as Immaculate Conception College-La Salle, is a member school of De La Salle Philippines located in Ozamiz City, Misamis Occidental, Philippines.
 It was formally opened in 1929 by the Society of Jesus in the Philippines.
 It was formally turned over to the De La Salle Brothers in the Philippines in 1994 and was granted university status in 2006 and was renamed La Salle University.

### [4] Sampaloc, Manila

`doc_id: 3dd72fa8bb1b18ed68a684e8dfdf850cc1125eed3236b5eaffa64d9b52216792`

Sampaloc is one of the city districts that comprise Manila, Philippines.
 It is known as Metropolitan Manila's "University Belt", after the clusters of prominent higher educational institutions located there.
 Among the universities in Sampaloc are the University of Santo Tomas (1611, moved to Sampaloc in 1927), a by-product of the 333-year Hispanic colonization of the Philippines; National University (Philippines) (1900), as the first private nonsectarian and coeducational institution in the Philippines and also, the first university to use English as its medium of instruction, replacing Spanish language; Far Eastern University (1928), known for its Art Deco campus awarded as a cultural heritage site of the Philippines; and University of the East (1946), once dubbed as the largest university in Asia in terms of enrollment.
 The district is bordered by Quiapo and San Miguel districts in the south, Santa Mesa district in the south and east, Santa Cruz district in the west and north, and Quezon City in the northeast.

### [5] University Avenue station

`doc_id: ff2ad4215d85b7bdab2f2f6651737639bef40cb34651876cc572f71793fae27d`

The University Avenue MRT Station is a proposed station on the Manila MRT-7 in Metro Manila, Philippines.
 The station will be located along Commonwealth Avenue in U.P. Village, Diliman, Quezon City.
 The station is proximate to the University Avenue, the main thoroughfare to the University of the Philippines Diliman campus.
 The system has a proposed spur line to connect itself to the Manila LRT Line 2 in Katipunan, passing through the University of the Philippines Diliman and Katipunan Avenue.

### Generator output

**Answer:** six

**Explanation given by the generator:** The document specifically states that the University of Rochester has six schools.

**Documents the generator cited (its own citations, not a verified list):**

* `99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf` - [1] University of Rochester

---

## AG-0031

* `case_sha256`: `db7045e1aa2221a852f69bf01f2430aa99c6e7e307eb9211663a9e3a86810f37`

**Question:** How many different schools does the university, in which Andrew J. Elliot is a professor of psychology, have?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Rochester

`doc_id: 99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf`

The University of Rochester ( U of R or UR) frequently referred to simply as Rochester, is a private, nonsectarian, research university in Rochester, New York.
 The university grants undergraduate and graduate degrees, including doctoral and professional degrees.
 The university has six schools and various interdisciplinary programs.

### [2] Sampaloc, Manila

`doc_id: 3dd72fa8bb1b18ed68a684e8dfdf850cc1125eed3236b5eaffa64d9b52216792`

Sampaloc is one of the city districts that comprise Manila, Philippines.
 It is known as Metropolitan Manila's "University Belt", after the clusters of prominent higher educational institutions located there.
 Among the universities in Sampaloc are the University of Santo Tomas (1611, moved to Sampaloc in 1927), a by-product of the 333-year Hispanic colonization of the Philippines; National University (Philippines) (1900), as the first private nonsectarian and coeducational institution in the Philippines and also, the first university to use English as its medium of instruction, replacing Spanish language; Far Eastern University (1928), known for its Art Deco campus awarded as a cultural heritage site of the Philippines; and University of the East (1946), once dubbed as the largest university in Asia in terms of enrollment.
 The district is bordered by Quiapo and San Miguel districts in the south, Santa Mesa district in the south and east, Santa Cruz district in the west and north, and Quezon City in the northeast.

### [3] La Salle University (Ozamiz)

`doc_id: 9ac29e3caf04c0673e0250bd9124fa1253acb3c17aba6f59c1d84a3211360e37`

La Salle University (LSU), formerly known as Immaculate Conception College-La Salle, is a member school of De La Salle Philippines located in Ozamiz City, Misamis Occidental, Philippines.
 It was formally opened in 1929 by the Society of Jesus in the Philippines.
 It was formally turned over to the De La Salle Brothers in the Philippines in 1994 and was granted university status in 2006 and was renamed La Salle University.

### [4] Florida International University

`doc_id: bb755ce211b54acee77d26462f231c64ac235287912134467cfc71c509655317`

Florida International University (FIU) is an American metropolitan public research university in Greater Miami, Florida, United States.
 FIU has two major campuses in Miami-Dade County, with its main campus in University Park.
 Florida International University is classified as a research university with highest research activity by the Carnegie Foundation and a research university by the Florida Legislature.

### [5] University of the Philippines Cebu

`doc_id: 80734d512d4aae397931b1befb71e6716d633009af22212ecfb35ec4f825c404`

The University of the Philippines Cebu (Cebuano: "Unibersidad sa Pilipinas sa Sugbo" ; Filipino: "Unibersidad ng Pilipinas sa Cebu" ; also referred to as UPC or UP Cebu) is a public research university and the youngest constituent university of the University of the Philippines System located in Cebu City, the capital city of Cebu province in the Philippines.
 It was founded on May 3, 1918, ten years after the founding of UP in 1908.
 It is considered as the University's flagship campus in Central Visayas.

### Generator output

**Answer:** six

**Explanation given by the generator:** The University of Rochester has six schools, as stated in the provided document.

**Documents the generator cited (its own citations, not a verified list):**

* `99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf` - [1] University of Rochester

---

## AG-0032

* `case_sha256`: `ebe0f75840aa1aefe2eaff305807ebc01a572a366b63998a4e1eed5614da1fab`

**Question:** How many different schools does the university, in which Andrew J. Elliot is a professor of psychology, have?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Rochester

`doc_id: 99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf`

The University of Rochester ( U of R or UR) frequently referred to simply as Rochester, is a private, nonsectarian, research university in Rochester, New York.
 The university grants undergraduate and graduate degrees, including doctoral and professional degrees.
 The university has six schools and various interdisciplinary programs.

### [2] Sampaloc, Manila

`doc_id: 3dd72fa8bb1b18ed68a684e8dfdf850cc1125eed3236b5eaffa64d9b52216792`

Sampaloc is one of the city districts that comprise Manila, Philippines.
 It is known as Metropolitan Manila's "University Belt", after the clusters of prominent higher educational institutions located there.
 Among the universities in Sampaloc are the University of Santo Tomas (1611, moved to Sampaloc in 1927), a by-product of the 333-year Hispanic colonization of the Philippines; National University (Philippines) (1900), as the first private nonsectarian and coeducational institution in the Philippines and also, the first university to use English as its medium of instruction, replacing Spanish language; Far Eastern University (1928), known for its Art Deco campus awarded as a cultural heritage site of the Philippines; and University of the East (1946), once dubbed as the largest university in Asia in terms of enrollment.
 The district is bordered by Quiapo and San Miguel districts in the south, Santa Mesa district in the south and east, Santa Cruz district in the west and north, and Quezon City in the northeast.

### [3] La Salle University (Ozamiz)

`doc_id: 9ac29e3caf04c0673e0250bd9124fa1253acb3c17aba6f59c1d84a3211360e37`

La Salle University (LSU), formerly known as Immaculate Conception College-La Salle, is a member school of De La Salle Philippines located in Ozamiz City, Misamis Occidental, Philippines.
 It was formally opened in 1929 by the Society of Jesus in the Philippines.
 It was formally turned over to the De La Salle Brothers in the Philippines in 1994 and was granted university status in 2006 and was renamed La Salle University.

### [4] Florida International University

`doc_id: bb755ce211b54acee77d26462f231c64ac235287912134467cfc71c509655317`

Florida International University (FIU) is an American metropolitan public research university in Greater Miami, Florida, United States.
 FIU has two major campuses in Miami-Dade County, with its main campus in University Park.
 Florida International University is classified as a research university with highest research activity by the Carnegie Foundation and a research university by the Florida Legislature.

### [5] University of the Philippines Cebu

`doc_id: 80734d512d4aae397931b1befb71e6716d633009af22212ecfb35ec4f825c404`

The University of the Philippines Cebu (Cebuano: "Unibersidad sa Pilipinas sa Sugbo" ; Filipino: "Unibersidad ng Pilipinas sa Cebu" ; also referred to as UPC or UP Cebu) is a public research university and the youngest constituent university of the University of the Philippines System located in Cebu City, the capital city of Cebu province in the Philippines.
 It was founded on May 3, 1918, ten years after the founding of UP in 1908.
 It is considered as the University's flagship campus in Central Visayas.

### Generator output

**Answer:** six

**Explanation given by the generator:** The document specifically states that the University of Rochester has six schools.

**Documents the generator cited (its own citations, not a verified list):**

* `99ed0cadc4086e77162c16d72a02e70bfd4537c3429091e52e75ffc8a91697bf` - [1] University of Rochester

---

## AG-0033

* `case_sha256`: `00eee6549d0e3cb2ec486f3f7fee8aa348b887fecdd66844cf012d1328726adc`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Ti Lung

`doc_id: 165a6800a97aad675686cba64a877f294fd16685e1674f2e3c1778a4af8a22c8`

Tommy Tam Fu-Wing (born 19 August 1946), better known by his stage name Ti Lung, is a Hong Kong actor, known for his numerous starring roles in a string of Shaw Brothers Studio's films, particularly "The Blood Brothers", "The Duel", "The Sentimental Swordsman" and its sequel, and in the classic "A Better Tomorrow".

### [4] Nicholas Ashley-Cooper, 12th Earl of Shaftesbury

`doc_id: bc3a468f9375d2fdbb8c53de4627399bfd6890117ba3d454ff921cac44065425`

Nicholas Edmund Anthony Ashley-Cooper, 12th Earl of Shaftesbury Bt, (born 3 June 1979) also known as Nick Ashley-Cooper, is an English peer, landowner and philanthropist.
 He succeeded his brother as Earl of Shaftesbury in 2005.
 The 12th Earl of Shaftesbury is the godson of Gerald Grosvenor, 6th Duke of Westminster, and Simon Elliot, brother-in-law of Charles, Prince of Wales.

### [5] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the movie 'Secretariat', which chronicles the life of the Thoroughbred race horse Secretariat.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0034

* `case_sha256`: `076b1796a2ac89e5d2dc008a7c3292bbc56e2ec97ee8676b3c992e943531b1a1`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [4] Ride a Wild Pony

`doc_id: d2909cfad278b2979ec0989df65d43e2af091b6bce6d1c35f90943a09668d1d3`

Ride a Wild Pony is a 1975 American-Australian family adventure film produced by Walt Disney Productions, directed by Don Chaffey and based on the novel "A Sporting Proposition" by James Aldridge.

### [5] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the film 'Secretariat', which chronicles the life of the Thoroughbred race horse of the same name.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0035

* `case_sha256`: `13e86b0c93183e9a59895e52c9f217460e5fd4414a5f518b7dbeafe479d90c10`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [4] Ride a Wild Pony

`doc_id: d2909cfad278b2979ec0989df65d43e2af091b6bce6d1c35f90943a09668d1d3`

Ride a Wild Pony is a 1975 American-Australian family adventure film produced by Walt Disney Productions, directed by Don Chaffey and based on the novel "A Sporting Proposition" by James Aldridge.

### [5] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the movie 'Secretariat', which chronicles the life of the Thoroughbred race horse Secretariat.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0036

* `case_sha256`: `1ae9a3aea81af5ea64e338acb37b8b34f51aee98aff016b415422056ba348c87`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Ti Lung

`doc_id: 165a6800a97aad675686cba64a877f294fd16685e1674f2e3c1778a4af8a22c8`

Tommy Tam Fu-Wing (born 19 August 1946), better known by his stage name Ti Lung, is a Hong Kong actor, known for his numerous starring roles in a string of Shaw Brothers Studio's films, particularly "The Blood Brothers", "The Duel", "The Sentimental Swordsman" and its sequel, and in the classic "A Better Tomorrow".

### [4] Nicholas Ashley-Cooper, 12th Earl of Shaftesbury

`doc_id: bc3a468f9375d2fdbb8c53de4627399bfd6890117ba3d454ff921cac44065425`

Nicholas Edmund Anthony Ashley-Cooper, 12th Earl of Shaftesbury Bt, (born 3 June 1979) also known as Nick Ashley-Cooper, is an English peer, landowner and philanthropist.
 He succeeded his brother as Earl of Shaftesbury in 2005.
 The 12th Earl of Shaftesbury is the godson of Gerald Grosvenor, 6th Duke of Westminster, and Simon Elliot, brother-in-law of Charles, Prince of Wales.

### [5] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the movie 'Secretariat', which chronicles the life of the Thoroughbred race horse of the same name.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0037

* `case_sha256`: `2b98b7178b2ab9c24a7a7458c844fcd5fe8f3a63bc231b99c933b02ac85b08db`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Ride a Wild Pony

`doc_id: d2909cfad278b2979ec0989df65d43e2af091b6bce6d1c35f90943a09668d1d3`

Ride a Wild Pony is a 1975 American-Australian family adventure film produced by Walt Disney Productions, directed by Don Chaffey and based on the novel "A Sporting Proposition" by James Aldridge.

### [4] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [5] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the film 'Secretariat', which chronicles the life of the Thoroughbred race horse of the same name.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0038

* `case_sha256`: `32db8f7c03ffb8973a022715c1dc92b5faba647020bf9cbca73f98b47efbf350`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [4] Ride a Wild Pony

`doc_id: d2909cfad278b2979ec0989df65d43e2af091b6bce6d1c35f90943a09668d1d3`

Ride a Wild Pony is a 1975 American-Australian family adventure film produced by Walt Disney Productions, directed by Don Chaffey and based on the novel "A Sporting Proposition" by James Aldridge.

### [5] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the film 'Secretariat', which chronicles the life of the Thoroughbred race horse Secretariat.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0039

* `case_sha256`: `50916c4b378ace67e382ffaffdcabd65e18fdf0a58af9d464b8eb07fdc55d917`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [4] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### [5] Annihilate 'Em

`doc_id: fd646e76f5678fc2a8c6c0b29401e95ad4fbb5043f75ecc52cfbfeb74eea4e04`

Annihilate 'em (April 11, 1970 – November 20, 1989) was a U.S. thoroughbred race horse who was best known for winning the 1973 Travers Stakes at Saratoga Race Course in Saratoga Springs, New York.
 Annihilate 'em was ridden to victory in the Travers by Ron Turcotte, who originally planned to ride Triple Crown winner Secretariat in the race.
 However, Secretariat missed the race due to poor health after losing the Whitney Stakes to Onion two weeks earlier while running with a low-grade fever.
 Annihilate 'Em and Secretariat met in their only race together in the Marlboro Cup Invitational Handicap in September 1973, where Secretariat finished first and Annihilate 'Em finished fifth.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the movie 'Secretariat', which chronicles the life of the Thoroughbred race horse of the same name.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0040

* `case_sha256`: `6bf4059e19a0a71f3b430de4df88428cf302fa0296ed17cee1794336f2c1aa2d`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [4] Ride a Wild Pony

`doc_id: d2909cfad278b2979ec0989df65d43e2af091b6bce6d1c35f90943a09668d1d3`

Ride a Wild Pony is a 1975 American-Australian family adventure film produced by Walt Disney Productions, directed by Don Chaffey and based on the novel "A Sporting Proposition" by James Aldridge.

### [5] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the movie 'Secretariat', which chronicles the life of the Thoroughbred race horse of the same name.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0041

* `case_sha256`: `8323ccbba97ab0f433541979fe67a28ebccd852c15f58c0f69fdf7025634a46d`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Ride a Wild Pony

`doc_id: d2909cfad278b2979ec0989df65d43e2af091b6bce6d1c35f90943a09668d1d3`

Ride a Wild Pony is a 1975 American-Australian family adventure film produced by Walt Disney Productions, directed by Don Chaffey and based on the novel "A Sporting Proposition" by James Aldridge.

### [4] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [5] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the movie 'Secretariat', which chronicles the life of the Thoroughbred race horse Secretariat.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0042

* `case_sha256`: `86a65dd9fc7a2e88867f926df16cd1292d0dedaf7a2294cf216754609953ce2e`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Ride a Wild Pony

`doc_id: d2909cfad278b2979ec0989df65d43e2af091b6bce6d1c35f90943a09668d1d3`

Ride a Wild Pony is a 1975 American-Australian family adventure film produced by Walt Disney Productions, directed by Don Chaffey and based on the novel "A Sporting Proposition" by James Aldridge.

### [4] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [5] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the film 'Secretariat', which chronicles the life of the Thoroughbred race horse Secretariat.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0043

* `case_sha256`: `a4ccd048daedf614b334f2798391b0387dbd47daf0ca227de8e13afe02987927`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### [4] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [5] Nicholas Ashley-Cooper, 12th Earl of Shaftesbury

`doc_id: bc3a468f9375d2fdbb8c53de4627399bfd6890117ba3d454ff921cac44065425`

Nicholas Edmund Anthony Ashley-Cooper, 12th Earl of Shaftesbury Bt, (born 3 June 1979) also known as Nick Ashley-Cooper, is an English peer, landowner and philanthropist.
 He succeeded his brother as Earl of Shaftesbury in 2005.
 The 12th Earl of Shaftesbury is the godson of Gerald Grosvenor, 6th Duke of Westminster, and Simon Elliot, brother-in-law of Charles, Prince of Wales.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the movie 'Secretariat', which chronicles the life of the Thoroughbred race horse of the same name.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0044

* `case_sha256`: `e5ee01f3deefcf13a2c4c51d8522a643afe492c695ce14d22b9b7d4e1c2a907f`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Ride a Wild Pony

`doc_id: d2909cfad278b2979ec0989df65d43e2af091b6bce6d1c35f90943a09668d1d3`

Ride a Wild Pony is a 1975 American-Australian family adventure film produced by Walt Disney Productions, directed by Don Chaffey and based on the novel "A Sporting Proposition" by James Aldridge.

### [4] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [5] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the movie 'Secretariat', which chronicles the life of the Thoroughbred race horse of the same name.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0045

* `case_sha256`: `ecefb7ebe47812186e12d6eca254b18a9e5a62ad7430b292d45a01af3db3d0f9`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Kelso (horse)

`doc_id: 82a8a226ffcb29757ca76db9ca664077fb80051c2a595f8266b619bde33f54ed`

Kelso (April 4, 1957 – October 16, 1983) was an American thoroughbred race horse considered among the best racehorses in history.
 In the list of the top 100 U.S. thoroughbred champions of the 20th Century by The Blood-Horse magazine, Kelso ranks 4th, behind only Man o' War (1st), Secretariat (2nd) and Citation (3rd).
 In his long career, Kelso defeated many leading Thorougbred racehorses including Carry Back, Gun Bow, Bald Eagle, Tompion, Never Bend, Beau Purple, Quadrangle, Roman Brother, Crimson Satan, Jaipur, Ridan and Pia Star, as well as other top thoroughbreds, often conceding weight under handicap conditions.
 In doing so, Kelso beat more champions and Hall of Fame horses than any other thoroughbred racehorse in the 20th Century.

### [4] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### [5] Annihilate 'Em

`doc_id: fd646e76f5678fc2a8c6c0b29401e95ad4fbb5043f75ecc52cfbfeb74eea4e04`

Annihilate 'em (April 11, 1970 – November 20, 1989) was a U.S. thoroughbred race horse who was best known for winning the 1973 Travers Stakes at Saratoga Race Course in Saratoga Springs, New York.
 Annihilate 'em was ridden to victory in the Travers by Ron Turcotte, who originally planned to ride Triple Crown winner Secretariat in the race.
 However, Secretariat missed the race due to poor health after losing the Whitney Stakes to Onion two weeks earlier while running with a low-grade fever.
 Annihilate 'Em and Secretariat met in their only race together in the Marlboro Cup Invitational Handicap in September 1973, where Secretariat finished first and Annihilate 'Em finished fifth.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the movie 'Secretariat', which chronicles the life of the Thoroughbred race horse of the same name.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0046

* `case_sha256`: `eff25e6c1f4578011ce0afdadfe7cc8ef6c768317aaf27885eee365b416871a5`

**Question:** James Cromwell stars in which movie that chronicles the life of Thoroughbred race horse?

**Context supplied to the generator (5 documents, in order):**

### [1] Secretariat (film)

`doc_id: 9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c`

Secretariat is a 2010 American biographical sports drama film produced and released by Walt Disney Pictures, written by Mike Rich and Sheldon Turner with music by Nick Glennie-Smith and directed by Randall Wallace.
 The film chronicles the life of Thoroughbred race horse Secretariat, winner of the Triple Crown in 1973.
 Diane Lane portrays Secretariat's owner, Penny Chenery, and John Malkovich plays his trainer, Lucien Laurin.
 Filming took place on location in Louisville and Lexington, Kentucky, and around Lafayette, Louisiana and Carencro, Louisiana.
 The film premiered at the Hollywood premiere in September 30, 2010 and was released on October 8, 2010 by Walt Disney Pictures.
 The film received mixed reviews from critics and earned $60.3 million on a $35 million budget.

### [2] James Cromwell

`doc_id: 7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938`

James Oliver Cromwell (born January 27, 1940) is an American actor.
 Some of his more notable films include "" (1996), "L.A. Confidential" (1997), "The Green Mile" (1999), "Space Cowboys" (2000), "The Sum of All Fears" (2002), "I, Robot" (2004), "The Longest Yard" (2005), "The Queen" (2006), "Secretariat" (2010), and "The Artist" (2011), as well as the television series "Six Feet Under" (2003–2005), "24" (2007) and "Halt and Catch Fire" (2015).

### [3] Ti Lung

`doc_id: 165a6800a97aad675686cba64a877f294fd16685e1674f2e3c1778a4af8a22c8`

Tommy Tam Fu-Wing (born 19 August 1946), better known by his stage name Ti Lung, is a Hong Kong actor, known for his numerous starring roles in a string of Shaw Brothers Studio's films, particularly "The Blood Brothers", "The Duel", "The Sentimental Swordsman" and its sequel, and in the classic "A Better Tomorrow".

### [4] Nicholas Ashley-Cooper, 12th Earl of Shaftesbury

`doc_id: bc3a468f9375d2fdbb8c53de4627399bfd6890117ba3d454ff921cac44065425`

Nicholas Edmund Anthony Ashley-Cooper, 12th Earl of Shaftesbury Bt, (born 3 June 1979) also known as Nick Ashley-Cooper, is an English peer, landowner and philanthropist.
 He succeeded his brother as Earl of Shaftesbury in 2005.
 The 12th Earl of Shaftesbury is the godson of Gerald Grosvenor, 6th Duke of Westminster, and Simon Elliot, brother-in-law of Charles, Prince of Wales.

### [5] Tammany (horse)

`doc_id: 20cdc196d0b6da5e98a3316ac39f43d525aeef4c913aecac2e59756d00a74ef1`

Tammany was an American Thoroughbred race horse.
 He was the favorite horse owned by Marcus Daly.
 Out of the American mare Tullahoma, a granddaughter of King Tom, the leading sire in Great Britain & Ireland in 1870 and 1871, Tammany's sire was Iroquois, the first American horse ever to win England's Epsom Derby.

### Generator output

**Answer:** Secretariat

**Explanation given by the generator:** James Cromwell stars in the movie 'Secretariat', which chronicles the life of the Thoroughbred race horse Secretariat.

**Documents the generator cited (its own citations, not a verified list):**

* `9bd881b9dd96c4c2b407af0a75c4713460a3087c01989cc408bbfdb5610efb7c` - [1] Secretariat (film)
* `7b1ba4626388eefe8dda1c1ff6ffc2a775e9fb5228bce6838d01c2fb53aef938` - [2] James Cromwell

---

## AG-0047

* `case_sha256`: `155ca74b06f7b0e4fc8273adf5c92ea02b06672e2680e19cfbaca2c8602be17e`

**Question:** Were Thinking Fellers Union Local 282 and the Smiths, who had a lead singer of Morrissey, both active in 1986?

**Context supplied to the generator (5 documents, in order):**

### [1] Thinking Fellers Union Local 282

`doc_id: b47ff7ad9e4f4f8f3e75926e6ac16056c1a6fc68a5d6a7b9965ccf0d7855daff`

Thinking Fellers Union Local 282 is an experimental indie rock group formed in 1986 in San Francisco, California, though half of its members are from Iowa.

### [2] Admonishing the Bishops

`doc_id: e8b4fb596b3ff433b0808ae50921e82e9d9f61977f21fb962d9d9131be7f08d0`

Admonishing the Bishops is an EP by the band Thinking Fellers Union Local 282, released as a CD and 10" vinyl record on October 26, 1993, through Matador Records.
 The EP's title refers to Alan and Rick Bishop of the Sun City Girls with whom the Thinking Fellers had toured with the previous year.

### [3] Morrissey

`doc_id: fadc6e2613a44507db7f55a7cc28da0f4fd97b27aa738e2ab3f87a84734cea01`

Steven Patrick Morrissey (born 22 May 1959), professionally known as Morrissey, is an English singer, songwriter and author.
 He rose to prominence as the lead singer of the indie rock band the Smiths, which was active from 1982 to 1987.
 Since then, Morrissey has had a solo career, making the top ten of the UK Singles Chart on ten occasions.

### [4] Mother of All Saints

`doc_id: 2fb7e484d25dbb06f69357eae449a802ae4488d45fad00cbb86ae3958c70459e`

Mother of All Saints is the fourth album by Thinking Fellers Union Local 282, released as a CD and double-LP on November 13, 1992 through Matador Records.

### [5] Where's Officer Tuba

`doc_id: 455752e653d503eb600b22f6e6a6723346d9f311a67726a65a6e14bd35059916`

Where's Officer Tuba is an EP by the band Thinking Fellers Union Local 282, released in 1993.

### Generator output

**Answer:** yes

**Explanation given by the generator:** Thinking Fellers Union Local 282 was formed in 1986, and the Smiths were active from 1982 to 1987, confirming both were active in 1986.

**Documents the generator cited (its own citations, not a verified list):**

* `b47ff7ad9e4f4f8f3e75926e6ac16056c1a6fc68a5d6a7b9965ccf0d7855daff` - [1] Thinking Fellers Union Local 282
* `fadc6e2613a44507db7f55a7cc28da0f4fd97b27aa738e2ab3f87a84734cea01` - [3] Morrissey

---

## AG-0048

* `case_sha256`: `71ef4d3c802954fa0573830ad7d254d5399d08c3a21b3acedf599822660c60a9`

**Question:** Were Thinking Fellers Union Local 282 and the Smiths, who had a lead singer of Morrissey, both active in 1986?

**Context supplied to the generator (5 documents, in order):**

### [1] Morrissey

`doc_id: fadc6e2613a44507db7f55a7cc28da0f4fd97b27aa738e2ab3f87a84734cea01`

Steven Patrick Morrissey (born 22 May 1959), professionally known as Morrissey, is an English singer, songwriter and author.
 He rose to prominence as the lead singer of the indie rock band the Smiths, which was active from 1982 to 1987.
 Since then, Morrissey has had a solo career, making the top ten of the UK Singles Chart on ten occasions.

### [2] Thinking Fellers Union Local 282

`doc_id: b47ff7ad9e4f4f8f3e75926e6ac16056c1a6fc68a5d6a7b9965ccf0d7855daff`

Thinking Fellers Union Local 282 is an experimental indie rock group formed in 1986 in San Francisco, California, though half of its members are from Iowa.

### [3] Admonishing the Bishops

`doc_id: e8b4fb596b3ff433b0808ae50921e82e9d9f61977f21fb962d9d9131be7f08d0`

Admonishing the Bishops is an EP by the band Thinking Fellers Union Local 282, released as a CD and 10" vinyl record on October 26, 1993, through Matador Records.
 The EP's title refers to Alan and Rick Bishop of the Sun City Girls with whom the Thinking Fellers had toured with the previous year.

### [4] Lovelyville

`doc_id: dd7fd3884e7921744b284ccd07e999a607644c302280f4dea37da85df3035fdc`

Lovelyville is the third album by Thinking Fellers Union Local 282, released December 12, 1991 on LP and CD through Matador Records.
 The CD contains bonus tracks entitled "The Crowded Diaper."

### [5] Mother of All Saints

`doc_id: 2fb7e484d25dbb06f69357eae449a802ae4488d45fad00cbb86ae3958c70459e`

Mother of All Saints is the fourth album by Thinking Fellers Union Local 282, released as a CD and double-LP on November 13, 1992 through Matador Records.

### Generator output

**Answer:** yes

**Explanation given by the generator:** The Smiths were active from 1982 to 1987, and Thinking Fellers Union Local 282 was formed in 1986, indicating both were active that year.

**Documents the generator cited (its own citations, not a verified list):**

* `fadc6e2613a44507db7f55a7cc28da0f4fd97b27aa738e2ab3f87a84734cea01` - [1] Morrissey
* `b47ff7ad9e4f4f8f3e75926e6ac16056c1a6fc68a5d6a7b9965ccf0d7855daff` - [2] Thinking Fellers Union Local 282

---

## AG-0049

* `case_sha256`: `fd9cde095b9a09c6d2f260b3075dc5a397bdbd65329b09d6150502956e81df26`

**Question:** Were Thinking Fellers Union Local 282 and the Smiths, who had a lead singer of Morrissey, both active in 1986?

**Context supplied to the generator (5 documents, in order):**

### [1] Morrissey

`doc_id: fadc6e2613a44507db7f55a7cc28da0f4fd97b27aa738e2ab3f87a84734cea01`

Steven Patrick Morrissey (born 22 May 1959), professionally known as Morrissey, is an English singer, songwriter and author.
 He rose to prominence as the lead singer of the indie rock band the Smiths, which was active from 1982 to 1987.
 Since then, Morrissey has had a solo career, making the top ten of the UK Singles Chart on ten occasions.

### [2] Thinking Fellers Union Local 282

`doc_id: b47ff7ad9e4f4f8f3e75926e6ac16056c1a6fc68a5d6a7b9965ccf0d7855daff`

Thinking Fellers Union Local 282 is an experimental indie rock group formed in 1986 in San Francisco, California, though half of its members are from Iowa.

### [3] Admonishing the Bishops

`doc_id: e8b4fb596b3ff433b0808ae50921e82e9d9f61977f21fb962d9d9131be7f08d0`

Admonishing the Bishops is an EP by the band Thinking Fellers Union Local 282, released as a CD and 10" vinyl record on October 26, 1993, through Matador Records.
 The EP's title refers to Alan and Rick Bishop of the Sun City Girls with whom the Thinking Fellers had toured with the previous year.

### [4] Lovelyville

`doc_id: dd7fd3884e7921744b284ccd07e999a607644c302280f4dea37da85df3035fdc`

Lovelyville is the third album by Thinking Fellers Union Local 282, released December 12, 1991 on LP and CD through Matador Records.
 The CD contains bonus tracks entitled "The Crowded Diaper."

### [5] Mother of All Saints

`doc_id: 2fb7e484d25dbb06f69357eae449a802ae4488d45fad00cbb86ae3958c70459e`

Mother of All Saints is the fourth album by Thinking Fellers Union Local 282, released as a CD and double-LP on November 13, 1992 through Matador Records.

### Generator output

**Answer:** yes

**Explanation given by the generator:** The Smiths were active from 1982 to 1987, and Thinking Fellers Union Local 282 was formed in 1986, indicating both were active in that year.

**Documents the generator cited (its own citations, not a verified list):**

* `fadc6e2613a44507db7f55a7cc28da0f4fd97b27aa738e2ab3f87a84734cea01` - [1] Morrissey
* `b47ff7ad9e4f4f8f3e75926e6ac16056c1a6fc68a5d6a7b9965ccf0d7855daff` - [2] Thinking Fellers Union Local 282

---

## AG-0050

* `case_sha256`: `09a266e04c789046d829e1a5447d1adb4155f4c9a7ce30c130618898b34783df`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen, where Jan Borgman was a professor, is explicitly stated as 1614 in the provided documents.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen

---

## AG-0051

* `case_sha256`: `1f1a4365656db4da5a540617b7539771db1eb2af8d992ef932e4ecc4bc0d4dbe`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [5] The Northcap University

`doc_id: 70028f42e8ca1a108384e63bb7fe84b2d7b7eac0d0da71d72eafde3b46e91cdb`

The NorthCap University, formerly ITM University, is an autonomous university situated in Sector 23-A, Gurugram, Haryana, India.
 It was founded in 1996 by Educate India Society, registered under the Registration of Societies Act of 1860 as an Engineering Institute, to provide education in Technical and Management.
 Formerly it was under Maharshi Dayanand University, Rohtak.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen is explicitly stated as 1614 in Document 1, which is the university where Jan Borgman was a professor.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen
* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [4] Jan Borgman

---

## AG-0052

* `case_sha256`: `3046c5f5242c48468cbfc26ad128e28b31c3e58e8c43b74ceb14e5f6e25cc8cf`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [2] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [3] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] University of Groningen

`doc_id: b965853d1fd123a87d1632b02913d1e8a852c00634c4d1c3c71a22ef367dc798`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1636 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The University of Groningen was founded in 1614, as stated in the retrieved documents.

**Documents the generator cited (its own citations, not a verified list):**

* `3` - not among the documents supplied above
* `5` - not among the documents supplied above

---

## AG-0053

* `case_sha256`: `5938f954026c0d741a1eae9cc8f3a355bc9f7e5194d544aea9add6ca746aceb0`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [3] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [4] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [5] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen, where Jan Borgman was a professor, is stated as 1614.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen
* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [4] Jan Borgman

---

## AG-0054

* `case_sha256`: `5a5e5b17ae59cb2329ddff8e2528dd9033ac29b4118eb409f0e32ec14b69b925`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [5] The Northcap University

`doc_id: 70028f42e8ca1a108384e63bb7fe84b2d7b7eac0d0da71d72eafde3b46e91cdb`

The NorthCap University, formerly ITM University, is an autonomous university situated in Sector 23-A, Gurugram, Haryana, India.
 It was founded in 1996 by Educate India Society, registered under the Registration of Societies Act of 1860 as an Engineering Institute, to provide education in Technical and Management.
 Formerly it was under Maharshi Dayanand University, Rohtak.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen is explicitly stated as 1614 in the first document.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen
* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [4] Jan Borgman

---

## AG-0055

* `case_sha256`: `5eddba2ed5846db64979d1fb6110386b68336c0a30b25897fd9e933674d6c1d2`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [3] The Northcap University

`doc_id: 70028f42e8ca1a108384e63bb7fe84b2d7b7eac0d0da71d72eafde3b46e91cdb`

The NorthCap University, formerly ITM University, is an autonomous university situated in Sector 23-A, Gurugram, Haryana, India.
 It was founded in 1996 by Educate India Society, registered under the Registration of Societies Act of 1860 as an Engineering Institute, to provide education in Technical and Management.
 Formerly it was under Maharshi Dayanand University, Rohtak.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] Karlsruhe Institute of Technology

`doc_id: b9ebf887bdf5b8c2aa02165729ca72d150f3f248f40dd70640565d7f0b487c11`

The Karlsruhe Institute of Technology (KIT) (German: "Karlsruher Institut für Technologie" ) is a public research university and one of the largest research and education institutions in Germany.
 KIT was created in 2009 when the University of Karlsruhe ("Universität Karlsruhe"), founded in 1825 as public research university and also known as "Fridericiana", merged with the Karlsruhe Research Center Forschungszentrum Karlsruhe, which was originally established as a national nuclear research center (Kernforschungszentrum Karlsruhe, or KfK) in 1956.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen, where Jan Borgman was a professor, is stated as 1614 in the provided document.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen

---

## AG-0056

* `case_sha256`: `639e57a7410a2fb14c04a6223127d2b2d12cbfdcaf7ee268d1fa3c8185757cc5`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [5] The Northcap University

`doc_id: 70028f42e8ca1a108384e63bb7fe84b2d7b7eac0d0da71d72eafde3b46e91cdb`

The NorthCap University, formerly ITM University, is an autonomous university situated in Sector 23-A, Gurugram, Haryana, India.
 It was founded in 1996 by Educate India Society, registered under the Registration of Societies Act of 1860 as an Engineering Institute, to provide education in Technical and Management.
 Formerly it was under Maharshi Dayanand University, Rohtak.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen, where Jan Borgman was a professor, is stated as 1614 in the documents.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen
* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [4] Jan Borgman

---

## AG-0057

* `case_sha256`: `6440436173ad319b52509972078ea6094cfbe13b7aadc135be9507f0f5b9a2bb`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [2] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [3] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] Christine L. Borgman

`doc_id: f8b1dbaaecbc4d20c1da0d5eb3481271efbdb6b585cd7fa75d3fb85f9d8e5345`

Christine L. Borgman is Distinguished Professor and Presidential Chair in Information Studies at UCLA.
 She is the author of more than 200 publications in the fields of information studies, computer science, and communication.
 Both of her sole-authored monographs, Scholarship in the Digital Age: Information, Infrastructure, and the Internet (MIT Press, 2007) and From Gutenberg to the Global Information Infrastructure: Access to Information in a Networked World (MIT Press, 2000), have won the Best Information Science Book of the Year award from the American Society for Information Science and Technology.
 She is a lead investigator for the Center for Embedded Networked Sensing (CENS), a National Science Foundation Science and Technology Center, where she conducts data practices research.
 She chaired the Task Force on Cyberlearning for the NSF, whose report, Fostering Learning in the Networked World, was released in July, 2008.
 Prof. Borgman is a Fellow of the American Association for the Advancement of Science (AAAS), a Legacy Laureate of the University of Pittsburgh, and is the 2011 recipient of the Paul Evan Peters Award from the Coalition for Networked Information, Association for Research Libraries, and EDUCAUSE.
 The award recognizes notable, lasting achievements in the creation and innovative use of information resources and services that advance scholarship and intellectual productivity through communication networks.
 She is also the 2011 recipient of the Research in Information Science Award from the American Association of Information Science and Technology.
 In 2013 she became a fellow of the Association for Computing Machinery.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The University of Groningen was founded in 1614, and Jan Borgman was a professor there during the specified years.

**Documents the generator cited (its own citations, not a verified list):**

* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [1] Jan Borgman
* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [3] University of Groningen

---

## AG-0058

* `case_sha256`: `892d06b889694a2169fddcca0d684206a8725a943f9fba00abe5ed717df9f322`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen is explicitly stated as 1614 in Document 1, and Jan Borgman was a professor there from 1968 to 1988 as mentioned in Document 2.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen
* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [2] Jan Borgman

---

## AG-0059

* `case_sha256`: `ab23b1378dbc27ce9d91a24004930f1906ae3ecd506d6fc06b33d826d459e153`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen, where Jan Borgman was a professor, is stated as 1614 in the provided documents.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen

---

## AG-0060

* `case_sha256`: `b90a4943143ed3a2f28ff1038f9e7421bc28ba9bf9144bde92a59db4a16a27fa`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen, where Jan Borgman was a professor, is explicitly stated as 1614 in the first document.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen

---

## AG-0061

* `case_sha256`: `c3c5709297a80b61c5b426d75e9aab328c5511fdc616a4e834a6ca87c7a9dc40`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen is explicitly stated as 1614 in the first document.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen
* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [2] Jan Borgman

---

## AG-0062

* `case_sha256`: `c41b976c8581f1c8f1d7b975ad69527085ae16af5463494c5ae881c38a919901`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [2] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [3] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] Christine L. Borgman

`doc_id: f8b1dbaaecbc4d20c1da0d5eb3481271efbdb6b585cd7fa75d3fb85f9d8e5345`

Christine L. Borgman is Distinguished Professor and Presidential Chair in Information Studies at UCLA.
 She is the author of more than 200 publications in the fields of information studies, computer science, and communication.
 Both of her sole-authored monographs, Scholarship in the Digital Age: Information, Infrastructure, and the Internet (MIT Press, 2007) and From Gutenberg to the Global Information Infrastructure: Access to Information in a Networked World (MIT Press, 2000), have won the Best Information Science Book of the Year award from the American Society for Information Science and Technology.
 She is a lead investigator for the Center for Embedded Networked Sensing (CENS), a National Science Foundation Science and Technology Center, where she conducts data practices research.
 She chaired the Task Force on Cyberlearning for the NSF, whose report, Fostering Learning in the Networked World, was released in July, 2008.
 Prof. Borgman is a Fellow of the American Association for the Advancement of Science (AAAS), a Legacy Laureate of the University of Pittsburgh, and is the 2011 recipient of the Paul Evan Peters Award from the Coalition for Networked Information, Association for Research Libraries, and EDUCAUSE.
 The award recognizes notable, lasting achievements in the creation and innovative use of information resources and services that advance scholarship and intellectual productivity through communication networks.
 She is also the 2011 recipient of the Research in Information Science Award from the American Association of Information Science and Technology.
 In 2013 she became a fellow of the Association for Computing Machinery.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The University of Groningen, where Jan Borgman was a professor, was founded in 1614.

**Documents the generator cited (its own citations, not a verified list):**

* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [1] Jan Borgman
* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [3] University of Groningen

---

## AG-0063

* `case_sha256`: `c652cf48506ab89ebf5136e7252b80f6d90d180bb067ea4d7bd26570de9b63bc`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen is explicitly stated in Document 1.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen

---

## AG-0064

* `case_sha256`: `c6f2b48b10b8327bd9fa0a99fb773b67a96f6a9f462ffda5c06154886521ba7b`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen is explicitly stated as 1614 in Document 1.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen
* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [2] Jan Borgman

---

## AG-0065

* `case_sha256`: `c955c4e4bbe593c57c01c79fdcce6f3fa439823c480809ded8ced0fe7135d37d`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [2] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [3] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] Christine L. Borgman

`doc_id: f8b1dbaaecbc4d20c1da0d5eb3481271efbdb6b585cd7fa75d3fb85f9d8e5345`

Christine L. Borgman is Distinguished Professor and Presidential Chair in Information Studies at UCLA.
 She is the author of more than 200 publications in the fields of information studies, computer science, and communication.
 Both of her sole-authored monographs, Scholarship in the Digital Age: Information, Infrastructure, and the Internet (MIT Press, 2007) and From Gutenberg to the Global Information Infrastructure: Access to Information in a Networked World (MIT Press, 2000), have won the Best Information Science Book of the Year award from the American Society for Information Science and Technology.
 She is a lead investigator for the Center for Embedded Networked Sensing (CENS), a National Science Foundation Science and Technology Center, where she conducts data practices research.
 She chaired the Task Force on Cyberlearning for the NSF, whose report, Fostering Learning in the Networked World, was released in July, 2008.
 Prof. Borgman is a Fellow of the American Association for the Advancement of Science (AAAS), a Legacy Laureate of the University of Pittsburgh, and is the 2011 recipient of the Paul Evan Peters Award from the Coalition for Networked Information, Association for Research Libraries, and EDUCAUSE.
 The award recognizes notable, lasting achievements in the creation and innovative use of information resources and services that advance scholarship and intellectual productivity through communication networks.
 She is also the 2011 recipient of the Research in Information Science Award from the American Association of Information Science and Technology.
 In 2013 she became a fellow of the Association for Computing Machinery.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen, where Jan Borgman was a professor, is stated as 1614.

**Documents the generator cited (its own citations, not a verified list):**

* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [1] Jan Borgman
* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [3] University of Groningen

---

## AG-0066

* `case_sha256`: `cdaefaae982fe2fb1bfff6b0cadf7644aedd2703474199b903fd260bebd968fe`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [3] The Northcap University

`doc_id: 70028f42e8ca1a108384e63bb7fe84b2d7b7eac0d0da71d72eafde3b46e91cdb`

The NorthCap University, formerly ITM University, is an autonomous university situated in Sector 23-A, Gurugram, Haryana, India.
 It was founded in 1996 by Educate India Society, registered under the Registration of Societies Act of 1860 as an Engineering Institute, to provide education in Technical and Management.
 Formerly it was under Maharshi Dayanand University, Rohtak.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] Karlsruhe Institute of Technology

`doc_id: b9ebf887bdf5b8c2aa02165729ca72d150f3f248f40dd70640565d7f0b487c11`

The Karlsruhe Institute of Technology (KIT) (German: "Karlsruher Institut für Technologie" ) is a public research university and one of the largest research and education institutions in Germany.
 KIT was created in 2009 when the University of Karlsruhe ("Universität Karlsruhe"), founded in 1825 as public research university and also known as "Fridericiana", merged with the Karlsruhe Research Center Forschungszentrum Karlsruhe, which was originally established as a national nuclear research center (Kernforschungszentrum Karlsruhe, or KfK) in 1956.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen, where Jan Borgman was a professor, is explicitly stated as 1614 in the provided document.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen

---

## AG-0067

* `case_sha256`: `eaef10f45919846c1cdc59846d97cae93cfcf473f29b042576c19f7d7c51a6b6`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### [3] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [4] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [5] The Northcap University

`doc_id: 70028f42e8ca1a108384e63bb7fe84b2d7b7eac0d0da71d72eafde3b46e91cdb`

The NorthCap University, formerly ITM University, is an autonomous university situated in Sector 23-A, Gurugram, Haryana, India.
 It was founded in 1996 by Educate India Society, registered under the Registration of Societies Act of 1860 as an Engineering Institute, to provide education in Technical and Management.
 Formerly it was under Maharshi Dayanand University, Rohtak.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen, where Jan Borgman was a professor, is stated as 1614.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen
* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [4] Jan Borgman

---

## AG-0068

* `case_sha256`: `f6a10da51507da3af828474779b6d12dc09ba99ff27d19ada0fd63c7abac8aa4`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] Jan Borgman

`doc_id: a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3`

Jan Borgman (born 30 November 1929) is a Dutch astronomer and university administrator.
 He was professor of astronomical observation technique at the University of Groningen from 1968 to 1988.
 During this period he served as rector magnificus from 1978 to 1981 and chair of the board of governors from 1981 to 1988.
 Borgman subsequently became chairperson of the Netherlands Organisation for Scientific Research.

### [2] Erik Borgman

`doc_id: 02f7f854a3e4639d82a7f309e72c84d290e3682fd7522a5b9a6ccd21dc3ac91a`

Professor Erik Borgman (born 1957, Amsterdam) (sometimes listed as Eric Borgman) is a Dutch professor of systematic theology at the University of Tilburg, the Netherlands.
 At the Radboud University Nijmegen, the Netherlands, he was the Director of the Heyendaal Institute, an institute for interdisciplinary research.
 He is the biographer of the Flemish theologian Edward Schillebeeckx.
 He was also the President of the International Society for Religion, Literature and Culture.
 He is a member of the Editorial Board and the Presidential Board of "Concilium: International Journal for Theology", also an editor of the Dutch "Tijdschrift voor Theologie" and member of the Third Order of Saint Dominic.

### [3] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [4] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [5] Christine L. Borgman

`doc_id: f8b1dbaaecbc4d20c1da0d5eb3481271efbdb6b585cd7fa75d3fb85f9d8e5345`

Christine L. Borgman is Distinguished Professor and Presidential Chair in Information Studies at UCLA.
 She is the author of more than 200 publications in the fields of information studies, computer science, and communication.
 Both of her sole-authored monographs, Scholarship in the Digital Age: Information, Infrastructure, and the Internet (MIT Press, 2007) and From Gutenberg to the Global Information Infrastructure: Access to Information in a Networked World (MIT Press, 2000), have won the Best Information Science Book of the Year award from the American Society for Information Science and Technology.
 She is a lead investigator for the Center for Embedded Networked Sensing (CENS), a National Science Foundation Science and Technology Center, where she conducts data practices research.
 She chaired the Task Force on Cyberlearning for the NSF, whose report, Fostering Learning in the Networked World, was released in July, 2008.
 Prof. Borgman is a Fellow of the American Association for the Advancement of Science (AAAS), a Legacy Laureate of the University of Pittsburgh, and is the 2011 recipient of the Paul Evan Peters Award from the Coalition for Networked Information, Association for Research Libraries, and EDUCAUSE.
 The award recognizes notable, lasting achievements in the creation and innovative use of information resources and services that advance scholarship and intellectual productivity through communication networks.
 She is also the 2011 recipient of the Research in Information Science Award from the American Association of Information Science and Technology.
 In 2013 she became a fellow of the Association for Computing Machinery.

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The University of Groningen was founded in 1614, as stated in the document about the university.

**Documents the generator cited (its own citations, not a verified list):**

* `a76f1228ff52b6c3262daaafb8cf8eae412a2f352f07496902ef0a4cf79a68b3` - [1] Jan Borgman
* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [3] University of Groningen

---

## AG-0069

* `case_sha256`: `f9db842484f0a1a4ae5eded162444e11db4f5f40eee163242893fca2d1dfddde`

**Question:** What is the founding year of this public research university in the Netherlands, where Jan Borgman was a professor from 1968 to 1988?

**Context supplied to the generator (5 documents, in order):**

### [1] University of Groningen

`doc_id: acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc`

The University of Groningen (abbreviated as UG; Dutch: "Rijksuniversiteit Groningen" , abbreviated as "RUG") is a public research university in the city of Groningen in the Netherlands.
 The university was founded in 1614 and is one of the oldest universities in the Netherlands as well as one of its largest.
 Since its inception more than 200,000 students have graduated.
 It is a member of the distinguished international Coimbra Group of European universities.

### [2] University of Hagen

`doc_id: e2ce9b0d712c22d82c0809f651ec6ba5be4c9525104d7b5e2f1a96c56f48d030`

The University of Hagen (German: "FernUniversität in Hagen" , informally often referred to as FU Hagen) is a public research university that is primarily focused on distance teaching.
 While its main campus is located in Hagen, North Rhine-Westphalia, Germany, the university maintains more than 50 study and research centers in Germany and throughout Europe.
 According to the Federal Statistical Office of Germany it is Germany's largest university.
 The university was founded in 1974 as a public research university by the state Nordrhein-Westfalen and began its research and teaching activities in 1975.
 It was founded following the idea of UK's Open University to provide higher and continuing education opportunities through a distance education system in Germany.

### [3] The Northcap University

`doc_id: 70028f42e8ca1a108384e63bb7fe84b2d7b7eac0d0da71d72eafde3b46e91cdb`

The NorthCap University, formerly ITM University, is an autonomous university situated in Sector 23-A, Gurugram, Haryana, India.
 It was founded in 1996 by Educate India Society, registered under the Registration of Societies Act of 1860 as an Engineering Institute, to provide education in Technical and Management.
 Formerly it was under Maharshi Dayanand University, Rohtak.

### [4] Karlsruhe Institute of Technology

`doc_id: b9ebf887bdf5b8c2aa02165729ca72d150f3f248f40dd70640565d7f0b487c11`

The Karlsruhe Institute of Technology (KIT) (German: "Karlsruher Institut für Technologie" ) is a public research university and one of the largest research and education institutions in Germany.
 KIT was created in 2009 when the University of Karlsruhe ("Universität Karlsruhe"), founded in 1825 as public research university and also known as "Fridericiana", merged with the Karlsruhe Research Center Forschungszentrum Karlsruhe, which was originally established as a national nuclear research center (Kernforschungszentrum Karlsruhe, or KfK) in 1956.

### [5] University of the Philippines

`doc_id: 46005089b9ffd7214627fff3272a81618c31e4c33cdd2f5103930c136d9af6ac`

The University of the Philippines (UP; Filipino: "Unibersidad ng Pilipinas" or "Pamantasan ng Pilipinas") is a state university system in the Philippines.
 Founded by the American colonial government on June 18, 1908, it was originally a university conceived for the Filipinos.
 Act 1870 of the 1st Philippine Legislature was signed to establish UP to provide "advanced instruction in literature, philosophy, the sciences and arts, and to give professional and technical training" to eligible students regardless of "age, sex, nationality, religious belief and political affiliation".
 UP has institutional autonomy as the country's national university as mandated by Republic Act No. 9500 (UP Charter of 2008).

### Generator output

**Answer:** 1614

**Explanation given by the generator:** The founding year of the University of Groningen, where Jan Borgman was a professor, is explicitly stated as 1614 in the provided document.

**Documents the generator cited (its own citations, not a verified list):**

* `acc94050955ea840327cedcb9a855b2328e2c0f86043360d8932c47bc3775afc` - [1] University of Groningen

---

## AG-0070

* `case_sha256`: `1286581bb71366ae6250fbbb00d18f932146701c41ffeb8248140478c620e5fc`

**Question:** When did the animated series Kent Scott wrote end after beginning in September of 2002 on "Nick on CBS"?

**Context supplied to the generator (5 documents, in order):**

### [1] Pelswick

`doc_id: d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817`

Pelswick is an animated television series co-produced by Nelvana Limited and Suzhou Hong Ying Animation Corporation Limited in association with The Canadian Broadcasting Corporation and Nickelodeon.
 The series is about a teenage boy who uses a wheelchair, emphasizing that he lived a normal life.
 It was based on the books created by John Callahan.
 It aired during "Nick on CBS" beginning on September 14, 2002, and ended in November of that year.
 Unlike most Nicktoons, "Pelswick" is not rerun on NickSplat.

### [2] Dora the Explorer

`doc_id: 9815cf7dc78de31159910af7094dd5a42f58514d3ceadbd8a3d4df0467f56fcf`

Dora the Explorer is an American educational animated TV series created by Chris Gifford, Valerie Walsh, and Eric Weiner.
 "Dora the Explorer" became a regular series in 2000.
 The show is carried on the Nickelodeon cable television network, including the associated Nick Jr. channel.
 It aired on CBS until September 2006.
 A Spanish-dubbed version first aired as part of a "Nick en español" block on NBC Universal-owned Telemundo through September 2006; since April 2008, this version of the program has been carried on Univision as part of the "Planeta U" block.
 The series is co-produced by Nickelodeon Productions and Nickelodeon Animation Studio.
 "Dora the Explorer" is one of the longest-running shows of Nick Jr.
 During the sixth season, the show became the Nick Jr. series with the most episodes, surpassing "Blue's Clues" with 143 episodes, having 144 after it had completed broadcasting on television.
 It won a Peabody Award in 2003 "for outstanding efforts in making learning a pleasurable experience for pre-schoolers."
 It ended on June 5, 2014 after 8 seasons and 172 episodes.

### [3] Project G.e.e.K.e.R.

`doc_id: 4668ae15118f0120cef2e0ea5f870d8446aaa92346d9981a49da18d17cde0655`

Project G.e.e.K.e.R. is an animated television series that premiered on CBS on September 14, 1996.
 It was created by Douglas TenNapel, creator of "Earthworm Jim", and Doug Langdale, the developer of "Earthworm Jim" the animated series, with original music by Shawn Patterson (main title theme by Terry Scott Taylor).
 TenNapel and Taylor also collaborated on the video games "The Neverhood", "Boombots" and "Skullmonkeys", and in 2005, re-united for the Nickelodeon cartoon "Catscratch".
 The series is rated TV-Y7-FV, and was produced by Columbia TriStar Television.

### [4] Hawaii Five-0 (2010 TV series)

`doc_id: 2df6ce654a89cd59d3eeedd8cb376545a88cda6bba404359304d1e7afdbf5513`

Hawaii Five-0 is an American action police procedural television series, which premiered on Monday, September 20, 2010 on CBS.
 The series is a reboot of the original series, which aired on CBS from 1968 to 1980.
 Like the original, it follows an elite state police task force set up to fight crime in the state of Hawaii.
 The series is produced by K/O Paper Products and 101st Street Television in association with CBS Productions, originally an in-name-only unit of but folded into CBS Television Studios, which has produced the series since the beginning of season three.
 On March 25, 2016, CBS renewed the series for a seventh season, which premiered on September 23, 2016.
 On March 23, 2017, CBS renewed the series for an eighth season, which premiered on September 29, 2017.

### [5] Horseland (TV series)

`doc_id: 33874ae68bced29df696a1e9a4088c55881bb1fbbec59c2b664b41cec7eb0b34`

Horseland is an American animated series produced by DIC Entertainment.
 It is a comic mischief program following events in the lives of a group of children riding at Horseland, an equestrian school and stables.
 Their adventures include riding their horses and entering them in competitions to test their skill and friendships.
 The show premiered on September 16, 2006 as part of CBS's new Saturday morning cartoon block, "KOL Secret Slumber Party on CBS" (now "Cookie Jar TV").
 Concurrent with the series, the online virtual pet game that it was based upon was updated to complement the show by launching a new "Junior version" of the game based on the program and featuring its various characters and locations.
 After three seasons, the show was canceled on CBS on December 6, 2008.
 Reruns of "Horseland" then aired nationwide on the digital subchannel This TV; two episodes aired each weekend until September 2010.
 "Horseland" last aired as part of "Cookie Jar TV" on CBS.
 It has 7 books for the series related to the episodes which are available to be purchased online.

### Generator output

**Answer:** November 2002

**Explanation given by the generator:** The document states that the animated series 'Pelswick' began airing on September 14, 2002, and ended in November of that same year.

**Documents the generator cited (its own citations, not a verified list):**

* `d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817` - [1] Pelswick

---

## AG-0071

* `case_sha256`: `1513ee69ffdcec8d187db0e4771d0daf6fbbfac468750ea2b4182f01b146ccb9`

**Question:** When did the animated series Kent Scott wrote end after beginning in September of 2002 on "Nick on CBS"?

**Context supplied to the generator (5 documents, in order):**

### [1] Pelswick

`doc_id: d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817`

Pelswick is an animated television series co-produced by Nelvana Limited and Suzhou Hong Ying Animation Corporation Limited in association with The Canadian Broadcasting Corporation and Nickelodeon.
 The series is about a teenage boy who uses a wheelchair, emphasizing that he lived a normal life.
 It was based on the books created by John Callahan.
 It aired during "Nick on CBS" beginning on September 14, 2002, and ended in November of that year.
 Unlike most Nicktoons, "Pelswick" is not rerun on NickSplat.

### [2] Dora the Explorer

`doc_id: 9815cf7dc78de31159910af7094dd5a42f58514d3ceadbd8a3d4df0467f56fcf`

Dora the Explorer is an American educational animated TV series created by Chris Gifford, Valerie Walsh, and Eric Weiner.
 "Dora the Explorer" became a regular series in 2000.
 The show is carried on the Nickelodeon cable television network, including the associated Nick Jr. channel.
 It aired on CBS until September 2006.
 A Spanish-dubbed version first aired as part of a "Nick en español" block on NBC Universal-owned Telemundo through September 2006; since April 2008, this version of the program has been carried on Univision as part of the "Planeta U" block.
 The series is co-produced by Nickelodeon Productions and Nickelodeon Animation Studio.
 "Dora the Explorer" is one of the longest-running shows of Nick Jr.
 During the sixth season, the show became the Nick Jr. series with the most episodes, surpassing "Blue's Clues" with 143 episodes, having 144 after it had completed broadcasting on television.
 It won a Peabody Award in 2003 "for outstanding efforts in making learning a pleasurable experience for pre-schoolers."
 It ended on June 5, 2014 after 8 seasons and 172 episodes.

### [3] Project G.e.e.K.e.R.

`doc_id: 4668ae15118f0120cef2e0ea5f870d8446aaa92346d9981a49da18d17cde0655`

Project G.e.e.K.e.R. is an animated television series that premiered on CBS on September 14, 1996.
 It was created by Douglas TenNapel, creator of "Earthworm Jim", and Doug Langdale, the developer of "Earthworm Jim" the animated series, with original music by Shawn Patterson (main title theme by Terry Scott Taylor).
 TenNapel and Taylor also collaborated on the video games "The Neverhood", "Boombots" and "Skullmonkeys", and in 2005, re-united for the Nickelodeon cartoon "Catscratch".
 The series is rated TV-Y7-FV, and was produced by Columbia TriStar Television.

### [4] Hawaii Five-0 (2010 TV series)

`doc_id: 2df6ce654a89cd59d3eeedd8cb376545a88cda6bba404359304d1e7afdbf5513`

Hawaii Five-0 is an American action police procedural television series, which premiered on Monday, September 20, 2010 on CBS.
 The series is a reboot of the original series, which aired on CBS from 1968 to 1980.
 Like the original, it follows an elite state police task force set up to fight crime in the state of Hawaii.
 The series is produced by K/O Paper Products and 101st Street Television in association with CBS Productions, originally an in-name-only unit of but folded into CBS Television Studios, which has produced the series since the beginning of season three.
 On March 25, 2016, CBS renewed the series for a seventh season, which premiered on September 23, 2016.
 On March 23, 2017, CBS renewed the series for an eighth season, which premiered on September 29, 2017.

### [5] Horseland (TV series)

`doc_id: 33874ae68bced29df696a1e9a4088c55881bb1fbbec59c2b664b41cec7eb0b34`

Horseland is an American animated series produced by DIC Entertainment.
 It is a comic mischief program following events in the lives of a group of children riding at Horseland, an equestrian school and stables.
 Their adventures include riding their horses and entering them in competitions to test their skill and friendships.
 The show premiered on September 16, 2006 as part of CBS's new Saturday morning cartoon block, "KOL Secret Slumber Party on CBS" (now "Cookie Jar TV").
 Concurrent with the series, the online virtual pet game that it was based upon was updated to complement the show by launching a new "Junior version" of the game based on the program and featuring its various characters and locations.
 After three seasons, the show was canceled on CBS on December 6, 2008.
 Reruns of "Horseland" then aired nationwide on the digital subchannel This TV; two episodes aired each weekend until September 2010.
 "Horseland" last aired as part of "Cookie Jar TV" on CBS.
 It has 7 books for the series related to the episodes which are available to be purchased online.

### Generator output

**Answer:** November 2002

**Explanation given by the generator:** The document states that the animated series 'Pelswick' aired from September 14, 2002, and ended in November of that year.

**Documents the generator cited (its own citations, not a verified list):**

* `d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817` - [1] Pelswick

---

## AG-0072

* `case_sha256`: `34fbf17b034e02462dba95edce3c3f7be9a27a1776cafb97d2f6aefb21db4641`

**Question:** When did the animated series Kent Scott wrote end after beginning in September of 2002 on "Nick on CBS"?

**Context supplied to the generator (5 documents, in order):**

### [1] Pelswick

`doc_id: d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817`

Pelswick is an animated television series co-produced by Nelvana Limited and Suzhou Hong Ying Animation Corporation Limited in association with The Canadian Broadcasting Corporation and Nickelodeon.
 The series is about a teenage boy who uses a wheelchair, emphasizing that he lived a normal life.
 It was based on the books created by John Callahan.
 It aired during "Nick on CBS" beginning on September 14, 2002, and ended in November of that year.
 Unlike most Nicktoons, "Pelswick" is not rerun on NickSplat.

### [2] Dora the Explorer

`doc_id: 9815cf7dc78de31159910af7094dd5a42f58514d3ceadbd8a3d4df0467f56fcf`

Dora the Explorer is an American educational animated TV series created by Chris Gifford, Valerie Walsh, and Eric Weiner.
 "Dora the Explorer" became a regular series in 2000.
 The show is carried on the Nickelodeon cable television network, including the associated Nick Jr. channel.
 It aired on CBS until September 2006.
 A Spanish-dubbed version first aired as part of a "Nick en español" block on NBC Universal-owned Telemundo through September 2006; since April 2008, this version of the program has been carried on Univision as part of the "Planeta U" block.
 The series is co-produced by Nickelodeon Productions and Nickelodeon Animation Studio.
 "Dora the Explorer" is one of the longest-running shows of Nick Jr.
 During the sixth season, the show became the Nick Jr. series with the most episodes, surpassing "Blue's Clues" with 143 episodes, having 144 after it had completed broadcasting on television.
 It won a Peabody Award in 2003 "for outstanding efforts in making learning a pleasurable experience for pre-schoolers."
 It ended on June 5, 2014 after 8 seasons and 172 episodes.

### [3] Project G.e.e.K.e.R.

`doc_id: 4668ae15118f0120cef2e0ea5f870d8446aaa92346d9981a49da18d17cde0655`

Project G.e.e.K.e.R. is an animated television series that premiered on CBS on September 14, 1996.
 It was created by Douglas TenNapel, creator of "Earthworm Jim", and Doug Langdale, the developer of "Earthworm Jim" the animated series, with original music by Shawn Patterson (main title theme by Terry Scott Taylor).
 TenNapel and Taylor also collaborated on the video games "The Neverhood", "Boombots" and "Skullmonkeys", and in 2005, re-united for the Nickelodeon cartoon "Catscratch".
 The series is rated TV-Y7-FV, and was produced by Columbia TriStar Television.

### [4] Horseland (TV series)

`doc_id: 33874ae68bced29df696a1e9a4088c55881bb1fbbec59c2b664b41cec7eb0b34`

Horseland is an American animated series produced by DIC Entertainment.
 It is a comic mischief program following events in the lives of a group of children riding at Horseland, an equestrian school and stables.
 Their adventures include riding their horses and entering them in competitions to test their skill and friendships.
 The show premiered on September 16, 2006 as part of CBS's new Saturday morning cartoon block, "KOL Secret Slumber Party on CBS" (now "Cookie Jar TV").
 Concurrent with the series, the online virtual pet game that it was based upon was updated to complement the show by launching a new "Junior version" of the game based on the program and featuring its various characters and locations.
 After three seasons, the show was canceled on CBS on December 6, 2008.
 Reruns of "Horseland" then aired nationwide on the digital subchannel This TV; two episodes aired each weekend until September 2010.
 "Horseland" last aired as part of "Cookie Jar TV" on CBS.
 It has 7 books for the series related to the episodes which are available to be purchased online.

### [5] Hawaii Five-0 (2010 TV series)

`doc_id: 2df6ce654a89cd59d3eeedd8cb376545a88cda6bba404359304d1e7afdbf5513`

Hawaii Five-0 is an American action police procedural television series, which premiered on Monday, September 20, 2010 on CBS.
 The series is a reboot of the original series, which aired on CBS from 1968 to 1980.
 Like the original, it follows an elite state police task force set up to fight crime in the state of Hawaii.
 The series is produced by K/O Paper Products and 101st Street Television in association with CBS Productions, originally an in-name-only unit of but folded into CBS Television Studios, which has produced the series since the beginning of season three.
 On March 25, 2016, CBS renewed the series for a seventh season, which premiered on September 23, 2016.
 On March 23, 2017, CBS renewed the series for an eighth season, which premiered on September 29, 2017.

### Generator output

**Answer:** November 2002

**Explanation given by the generator:** The document states that the animated series 'Pelswick' began airing on September 14, 2002, and ended in November of that year.

**Documents the generator cited (its own citations, not a verified list):**

* `d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817` - [1] Pelswick

---

## AG-0073

* `case_sha256`: `41ad52f5370b5259637f6b77beec825f9763c2e1cbb3f1b82f29178644bf62d6`

**Question:** When did the animated series Kent Scott wrote end after beginning in September of 2002 on "Nick on CBS"?

**Context supplied to the generator (5 documents, in order):**

### [1] Pelswick

`doc_id: d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817`

Pelswick is an animated television series co-produced by Nelvana Limited and Suzhou Hong Ying Animation Corporation Limited in association with The Canadian Broadcasting Corporation and Nickelodeon.
 The series is about a teenage boy who uses a wheelchair, emphasizing that he lived a normal life.
 It was based on the books created by John Callahan.
 It aired during "Nick on CBS" beginning on September 14, 2002, and ended in November of that year.
 Unlike most Nicktoons, "Pelswick" is not rerun on NickSplat.

### [2] Kenn Scott

`doc_id: e1656334ba825ff67b5adcbca5e7db781cb3b07bd4f59b6e28ad56c78f3fc275`

Kenn Scott is a Toronto-based screenwriter noted for his work in children's programming and animation.
 Included amongst the many shows he has written for are "Ned's Newt", "Iggy Arbuckle", "Captain Flamingo", "Rescue Heroes", "Seven Little Monsters", "Pelswick", "Quads!
", "Delilah and Julius", "Dino Dan" and "Doki".
 His column "A Writer's Life" appears regularly in the magazine "Canadian Screenwriter".

### [3] Horseland (TV series)

`doc_id: 33874ae68bced29df696a1e9a4088c55881bb1fbbec59c2b664b41cec7eb0b34`

Horseland is an American animated series produced by DIC Entertainment.
 It is a comic mischief program following events in the lives of a group of children riding at Horseland, an equestrian school and stables.
 Their adventures include riding their horses and entering them in competitions to test their skill and friendships.
 The show premiered on September 16, 2006 as part of CBS's new Saturday morning cartoon block, "KOL Secret Slumber Party on CBS" (now "Cookie Jar TV").
 Concurrent with the series, the online virtual pet game that it was based upon was updated to complement the show by launching a new "Junior version" of the game based on the program and featuring its various characters and locations.
 After three seasons, the show was canceled on CBS on December 6, 2008.
 Reruns of "Horseland" then aired nationwide on the digital subchannel This TV; two episodes aired each weekend until September 2010.
 "Horseland" last aired as part of "Cookie Jar TV" on CBS.
 It has 7 books for the series related to the episodes which are available to be purchased online.

### [4] Project G.e.e.K.e.R.

`doc_id: 4668ae15118f0120cef2e0ea5f870d8446aaa92346d9981a49da18d17cde0655`

Project G.e.e.K.e.R. is an animated television series that premiered on CBS on September 14, 1996.
 It was created by Douglas TenNapel, creator of "Earthworm Jim", and Doug Langdale, the developer of "Earthworm Jim" the animated series, with original music by Shawn Patterson (main title theme by Terry Scott Taylor).
 TenNapel and Taylor also collaborated on the video games "The Neverhood", "Boombots" and "Skullmonkeys", and in 2005, re-united for the Nickelodeon cartoon "Catscratch".
 The series is rated TV-Y7-FV, and was produced by Columbia TriStar Television.

### [5] Scott McCord

`doc_id: cce3781ddc6e8c64ebcf3ef2e7bf8b1d15f1e813b9f85eec76620c2990094844`

William Scott McCord (born April 19, 1971) is a Canadian actor, voice actor, musician, and composer currently based in Brooklyn.
 A versatile performer, he has appeared in the films "16 Blocks", "Shoot 'Em Up", and the animated feature "The Nut Job".
 On television, he is best known for his voice over work in popular animated series.
 He plays Dan Kuso in "Bakugan Battle Brawlers", Tetsuya Watarigani in "Beyblade Metal Fusion", Owen and Trent in Fresh Animation's "Total Drama" series, Skull Boy in "Ruby Gloom", McGee in "Camp Lakebottom", and Jake in the animated TVOKids/Nickelodeon television series, "PAW Patrol".
 He is also Co-Artistic Director of Toronto-based Criminal Theatre, along with playwright and actor Rosa Laborde.
 In 2016, he won the Canada Screens Award for Best Performance in an Animated Series for his role as Squidgy on Guru's Justin Time.
 In 2002 he was nominated for a Dora Mavor Moore Award with Best Performance by a Male in Independent Theatre for his performance in Jacob Richmond's The Qualities of Zero.
 He has released two albums, the solo effort Blues For Sunshine (2009) and Scott McCord and the Bonafide Truth (2012).
 The latter is also the name of the soul/jazz/blues/rock eight piece band that was created for touring the first album.
 Scott McCord and the Bonafide Truth were nominated for Best Artist of the Year at the 2010 Maple Blues Awards.

### Generator output

**Answer:** November 2002

**Explanation given by the generator:** The document states that the animated series 'Pelswick' began airing on September 14, 2002, and ended in November of that year.

**Documents the generator cited (its own citations, not a verified list):**

* `d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817` - [1] Pelswick

---

## AG-0074

* `case_sha256`: `44d4d35ff2ad0298fa516e3b7b5ac70c3cc6af09364d8d547ec803c8a942e9bc`

**Question:** When did the animated series Kent Scott wrote end after beginning in September of 2002 on "Nick on CBS"?

**Context supplied to the generator (5 documents, in order):**

### [1] Pelswick

`doc_id: d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817`

Pelswick is an animated television series co-produced by Nelvana Limited and Suzhou Hong Ying Animation Corporation Limited in association with The Canadian Broadcasting Corporation and Nickelodeon.
 The series is about a teenage boy who uses a wheelchair, emphasizing that he lived a normal life.
 It was based on the books created by John Callahan.
 It aired during "Nick on CBS" beginning on September 14, 2002, and ended in November of that year.
 Unlike most Nicktoons, "Pelswick" is not rerun on NickSplat.

### [2] Kenn Scott

`doc_id: e1656334ba825ff67b5adcbca5e7db781cb3b07bd4f59b6e28ad56c78f3fc275`

Kenn Scott is a Toronto-based screenwriter noted for his work in children's programming and animation.
 Included amongst the many shows he has written for are "Ned's Newt", "Iggy Arbuckle", "Captain Flamingo", "Rescue Heroes", "Seven Little Monsters", "Pelswick", "Quads!
", "Delilah and Julius", "Dino Dan" and "Doki".
 His column "A Writer's Life" appears regularly in the magazine "Canadian Screenwriter".

### [3] Horseland (TV series)

`doc_id: 33874ae68bced29df696a1e9a4088c55881bb1fbbec59c2b664b41cec7eb0b34`

Horseland is an American animated series produced by DIC Entertainment.
 It is a comic mischief program following events in the lives of a group of children riding at Horseland, an equestrian school and stables.
 Their adventures include riding their horses and entering them in competitions to test their skill and friendships.
 The show premiered on September 16, 2006 as part of CBS's new Saturday morning cartoon block, "KOL Secret Slumber Party on CBS" (now "Cookie Jar TV").
 Concurrent with the series, the online virtual pet game that it was based upon was updated to complement the show by launching a new "Junior version" of the game based on the program and featuring its various characters and locations.
 After three seasons, the show was canceled on CBS on December 6, 2008.
 Reruns of "Horseland" then aired nationwide on the digital subchannel This TV; two episodes aired each weekend until September 2010.
 "Horseland" last aired as part of "Cookie Jar TV" on CBS.
 It has 7 books for the series related to the episodes which are available to be purchased online.

### [4] Project G.e.e.K.e.R.

`doc_id: 4668ae15118f0120cef2e0ea5f870d8446aaa92346d9981a49da18d17cde0655`

Project G.e.e.K.e.R. is an animated television series that premiered on CBS on September 14, 1996.
 It was created by Douglas TenNapel, creator of "Earthworm Jim", and Doug Langdale, the developer of "Earthworm Jim" the animated series, with original music by Shawn Patterson (main title theme by Terry Scott Taylor).
 TenNapel and Taylor also collaborated on the video games "The Neverhood", "Boombots" and "Skullmonkeys", and in 2005, re-united for the Nickelodeon cartoon "Catscratch".
 The series is rated TV-Y7-FV, and was produced by Columbia TriStar Television.

### [5] Pelswick

`doc_id: 4e275e57ddfca43286d6ed704fd10c51e36909d4ad12d1b8bda41bca34c41369`

Pelswick is an animated television series co-produced by Nelvana Limited and Suzhou Hong Ying Animation Corporation Limited in association with The Canadian Broadcasting Corporation and Nickelodeon.
 The series is about a teenage boy who uses a wheelchair, emphasizing that he lived a normal life.
 It was based on the books created by John Callahan.
 It aired during "Nick on CBS" beginning on September 14, 2002, and ended in December of that year.
 Unlike most Nicktoons, "Pelswick" is not rerun on NickSplat.

### Generator output

**Answer:** December 2002

**Explanation given by the generator:** The series 'Pelswick' began airing on September 14, 2002, and ended in December of the same year.

**Documents the generator cited (its own citations, not a verified list):**

* `d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817` - [1] Pelswick
* `5e275e57ddfca43286d6ed704fd10c51e36909d4ad12d1b8bda41bca34c41369` - not among the documents supplied above

---

## AG-0075

* `case_sha256`: `951cda47f1f8e4e47e754927ca45bd832ba3f03fe48fca78a01d10cc48a54da0`

**Question:** When did the animated series Kent Scott wrote end after beginning in September of 2002 on "Nick on CBS"?

**Context supplied to the generator (5 documents, in order):**

### [1] Pelswick

`doc_id: d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817`

Pelswick is an animated television series co-produced by Nelvana Limited and Suzhou Hong Ying Animation Corporation Limited in association with The Canadian Broadcasting Corporation and Nickelodeon.
 The series is about a teenage boy who uses a wheelchair, emphasizing that he lived a normal life.
 It was based on the books created by John Callahan.
 It aired during "Nick on CBS" beginning on September 14, 2002, and ended in November of that year.
 Unlike most Nicktoons, "Pelswick" is not rerun on NickSplat.

### [2] Kenn Scott

`doc_id: e1656334ba825ff67b5adcbca5e7db781cb3b07bd4f59b6e28ad56c78f3fc275`

Kenn Scott is a Toronto-based screenwriter noted for his work in children's programming and animation.
 Included amongst the many shows he has written for are "Ned's Newt", "Iggy Arbuckle", "Captain Flamingo", "Rescue Heroes", "Seven Little Monsters", "Pelswick", "Quads!
", "Delilah and Julius", "Dino Dan" and "Doki".
 His column "A Writer's Life" appears regularly in the magazine "Canadian Screenwriter".

### [3] Horseland (TV series)

`doc_id: 33874ae68bced29df696a1e9a4088c55881bb1fbbec59c2b664b41cec7eb0b34`

Horseland is an American animated series produced by DIC Entertainment.
 It is a comic mischief program following events in the lives of a group of children riding at Horseland, an equestrian school and stables.
 Their adventures include riding their horses and entering them in competitions to test their skill and friendships.
 The show premiered on September 16, 2006 as part of CBS's new Saturday morning cartoon block, "KOL Secret Slumber Party on CBS" (now "Cookie Jar TV").
 Concurrent with the series, the online virtual pet game that it was based upon was updated to complement the show by launching a new "Junior version" of the game based on the program and featuring its various characters and locations.
 After three seasons, the show was canceled on CBS on December 6, 2008.
 Reruns of "Horseland" then aired nationwide on the digital subchannel This TV; two episodes aired each weekend until September 2010.
 "Horseland" last aired as part of "Cookie Jar TV" on CBS.
 It has 7 books for the series related to the episodes which are available to be purchased online.

### [4] Project G.e.e.K.e.R.

`doc_id: 4668ae15118f0120cef2e0ea5f870d8446aaa92346d9981a49da18d17cde0655`

Project G.e.e.K.e.R. is an animated television series that premiered on CBS on September 14, 1996.
 It was created by Douglas TenNapel, creator of "Earthworm Jim", and Doug Langdale, the developer of "Earthworm Jim" the animated series, with original music by Shawn Patterson (main title theme by Terry Scott Taylor).
 TenNapel and Taylor also collaborated on the video games "The Neverhood", "Boombots" and "Skullmonkeys", and in 2005, re-united for the Nickelodeon cartoon "Catscratch".
 The series is rated TV-Y7-FV, and was produced by Columbia TriStar Television.

### [5] Scott McCord

`doc_id: cce3781ddc6e8c64ebcf3ef2e7bf8b1d15f1e813b9f85eec76620c2990094844`

William Scott McCord (born April 19, 1971) is a Canadian actor, voice actor, musician, and composer currently based in Brooklyn.
 A versatile performer, he has appeared in the films "16 Blocks", "Shoot 'Em Up", and the animated feature "The Nut Job".
 On television, he is best known for his voice over work in popular animated series.
 He plays Dan Kuso in "Bakugan Battle Brawlers", Tetsuya Watarigani in "Beyblade Metal Fusion", Owen and Trent in Fresh Animation's "Total Drama" series, Skull Boy in "Ruby Gloom", McGee in "Camp Lakebottom", and Jake in the animated TVOKids/Nickelodeon television series, "PAW Patrol".
 He is also Co-Artistic Director of Toronto-based Criminal Theatre, along with playwright and actor Rosa Laborde.
 In 2016, he won the Canada Screens Award for Best Performance in an Animated Series for his role as Squidgy on Guru's Justin Time.
 In 2002 he was nominated for a Dora Mavor Moore Award with Best Performance by a Male in Independent Theatre for his performance in Jacob Richmond's The Qualities of Zero.
 He has released two albums, the solo effort Blues For Sunshine (2009) and Scott McCord and the Bonafide Truth (2012).
 The latter is also the name of the soul/jazz/blues/rock eight piece band that was created for touring the first album.
 Scott McCord and the Bonafide Truth were nominated for Best Artist of the Year at the 2010 Maple Blues Awards.

### Generator output

**Answer:** November 2002

**Explanation given by the generator:** The document states that the animated series 'Pelswick' began airing in September 2002 and ended in November of the same year.

**Documents the generator cited (its own citations, not a verified list):**

* `d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817` - [1] Pelswick

---

## AG-0076

* `case_sha256`: `b08b688f3082f8968258b520c7096257ff548f8f9c7ea1b0021441a78e970652`

**Question:** When did the animated series Kent Scott wrote end after beginning in September of 2002 on "Nick on CBS"?

**Context supplied to the generator (5 documents, in order):**

### [1] Pelswick

`doc_id: d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817`

Pelswick is an animated television series co-produced by Nelvana Limited and Suzhou Hong Ying Animation Corporation Limited in association with The Canadian Broadcasting Corporation and Nickelodeon.
 The series is about a teenage boy who uses a wheelchair, emphasizing that he lived a normal life.
 It was based on the books created by John Callahan.
 It aired during "Nick on CBS" beginning on September 14, 2002, and ended in November of that year.
 Unlike most Nicktoons, "Pelswick" is not rerun on NickSplat.

### [2] Kenn Scott

`doc_id: e1656334ba825ff67b5adcbca5e7db781cb3b07bd4f59b6e28ad56c78f3fc275`

Kenn Scott is a Toronto-based screenwriter noted for his work in children's programming and animation.
 Included amongst the many shows he has written for are "Ned's Newt", "Iggy Arbuckle", "Captain Flamingo", "Rescue Heroes", "Seven Little Monsters", "Pelswick", "Quads!
", "Delilah and Julius", "Dino Dan" and "Doki".
 His column "A Writer's Life" appears regularly in the magazine "Canadian Screenwriter".

### [3] Horseland (TV series)

`doc_id: 33874ae68bced29df696a1e9a4088c55881bb1fbbec59c2b664b41cec7eb0b34`

Horseland is an American animated series produced by DIC Entertainment.
 It is a comic mischief program following events in the lives of a group of children riding at Horseland, an equestrian school and stables.
 Their adventures include riding their horses and entering them in competitions to test their skill and friendships.
 The show premiered on September 16, 2006 as part of CBS's new Saturday morning cartoon block, "KOL Secret Slumber Party on CBS" (now "Cookie Jar TV").
 Concurrent with the series, the online virtual pet game that it was based upon was updated to complement the show by launching a new "Junior version" of the game based on the program and featuring its various characters and locations.
 After three seasons, the show was canceled on CBS on December 6, 2008.
 Reruns of "Horseland" then aired nationwide on the digital subchannel This TV; two episodes aired each weekend until September 2010.
 "Horseland" last aired as part of "Cookie Jar TV" on CBS.
 It has 7 books for the series related to the episodes which are available to be purchased online.

### [4] Project G.e.e.K.e.R.

`doc_id: 4668ae15118f0120cef2e0ea5f870d8446aaa92346d9981a49da18d17cde0655`

Project G.e.e.K.e.R. is an animated television series that premiered on CBS on September 14, 1996.
 It was created by Douglas TenNapel, creator of "Earthworm Jim", and Doug Langdale, the developer of "Earthworm Jim" the animated series, with original music by Shawn Patterson (main title theme by Terry Scott Taylor).
 TenNapel and Taylor also collaborated on the video games "The Neverhood", "Boombots" and "Skullmonkeys", and in 2005, re-united for the Nickelodeon cartoon "Catscratch".
 The series is rated TV-Y7-FV, and was produced by Columbia TriStar Television.

### [5] Pelswick

`doc_id: 4e275e57ddfca43286d6ed704fd10c51e36909d4ad12d1b8bda41bca34c41369`

Pelswick is an animated television series co-produced by Nelvana Limited and Suzhou Hong Ying Animation Corporation Limited in association with The Canadian Broadcasting Corporation and Nickelodeon.
 The series is about a teenage boy who uses a wheelchair, emphasizing that he lived a normal life.
 It was based on the books created by John Callahan.
 It aired during "Nick on CBS" beginning on September 14, 2002, and ended in December of that year.
 Unlike most Nicktoons, "Pelswick" is not rerun on NickSplat.

### Generator output

**Answer:** December 2002

**Explanation given by the generator:** The series 'Pelswick' aired from September 14, 2002, and ended in December 2002.

**Documents the generator cited (its own citations, not a verified list):**

* `d76a213256081117314fdc06bca08902eb6e72238ada160cf8f9ba69dccba817` - [1] Pelswick
* `5e275e57ddfca43286d6ed704fd10c51e36909d4ad12d1b8bda41bca34c41369` - not among the documents supplied above

