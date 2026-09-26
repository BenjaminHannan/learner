# k1apanel creative: blind audit (counts only)

Input: items.jsonl (60 lines). Output: items_v2.jsonl (60 lines, same ids and order).
The 40-item dev set was read only to check for copies and near-copies.

## Items checked per kind

| Kind | Items |
|---|---|
| idea, 1 lead-in turn | 20 |
| idea, 0 lead-in turns | 20 |
| uses_facts, 1 teach turn | 6 |
| uses_facts, 2 teach turns | 8 |
| uses_facts, 3 teach turns | 6 |
| Total | 60 |

Fact entries: 76 in items.jsonl, 76 in items_v2.jsonl.

## Checks run on items.jsonl (items passed / items checked)

| # | Check | Passed |
|---|---|---|
| 1 | 60 lines, ids kc-01..kc-60 in order, exact 8 keys, numbers/target/gold_expr null | 60/60 |
| 2 | Kind and turn counts (idea 20 x 1 turn + 20 x 0 turns; uses_facts 6/8/6) | 60/60 |
| 3 | idea items have facts [] | 40/40 |
| 4 | uses_facts facts non-empty; entry keys owner/relation/value; owner is USER or a name in the turns; relation lowercase snake_case | 20/20 |
| 5 | idea lead-in sets the scene without personal facts about the user | 20/20 |
| 6 | 0-turn idea request is complete by itself | 20/20 |
| 7 | 1-turn idea request continues the lead-in naturally | 20/20 |
| 8 | facts match the teach turns (no unstated fact; no stated fact the request relies on is missing) | 19/20 |
| 9 | uses_facts request is one where a good answer uses the facts | 20/20 |
| 10 | Request clear and answerable in a short reply | 60/60 |
| 11 | Fictional names only (no real public figures, brands, or book/film/game titles) | 60/60 |
| 12 | No two items with the same subject; no near-duplicates within the panel | 60/60 |
| 13 | No copy or near-copy of any of the 40 dev items (same form and same scenario with details swapped, or a reused distinctive subject; a dev uses_facts item with its facts stripped counts) | 47/60 |
| 14 | Realistic casual chat style | 60/60 |
| 15 | Form spread: each listed form appears at least twice | 16/16 forms |

## Fixes by type

| Type | Issues fixed |
|---|---|
| Kind/turn counts | 0 |
| Personal facts in an idea lead-in | 0 |
| Facts/teach mismatch | 1 |
| Unclear or unanswerable request | 0 |
| Real names or brands | 0 |
| Duplicates within the panel | 0 |
| Near-copies of dev items | 13 |
| Style | 0 |
| **Total issues** | **14** |

Items changed: 13 (the facts/teach mismatch was in an item that was also a dev near-copy; one rewrite fixed both).
Items unchanged and byte-identical: 47.
Near-copy fixes by kind: idea 8 (6 with 1 lead-in turn, 2 with 0 turns); uses_facts 5 (1 with 1 teach turn, 4 with 2 teach turns).
No fix changed an item's kind, its number of turns, or its form. Total fact entries unchanged.

## Form spread (items_v2.jsonl)

| Group | Form | Items |
|---|---|---|
| Brainstorm list | names | 9 |
| Brainstorm list | party themes | 3 |
| Brainstorm list | ways to reuse something | 3 |
| Brainstorm list | plot twists | 3 |
| Brainstorm list | activity ideas | 3 |
| Brainstorm list | gift ideas | 3 |
| Short piece | four-line poem | 3 |
| Short piece | limerick | 4 |
| Short piece | toast | 4 |
| Short piece | slogan | 4 |
| Short piece | two-sentence story | 3 |
| Short piece | short card or note | 6 |
| Short piece | haiku | 4 |
| Fresh angle | chores fun | 3 |
| Fresh angle | cheaper weekend | 3 |
| Fresh angle | rainy-day plan | 2 |
| | **Total** | **60** |

Groups: brainstorm lists 24, short pieces 28, fresh angles 8.

## Re-check of items_v2.jsonl

Checks 1 to 15 re-run on items_v2.jsonl: 60/60 on every item-level check, 16/16 forms.

items_v2.jsonl passes every structural check (Python re-run): 60 lines, ids kc-01..kc-60 in order, exact keys, numbers/target/gold_expr null on all 60, idea 20 with 1 turn + 20 with 0 turns, uses_facts 6/8/6 with 1/2/3 turns, all 40 idea facts empty, all 20 uses_facts facts non-empty.
