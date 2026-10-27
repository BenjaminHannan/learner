# Correction panel 252 (TEST-ONLY)

TEST-ONLY. Builders must not open, print or tune on panel.jsonl or base138k.jsonl. This README is category-level on purpose: it quotes no item, name, wording or value.

## Families and counts (100 items)

| family | items | base_right | base_wrong_value | lowercase turns | unlisted wordings |
|---|---|---|---|---|---|
| verb_denial | 14 | 0 | 10 | 3 | 9 |
| possessive_denial | 10 | 2 | 7 | 2 | 6 |
| contextual_denial | 12 | 0 | 11 | 5 | 8 |
| contextual_correction | 14 | 0 | 14 | 3 | 10 |
| explicit_correction | 12 | 0 | 10 | 2 | 8 |
| unstored_denial | 8 | 8 | 0 | - | - |
| ambiguous | 6 | 6 | 0 | - | - |
| question_trap | 12 | 12 | 0 | - | - |
| control | 12 | 12 | 0 | - | - |

"Unlisted wording" means the turn's wording is not among the examples in the schema. "Lowercase" means the scored turn is typed all in lowercase. Both are counted only for the five cause families, as the schema asks.

## How base138k.jsonl was made

- Base: scripts/claude_loop138k_agent.py with artifacts/claude-merge138k-20260922/loop138k-config.json. It was treated as a black box.
- The runner is a batch copy of the director's dialog_nb.py: it makes the same calls and saves the reply and stored triples per dialog.
- Each dialog was run three times, each in its own fresh work dir: setup only, setup + turn, and setup + turn + followup. The stored triples at the end of each run give stored_after_setup, stored_after_turn and stored_after_followup. The replies come from the full run.
- Prefix determinism: the shared-prefix replies were compared across the three runs. There were 0 mismatches in the screening run and 0 in a separate fresh confirmation run of the final 100. The two runs also gave identical base rows.
- For every correction item, a separate fresh dialog taught the new value plainly. The base stored it under the same relation label used in expect_store.
- base_right and base_wrong_value come from a checker that implements the schema's scoring rules exactly.

## Relation labels used

boss, brother, city, coach, cousin, employer, friend, language, manager, place_of_birth, sister, spouse, teacher (13 labels, all as the base stores them).

## Acceptance checks (all met)

- Every setup teach was saved, and stated_facts == stored_after_setup.
- In the contextual families, the base's reply to the last setup turn contains exactly one stored value, and it is the disputed one.
- In ambiguous items, that reply states 2 or more values, or none.
- Cause families have at most 2 base_right items each (possessive_denial has 2; the others have 0).
- control is 12/12 base_right.
- Every cause family has at least 2 lowercase turns, and at least half of its items use unlisted wordings.
- Names are fictional and 1 to 4 words long.

## Candidates replaced

There were 120 candidates, and 100 were kept.
- 3 were dropped by rule:
  - 1 possessive_denial: it would have been the third base_right item in a cause family.
  - 1 ambiguous: the reply to its last setup turn stated exactly one value.
  - 1 control: the base did not get it right.
- 17 were surplus, beyond the family counts. They were dropped to balance relations and wordings. None of them broke a rule.
