# Teach panel 229 (statement panel, blind)

Written 2026-09-22 by a Claude Opus agent working only from its brief. It did not read any code, relation tables, design docs, earlier panels or results.

File: `panel.jsonl`, 100 items. Fields: id, family, statement, expect (save/nosave), subject, relation_any (acceptable relation words), value, notes.
Seal: `SEAL.sha256.txt` (sha256 of panel.jsonl). Any edit after sealing voids the panel.

## Families
| family | count | save / nosave |
|---|---|---|
| verbs (works at/for, lives in/on, born in, studied at, teaches at, plays for, speaks, owns, coaches, founded, married to) | 13 | 13 / 0 |
| occupation ("is a vet", "works as a nurse", "does accounting for a living") | 12 | 12 / 0 |
| the_R_of_Y ("X is the R of Y" -> subject Y, relation R, value X) | 12 | 12 / 0 |
| a_R_of_Y ("X is a/an R of Y" -> subject Y, relation R, value X) | 12 | 12 / 0 |
| user ("I work at", "My sister is", "I'm a", subject "me") | 13 | 13 / 0 |
| tense_time (used to, now, currently, since, until, old, will, moving, no longer) | 12 | 9 / 3 |
| traps (category statements, opinion, feeling, hypothetical, negation, questions without "?", joke, unsure, role titles inside titles of works, wish, request) | 14 | 0 / 14 |
| harder (pronoun follow-ups, appositives, relative clause, two facts in one sentence) | 12 | 12 / 0 |

Totals: 83 save, 17 nosave.

## Rules followed
- Everyday English; all names, places, companies, teams, languages invented.
- relation_any lists are generous; an item scores correct if subject and value match and the stored relation is any listed word.
- For the user, subject is "me" (user / I also fine).
- Two-fact sentences: the first fact is the graded one; the second is in notes.
- Pronoun items: the previous sentence is in notes (the grader must feed it first).

## Judgement calls (explained per item in notes)
- Past facts ("used to live in", "worked at ... until 2019", "old dentist") are save, but only with a past-marked relation (former residence, former employer, old dentist). Storing them as the current relation counts as wrong.
- Future ("will start at", "is moving to next week") and "no longer works at" are nosave: storing the current relation would be false. A "future employer" / "former employer" note would be defensible; the default label is nosave.
- Owns / coaches / founded / member of / patient of / employee of / fan of: the inverse direction is equally correct (noted per item); relation_any is written for the listed subject only.
- Appositives ("My sister Ada Wrennick lives in Dunmere.") grade the main-clause fact; the side fact (me, sister, Ada Wrennick) is noted as also acceptable.
- "Varnholm is a city of Talvenia." is treated as a category statement (nosave) as the brief asked, although (Talvenia, city, Varnholm) is arguably storable.
- "Selma Ruud is a dentist." is an occupation, not someone's dentist.
