# rv-385 blind recount (independent, from the raw run files)

Script: `/tmp/claude-0/-home-user-learner/fb9ceec8-de99-5e43-a641-93796fea5adc/scratchpad/recount385.py` (python3, standard library only; its JSON output is in `recount385.json` next to it). I did not open `scripts/claude_rv385_count.py`. Inputs: `artifacts/claude-rv385-20260925/run/*.jsonl` and `PASSMARKS.md`.

## Numbers

| seed | arm | solved (my check) | rows whose `solved` flag disagrees | max steps (budget 60) | steps = non-back log entries | total steps |
|---|---|---|---|---|---|---|
| 385101 | restart | 0 / 80 | 0 | 60 | 80 / 80 rows | 4800 |
| 385101 | revert_ban | 46 / 80 | 0 | 60 | 80 / 80 rows | 3474 |
| 385101 | revert_note | 13 / 80 | 0 | 60 | 80 / 80 rows | 4607 |
| 385202 | restart | 0 / 80 | 0 | 60 | 80 / 80 rows | 4800 |
| 385202 | revert_ban | 54 / 80 | 0 | 60 | 80 / 80 rows | 3424 |
| 385202 | revert_note | 14 / 80 | 0 | 60 | 80 / 80 rows | 4533 |

"Solved" means the final grid keeps every given number of `puz` and every row and every column holds 1..5 exactly once. Every grid I count as solved also equals the stored unique solution `sol`. Every unsolved row used exactly 60 steps. All six counts match the run's own `log.txt` summary lines.

Note-repeat share (item 5, revert_note; a choice counts when its position's noted set is non-empty):

| seed | choices with a non-empty note | repeats of a noted number | repeat share | blind-guess baseline |
|---|---|---|---|---|
| 385101 | 3493 | 2025 | 0.580 | 0.366 |
| 385202 | 3372 | 1893 | 0.561 | 0.350 |

Extra check: running the same bookkeeping on revert_ban as a "ban set" gives 0 repeats out of 2413 (385101) and 2308 (385202) such choices. So the ban arm never picked a ruled-out number, and the ban and the note track the same set.

## Validity checks (all pass)

- **Re-check of solved grids:** in all six arm files, 0 rows have a `solved` flag that disagrees with my check.
- **Same grids across arms:** in each seed, all three arms have 80 rows with 80 distinct pids. The three pid sets are identical, equal the puzzles file's pids, and come in the same order. Size is 5 and `blanks` equals the number of zeros in `puz` on 80/80 rows of every arm. Every final grid keeps all givens (80/80 in every arm).
- **Budget:** the maximum steps is 60 in every arm. No row exceeds 60, counted either by `steps` or by non-back log entries, and `steps` equals the non-back entry count on every row.
- **Log replay (extra):** I replayed every log against its puzzle, with positions as indices into the blank cells in row-major order.
  - Every choice is at the next blank after the current filled prefix.
  - Every "ok" breaks no row or column rule, and every "conflict" really does repeat a number already in its row or column.
  - Every "back" removes exactly the number last written at that position.
  - restart has no "back" rows and wipes its grid after each conflict.
  - The replayed grid equals `final` on 480/480 rows, with no problems found.
- **Puzzles file:** 80/80 `sol` are valid Latin squares consistent with `puz`, and my own solver finds exactly one solution for 80/80 puzzles, in both seeds.
- **Puzzles match the seal (item 6):** `E.make_latin_base(random.Random(seed), 5)` called 80 times, converted with v+1 and 0 for blanks, reproduces the puzzles file exactly, in order (pid `<seed>-<i>`): 80/80 for 385101 and 80/80 for 385202.
- **Seal hashes (extra):** sha256 of `scripts/claude_rsn358a_envs.py`, `scripts/claude_rv385.py`, `scripts/claude_blurt1.py` and `PASSMARKS.md` match `SEAL.sha256.txt`. I did not hash `claude_rv385_count.py`, so as not to touch it.

## Verdict against PASSMARKS.md

- **PASS** needs revert_note to beat restart by at least 6 and revert_ban by at least 2 in both seeds. It fails: revert_note trails revert_ban by 33 (385101: 13 vs 46) and by 40 (385202: 14 vs 54).
- **PROVED WRONG** holds: in both seeds revert_note solves no more grids than revert_ban (13 ≤ 46, 14 ≤ 54).
- **Validity:** all three conditions pass, so the run is not void.

**Result: PROVED WRONG.** In this setup the note adds nothing over classic backtracking; it does much worse.

## Predictions

- **P385.1: came true.** revert_ban solves more grids than restart in both seeds (46 > 0, 54 > 0).
- **P385.2: came true.** revert_note solves fewer grids than revert_ban in both seeds (13 < 46, 14 < 54).
- **P385.3: came true.** revert_note solves more grids than restart in both seeds (13 > 0, 14 > 0).
- **P385.4 (report-only): came true.** The note-repeat share is above the blind-guess baseline in both seeds (0.580 vs 0.366, 0.561 vs 0.350).

## Factual notes

- **restart is at the floor:** it solved 0/80 in both seeds. So "steps on grids every arm solved" covers an empty set and cannot be computed.
- **Overlap between the revert arms:** of the grids revert_note solved, revert_ban also solved 12 of 13 (385101) and 13 of 14 (385202). One grid per seed was solved by revert_note only.
- **Not computed:** first-choice accuracy (report-only). It was not in the recount brief.
