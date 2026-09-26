# k1c creative panel: blind audit (counts only)

Input: items.jsonl (100 lines). Output: items_v2.jsonl (100 lines, same ids and order; 67 lines byte-identical, 33 lines changed).
Reference sets read only for the copy check: the 40-item development set and the 60-item k1a test panel (items_v2).

## Items checked per kind

| kind | lead-in / teach turns | items checked |
|---|---|---|
| idea | 1 | 35 |
| idea | 0 | 35 |
| uses_facts | 1 | 10 |
| uses_facts | 2 | 10 |
| uses_facts | 3 | 10 |
| total | | 100 |

## Checks run on items.jsonl (items passed / items checked)

| check | passed |
|---|---|
| valid JSON, exact 8 keys in order, ids kq-001..kq-100 in order | 100 / 100 |
| numbers, target, gold_expr all null | 100 / 100 |
| kind and turn counts (35 / 35 / 10 / 10 / 10) | 100 / 100 |
| idea items have facts [] | 70 / 70 |
| idea lead-in sets the scene with no personal facts about the user | 35 / 35 |
| idea 0-turn request complete by itself | 35 / 35 |
| uses_facts facts non-empty, keys owner/relation/value, relation lowercase snake_case | 30 / 30 |
| uses_facts facts match teach turns (no unstated fact, no relied-on fact missing) | 30 / 30 |
| request clear and answerable in a short reply | 100 / 100 |
| realistic casual chat style | 100 / 100 |
| fictional names only (no real people, brands or titles) | 100 / 100 |
| no two panel items with the same subject | 100 / 100 |
| no copy or near-copy of a dev item or a k1a panel item | 67 / 100 |

Notes on method:
- Near-copy rule: an idea item fails when its subject matches a reference item's subject (even in a different form); a uses_facts item fails when it shares both the occasion/request and a key taught fact with a reference item, or when a fact owner has the same name as a person or pet in a reference set.
- 23 more items shared only a form or a wording template with a reference item, with a different subject. They were kept unchanged.
- 1 idea item shares a place name with a dev item. No facts are attached to it, so it was kept unchanged.
- Kinship labels were not required as fact entries. The panel leaves them out throughout, and no request depends on them.

## Fixes by type (items changed)

| fix type | items |
|---|---|
| kind / turn counts | 0 |
| personal facts in an idea lead-in | 0 |
| facts / teach mismatch | 0 |
| unclear or unanswerable request | 0 |
| real names or brands | 0 |
| duplicates within the panel | 0 |
| near-copies of dev or k1a-panel items | 33 |
| style | 0 |
| **total** | **33** |

Near-copy fixes broken down:
- by reference set: 19 dev, 14 k1a panel
- by what was changed: 29 had their subject or a taught fact changed; 4 had only a fact owner renamed
- by kind: 11 idea with 1 lead-in, 10 idea with 0 lead-ins, 12 uses_facts
- in all 12 changed uses_facts items, the facts entries were updated with the turns. They were re-checked against the turns afterwards (30 / 30 pass).
- no fix changed an item's kind, turn count or form. Every edited turn or request was kept in the same casual style.

## Form spread in items_v2.jsonl (each item counted once)

| form | items |
|---|---|
| names | 8 |
| party themes | 6 |
| ways to reuse something | 6 |
| plot twists | 6 |
| activity ideas | 8 |
| gift ideas | 7 |
| four-line poem | 7 |
| limerick | 6 |
| toast | 6 |
| slogan | 6 |
| two-sentence story | 6 |
| short card or note | 7 |
| haiku | 6 |
| chores fun | 6 |
| cheaper weekend | 5 |
| rainy-day plan | 4 |
| total | 100 |

Every form appears at least 4 times. Requests that name an output count: 50 / 100 (33 name a number of items and 17 a number of lines or sentences). The count was the same before and after the fixes.

items_v2.jsonl passes every structural check (Python re-run: 100 lines, ids kq-001..kq-100 in order, exact keys, three null fields, kind and turn counts 35/35/10/10/10, idea facts empty, uses_facts facts non-empty): PASS
