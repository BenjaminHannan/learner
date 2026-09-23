# invpanel138nb (backwards questions) — blind panel, base 138n run

70 items, one fresh session each. Category level only; no item text quoted.

Families (n): whose_R 14 (8 single-subject, 6 two-subject), lives_born 10
(5 city / 5 birthplace; 4 two-subject), has_as 6 (2 two-subject),
verb_backwards 10 (3 two-subject), my_backwards 4, no_match 8,
unknown_value 4, forward_control 10, teach_control 4.
Two-teach items: 19. Items using a two-word person name: 43.
Items with a work title starting with "The": 6.
whose_R relations span 9 relations with at most 3 items per relation.
Every setup was checked on the base before use: all 70 store exactly the
listed triple (one candidate dropped and replaced during piloting).
Base 138n ran once per item (fresh temp state dir outside the repo,
sleep_threshold 100000, one process at a time).

Scoring (sealed score_panel.py): backwards families need every gold name
(case-insensitive) plus the "(worked out backwards)" label; my_backwards
also needs "your"/"you". forward_control needs the value. no_match /
unknown_value need an abstain naming no taught subject. teach_control
needs the statement turn to store exactly its own triple.

Base 138n counts per family (right / right_names / wrong / question_wrote):

- whose_R (14): 2 / 14 / 0 / 0
- lives_born (10): 0 / 10 / 0 / 0
- has_as (6): 2 / 6 / 0 / 0
- verb_backwards (10): 9 / 9 / 0 / 0
- my_backwards (4): 1 / 4 / 0 / 0
- no_match (8): 8 / n/a / 0 / 0
- unknown_value (4): 4 / n/a / 0 / 0
- forward_control (10): 10 / n/a / 0 / 0
- teach_control (4): 4 / n/a / 0 / 4

Totals: n 70, right 40, wrong 0, question_wrote 4.

Files: panel.jsonl, base138n.jsonl, make_panel.py, run_base.py,
score_panel.py. SEAL.sha256.txt holds sha256 of those five.
