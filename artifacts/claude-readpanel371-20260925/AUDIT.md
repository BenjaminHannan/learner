# rp371 key audit against label B (TEST-ONLY, counts only)

> Never read, train or tune on this panel. This file gives counts only and quotes no turns, names or facts.

A separate labeller wrote `label_B.jsonl` blind, from `blind_input.jsonl`. It has 428 facts in total, and its relations are free words. The first version of the key was compared with it row by row.

## How the rows were matched

Each gold fact is matched to at most one B fact in the same row.
- **Owner**: `USER` matches only `USER`. Any other owner matches on the full name or the first name, ignoring case.
- **Value**: must match exactly, ignoring case.
- **Relation**: ignored.

On rows with no facts, the `nosave_reason` is compared as well. A row counts as fully agreed when B gave every gold fact, added no extra facts, and (on no-fact rows) gave the same reason.

The script is `rp371/compare.py` in the build session's scratchpad.

## First pass (key v1, 411 gold facts)

| measure | count |
|---|---:|
| gold facts B also gave | 400 |
| gold facts B missed | 11 |
| extra B facts | 28 |
| rows fully agreed | 212 / 240 |
| rows disagreeing | 28 (long_multi 19, trap 7, short_answer 2) |
| no-fact rows where B also gave no facts | 65 / 65 |
| nosave reason agreement on those rows | 65 / 65 |

Kinds with no disagreements: teach_single, correct, nosave and smalltalk.

## What was done with the 28 disagreeing rows

For each row, the change came from re-reading the turn against the brief's rules, not from copying B's label.

| action | rows |
|---|---:|
| key fixed only; the turn and prev_reply are unchanged (the key had left out a fact the turn clearly states) | 8 |
| turn rewritten to remove the ambiguity, with the key updated to match | 20 |
| dropped and replaced with a fresh row | 0 |
| **changed in total** | **28** |

Why the 20 turns were rewritten:
- **8 rows**: the value's boundaries were unclear, such as a title in front of a name or a degree word in front of a subject.
- **8 rows**: a place or pet could be attached to the wrong owner, or to an unnamed relative, or was hedged.
- **4 rows**: a fact was implied rather than stated.

On 6 of the 20 rewritten rows, a fact in the key was added, removed or restated to match the new wording. On 3 more, only a value's wording changed. The key-only fixes added 8 facts and the rewrites a net 4.

All 28 rows keep their id and kind. `changed_ids.txt` lists them, and `changed_blind.jsonl` gives their blind input (id, prev_reply, turn). The 8 key-only rows appear in both files with their text unchanged.

## After the audit

- 240 rows with the kind and nosave-reason counts unchanged.
- **Facts**: 423 in total (was 411). The label-B2 pass below brings the final total to 426.
  - long_multi 199 (was 192)
  - trap 155 (was 151)
  - short_answer 17 (was 16)
  - teach_single 30 and correct 22, both unchanged
- **Owners**: 217 USER and 206 other (219 and 207 after the label-B2 pass).
- The full check script passes with 0 errors, and the dev-set name check finds 0 name overlaps.
- `blind_input.jsonl` was regenerated and matches `panel.jsonl`.
- B's labels were made for the old text of the 20 rewritten rows, so agreement with B is not re-scored here. To re-score, have B label `changed_blind.jsonl` blind.

## Second blind pass (label B2, the 28 changed rows)

A fresh blind labeller labelled the 28 rows in `changed_blind.jsonl`. B2 wrote 101 facts. They were matched against the key with the same rules as the first pass.

| measure | count |
|---|---:|
| gold facts B2 also gave | 90 of 90 |
| gold facts B2 missed | 0 |
| extra B2 facts | 11 |
| rows fully agreed | 18 of 28 |
| rows disagreeing | 10 (long_multi 8, trap 2) |

The key was fixed only where it was clearly wrong under the brief's rules, and no turn was rewritten again.
- **3 rows**: the key gained 1 fact each, a fact the turn clearly states. The turns and `blind_input.jsonl` are unchanged.
- **The other 8 extra B2 facts were left out of the key.** Each is one of these:
  - a small detail about an object or a duration,
  - a date or year attached to an event,
  - a fact whose owner is an unnamed relative,
  - a second relation for a person who is already in the key,
  - something the turn hints at but does not say.

After the fixes, B2 agreed on 93 of 93 gold facts in these rows, missed 0, added 8 extras, and fully agreed on 21 of 28 rows.

## Final agreement (final key against label B on the 212 unchanged rows and label B2 on the 28 changed rows)

| measure | count |
|---|---:|
| gold facts in the final key | 426 |
| gold facts the labellers also gave | 426 |
| gold facts missed | 0 |
| extra labeller facts | 8 |
| rows fully agreed | 233 of 240 |
| no-fact rows where the labeller also gave no facts | 65 of 65 |
| nosave reason agreement | 65 of 65 |

**Final key:**
- 426 facts: long_multi 202, trap 155, teach_single 30, correct 22, short_answer 17.
- Owners: 219 USER and 207 other.
- The full check passes with 0 errors.
- The dev-set name check finds 0 name overlaps.
