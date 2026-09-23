# Ear panel 261b (blind reader panel), 2026-09-23

TEST-ONLY panel for the "reader": one chat turn in, the facts it states
(TEACH) or the question it asks (ASK) out. Written blind: the author read
only the 261b spec, OPUS-RULES.txt, and the schema and judgement-call
sections of the earpanel235 README. No code, relation tables, training
data, design notes, results, other briefs, or other panels were read.
All names of people, towns, companies, pets, and languages are made up.
No name or place from the panel-235 README is reused.

Files:
- `panel.jsonl`: 150 items, one JSON object per line.
- `make_panel.py`: holds the items by hand, writes `panel.jsonl`
  deterministically, and runs the self-checks (family counts, no duplicate
  turn, subject/value spans, every R1-R14 quota, lowercase/typo and no-"?"
  counts, schema exactness including chain_aliases).
- `SEAL.sha256.txt`: SHA-256 of `panel.jsonl` and `make_panel.py`.

## Families (category level only)

| family | items | clear: false |
|---|---|---|
| plain_teach | 25 | 1 |
| varied_teach | 30 | 0 |
| full_names | 15 | 1 |
| questions | 25 | 4 |
| chain_questions | 15 | 1 |
| no_save | 25 | 12 |
| corrections | 15 | 0 |
| **total** | **150** | **19** |

## Risk-quota counts (category level only)

R1 12 (varied_teach + full_names) | R2 12 (9 statement-questions in
no_save, 5 of them with no question mark; 3 question-word statements with
TEACH gold in varied_teach) | R3 8 | R4 8 | R5 16 | R6 9 of 15
chain_questions | R7 7 | R8 7 (3 varied_teach with a real current fact
as gold, 4 no_save plans) | R9 6 | R10 5 | R11 7 | R12 5 | R13 8 |
R14 7 | lowercase-or-typo turns 26 | noq tags 11 (6 of them on
questions/chain_questions).

## Judgement calls (category level only)

- Pronouns across clauses resolve to the named person.
- Statement-shaped questions save nothing (clear: false).
- Teaching/coaching at a school, college or club is workplace; studying
  at one is school.
- Plans and wishes save nothing unless another clause states a real
  current fact; then only that fact is gold.
- Pretend and hypothetical turns save nothing.
- Corrections hold only the new value.
- "Grew up" is hometown (clear: false); "used to live" saves nothing
  (clear: false); hearsay and news items save nothing (clear: false).
- Job/workplace-ambiguous questions are gold job (clear: false).
