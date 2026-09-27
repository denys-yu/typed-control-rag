# Stage 13 - adjudication of the unresolved review proposals

Proposals prepared for researcher acceptance. No reviewer name is assigned to any decision, and this is not an independent human review.

Scope: the 23 unresolved cases inside the 18 unresolved-only questions. Decisions in the supplied package that this adjudication does not touch are carried over unchanged into `results/main_fault_review_proposals_v2.jsonl`.

## Rules applied

- **R-1**: Coexistence: two descriptors of nationality, occupation, genre, membership or office, award, or alternative name/translation for the same entity are not incompatible claims. Such a substitution alone does not make a context INCONSISTENT.
- **R-1b**: Non-exclusive plural or partial descriptors: statements about some members of a set, or about part of a work's subject matter, can both hold; they are not competing accounts.
- **R-2**: Ordinary reading: an answer supported by ordinary inference from an uncontested statement counts as supported; it need not appear verbatim, and a single uncontested descriptor may support a negative answer without an explicit denial.
- **R-3**: Singular attribution: different dates, quantities, locations, actors or single-valued category assignments for the same event, entity or definitional slot are competing accounts, unless the context supplies a temporal or entity distinction that resolves them.
- **R-4**: Identifying relationships: every relationship needed to identify the answer must be supported by the documents themselves.
- **G-1** **(new, proposed at stage 13)**: Identifier granularity (proposed clarification, new at stage 13): where a question asks for a specific designator and only a coarser descriptive identification of the same thing remains, the context is PARTIAL rather than OK.
- **K-1** **(new, proposed at stage 13)**: Kinship and spouse slots (proposed clarification, new at stage 13): distinct kinship or spouse terms filling the same relational slot between the same two people are competing accounts, unless the context supplies a basis for both holding.

R-1, R-1b, R-2, R-3 and R-4 restate standards already in force: the pilot annotation rules, the accepted evidence standard of the supplied package, and the distinctions the researcher set for this stage. G-1 and K-1 are new interpretive clarifications and are proposed, not preregistered and not previously accepted.

## Case decisions

### Q5 / INCONSISTENT - case `d7dd291bc3aad91b`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1
- evidence:
    - `1407a298776cfb1d1aee27e983ce2fa8c1e2c41390395bcedf5d8a7e7eba30e1` (gold, position 2, The Five Obstructions): "The Five Obstructions is a 2003 Danish documentary film directed by Lars von Trier"
    - `a641593530123e00478aa373715514afa7f372dd8552af6b6178c666e9e92027` (added, position 5, The Five Obstructions): "The film is conceived as a documentary, but incorporates lengthy sections of experimental films"
- reasoning: Genre labels coexist under R-1, and the edited copy itself still calls the film a documentary in its second sentence. The comparison the question needs - both films being documentaries - stays supported, so the context is OK and not the intended INCONSISTENT.
- competing reading: Treating 'science fiction film' as denying 'documentary film' would make this INCONSISTENT; that reading is rejected because R-1 governs genre and because the same paragraph reasserts the documentary framing.

### Q9 / INCONSISTENT - case `0aa5e2a8e52ddd13`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1
- evidence:
    - `3bac0deeb6d43fb7fab4d30af4a78647360afbde31c899ab08de877a59289aa3` (gold, position 3, Emilie de Ravin): "is an Australian actress"
    - `091e1a14a2bd7ddd6f317a0e709abebafd6161743a7582cdaec3dba4955c7976` (gold, position 1, Belle (Once Upon a Time)): "She is portrayed by Emilie de Ravin"
- reasoning: Australian and Canadian nationality descriptions coexist under R-1. The portrayal link and the Australian nationality both remain, so the expected answer is still supported: the context is OK.
- competing reading: Reading the two copies of the same article as competing accounts would give INCONSISTENT, but R-1 explicitly covers nationality substitutions.

### Q16 / CLEAN - case `9b823b75ce3fd010`

- proposed observed state: **OK** (was None); intended OK; matches intended: True
- proposed review status: **approved** (was pending)
- rules: R-2
- evidence:
    - `d369c381dffa43e7b46c5c58bb21987b543215157ba398aed24d468a20d69e10` (gold, position 1, George Stevens): "was an American film director, producer, screenwriter and cinematographer"
    - `335a2e1f6e09dd8b8fe81b0ae327dc8543fddb6c55a2e41e6416ee0cdff5b69d` (gold, position 5, Luc Besson): "is a French film director, screenwriter, and producer"
- reasoning: Under R-2 the ordinary reading of Besson's uncontested biography - French, and not listed as a cinematographer - supports the negative answer to the conjunction, exactly as a single counterexample decides a yes/no conjunction elsewhere in this review. The unmodified top-5 is therefore OK.
- competing reading: Requiring an explicit denial of American citizenship would leave this unresolved; that standard would make every negative yes/no question unanswerable and is rejected under R-2.

### Q16 / PARTIAL - case `096c32fe6ed96aec`

- proposed observed state: **OK** (was None); intended PARTIAL; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-2
- evidence:
    - `d369c381dffa43e7b46c5c58bb21987b543215157ba398aed24d468a20d69e10` (gold, position 1, George Stevens): "was an American film director, producer, screenwriter and cinematographer"
    - `1758709a06987b783ba546b5a4896e6abc559491cea1bbc31955a3790461bc34` (other, position 3, Shanna Besson): "the only child of French directors Maïwenn and Luc Besson"
- reasoning: Removing Besson's biography does not remove the counterexample: a retained paragraph still describes Luc Besson as a French director, which under R-2 supports the negative answer. Alternative evidence therefore keeps the chain complete, so the state is OK and not the intended PARTIAL.
- competing reading: Counting only the removed biography as admissible evidence would give PARTIAL; that contradicts the standing rule that removing annotated support does not by itself establish PARTIAL when alternative evidence remains.

### Q16 / EMPTY - case `d6e39bb167cb4d12`

- proposed observed state: **OK** (was None); intended EMPTY; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-2
- evidence:
    - `1758709a06987b783ba546b5a4896e6abc559491cea1bbc31955a3790461bc34` (other, position 3, Shanna Besson): "the only child of French directors Maïwenn and Luc Besson"
    - `7849321121523110fcb692cbed372ed2250efcddc48a237aa6dca17fd672a4d4` (added, position 5, Jean-Jacques Beineix): "The "cinéma du look" included the films of Luc Besson"
- reasoning: Both gold biographies are gone, but the retained Shanna Besson paragraph still describes Luc Besson as a French director, which is enough to decide the negative conjunction under R-2. The context is therefore OK, not the intended EMPTY.
- competing reading: If the incidental third-party mention were held too weak to carry the answer, the state would be PARTIAL; either way the intended EMPTY is not observed, so the question is excluded under both readings.

### Q16 / INCONSISTENT - case `15b9cbdb2f772cb3`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1, R-2
- evidence:
    - `374d29a29441af159e4bb38a96e68a0318bce7ae16bb9a0e4aa7c4cf3b108465` (added, position 4, Luc Besson): "is an American film director, screenwriter, and producer"
    - `335a2e1f6e09dd8b8fe81b0ae327dc8543fddb6c55a2e41e6416ee0cdff5b69d` (gold, position 5, Luc Besson): "is a French film director, screenwriter, and producer"
- reasoning: French and American descriptions coexist under R-1, and neither copy lists Besson as a cinematographer, so the negative answer survives the edit. The context is OK rather than INCONSISTENT.
- competing reading: Reading the duplicated article as competing accounts would give INCONSISTENT; R-1 governs nationality substitutions and is applied consistently across questions 9, 17, 61, 119 and here.

### Q17 / INCONSISTENT - case `043d97b53c88655c`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1
- evidence:
    - `de3cd16aa84f28b7f3ef04a0d341f239ee0ae8b241339e5b4ef3cf9949cccbc0` (gold, position 1, Edmund Leach): "was a British social anthropologist"
    - `e10bd9161164388b7558c07624378d5ad97ad901a89dd6059e0acce41e72e527` (gold, position 2, Alfred Gell): "was a British social anthropologist"
- reasoning: British and New Zealand descriptions coexist under R-1. Gell is still British and Leach is still described as British in the retained copy, so the shared-nationality answer remains supported: OK, not INCONSISTENT.
- competing reading: A same-slot competing-accounts reading would yield INCONSISTENT, but that reading is reserved for categories outside R-1.

### Q20 / CLEAN - case `d00b8bbe5204d9ac`

- proposed observed state: **OK** (was None); intended OK; matches intended: True
- proposed review status: **approved** (was pending)
- rules: R-2, R-4
- evidence:
    - `b35da0bf2926eb4d53a8fda59611439ba9bbcb7d6a26fa58a8e4fb2901e94396` (gold, position 2, Chilopsis): "Chilopsis is a monotypic genus of flowering plants containing the single species Chilopsis linearis"
    - `05956c9bd6bd03464f3e6d534ac6abbb3357a6d05a6a1bfc52605dba3628725e` (gold, position 1, Cunninghamia): "Cunninghamia is a genus of one or two living species"
- reasoning: One genus is explicitly monotypic with a single species; the other is explicitly not settled at one species. Under R-2 the ordinary reading picks out Chilopsis, and both identifying statements are present, so the unmodified top-5 is OK.
- competing reading: Treating 'one or two living species' as a possible second monotypic genus would leave the choice ambiguous; that reading is rejected because the phrase states the count is unsettled rather than asserting exactly one.

### Q23 / INCONSISTENT - case `3477b7b61747864c`

- proposed observed state: **INCONSISTENT** (was None); intended INCONSISTENT; matches intended: True
- proposed review status: **approved** (was pending)
- rules: K-1, R-3
- evidence:
    - `918ffc4afbad3b751127d944fd6dab0f7e8327790b8fe142b479f31ad8203972` (gold, position 2, Helen Walton): "was the wife of Wal-Mart and Sam's Club founder Sam Walton"
    - `fe5871cfc9e698729327e611e178b8e131bfc2318e48de24b2cfbbe82207e27c` (added, position 5, Helen Walton): "was the wife of Wal-Mart co-founder James "Bud" Walton"
    - `60ea38c960421d9a07877a2562def681f0a00c65647580ba77cb42a38f3d3ab9` (gold, position 1, Walton family): "the heritage of Bud and Sam Walton, who were the co-founders"
- reasoning: The two copies fill the same spouse slot of the same person with two different men, and the family paragraph shows Sam and Bud are distinct co-founders. No date, order or other distinction lets both hold, so the fact the question asks for is contested: INCONSISTENT, matching the intended state.
- competing reading: Successive marriages could in principle reconcile the two sentences, but nothing in the context suggests a second marriage; under K-1 a purely hypothetical reconciliation does not dissolve the conflict. If the researcher extends coexistence to spouse slots, this case becomes OK and question 23 leaves the matching set.

### Q30 / INCONSISTENT - case `e1625834b8a10b92`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1
- evidence:
    - `aaea2a0660b717b36f987714862d990a467e78addf35cc9039eee3437f9ef256` (gold, position 2, BraveStarr): "BraveStarr is a 1980s American Space Western animated series"
    - `67805cb9c4cad3fe783b38045e9c0f0b76175192154eacfb315a5b06a7631c24` (gold, position 1, Celebrity Home Entertainment): "they also released some material that was very famous at the time of its original release (such as "BraveStarr""
- reasoning: Genre and national-origin descriptors coexist under R-1, and the retained copy still supplies the American Space Western identification the question uses. The context is OK, not INCONSISTENT.
- competing reading: Reading 'Japanese fantasy' as excluding 'American Space Western' would give INCONSISTENT; that is exactly the genre case R-1 covers.

### Q40 / INCONSISTENT - case `3d5fa20142884b86`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1b
- evidence:
    - `2f21c11a1405b38bb4920f310226929ce5d2b7d8266fa899dcd91cdf6f856a7c` (gold, position 1, MS Kronprins Harald): "Several motor ships have borne the name Kronprins Harald"
    - `163aeaffc06005a0d743c55e9bd7dd00e551519765edfca50bc542f00e9fba23` (added, position 5, MS Kronprins Harald): "Several sailing yachts have borne the name Kronprins Harald"
- reasoning: Both sentences quantify over some vessels bearing the name; several motor ships and several sailing yachts can both have borne it, so under R-1b these are not competing accounts. The expected answer remains supported: OK.
- competing reading: If the sentence were read as an exhaustive classification of all vessels with that name, the two claims would conflict; the text does not make that exhaustive claim.

### Q54 / CLEAN - case `27f41409acfbb644`

- proposed observed state: **OK** (was None); intended OK; matches intended: True
- proposed review status: **approved** (was pending)
- rules: R-2, R-3
- evidence:
    - `8c165001ae6366f328d0b384bc9444cd123428bb0eaa2b273bd2358b3ed2e645` (gold, position 1, Boules at the 1900 Summer Olympics): "Boules was featured in the Summer Olympic Games unofficial programme in 1900"
    - `007af166adc626665aa262c5ee34e8d1ed87edfb2e548d680c8b274d0c29bb73` (gold, position 2, Summer Olympic Games): "this tradition began in 1904"
- reasoning: The two gold paragraphs place Boules in the 1900 Summer Olympics and date the gold/silver/bronze award tradition to 1904, which under R-2 supports the intended identification by ordinary inference. The Sweden paragraph concerns medals won in general, a different statement from the award tradition, so under R-3 no conflict arises.
- competing reading: Read strictly, 'right before medals started to be awarded' is a loose premise, since Sweden's paragraph implies medals existed in 1900. This is a looseness in the question's wording, not missing or contradictory evidence, and it is not repaired here.

### Q54 / INCONSISTENT - case `dd4d2c1ae951b7de`

- proposed observed state: **INCONSISTENT** (was None); intended INCONSISTENT; matches intended: True
- proposed review status: **approved** (was pending)
- rules: R-3
- evidence:
    - `8c165001ae6366f328d0b384bc9444cd123428bb0eaa2b273bd2358b3ed2e645` (gold, position 1, Boules at the 1900 Summer Olympics): "Boules was featured in the Summer Olympic Games unofficial programme in 1900"
    - `0579ed3b9c78c8d7c41ced8466356fbfafe7d391462a903c81e18a8af488c08c` (added, position 5, Boules at the 1900 Summer Olympics): "Boules was featured in the Winter Olympic Games unofficial programme in 1900"
    - `007af166adc626665aa262c5ee34e8d1ed87edfb2e548d680c8b274d0c29bb73` (gold, position 2, Summer Olympic Games): "The Winter Olympic Games were created due to the success of the Summer Olympics"
- reasoning: One featuring of Boules in 1900 is attributed to two different, explicitly distinct games. Under R-3 this is a competing account of the same event, and the retained paragraph shows the Winter Games are a separate later creation, so nothing resolves it: INCONSISTENT, matching the intended state.
- competing reading: Boules could in principle have appeared at both; the sentences describe the same single 1900 unofficial programme, and the context offers no second event.

### Q58 / INCONSISTENT - case `db9a7fefd83582c7`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1
- evidence:
    - `956472915c193e98c1feb05c0ca00b4c5cf139894fba2d894fed58df15d72b89` (gold, position 4, Philip Aaberg): "is an American pianist and composer"
    - `df2c16be75c8ba427b8a08dc146b342b5598f249db374610cda9004f16424350` (added, position 5, Philip Aaberg): "He gained international recognition through a series of successful piano recordings"
- reasoning: Occupations coexist under R-1, and the edited copy still describes piano recordings and solo piano work. The pianist-and-composer identification the question needs remains supported: OK.
- competing reading: Treating 'drummer and record producer' as replacing the original occupations would give INCONSISTENT; R-1 covers occupation substitutions.

### Q61 / INCONSISTENT - case `f74ee69dd23c0065`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1, R-3
- evidence:
    - `58b918dca153aee20a8c7cfcd48d89c6ca2dad550d773f5bff1331d76ce02fc5` (gold, position 3, Nikolai Morozov (figure skater)): "is a Russian figure skating coach and choreographer"
    - `282253fcbc5ace98e058104f3d003bcbc19f4df5a1defbdda71f29dbacd6ea5e` (added, position 5, Nikolai Morozov (figure skater)): "he competed with Olga Pershankova for Azerbaijan and with Ekaterina Gvozdkova for Russia"
- reasoning: Nationality descriptors coexist under R-1, and both copies state that he competed for Azerbaijan with this partner and for Russia with another - an entity distinction that under R-3 resolves the apparent tension. The Russian-coach identification remains supported: OK.
- competing reading: A bare same-slot reading would give INCONSISTENT, but here the context itself supplies the distinction that reconciles the two descriptions.

### Q88 / INCONSISTENT - case `dc27f6a383a13cca`

- proposed observed state: **INCONSISTENT** (was None); intended INCONSISTENT; matches intended: True
- proposed review status: **approved** (was pending)
- rules: K-1, R-3
- evidence:
    - `87d9951862ce949145a86f14186297cb2480c19fbf28ae47abc2a8a829d1e23f` (gold, position 1, Juan García Ábrego): "under the tutelage of his uncle Juan Nepomuceno Guerra"
    - `29afe7c3c7b4dedd9132a60b348e234f497b2f53a8c071d10c7bbd50861a3666` (added, position 5, Juan García Ábrego): "under the tutelage of his father-in-law Juan Nepomuceno Guerra"
    - `bf7cc45a2d77f15ea3f56ce04ef8c0e2f249101e1e4b7989e022d1fd38384f4b` (gold, position 2, Juan Nepomuceno Guerra): "who founded the Gulf Cartel"
- reasoning: The question asks for exactly this relationship, and the same relational slot between the same two people is filled with two different kinship terms. Under K-1 no basis for both holding appears in the context, so the requested fact is contested: INCONSISTENT, matching the intended state.
- competing reading: An uncle could also be a father-in-law through marriage within the family; nothing in the context supports that, so under K-1 the hypothetical does not dissolve the conflict. If the researcher extends coexistence to kinship terms, this case becomes OK and question 88 leaves the matching set.

### Q90 / PARTIAL - case `dc67c96400cdac6c`

- proposed observed state: **PARTIAL** (was None); intended PARTIAL; matches intended: True
- proposed review status: **approved** (was pending)
- rules: G-1, R-4
- evidence:
    - `b70206eff4795aff90e55dba6d1bd0e8741a02939cab07436d3b39fafe77821f` (gold, position 1, Onizuka Prop Wash Award): "named in memory of TPS graduate Ellison Onizuka who perished in the explosion of the Space Shuttle "Challenger" in 1986"
- reasoning: The award paragraph still identifies the man and the vehicle and year of the accident, but the mission designator the question asks for was carried by the removed biography and no longer appears anywhere. Under G-1 a coarser descriptive identification leaves the chain incomplete: PARTIAL, matching the intended state.
- competing reading: If 'the 1986 Challenger flight' is accepted as naming the mission, the state would be OK and question 90 would leave the matching set. This is the one decision in this stage that depends on the newly proposed granularity clarification G-1.

### Q98 / INCONSISTENT - case `f5cca161d98956ce`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1
- evidence:
    - `a14c1295b3b8dda8f12c8f46f3ce2ca3787de14f84ebc4ef86fc372998a060e7` (gold, position 2, William J. Crowe): "as the ambassador to the United Kingdom under President Bill Clinton"
    - `929401987cf2c0bbc9389a5efba0d11f474c7d9feec5c548e24c5fc7273e5c77` (gold, position 1, David Chanoff): "His collaborators have included; Augustus A. White, Joycelyn Elders, Đoàn Văn Toại, William J. Crowe"
- reasoning: An office held across administrations falls under the membership and office category of R-1: serving under one president does not exclude serving under another, and neither sentence fixes dates. The collaboration link and the Clinton answer remain supported: OK.
- competing reading: Reading the sentence as describing one indivisible tenure would give INCONSISTENT; R-1 covers offices and the text supplies no dates to fix a single tenure.

### Q108 / INCONSISTENT - case `0cd4946f8539c0a0`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1b
- evidence:
    - `687c79364d47607dc0a12ce16bf46dc0ec0bf1f649116a10c778a699142529a4` (gold, position 3, The Wailing (film)): "about a policeman who investigates a series of mysterious killings and illnesses"
    - `13837930533b9c76c7ecc69de88850f071f0f9ecb4eb714e04a58000d97023ef` (gold, position 2, Chun Woo-hee): "Her other notable films include "The Beauty Inside" (2015), "Love, Lies" (2016) and "The Wailing" (2016)"
- reasoning: A plot summary naming disappearances does not deny that illnesses are also investigated; under R-1b partial descriptions of a work's subject matter coexist. The retained paragraph still supplies the expected answer: OK.
- competing reading: Treating each synopsis as an exhaustive list of what is investigated would give INCONSISTENT; the text makes no exhaustiveness claim.

### Q119 / INCONSISTENT - case `a5d6515ab52f8f2d`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1
- evidence:
    - `b6e45c3763241bfcb1ec1e3e4475b8ff3017f36d95d9d06cf7d4032ccee4f683` (gold, position 2, Niccolò Paganini): "was an Italian violinist, violist, guitarist, and composer"
    - `bfc082dd0f098ef9907a1a276f998d9f790ab7dd5b5f6eb2977e840ee05e87b4` (gold, position 1, Caprice No. 5 (Paganini)): "Caprice No. 5 is one of 24 pieces composed by virtuoso violinist Niccolò Paganini"
- reasoning: Italian and French descriptions coexist under R-1, and the retained copy plus the Caprice paragraph still support the identification the question asks for: OK.
- competing reading: A same-slot competing-accounts reading would give INCONSISTENT, which R-1 excludes for nationality.

### Q132 / CLEAN - case `8b127e8321960202`

- proposed observed state: **OK** (was None); intended OK; matches intended: True
- proposed review status: **approved** (was pending)
- rules: R-2, R-4
- evidence:
    - `415a7a5e1c54c8aaebe222408596c364c9a8685d5a40a50ee4f920dacf07668b` (gold, position 2, Svíčková): "It is generally served with "houskové knedlíky" (bread dumplings)"
    - `ba2780b0df1031f8cf9fe6f26de76866eef7612b5c4c409202bdccb125066bdf` (gold, position 5, Knödel): "are boiled dumplings commonly found in Central European and East European cuisine"
    - `ba2780b0df1031f8cf9fe6f26de76866eef7612b5c4c409202bdccb125066bdf` (gold, position 5, Knödel): "Slovakia, and the Czech Republic"
- reasoning: The dish paragraph names bread dumplings and the dumpling paragraph describes boiled dumplings made from flour, bread or potatoes and popular in the Czech Republic. Linking them is ordinary reading under R-2, and both identifying statements are present, so the unmodified top-5 is OK.
- competing reading: Demanding an explicit statement that houskové knedlíky are Knödel would leave this unresolved; that standard would forbid ordinary cross-paragraph reading, which R-2 permits.

### Q132 / INCONSISTENT - case `9ef10efffb623a81`

- proposed observed state: **INCONSISTENT** (was None); intended INCONSISTENT; matches intended: True
- proposed review status: **approved** (was pending)
- rules: R-3
- evidence:
    - `ba2780b0df1031f8cf9fe6f26de76866eef7612b5c4c409202bdccb125066bdf` (gold, position 5, Knödel): "are boiled dumplings commonly found in Central European and East European cuisine"
    - `06f124da8aa5b028fa298d77e9a71570c220e415707144088c56957ea1c2eddc` (added, position 4, Knödel): "are deep-fried dumplings commonly found in Central European and East European cuisine"
- reasoning: Both sentences are definitional statements about the same dumpling category in the same slot, and preparation method is exactly the fact the question asks for. Under R-3 that is a competing account with no distinction to resolve it: INCONSISTENT, matching the intended state.
- competing reading: Individual dumplings can of course be fried as well as boiled, but the two sentences define the category itself, and the question asks how these dumplings are prepared.

### Q133 / INCONSISTENT - case `92bebdc534b87305`

- proposed observed state: **OK** (was None); intended INCONSISTENT; matches intended: False
- proposed review status: **rejected** (was pending)
- rules: R-1
- evidence:
    - `f8290e9bb656bd4577a5da3fef6c4d62213e70a81d2e3452b39a7485f5793d64` (gold, position 3, The Four (film)): ""Si Da Ming Bu" (四大名捕; "The Four Great Constables")"
    - `30658625db0280f5a5ead5971163eaa1f0e9c19845d4f06a0335c38945f4eae5` (gold, position 1, The Four III): "It is the final installment of the trilogy based on Woon Swee Oan's novel series"
- reasoning: Two English renderings of the same Chinese title are alternative names rather than incompatible claims, which R-1 covers. The expected translation remains supported by the retained copy: OK.
- competing reading: If a work's English title were treated as single-valued, the two renderings would conflict; translations of a Chinese title are routinely plural and the context asserts no official single rendering.

## Question-level result

| Category | Before | After |
| --- | ---: | ---: |
| matching quadruplet | 55 | 61 |
| unresolved only | 18 | 0 |
| known mismatch | 70 | 82 |

Questions that moved into the matching set: Q20, Q23, Q54, Q88, Q90, Q132.

Questions that moved from unresolved-only to a definite mismatch: Q5, Q9, Q16, Q17, Q30, Q40, Q58, Q61, Q98, Q108, Q119, Q133.

## Consistency inspection of decisions this stage did not reopen

The two new clarifications and the coexistence rule were checked against the decisions already supplied, limited to the cases they could touch:

- **All 55 INCONSISTENT cases of the previously matching questions** were listed by the property their edit changes. Their conflicts are dates, quantities, distances, venues, single-valued category assignments or explicit denials, none of which R-1 covers. Two were inspected in full because their property names looked like coexistence categories: Q15 (the edit also reassigns which national team claimed the 1976 title, a singular-event attribution under R-3) and Q110 (language of production, a single-valued production attribute). Neither decision changes.
- **The two questions whose only mismatch is a rejected INCONSISTENT case** (Q114 Reagan's earlier profession, Q115 a weaker numerical lower bound) were re-read. Both rejections follow R-1 and the compatible-lower-bounds distinction and stand unchanged.
- **The nine questions whose only mismatch is a CLEAN or PARTIAL case** were re-read to see whether G-1 applies. All of them turn on alternative evidence surviving a removal, not on identifier granularity; none changes.

No decision outside the 23 adjudicated cases is altered by this stage.

## Sample consequence

- matching quadruplets available: **61** (target 60)
- shortfall: **0**
- selection provisional: **False** - no question at or before the cut-off is unresolved-only, so membership is unambiguous given these proposals

Two of the decisions carrying the sample are the ones that rest on the new clarifications: Q23 and Q88 under K-1, and Q90 under G-1. If the researcher rejects K-1, questions 23 and 88 leave the matching set; if the researcher rejects G-1, question 90 leaves it. Each such rejection reduces the available set by one question, and the sample falls below 60 as soon as two of those three decisions are overturned.

Nothing here is frozen. The proposals still need researcher acceptance, and no reviewer name has been recorded for any of them.
