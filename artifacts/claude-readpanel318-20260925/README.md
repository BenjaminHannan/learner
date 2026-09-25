# readpanel318: sealed blind panel for reading facts from casual chat

**TEST-ONLY: never read, train or tune on this panel. Runners read it; scorers print counts only.**
Do not quote turns, names or facts from it in logs, reports, prompts or commits.

Built 2026-09-25 by a Claude subagent. The parent session has never seen the items.

## Files
- `panel.jsonl`: 240 rows, keys `id, prev_reply, turn, kind, facts[{owner, relation, value}], nosave_reason`.
- `label_B.jsonl`: labels from a separate blind labeller (keys `id, facts, nosave_reason`).
- `AUDIT.md`: counts from the agreement audit.
- `SEAL.sha256.txt`: sha256 of the four files above.

## Counts
| kind | rows | facts |
|---|---|---|
| teach_single | 40 | 40 |
| teach_multi | 60 | 147 (35 rows with 2, 23 with 3, 2 with 4) |
| teach_passing | 30 | 32 |
| correct | 20 | 21 (new values only) |
| short_answer | 15 | 15 |
| nosave | 45 | 0 |
| smalltalk | 30 | 0 |
| **total** | **240** | **255** |

- nosave_reason: negation 7, plan 7, hypothetical 7, reported 6, question 7, our_we 6, sarcasm 5, smalltalk 30 (75 rows with no facts).
- Facts owned by USER: 176; by a named person or pet: 79.
- Distinct relation labels: 81.
- Every fact value appears in its turn (case-insensitive), except 2 short_answer facts whose value appears only in `prev_reply` (the turn points to one of the options in the assistant's question).

## Key conventions
- owner `USER` = the speaker; otherwise the person's or pet's name as the user says it.
- `correct` rows hold only the new value.
- No fact is saved for negation, plans or hopes, hypotheticals or pretending, someone else's unverified claim, questions (including a "so X is Y" check with no question mark), our/we ownership, sarcasm or jokes, and small talk.
- Plural lists give one fact per value.

## Name rule
All people, pets, towns, companies, schools, teams and bands are freshly invented and fictional; none is a real public figure. Real countries and big real cities are used only as places. No name from the dev set `artifacts/claude-e2e331-dev-20260924/turns.jsonl` is reused. An automated check matched 0 names; it also matched 6 ordinary words (e.g. a sentence-start "again" and generic words inside business names), which are not names.

## Blind second-labeller audit (details in AUDIT.md)
- Labeller B was a separate Claude Opus instance. It saw only `id, prev_reply, turn` and the labelling rules, not the key.
- First pass: 254 of 256 gold facts agreed. There were 4 fact-level disagreements (2 gold facts that B did not give, 2 extra facts from B), and 236 of 240 rows agreed fully. B saved no facts on any no-save row, and nosave reasons agreed on all 75 rows with no facts.
- How the 4 disagreeing rows were resolved: 1 key fix (an inferred fact was dropped), 2 rewrites to remove the ambiguity (one turn, one prev_reply), and 1 row dropped and replaced with a fresh row of the same kind.
- A fresh run of B on the 3 changed rows agreed 3 of 3.
- Final agreement: 255 of 255 gold facts, 0 extra facts, 240 of 240 rows, and nosave reasons agree on all 75 rows.
