# Exp 229 RESULTS: relation-table TEACHES on 138i

**Result: FAIL (registered).** One mark missed: M1a. On the blind panel, 229 has 7 wrong-save items and 138i has 5; the bar was 229 <= 138i. The two new wrong saves (t229-009 "Silas Wendt owns Juniper Lane Books.", t229-011 "Fenella Okoro founded Tidewell Robotics.") are direction mismatches, not junk. 229 stored the table's canonical direction, (business, owner / founder, person). The panel's gold wants (person, owns / founded, business). Under the sealed scoring rule these are WRONG. Every other mark passed. Right saves on the panel went from 3 to 26 of 83. There were 0 new saves on nosave traps. The frozen suites moved exactly as predicted (1 reply-only move), and the sleep smoke passed.

Diagnosis note (one): the table stores ownership and founding in one direction only (on the business), and "inverses are never stored". The panel's gold for the verb sentences "X owns Y" and "X founded Y" names the person as the subject and has no alias for the business-side relation, so no store in the table's direction could score RIGHT. It is a conflict between the table's direction and the panel's gold, not a false fact. Still, it is registered as it scored.

Seal: artifacts/claude-tableteach229-20260922/SEAL.sha256.txt (7 files). It verified OK after all runs. The panel SEAL (artifacts/claude-teachpanel229-20260922/SEAL.sha256.txt) verified OK before the panel was opened. There were no post-seal edits and no re-runs.

## Marks

| mark | bar | 138i | 229 | verdict |
|---|---|---|---|---|
| M1a panel wrong-save items | 229 <= 138i | 5 | 7 | FAIL |
| M1b panel new saves on nosave items | 0 | - | 0 | PASS |
| M1c panel right saves (of 83 save items) | 229 >= 138i + 15 = 18 | 3 | 26 | PASS |
| M2 dev right, scored subset (47 save items) | >= 43 | 1 | 46 | PASS |
| M2 dev new wrong saves | 0 | - | 0 | PASS |
| M3 frozen suites: new WRONG / WRONG-WRITE / junk / lost OK | 0 / 0 / 0 / 0 | - | 0 / 0 / 0 / 0 | PASS |
| M3 moves outside the prediction | 0 | - | 0 (1 move, predicted) | PASS |
| M4 suites: write-change moves | 0 | - | 0 | PASS |
| M4 panel: items 138i saves with same triples | all | 8 | 8 of 8 | PASS |
| M4 dev: items 138i saves with same triples | all | 3 | 3 of 3 | PASS |
| M5 sleep smoke (installed / probes / wrong / taught / ow) | 1 / 5 of 5 / 0 / 50 of 50 / 0 | 1 / 5 / 0 / 50 / 0 | 1 / 5 / 0 / 50 / 0 | PASS |
| M6 median added time per item, panel / dev | <= 10 ms | - | -0.01 ms / -2.70 ms | PASS |
| Hygiene: runs < 25 min, load < 60, seal OK | yes | - | slowest 97 s (sleep smoke), max 1-min load 30.3 | PASS |

Literal M2 ("0 wrong saves", as the brief states it): 229 has 2 dev wrong-save items and 138i has the same 2. Both are inherited: d229-031, where 138i itself stores composer_of, and d229-048, which is in the cut family and where 138i stores officeholder. So a literal reading would fail both arms. This was declared before the seal.

## Every move

- Frozen suites (runs/frozen/): rt136 has 1 move. C115, "the capital of peru is lima.", is reply-only (MISSED -> MISSED, stored identical). The new reply: "I did not save that: I read it as peru's capital is lima, but peru does not look like a name." It was predicted. rt143, sessions152 and all 4 bench splits (800 items) had 0 moves. GATE clean.
- Panel, 229 vs 138i: 23 items newly RIGHT. There are 2 new WRONG (t229-009, t229-011, direction). 5 WRONG are identical in both arms (t229-035 author_of, t229-037 founder_of, t229-054 "Dr. Rosa Imrie" with the title kept, t229-085 officeholder junk on a nosave trap, t229-097 "It" founded_by). 3 are RIGHT in both. The full per-item table is below.
- Panel right saves by family (229 / 138i, of n): verbs 7/1 of 13; occupation 6/0 of 12; the_R_of_Y 4/0 of 12; a_R_of_Y 5/0 of 12; user 4/2 of 13; tense_time 0/0 of 9; harder 0/0 of 12.

## Predictions (ledger P229.x)

| prediction | outcome |
|---|---|
| P229.1 M1 | FALSE (M1a 7 > 5) |
| P229.2 M2 | TRUE (46 of 47, 0 new wrong) |
| P229.3 M3 | TRUE (only C115) |
| P229.4 M4 | TRUE |
| P229.5 M5 | TRUE |
| P229.6 M6 | TRUE |
| P229.7 panel right >= 50% of save items | FALSE (26 of 83 = 31%) |

## Deviations

- Cut family: the generic of_form "The R of X is Y." was cut before the seal. It turned rt136 nowrite traps into WRONG-WRITEs in the pilot. The table's own "The capital of {X} is {Y}"-style teach rows remain. Shouted all-caps turns are refused.
- EXT229 adds teach shapes that are not in the table's teach rows: occupation "X is a/an J" (from a closed job lexicon), "X works as a J", "Y is a/an R of X" and "X has a R called Y" (multi-valued relations only), "Y is my R", first-person forms, and a few verb forms. 217 had left "X is a J" out.
- M2 counts NEW wrong saves (see the literal M2 line above).
- Pilot-only flake evidence: the 138i stale-id bug (Exp 228's diagnosis) moved single bench items in some pilot runs. With a passive detector, 1 move in 3,400 bench items coincided exactly with a stale-id hit (bench121-4hop-142). The registered bench run had 0 moves, so no 5x item reruns were needed.
- Known limits seen on the panel, not fixed:
  - USER plus a multi-word relation ("I was born in", "I studied at") gets an honest not-saved reply.
  - "I'm ..." contractions are not read.
  - Multi-word jobs outside the lexicon ("pastry chef") are not read.
  - Some not-saved replies quote an awkward reading (for example "Lee Parrish now's city").
  - Saved replies use raw relation names ("educated at is").

## What it means

- The new teaching step lets the model save many more everyday facts it used to drop. On a fresh test set it saved 26 correct facts instead of 3, and on our own practice set 46 instead of 1.
- It did not make the model save anything on the trick sentences (negations, wishes, questions, jokes) that the old model left alone.
- It did not change any fact the old model already saved, it did not break the older test suites, and it is no slower.
- It failed its registered test on one mark. For "X owns Y" and "X founded Y", it saved the fact from the business's side ("Y's owner is X"), while the test's answer key wanted it from the person's side. So it counts as 2 extra wrong saves.

## What it doesn't mean

- It doesn't mean the model saved false facts in those 2 cases. The fact is the same, seen from the other side, but the registered rule counts it as wrong, and the mark stays failed.
- It doesn't mean the model understands English sentences in general. It only reads a fixed list of sentence shapes. It still misses pronouns ("She works at..."), sentences with two facts, time words ("used to", "since 2010"), and many phrasings. On the fresh panel it caught fewer than a third of the facts.
- It doesn't show that the bench flake is gone. The flake comes from a separate bug in the base (Exp 228). It just did not show up in this registered run.

## Files

- Agent scripts/claude_loop229_agent.py; runner and scorer scripts/claude_teach229_run.py; config loop229-config.json.
- Dev cases dev229.jsonl; PASSMARKS.md; design note design/v3/30-modes/229-tableteach-opus.md.
- Runs in runs/:
  - panel-{138i,229}.jsonl, panel-score.json
  - dev-{138i,229}.jsonl, dev-score.json
  - frozen/ and frozen.log
  - sleepsmoke-{229,138i}.json
  - load-uptime.txt

## Panel, every item (blind, 100 items)

| id | family | expect | 229 | 138i | statement | 229 stored / reply |
|---|---|---|---|---|---|---|
| t229-001 | verbs | save | RIGHT | - | Marta Quellen works at Brindle Logistics. | (Marta Quellen, employer, Brindle Logistics) |
| t229-002 | verbs | save | RIGHT | - | Osric Dahl works for Pennant Insurance. | (Osric Dahl, employer, Pennant Insurance) |
| t229-003 | verbs | save | RIGHT | - | Lucia Farnham lives in Coldwater Bay. | (Lucia Farnham, city, Coldwater Bay) |
| t229-004 | verbs | save | RIGHT | - | Tobiah Rask was born in Elmsford. | (Tobiah Rask, place_of_birth, Elmsford) |
| t229-005 | verbs | save | RIGHT | - | Wynn Carradine studied at Ashcombe University. | (Wynn Carradine, educated_at, Ashcombe University) |
| t229-006 | verbs | save | - | - | Priya Selwyn teaches at Hollin Grove Academy. | I did not save that: I read it as at Hollin Grove Academy's teacher is Priya Selwyn, but a |
| t229-007 | verbs | save | - | - | Dario Maske plays for the Greywater Hawks. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-008 | verbs | save | RIGHT | - | Anja Korbel speaks Vellish. | (Anja Korbel, language, Vellish) |
| t229-009 | verbs | save | WRONG | - | Silas Wendt owns Juniper Lane Books. | (Juniper Lane Books, owner, Silas Wendt) |
| t229-010 | verbs | save | - | - | Hedda Brun coaches the Millbrook Otters. | I did not save that: I read it as the Millbrook Otters's coach is Hedda Brun, but the Mill |
| t229-011 | verbs | save | WRONG | - | Fenella Okoro founded Tidewell Robotics. | (Tidewell Robotics, founder, Fenella Okoro) |
| t229-012 | verbs | save | RIGHT | RIGHT | Rufus Adair is married to Clementine Adair. | (Rufus Adair, spouse, Clementine Adair) |
| t229-013 | verbs | save | - | - | Jem Tolliver lives on Orchard Row. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-014 | occupation | save | RIGHT | - | Mara Holtby is a vet. | (Mara Holtby, occupation, vet) |
| t229-015 | occupation | save | RIGHT | - | Ivo Kestner works as a nurse. | (Ivo Kestner, occupation, nurse) |
| t229-016 | occupation | save | RIGHT | - | Talia Brenner is an architect. | (Talia Brenner, occupation, architect) |
| t229-017 | occupation | save | - | - | Gus Pemberton is a retired firefighter. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-018 | occupation | save | - | - | Oona Farquhar is a pastry chef. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-019 | occupation | save | RIGHT | - | Bram Castellan is a lawyer. | (Bram Castellan, occupation, lawyer) |
| t229-020 | occupation | save | RIGHT | - | Selma Ruud is a dentist. | (Selma Ruud, occupation, dentist) |
| t229-021 | occupation | save | RIGHT | - | Hector Vale works as a bus driver. | (Hector Vale, occupation, bus driver) |
| t229-022 | occupation | save | - | - | Nika Solberg is a high school math teacher. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-023 | occupation | save | - | - | Arlo Pinnock is an electrician by trade. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-024 | occupation | save | - | - | Fern Adeyemi is a software engineer at Loftwise. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-025 | occupation | save | - | - | Corin Mayhew does accounting for a living. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-026 | the_R_of_Y | save | RIGHT | - | Nils Aberdale is the director of Glasshaven Museum. | (Glasshaven Museum, director, Nils Aberdale) |
| t229-027 | the_R_of_Y | save | - | - | Petra Ilves is the mayor of Dunhollow. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-028 | the_R_of_Y | save | - | - | Omar Reyes-Kell is the owner of the Copper Kettle Diner. | I did not save that: I read it as the Copper Kettle Diner's owner is Omar Reyes-Kell, but  |
| t229-029 | the_R_of_Y | save | - | - | Harriet Voss is the principal of Elmbridge Primary. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-030 | the_R_of_Y | save | RIGHT | - | Ines Garrick is the CEO of Stillwater Energy. | (Stillwater Energy, chief_executive_officer, Ines Garrick) |
| t229-031 | the_R_of_Y | save | - | - | Ruben Achter is the captain of the Kilnworth Falcons. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-032 | the_R_of_Y | save | - | - | Mireille Dufort is the landlord of Tova Renwick. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-033 | the_R_of_Y | save | RIGHT | - | Ashby is the capital of Norrland Vale. | (Norrland Vale, capital, Ashby) |
| t229-034 | the_R_of_Y | save | RIGHT | - | Keir Lomond is the coach of Bexley Harriers. | (Bexley Harriers, coach, Keir Lomond) |
| t229-035 | the_R_of_Y | save | WRONG | WRONG | Sunita Varma is the author of The Glass Orchard. | (Sunita Varma, author_of, The Glass Orchard) |
| t229-036 | the_R_of_Y | save | - | - | Willa Crane is the editor of the Harbourside Gazette. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-037 | the_R_of_Y | save | WRONG | WRONG | Pavel Orlov is the founder of Moth & Lantern. | (Pavel Orlov, founder_of, Moth & Lantern) |
| t229-038 | a_R_of_Y | save | RIGHT | - | Ada Wrenley is a friend of Tova Rask. | (Tova Rask, friend, Ada Wrenley) |
| t229-039 | a_R_of_Y | save | RIGHT | - | Jonas Ekberg is a cousin of Lotte Ekberg. | (Lotte Ekberg, cousin, Jonas Ekberg) |
| t229-040 | a_R_of_Y | save | RIGHT | - | Mei Halloran is a colleague of Dev Patrick. | (Dev Patrick, colleague, Mei Halloran) |
| t229-041 | a_R_of_Y | save | - | - | Rolf Anker is a client of Sabine Morrell. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-042 | a_R_of_Y | save | - | - | Tess Marlowe is a student of Professor Ian Gault. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-043 | a_R_of_Y | save | RIGHT | - | Liam Castro is an uncle of Pia Castro. | (Pia Castro, uncle, Liam Castro) |
| t229-044 | a_R_of_Y | save | RIGHT | - | Karin Holt is a neighbor of Mateo Brisk. | (Mateo Brisk, neighbour, Karin Holt) |
| t229-045 | a_R_of_Y | save | - | - | Otto Venn is a member of the Larkspur Chess Club. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-046 | a_R_of_Y | save | - | - | Fiona Grady is a patient of Dr. Hal Osei. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-047 | a_R_of_Y | save | - | - | Bex Tamura is an employee of Norrow Freight. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-048 | a_R_of_Y | save | - | - | Aurelio Pinto is a fan of the Redbank Comets. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-049 | a_R_of_Y | save | - | - | Sadie Crum is a former teammate of Jo Ellery. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-050 | user | save | RIGHT | - | I work at Veltrane. | (USER, employer, Veltrane) |
| t229-051 | user | save | RIGHT | RIGHT | My sister is Ada Wrennick. | (USER, sister, Ada Wrennick) |
| t229-052 | user | save | RIGHT | - | I live in Tamsford. | (USER, city, Tamsford) |
| t229-053 | user | save | - | - | I was born in Kellbridge. | I did not save that: I read it as your place of birth is Kellbridge, but I could not store |
| t229-054 | user | save | WRONG | WRONG | My dentist is Dr. Rosa Imrie. | (USER, dentist, Dr. Rosa Imrie) |
| t229-055 | user | save | - | - | I'm a paramedic. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-056 | user | save | - | - | I speak Dunnish and Vellish. | I did not save that: I read it as your language is Dunnish and Vellish, but Dunnish and Ve |
| t229-057 | user | save | - | - | My dog's name is Pickle. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-058 | user | save | - | - | I'm married to Theo Lark. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-059 | user | save | - | - | I studied at Carrow College. | I did not save that: I read it as your educated at is Carrow College, but I could not stor |
| t229-060 | user | save | RIGHT | RIGHT | My birthday is November 2. | (USER, birthday, November 2) |
| t229-061 | user | save | - | - | I play for the Southmere Kestrels. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-062 | user | save | - | - | I drive a Kessler Alto. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-063 | tense_time | save | - | - | Kim Ashgrove used to live in Norrby. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-064 | tense_time | save | - | - | Lee Parrish now lives in Bergholt. | I did not save that: I read it as Lee Parrish now's city is Bergholt, but Lee Parrish now  |
| t229-065 | tense_time | nosave | - | - | Anya Frost will start at Merrow Bank next month. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-066 | tense_time | save | - | - | Joel Maddox was born in Farrowby in 1979. | I did not save that: I read it as Joel Maddox's place of birth is Farrowby in 1979, but Fa |
| t229-067 | tense_time | save | - | - | Rhona Kitt currently works at Pinefold Studio. | I did not save that: I read it as Rhona Kitt currently's employer is Pinefold Studio, but  |
| t229-068 | tense_time | save | - | - | Dmitri Sallow worked at Hesketh Mills until 2019. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-069 | tense_time | save | - | - | Since March, Coraline Ebb has been living in Wexmoor. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-070 | tense_time | save | - | - | Theo Varga's old dentist was Mira Kell. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-071 | tense_time | nosave | - | - | Brynn Coley is moving to Saltmarsh next week. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-072 | tense_time | save | - | - | Owain Price is still with Harrowgate Rail. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-073 | tense_time | save | - | - | Petra Owusu has lived in Calder Heights since 2010. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-074 | tense_time | nosave | - | - | Kim Hadley no longer works at Lumen Dairy. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-075 | traps | nosave | - | - | Varnholm is a city of Talvenia. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-076 | traps | nosave | - | - | Wexmoor is lovely in the spring. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-077 | traps | nosave | - | - | I'm so tired of Hollin Ward's emails. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-078 | traps | nosave | - | - | If Kim Ostrander lived in Farrowby, she'd be a lot happier. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-079 | traps | nosave | - | - | Kim Ostrander doesn't live in Farrowby. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-080 | traps | nosave | - | - | who is Tova Renwick's landlord | I don't know anyone called Tova Renwick. |
| t229-081 | traps | nosave | - | - | where does Pell Harker work | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-082 | traps | nosave | - | - | My boss is basically a dragon lol | That sounds like a description, not a name, so I didn't save it. What is your boss's name? |
| t229-083 | traps | nosave | - | - | Grelling is a town. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-084 | traps | nosave | - | - | Maybe Dex Porter works at Cindervale, I'm not sure. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-085 | traps | nosave | WRONG | WRONG | The Mayor of Dunhollow is such a good podcast. | (Mayor of Dunhollow, officeholder, such a good podcast) |
| t229-086 | traps | nosave | - | - | I just finished The Doctor of Wexmoor, what a book! | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-087 | traps | nosave | - | - | I wish my sister lived in Tamsford. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-088 | traps | nosave | - | - | tell me who owns Fenwick Cafe | I did not save that: I read it as Fenwick Cafe's owner is tell me who, but tell me who doe |
| t229-089 | harder | save | - | - | She works at Coldharbour Press. | I did not save that: I read it as She's employer is Coldharbour Press, but She does not lo |
| t229-090 | harder | save | - | - | His dentist is Rhea Salk. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-091 | harder | save | - | - | My sister Ada Wrennick lives in Dunmere. | I did not save that: I read it as My sister Ada Wrennick's city is Dunmere, but My sister  |
| t229-092 | harder | save | - | - | Our neighbour, Gil Farris, teaches at Hollowmere College. | I did not save that: I read it as at Hollowmere College's teacher is Our neighbour, Gil Fa |
| t229-093 | harder | save | - | - | Ines Morrow lives in Ketterby and works at Salt & Sparrow. | I did not save that: I read it as Ines Morrow lives in Ketterby and's employer is Salt & S |
| t229-094 | harder | save | - | - | Tomas Weir's wife is Ada Weir and his son is Pip Weir. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-095 | harder | save | - | - | My boss, Rhiannon Tate, was born in Glenholm. | I did not save that: I read it as My boss, Rhiannon Tate,'s place of birth is Glenholm, bu |
| t229-096 | harder | save | - | - | He plays for the Fenmoor Badgers. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-097 | harder | save | WRONG | WRONG | It was founded by Anya Petrell. | (It, founded_by, Anya Petrell) |
| t229-098 | harder | save | - | - | Both Rosa and Ilse Kimura work at Pennant Insurance. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-099 | harder | save | - | - | Dr. Hana Leroux, who's my dentist, lives in Crale. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| t229-100 | harder | save | - | - | Otto Venn, the guy from my book club, owns a bakery called Rye & Rise. | I did not save that: I read it as a bakery called Rye & Rise's owner is Otto Venn, the guy |

## Dev, every item (77 items)

| id | family | expect | 229 | 138i | statement | 229 stored / reply |
|---|---|---|---|---|---|---|
| d229-001 | occupation | save | RIGHT | - | Mirel Oskan is a vet. | (Mirel Oskan, occupation, vet) |
| d229-002 | occupation | save | RIGHT | - | Tavi Brune is an electrician. | (Tavi Brune, occupation, electrician) |
| d229-003 | occupation | save | RIGHT | - | Corra Wend works as a librarian. | (Corra Wend, occupation, librarian) |
| d229-004 | occupation | save | RIGHT | - | Ilsa Porrow is a software engineer. | (Ilsa Porrow, occupation, software engineer) |
| d229-005 | occupation | save | RIGHT | - | I am a nurse. | (USER, occupation, nurse) |
| d229-006 | occupation | save | RIGHT | - | Bex Hallam works as a sound mixer. | (Bex Hallam, occupation, sound mixer) |
| d229-007 | occupation | save | RIGHT | - | Doran Vess is a Teacher. | (Doran Vess, occupation, teacher) |
| d229-008 | verb | save | RIGHT | - | Anya Colt composed Silver Fen. | (Silver Fen, composer, Anya Colt) |
| d229-009 | verb | save | RIGHT | - | Grey Lantern was painted by Oriel Sand. | (Grey Lantern, painter, Oriel Sand) |
| d229-010 | verb | save | RIGHT | - | Pell Harte wrote Quiet Tide. | (Quiet Tide, author, Pell Harte) |
| d229-011 | verb | save | RIGHT | RIGHT | Marrow Hill was written by Jessa Crane. | (Marrow Hill, written_by, Jessa Crane) |
| d229-012 | verb | save | RIGHT | - | Hollis Vane founded Brightmoor Works. | (Brightmoor Works, founder, Hollis Vane) |
| d229-013 | verb | save | RIGHT | - | Tamsin Rook directed Low Harbour. | (Low Harbour, director, Tamsin Rook) |
| d229-014 | verb | save | RIGHT | - | Kell Arden teaches Pim Farrow. | (Pim Farrow, teacher, Kell Arden) |
| d229-015 | verb | save | RIGHT | - | Rhosyn Tell coaches Bray Minton. | (Bray Minton, coach, Rhosyn Tell) |
| d229-016 | verb | save | RIGHT | - | Fenna Lusk moved to Carrowby. | (Fenna Lusk, city, Carrowby) |
| d229-017 | verb | save | RIGHT | - | Oswin Pale is from Tarnmouth. | (Oswin Pale, hometown, Tarnmouth) |
| d229-018 | verb | save | RIGHT | - | Juda Merrin studied at Kestle College. | (Juda Merrin, educated_at, Kestle College) |
| d229-019 | verb | save | RIGHT | - | Lio Barrent is 34 years old. | (Lio Barrent, age, 34) |
| d229-020 | verb | save | RIGHT | - | Senna Quail likes archery. | (Senna Quail, hobby, archery) |
| d229-021 | verb | save | RIGHT | - | Nim Hatherly owns Biscuit. | (Biscuit, owner, Nim Hatherly) |
| d229-022 | verb | save | RIGHT | - | Vosk Mill is based in Durnhaven. | (Vosk Mill, headquarters_location, Durnhaven) |
| d229-023 | verb | save | RIGHT | - | Cade Ormond was born on 12 March 1988. | (Cade Ormond, date_of_birth, 12 March 1988) |
| d229-024 | verb | save | RIGHT | - | The Ember Gate was designed by Lark Denholm. | (The Ember Gate, designer, Lark Denholm) |
| d229-025 | verb | nosave | - | - | Wren Asher invented the Tallow Lamp. | I did not save that: I read it as the Tallow Lamp's inventor is Wren Asher, but the Tallow |
| d229-026 | verb | save | RIGHT | - | I live in Pellford. | (USER, city, Pellford) |
| d229-027 | verb | save | RIGHT | - | I grew up in Ashcombe. | (USER, hometown, Ashcombe) |
| d229-028 | verb | save | RIGHT | - | I speak Norrish. | (USER, language, Norrish) |
| d229-029 | inverted | save | RIGHT | - | Sorrel Vane is the boss of Kip Dunmore. | (Kip Dunmore, boss, Sorrel Vane) |
| d229-030 | inverted | save | RIGHT | - | Lenna Ross is the mother of Theo Brand. | (Theo Brand, mother, Lenna Ross) |
| d229-031 | inverted | save | WRONG | WRONG | Arlo Fisk is the composer of Blue Rook. | (Arlo Fisk, composer_of, Blue Rook) |
| d229-032 | inverted | save | RIGHT | - | Mab Kettering is the CEO of Orrin Mills. | (Orrin Mills, chief_executive_officer, Mab Kettering) |
| d229-033 | inverted | save | RIGHT | - | Harrow is the capital of Velmark. | (Velmark, capital, Harrow) |
| d229-034 | inverted | save | RIGHT | - | Tully Brisk is the manager of Nessa Gale. | (Nessa Gale, boss, Tully Brisk) |
| d229-035 | inverted | save | RIGHT | - | Ivo Stane is Mira Cole's doctor. | (Mira Cole, doctor, Ivo Stane) |
| d229-036 | inverted | save | RIGHT | - | Pella Vey is my sister. | (USER, sister, Pella Vey) |
| d229-037 | inverted | save | RIGHT | - | Dunstan Roe is my Boss. | (USER, boss, Dunstan Roe) |
| d229-038 | inverted | save | RIGHT | - | Oma Treadwell is the Mum of Ciaran Lusk. | (Ciaran Lusk, mother, Oma Treadwell) |
| d229-039 | a_r_of | save | RIGHT | - | Rosa Keeling is a grandma of Odile Verrin. | (Odile Verrin, grandmother, Rosa Keeling) |
| d229-040 | a_r_of | save | RIGHT | - | Juno Holt is a Friend of Marlo Quill. | (Marlo Quill, friend, Juno Holt) |
| d229-041 | a_r_of | save | RIGHT | - | Pia Lundry is a coworker of Tomas Aske. | (Tomas Aske, colleague, Pia Lundry) |
| d229-042 | a_r_of | save | RIGHT | - | Edda Crane is a cousin of Bran Tolley. | (Bran Tolley, cousin, Edda Crane) |
| d229-043 | a_r_of | save | RIGHT | - | Kit Farrow is a neighbor of Lyle Penn. | (Lyle Penn, neighbour, Kit Farrow) |
| d229-044 | has_a | save | RIGHT | - | Brin Tallis has a dog called Moss. | (Brin Tallis, dog, Moss) |
| d229-045 | has_a | save | RIGHT | - | I have a sister named Ottilie. | (USER, sister, Ottilie) |
| d229-046 | of_form_cut | save | - | - | The painter of Blue Orchid is Tilda Varr. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-047 | of_form_cut | save | - | - | The founder of Crestwell Books is Amos Reiner. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-048 | of_form_cut | save | WRONG | WRONG | The coach of Dray Collins is Hester Moon. | (coach of Dray Collins, officeholder, Hester Moon) |
| d229-049 | of_form_cut | save | - | - | The grandma of Wes Tarrant is Ina Tarrant. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-050 | negation | nosave | - | - | Mirel Oskan is not a vet. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-051 | negation | nosave | - | - | Sorrel Vane isn't the boss of Kip Dunmore. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-052 | tense | nosave | - | - | Tavi Brune used to be an electrician. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-053 | tense | nosave | - | - | Tavi Brune was a baker. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-054 | pronoun | nosave | - | - | She is a vet. | I did not save that: I read it as She's occupation is vet, but She does not look like a na |
| d229-055 | pronoun | nosave | - | - | He is the boss of Kip Dunmore. | I did not save that: I read it as Kip Dunmore's boss is He, but He does not look like a na |
| d229-056 | appositive | nosave | - | - | My sister Ada Crane lives in Leeby. | I did not save that: I read it as My sister Ada Crane's city is Leeby, but My sister Ada C |
| d229-057 | two_facts | nosave | - | - | Corra Wend is a nurse and lives in Hollin. | I did not save that: I read it as Corra Wend is a nurse and's city is Hollin, but Corra We |
| d229-058 | two_facts | nosave | - | - | Fenna Lusk moved to Carrowby with Dale Hart. | I did not save that: I read it as Fenna Lusk's city is Carrowby with Dale Hart, but Carrow |
| d229-059 | hearsay | nosave | - | - | Jona Pike said Mirel Oskan is a vet. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-060 | hypothetical | nosave | - | - | If Mirel Oskan is a vet, she can help. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-061 | not_job | nosave | - | - | Moss is a dog. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-062 | not_job | nosave | - | - | Tavi Brune is a genius. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-063 | not_job | nosave | - | - | Corra Wend is a friend. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-064 | single_a_of | nosave | - | - | Lenna Ross is a mother of Theo Brand. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-065 | unknown_rel | nosave | - | - | Mab Kettering is the landlord of Orrin Mills. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-066 | value_type | nosave | - | - | Senna Quail likes Tom Arden. | I did not save that: I read it as Senna Quail's hobby is Tom Arden, but Tom Arden does not |
| d229-067 | value_type | nosave | - | - | Lio Barrent is many years old. | I did not save that: I read it as Lio Barrent's age is many, but many is not a number. |
| d229-068 | modal | nosave | - | - | Mirel Oskan might be a vet. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-069 | chitchat | nosave | - | - | It is a lovely day. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-070 | chitchat | nosave | - | - | That is the end of the story. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-071 | future | nosave | - | - | Tavi Brune will be a pilot. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-072 | pronoun | nosave | - | - | They moved to Carrowby. | I did not save that: I read it as They's city is Carrowby, but They does not look like a n |
| d229-073 | wish | nosave | - | - | Kell Arden hopes to be a pilot. | I do not know that from what you taught me. I have no record of it, so I will not guess. I |
| d229-074 | reteach | nosave | - | - | Tully Brisk is the boss of Kip Dunmore. | I have Kip Dunmore's boss as Sorrel Vane. Do you want me to change it to Tully Brisk? |
| d229-075 | multi_add | save | RIGHT | - | Juno Holt is a friend of Marlo Quill. | (Marlo Quill, friend, Juno Holt) |
| d229-076 | alias_canonical | save | RIGHT | - | Wyn Carrow is a co-worker of Esme Dale. | (Esme Dale, colleague, Wyn Carrow) |
| d229-077 | alias_canonical | save | RIGHT | - | Nell Ashby is a Grandma of Rory Pike. | (Rory Pike, grandmother, Nell Ashby) |