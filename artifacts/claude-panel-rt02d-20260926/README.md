# rt-02d blind test panel (2026-09-26)

**TEST-ONLY: never opened, printed or quoted except by the runner and scorer.**
Builders of the rt-02d route must not read `make_panel.py`, `chat_puzzles.jsonl` or `negatives.jsonl`.

Written blind for PASSMARKS rt-02d (`artifacts/claude-rt02d-20260926/PASSMARKS-rt02d.md`, "Test data"), without
seeing the route code, the repo's chat templates or any other panel.

## Files
- `make_panel.py`: deterministic generator (Python 3 stdlib + `scripts/claude_blurt2.py`). Run `python -B make_panel.py`
  from this folder; it rewrites both jsonl files byte-identically.
- `chat_puzzles.jsonl`: 100 lines `{"id", "wording_id", "text", "nums", "target"}`. Ten held-out wordings
  (`wording_id` 0-9), ten puzzles each; puzzle i gets wording i // 10. `nums` is the generator's (sorted) list; the
  numbers in `text` are in a seeded shuffled order. Numbers are written as digits. No wording equals or paraphrases
  `claude_sleep02c.CHAT_ASK`.
- `negatives.jsonl`: 100 lines `{"id", "text"}`: ordinary chat messages that contain numbers but are not number
  puzzles (ages, prices, dates, times, counts, recipes, scores, everyday talk), the last 22 of them near-misses that
  mention numbers and a goal. Fictional names only.
- `SEAL-panel.sha256.txt`: sha256sum of the four files above.

## Generator seed and exclusions
Puzzles: the first 100 of `claude_blurt2.puzzles(4797, 1000)` whose key `(tuple(nums), target)` is not excluded.
Every puzzle comes from that generator, which keeps a puzzle only when `claude_blurt1.solve` finds a solution.

Excluded keys (673) mirror `claude_sleep02c.run` with the default arguments used by the 0.2c jobs
(`--nights 3 --n-day 150 --n-test 100 --n-chat 40`):
- day puzzles `puzzles(4700 + d, 150)` for d = 1, 2, 3 (the code's nights; the PASSMARKS text says 4700-4702);
- TEST: the first 100 of `puzzles(4790, 400)` not among the day keys;
- chat: the first 40 of `puzzles(4795, 340)` not among the day or TEST keys;
- plus, as a superset guard for the PASSMARKS wording, `puzzles(4700, 150)`.
Checked: none of the 100 panel keys is in the excluded set, nor in the set built literally from the PASSMARKS
description (days 4700-4702, first 100 of seed 4790, chat of seed 4795).

## sha256
```
ada1c2ae3e42ffde4feeee682150875836f8ce610299fabfba007219cdb03c73  make_panel.py
0f51e608fb3f6a0f6228d40aea24e38083335764c739807669c14f58f66c943c  chat_puzzles.jsonl
dc3c440e15b4c9c98b116fe3828447873db9f698b7534eedec593b1973558568  negatives.jsonl
```
README.md's own hash is in `SEAL-panel.sha256.txt`.
