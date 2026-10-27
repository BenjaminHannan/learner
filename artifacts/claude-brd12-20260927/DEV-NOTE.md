# brd-12 DEV note: hindsight relabelling on key games (written 2026-09-27 05:49 UTC by `date -u`)

DEV only (seeds 900000-900019, already DEV in brd-11). Plain MiniCPM5-1B on CPU, thinking off, no constrained
decoding, 30 samples per game. Probe: scripts/claude_brd12_dev.py (6614b4dc3). "Relabelled goals" = distinct rooms a
sample's legal moves reached, other than the start and the asked goal, each checked by the world's own claude_textgames.check
on the same maze with the goal rewritten.

| level | T | games | games with an asked-goal hit | samples with a legal move | games with a relabelled goal | relabelled goals |
|---|---|---|---|---|---|---|
| 1 (plans 3-8) | 1.0 | 10 | 0 | 43 of 300 | 5 | 6 |
| 1 | 1.5 | 20 | 0 | 38 of 600 | 15 | 16 |
| 0 (plans 1-2) | 1.0 | 20 | 9 | 54 of 600 | 2 | 2 |

Files: dev/her_level1_T1.0_10.json, dev/her_level1_T1.5_20.json, dev/her_level0_T1.0_20.json.
Commands: python3 -B scripts/claude_brd12_dev.py --model M --out F --level 1 --items 10  (then --items 20 --temp 1.5;
then --level 0 --items 20).

Finding: at level 1 the plain 1B never reaches the asked room, and most samples break a rule on the first move (only 38
of 600 at T 1.5 have a legal move), but relabelling still gives about one checked goal per game at T 1.5 (16 in 20
games). Guess (not measured; the probe does not save walk lengths): the relabelled walks are mostly one or two moves,
so HER at level 1 mainly teaches legal first moves in bigger mazes. Whether that helps multi-step plans is what brd-12
would test.
