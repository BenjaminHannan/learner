# Blind recount (all counts: shown; script recount.py in this folder)
Scope: dev + backref rows = 136; gold cards = 136 (all ASSERT/current, all named owners, none "me").
Person-naming relations (owner is always "me" in data): aunt, best_friend, boss, brother, classmate, colleague, cousin, daughter, father, friend, grandfather, grandmother, husband, landlord, mother, neighbour, nephew, niece, roommate, sister, son, teammate, uncle, wife. Pet/job/etc. relations are not treated as people.

| count | vector | LoRA |
|---|---|---|
| (a) matched named-owner cards M | 136 of 136 gold | 135 of 136 gold |
| (b) right owner | 119 of 136 | 131 of 135 |
| (b) wrong person | 17 of 136 | 4 of 135 |
| (b) owner "me" | 0 of 136 | 0 of 135 |
| (c) matched with rival named | 47 of 136 | 46 of 135 |
| (c) wrong person with rival named | 16 of 17 | 3 of 4 |
| (d) picked name mentioned more recently than gold owner | 8 of 16 | (LoRA: 3 of 3 rival-wrong) |
| (d) picked = most recently mentioned person of all | 6 of 16 | (LoRA: 1 of 3) |
| (e) LoRA right where vector wrong, among vector matched-with-rival | 14 of 47 | |

Extra: each reader had 1 emitted card unmatched (vector 1, LoRA 1). Vector wrong-person-with-rival picks: 14 of 16 picked names appear in seen text; 13 of 16 are persons of the dialogue.

Choices made:
- Persons of a dialogue = non-"me" owners plus values of person relations over all rows of that dialogue (any turn, any split), excluding the gold owner. Rival "named" = whole word, exact case, in seen text (user texts 1..N and bot replies 1..N-1, interleaved).
- Recency = character offset of last whole-word mention; unmentioned = -1. "Most recent of all" = picked offset equals maximum offset over all dialogue persons incl. gold owner (ties count; picked must be mentioned).
- Owner comparison lowercased and whitespace-collapsed; (b) does not require the value to match.
- (e): vector set = matched cards with rival named (47); LoRA judged on the same gold card (row, rel, state); a LoRA card missing counts as not right.
- LoRA reads restricted to modes ASSERT/CORRECT/FORMER.

## Manager's comparison with DIAGNOSIS.md (added 2026-09-28 by the manager, after the recount was written)
- Agrees exactly (shown): wrong person, vector 17 of 136 and LoRA 4 of 135; matched, LoRA 135 of 136; vector wrong person with a rival named: 16.
- Differs by definition (shown): the rival-named base is 47 (vector) / 46 (LoRA) here against 41 / 40 in DIAGNOSIS.md. Here, "seen text" = all user turns 1..N and bot replies 1..N-1. DIAGNOSIS.md searched the reader's actual prompt (build_prompt_hist) and counted names from dev rows only. LoRA wrong person with a rival named is 3 here against 2 there. The picked name is newer than the gold owner in 8 of 16 here, against 8 of 13 known people there. It is the newest person in 6 of 16 here, against 7 there. The conclusion does not change: the vector reader's wrong-person errors sit on rival-named rows, and "always newest" explains only about half of them.
