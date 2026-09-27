# y1t Luna pilot: PASS on L1, L2 and L3 (Answering-from-memory thread, scored 2026-09-27 07:17 UTC)

Marks: ADDENDUM-5-luna-writer.md (sealed 03:53 UTC in SEAL-y1t-add5.sha256.txt, before any Luna call). Rows:
builder-outbox artifacts/claude-y1t-20260926/luna/ (4e5bf6c39, pushed 03:09:31 Mac time = 07:09 UTC). The builder's
report is RESULTS-luna-pilot.md there. Every count below was recomputed in this container from the pushed rows.

## Verdict
| Mark | Bar (sealed) | Result | |
|---|---|---|---|
| L1 route | at most 3 of 60 dropped by the route-loss filter | 0 dropped (60 in, 60 kept; empty 0, r1 0, r2 0) | PASS |
| L2 parse | at least 54 of 60 parsed | 60 of 60 ("parsed" not null) | PASS |
| L3 G2 (asks) | at least 30 - floor(0.1 x 30) = 27 of 30 | 30 of 30 | PASS |
| L3 G3 (stated) | at least 27 of 30 | 30 of 30 | PASS |

Pilot PASS. By ADDENDUM-5: the other 255 are worded by Luna with the same runner, then the route filter, the merge and
the full data gate (GATE-data.md with GATE-ADDENDUM-1) as sealed. The 60 pilot rows are kept.

## How it was checked
- Rows: raw_luna.jsonl and raw_luna_rf.jsonl both sha256 5e98dec2...6e78 (as the builder reported). The route filter
  (claude_y1t_routefilter.py, sealed) rerun here gives the same counts line and a byte-identical file.
- The 60 dialog ids are exactly the first 60 of luna_seeds.jsonl (sha256 6184cd22...83de, regenerated here from seed
  4027); every row's model is codex/gpt-6-luna.
- L3, unchanged scripts: lis-320's check (claude_lis320_check.py, sha256 5a3148be..., the version main has held since
  dc2b7f7f7, the same one the 1,440 top-up merge used) on the 60 dialogs, then y1t's items step (claude_y1t_data.py
  items, seed 4027, sealed ee349fbe...), then G1b (claude_y1t_gate2.py filter, sealed) on items_train and items_dev.
  The two filtered files were joined (60 items: 30 answerable, 30 never-told) and passed to
  `claude_y1t_gate.py sample --n 1000 --seed 4034`, so all 30 answerable pilot items were judged.
- Judges: two fresh blind Opus agents, each given a copy of only its own folder (INSTRUCTIONS.md and batch.jsonl) in
  a separate randomly named directory, told to read nothing else, to judge each item by reading it, and not to quote
  any item. The first line of each prompt said never to use WebFetch or any web tool. They agreed on all 30 items for both
  questions, so `splits` found 0 disagreements and no third judge was needed. `score` printed items 30, asks_yes 30,
  stated_yes 30. Its G2 and G3 booleans (fixed at 54 of 60) do not apply to the pilot (ADDENDUM-5, last line).
- A code count on the same 30 items (not a mark): every last message has a question mark, every gold value appears in
  an earlier message, and no question contains its own answer.
- Files: pilot-gate/ (judge folders with labels, gate_key.json, gate_result.json, inputs.sha256.txt with the sha256 of
  the kept, items and G1b files).

## Report only (ADDENDUM-5)
| lis-320 check | Luna pilot (60 dialogs) | GLM top-up (1,440 rows) |
|---|---|---|
| dialogs not parsed | 0 | 80 |
| turns in parsed dialogs | 423 | 9,525 |
| kept | 409 (96.7%) | 8,376 (87.9%) |
| dropped turns | 14 | 1,149 |
| drop reasons (a turn can have more than one) | no_cue 12, assert_hedged 2 | assert_hedged 449, assert_reported 237, must_missing 230, former_present_cue 129, no_cue 105, smalltalk_self 86, plan_leak 60, 8 other reasons 114 |

- Items from the pilot: 30 asks kept, 30 answerable and 30 never-told items (50 train, 10 practice-dev), 1 corrected
  ask. G1b: 26 clean twins and 4 name-only twins (G4 in the full gate decides those), no twin dropped.
- Luna's dialogs lose fewer turns to lis-320's check. That is suggested only (60 dialogs), and says nothing yet
  about quality beyond the check and the 30 judged items.

## Why the job's exit code (rc=1) does not change this
The job's runner (rungo5) marks a builder pass done only if its log contains none of four plan-error phrases
anywhere (rungo5.sh, the grep after `rc=$?`; one of them is the two words for a plan running out of its allowance). The first builder pass (go1) did every step
once: the pilot ran once, 06:38:12 to 06:58:43 UTC, exit 0, with totals {"calls": 60, "parsed": 60, "skipped": 0,
"failed_calls": 0, "batches": 3, "stopped": "done", "minutes": 20.5}. But while looking for the Director's Luna
share it printed another job's queue file, whose WHY line contains that phrase (go1.err.txt line 531).
The runner took that for a plan error, so it started a second pass (go2), which re-checked go1's work and made no Luna
call (its only Luna-related command was a ps). go2's log carries the same words from other job files (lines 1741 and
1820), so the chain ended with rc=1. The rows, the log and the counts come from go1's single run and were rechecked
here, so the exit code has no bearing on L1-L3. Reported to the Director between 07:13 and 07:17 UTC as a runner bug.

## Deviations (disclosed)
- The two G1b-filtered files were joined into one before `sample`, which reads one items file; ADDENDUM-5 asks for
  every answerable pilot item to be judged, and all 30 were.
- The checks ran here with Python 3.11 (the Mac jobs use 3.12); the scripts are standard-library only.
