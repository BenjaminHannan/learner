# lis-300 blind test panel: counts per family

Written blind: no access to the lis-300 training data, lis300 scripts or any other panel.
240 turns in total. Ids p300-001 to p300-240, shuffled with a fixed seed so the families are mixed.

| family | count |
|---|---|
| tell-single | 14 |
| tell-multi (2-3 facts in one sentence) | 10 |
| tell-plural | 8 |
| tell-appositive | 10 |
| tell-verb (lives in / works at / born in / allergic to ...) | 12 |
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

## Key conventions where the spec leaves room (for the grader)

- check: act CHECK, fact mode CHECK, and `ask` is filled as a yes/no confirm (`value` set), per key-writing rule 2.
- reported: act STATE, fact mode REPORTED (the act list has no REPORTED act).
- pronoun-ambiguous: act UNCLEAR, fact mode UNCLEAR, owner is the pronoun as typed.
- short-answer: the fact's owner or value may come from prev_reply only.
- correct: `old` is given only when the turn itself names the old value.
- question-twohop: the spec has no two-hop form. `ask` holds the first hop (owner, rel), and an extra `"then": <rel>` field holds the second hop. Graders that ignore `then` score the first hop only.
- Yes/no questions list the asked fact with mode QUESTION. Wh and inverse questions have `facts: []`.
- negation turns always name a value (no "has no dog" items without a value).
