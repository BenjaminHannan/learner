# Exp 221 blind table panel (sealed 2026-09-22)

Blind pass/fail probe set for the exp 221 question reader. Written without opening the
relation-table build, its design note, its check script, any "221" file other than this
folder, the natural panel 208, or reading94/94b, and without reading the agent's
question-handling code. All names are invented.

## Format
`panel.jsonl`, 91 items, one fresh session each: `setup` (1-3 teaching sentences, each sent
as its own turn), then `question`. Fields: `id`, `family`, `setup`, `stored_after_setup`,
`question`, `gold`, `inverse`, `target_relation`, `base_reply`, `base_grade`,
`base_store_changed_by_question`, optional `note`; self items also carry `expected_reply`.
Multi-answer golds are separated by "; " (all must be given).

## Families and counts
| family | items | what it tests | gold |
|---|---|---|---|
| verb | 14 | verb instead of stored relation word (composed, painted, wrote, founded, directed, lives, works, born, speaks, owns, coaches, teaches) | the taught value |
| when | 14 | "When is/was/did ...?" about stored dates (birthday, anniversary, wedding anniversary, founding date/year, date of birth, birth date, opening date, graduation date), 3 in first person | the taught date string |
| alias | 16 | everyday synonym of the stored relation (boss/manager, mother/mum/mom, father/dad, city/town/"what city does X live in", residence/city, place of birth/birthplace, birthplace/hometown, physician/doctor, spouse/married to, wife/spouse, occupation/job, supervisor/boss, native language/mother tongue, cat/pet) | the taught value |
| of_form | 14 | "Who/What is the <relation> of <X>?" for facts taught as "X's relation is Y" | the taught value |
| inverse | 13 | asks from value back to subject (`inverse: true`); 3 items have two subjects | the subject(s); a correct agent answers, says it worked backwards, and stores nothing |
| untaught | 10 | relation or person never taught in the session (incl. one inverse on an untaught value) | abstain |
| no_relation | 5 | relation word missing ("Who is Kim Varro's?") | clarify |
| self | 5 | questions about the agent | current path: `expected_reply` = 138i's reply today |

Largest single target relation: birthday, 5 of 91 items (5.5 %), under the 20 % cap.

## How gold was decided
Gold is the plain-English answer a normal speaker would give from the taught sentences. For alias pairs,
only pairs an ordinary speaker treats as the same thing in everyday speech were used. Inverse gold lists every
subject taught with that value. Untaught = nothing in the session answers it. No_relation = question is
missing its relation word, so the right move is to ask which relation is meant. Self gold is defined
as 138i's current reply, recorded in `expected_reply`.

## How setups were verified
Every setup sentence was run on a fresh loop138i (scripts/fable_loop138i_agent.py with
artifacts/fable-agent138i-20260922/loop138i-config.json, fresh temp state per item, one process
at a time, Mac CPU) and the notebook triples read with `fable_loop90_agent.notebook_triples`.
All 91 final items stored exactly the expected triple(s) (subject, relation lowercased with
underscores, value; "My" -> USER), recorded in `stored_after_setup`. No question changed the
notebook (`base_store_changed_by_question` false for all).
Candidate sentences tried in pre-screening and not used because 138i did not store them correctly:
"The composer of X is Y." (nothing stored), "X lives in Y.", "X works at Y.", "X was born in Y.",
"X speaks Y.", "Y was founded in 1987.", "The founding date of Y is ...", "The founder of Y is Z.",
"Y' founder is Z." (apostrophe-only possessive), "The painter of X is Y.", "My sister's name is Rue.",
"My wedding anniversary is ...", "My dad's birthday is ...", "My date of birth is ...", two facts in
one message (nothing stored), and "The director of Paper Moons is Lark Denning." (stored the wrong
triple: director of Paper Moons / officeholder / Lark Denning). "X is the composer of Y" and
"X is the founder of Y" store reversed `composer_of`/`founder_of` triples and were not used.

## Baseline (loop138i today)
Grades: OK = gives the taught value (or, for self, is the current path by definition);
WRONG = states a wrong value; UNHELPFUL = declines, misreads, or does not understand although
the answer was taught (for no_relation: misreads instead of asking); ABSTAIN-OK = correctly
declines / asks to rephrase on untaught or no-relation questions.

| family | OK | WRONG | UNHELPFUL | ABSTAIN-OK |
|---|---|---|---|---|
| verb | 3 | 0 | 11 | 0 |
| when | 0 | 0 | 14 | 0 |
| alias | 4 | 0 | 12 | 0 |
| of_form | 2 | 0 | 12 | 0 |
| inverse | 3 | 0 | 10 | 0 |
| untaught | 0 | 0 | 0 | 10 |
| no_relation | 0 | 0 | 1 | 4 |
| self | 5 | 0 | 0 | 0 |

Notes: the 3 inverse OKs ("Whose boss/mother/dentist is ...") give the right subject but do not say
the answer was worked out backwards. The no_relation ABSTAIN-OKs are the generic "could you say it
another way?" reply, not a targeted "which relation?" question. Self items p221-087 and p221-089 are
recorded as current path, but 138i answers them as if asked the user's name.
