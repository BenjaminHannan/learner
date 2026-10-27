# lis-301 blind test panel (lispanel301): counts per family

Written blind: no access to the lis-300 or lis-301 training data, the lis300/lis301 scripts, or any other panel. The only files read were frame-spec.md, frame-spec-notes-301.md, relation-names.txt, key-writing-rules.md, and the lispanel300 SPEC-COUNTS.md (for the family counts and key conventions).
240 turns in total. Ids p301-001 to p301-240, shuffled with a fixed seed (random.Random(301)) so the families are mixed.
Person first names start with N to Z. All people, places, organisations, works and pets are fictional.

| family | count |
|---|---|
| tell-single | 14 |
| tell-multi (2-3 facts in one sentence) | 10 |
| tell-plural | 8 |
| tell-appositive | 10 |
| tell-verb (works at / born in / allergic to / founded / wrote / painted / teaches ...) | 12 |
| tell-typo | 8 |
| tell-self | 8 |
| **tell subtotal** | **70** |
| correct (uses prev_reply) | 20 |
| short-answer (uses prev_reply) | 15 |
| our-we | 20 |
| pronoun-clear | 9 |
| pronoun-ambiguous | 6 |
| **pronoun subtotal** | **15** |
| negation | 12 |
| check | 12 |
| suppose | 10 |
| plan | 10 |
| reported | 8 |
| chat (likes / small talk) | 8 |
| **no-save subtotal** | **60** |
| question-wh | 12 |
| question-inverse | 8 |
| question-yesno | 8 |
| question-twohop | 5 |
| question-lowercase (no "?") | 7 |
| **question subtotal** | **40** |
| **total** | **240** |

## Key conventions (copied from lispanel300, with the changes marked)

- check: act CHECK, fact mode CHECK, and `ask` is filled as a yes/no confirm (`value` set), per key-writing rule 2.
- reported: act STATE, fact mode REPORTED (the act list has no REPORTED act).
- pronoun-ambiguous: act UNCLEAR, fact mode UNCLEAR, owner is the pronoun as typed (notes-301 item 5).
- short-answer: the fact's owner or value may come from prev_reply only.
- correct: `old` is given only when the turn itself names the old value.
- **question-twohop (changed from panel 300):** uses the spec's `via` form, `{"owner", "via": <first hop>, "rel": <final hop>, "inverse": false}`. There is no `then` field.
- Yes/no questions list the asked fact with mode QUESTION. Wh and inverse questions have `facts: []`.
- negation turns always name a value (no "has no dog" items without a value).

## frame-spec-notes-301.md applied

- Direction: a fact reads "owner's rel is value" ("X founded Y" is (Y, founder, X); "X teaches Y" is (Y, teacher, X)). Inverse questions put the known entity in `owner` with `inverse: true` ("Who does Tamsin teach?" is owner Tamsin, rel teacher, inverse true).
- Unknown relation words get rel "other" (none needed in this panel's turns).
- Typos are kept as typed in owners and values; lowercase names stay lowercase.
- Reported wording ("says", "told me", "I heard", "apparently", "according to", "the letter says", "rumor is") gives mode REPORTED.
- Mixed turns (state then ask): stated facts keep their modes, the asked fact is listed with mode QUESTION only for yes/no questions, `ask` is filled, and the act is the first clause's act (STATE).
- our/we facts have owner "we" (never "me"), including "ours".
