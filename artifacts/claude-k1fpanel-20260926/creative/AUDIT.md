# k1f creative panel: blind audit (counts only)

Input: `items.jsonl` (100 lines). Output: `items_v2.jsonl` (100 lines, same ids and order; unchanged lines byte-identical).
Reference sets read only for overlap checks: the dev set (40), k1a (60), k1c (100), k1-02d (100).

## Items checked

| Kind | Lead-in / teach turns | Items |
|---|---|---|
| idea | 1 lead-in turn | 35 |
| idea | 0 lead-in turns | 35 |
| uses_facts | 1 teach turn | 10 |
| uses_facts | 2 teach turns | 10 |
| uses_facts | 3 teach turns | 10 |
| **Total** | | **100** |

## Checks run on items.jsonl (items passed)

| Check | Passed |
|---|---|
| Valid JSON, one object per line | 100 / 100 |
| Exact 8 keys in spec order | 100 / 100 |
| ids kf-001..kf-100 in order | 100 / 100 |
| numbers, target, gold_expr all null | 100 / 100 |
| Kind and turn counts match the spec split | 100 / 100 |
| idea facts empty | 70 / 70 |
| uses_facts facts non-empty and well formed (owner/relation/value, relation in lowercase snake_case, owner is USER or named in the teach turns) | 30 / 30 |
| idea lead-in has no personal facts about the user | 35 / 35 |
| uses_facts facts match the teach turns (nothing extra, nothing missing that the request relies on) | 30 / 30 |
| Request clear and answerable in a short reply | 100 / 100 |
| Realistic casual chat style | 100 / 100 |
| Fictional names only (no real public figures, brands or titles) | 100 / 100 |
| Fact owner does not share a name with a person or pet in a reference set (exact, or the same name in another spelling or gender form) | 17 / 30 |
| Not a near-copy of a reference item (idea: same subject in any form; uses_facts: same occasion/request plus a shared key taught fact) | 42 / 100 (idea 29 / 70, uses_facts 13 / 30) |
| No subject duplicated inside the panel | 96 / 100 (2 pairs) |
| Every form used at least 4 times | pass (lowest form count: 5) |
| About half the requests name a count | 43 / 100 (37 give a number of items, 6 give a sentence or word limit) |

A further 20 unchanged items shared only part of a reference item (a setting, a frame or a fact with a different value) and were judged not to be near-copies.

## Fixes by type

| Fix type | Items fixed |
|---|---|
| Kind / turn counts | 0 |
| Personal facts in an idea lead-in | 0 |
| Facts / teach mismatch | 0 |
| Unclear or unanswerable request | 0 |
| Real names or brands | 0 |
| Duplicates within the panel | 2 pairs found; both resolved by near-copy fixes (0 extra edits) |
| Near-copies of dev or other-panel items | 63 |
| Style | 0 |
| **Total items changed** | **63** (idea 41, uses_facts 22); 37 lines byte-identical |

The 63 near-copy fixes break down like this:

- Subject or occasion-plus-fact match: 58 items (idea 41, uses_facts 17).
- Fact-owner name match: 13 items (10 exact, 3 spelling or gender variants). 8 of these also had a content match, so 5 were changed for the name only.

Number of items matching each reference set (an item can match more than one set):

| Reference set | Content match (idea / uses_facts) | Name match | Items matching (either) |
|---|---|---|---|
| dev set | 15 (11 / 4) | 4 | 18 |
| k1a | 18 (12 / 6) | 3 | 19 |
| k1c | 25 (16 / 9) | 5 | 27 |
| k1-02d | 10 (8 / 2) | 2 | 12 |

Every fix kept the item's kind, its number of turns and its form. When teach turns changed, the facts list was rewritten to match them exactly.

## Form spread (items_v2.jsonl; identical to items.jsonl)

| Group | Form | Items |
|---|---|---|
| Brainstorm list | names | 10 |
| Brainstorm list | gift ideas | 9 |
| Brainstorm list | activity ideas | 8 |
| Brainstorm list | party themes | 5 |
| Brainstorm list | ways to reuse something | 5 |
| Brainstorm list | plot twists | 5 |
| Short piece | short card or note | 9 |
| Short piece | four-line poem | 6 |
| Short piece | limerick | 6 |
| Short piece | slogan | 6 |
| Short piece | haiku | 6 |
| Short piece | toast | 5 |
| Short piece | two-sentence story | 5 |
| Fresh angle | chores fun | 5 |
| Fresh angle | cheaper weekend | 5 |
| Fresh angle | rainy-day plan | 5 |
| **Total** | | **100** (brainstorm 42, short pieces 43, fresh angles 15) |

## Final structural check on items_v2.jsonl

A Python check was re-run on items_v2.jsonl: 100 lines; ids kf-001..kf-100 in order; exact 8 keys; numbers, target and gold_expr all null; kinds idea 70 and uses_facts 30; idea turns 35 × 0 and 35 × 1; uses_facts turns 10 × 1, 10 × 2 and 10 × 3; idea facts empty 70 / 70; uses_facts facts non-empty and well formed 30 / 30; no item's kind or turn count changed.

**items_v2.jsonl passes every structural check.**
