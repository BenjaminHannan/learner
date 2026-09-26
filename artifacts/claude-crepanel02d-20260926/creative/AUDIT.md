# AUDIT: crepanel02d (blind, counts only)

Auditor: blind audit session, 2026-09-26. This file gives counts only. It does not quote, paraphrase or describe any item.

Input: `items.jsonl` (100 lines). Output: `items_v2.jsonl` (100 lines, same ids and order; 51 lines byte-identical, 49 lines changed).
Reference sets read only for the near-copy check: dev set (40 items), escrow-k1a panel (60 items), escrow-k1c panel (100 items).

## Items checked per kind

| kind | items | 0 lead-in / teach turns | 1 | 2 | 3 |
|---|---|---|---|---|---|
| idea | 70 | 35 | 35 | - | - |
| uses_facts | 30 | - | 10 | 10 | 10 |
| total | 100 | | | | |

## Checks run on items.jsonl (items passed / items checked)

| check | passed |
|---|---|
| Valid JSON, exact 8 keys in order, ids kd-001..kd-100 in order | 100 / 100 |
| numbers, target, gold_expr all null | 100 / 100 |
| Kind and turn counts (idea 35 x 0 + 35 x 1; uses_facts 10 x 1, 10 x 2, 10 x 3) | 100 / 100 |
| idea facts empty; uses_facts facts non-empty, keys owner/relation/value, relation lowercase snake_case | 100 / 100 |
| Idea lead-in sets the scene with no personal facts about the user (1-turn idea items) | 35 / 35 |
| uses_facts facts match the teach turns (nothing unstated, nothing relied on missing) | 30 / 30 |
| Request clear and answerable in a short reply | 100 / 100 |
| Realistic casual chat style | 100 / 100 |
| Fictional names only (no real public figures, brands or titles) | 100 / 100 |
| Unique subject within the panel (no in-panel duplicates or near-duplicates) | 100 / 100 |
| No near-copy of a dev or other-panel item (all rules below) | 51 / 100 |
| - idea items: subject differs from every reference item's subject | 36 / 70 |
| - uses_facts items: no shared occasion/request plus key taught fact | 15 / 30 |
| - uses_facts items: no fact owner shares a name with a reference person or pet | 26 / 30 |

Near-copy failures by reference set (an item can match more than one set; 5 items matched two):
dev set 14, escrow-k1a 18, escrow-k1c 22 (54 matches over 49 distinct items).

## Fixes by type (items changed)

| fix type | items |
|---|---|
| Kind / turn counts | 0 |
| Personal facts in an idea lead-in | 0 |
| Facts / teach mismatch | 0 |
| Unclear or unanswerable request | 0 |
| Real names or brands | 0 |
| Duplicates within the panel | 0 |
| Near-copies of dev or other-panel items | 49 (idea 34, uses_facts 15; includes the 4 owner-name collisions) |
| Style | 0 |
| **Total items changed** | **49** |

Fields touched by the 49 fixes: idea request only 23; idea lead-in only 9; idea lead-in and request 2; uses_facts request only 1; uses_facts teach turns plus matching facts 14. In every uses_facts fix the facts list was updated in the same edit so it still matches the teach turns exactly. No item changed kind or number of turns; no fixed item copies another item in this panel or in the reference sets (re-checked after editing).

## Form spread (items_v2.jsonl)

| group | form | items |
|---|---|---|
| brainstorm list | names | 9 |
| brainstorm list | party themes | 6 |
| brainstorm list | ways to reuse something | 5 |
| brainstorm list | plot twists | 5 |
| brainstorm list | activity ideas | 8 |
| brainstorm list | gift ideas | 6 |
| short piece | four-line poem | 7 |
| short piece | limerick | 6 |
| short piece | toast | 7 |
| short piece | slogan / short line | 8 |
| short piece | two-sentence story | 4 |
| short piece | short card or note | 7 |
| short piece | haiku | 6 |
| fresh angle | chores fun | 5 |
| fresh angle | cheaper weekend | 4 |
| fresh angle | rainy-day plan | 4 |
| fresh angle | other problem angle | 3 |
| | total | 100 |

Every named form appears at least 4 times. One fix moved one item from two-sentence story (was 5) to limerick (was 5). Every other form count is unchanged.
Requests naming a count: 38 name a number of items or options; a further 13 name a length (lines or sentences); 51 of 100 name at least one of these.

## Final structural check on items_v2.jsonl

Re-ran the Python check: 100 lines, ids kd-001..kd-100 in order, exact keys, numbers/target/gold_expr null, idea 35 x 0 + 35 x 1 turns, uses_facts 10 x 1 + 10 x 2 + 10 x 3 turns, idea facts empty, uses_facts facts non-empty.

**items_v2.jsonl passes every structural check.**
