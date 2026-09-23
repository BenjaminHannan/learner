# Exp 273 — RESULTS (verdict: PASS M1–M4)

Listen-before-sleep on the 292t base. ONE change: new file
scripts/claude_loop273_agent.py provides build_agent273(cfg) and
Loop273Daemon, built exactly like 292t (292t imported read-only, never
edited), with the loop's step() order changed ONLY to
inbox -> sleep_due -> work_queue -> thinking via a wrapper installed on
the built loop object. scripts/fable_agent_loop.py and every 292t file
untouched; reader/ear stages untouched. CPU only (GPU: no).

**Verdict: PASS.** A waiting user turn is now heard first (20/20), sleep
never starves (20/20, sleeps 1 tick after the inbox empties), and the full
verified 292t blind panel is byte-identical to the recorded run (90/90,
0 overlaps, 0 wrong, 0 new wrong saves).

## Marks table (integer counts)

| mark | bar | result |
|---|---|---|
| M1 273 listening-first (sleep due + 1 inbox message) | 20/20 | 20/20 |
| M1 292t listening-first (comparison) | report (expect 0/20) | 0/20 (SLEEP 20/20) |
| M2 273 sleep within 3 ticks of inbox emptying | 20/20 | 20/20 (all exactly 1 tick) |
| M2 292t within 3 ticks (comparison) | report | 20/20 (all exactly 3 ticks) |
| M3 agreement 273 vs mechanical owner | 90/90 identical | 90/90 identical |
| M3 overlaps | 0 | 0 |
| M3 wrong (moved turns + old-sheet hits) | 0 | 0 + 0 |
| M3 per-category agreement identical | identical | identical (25/8/12/25/10/10) |
| M3 mechanical owners identical | 292:65 280b:20 282b:5 | identical |
| M3 per-turn 273 vs recorded 292t | report | 90/90 identical |
| M4 new wrong saves anywhere in M3 | 0 | 0 (0 question writes, 0 smalltalk writes, 0 store diffs) |

## Every move, every miss, deviations

- **Moves: 0.** No panel turn changed reply, writes, or store vs the
  recorded 292t run (90/90 per-turn identical). No suite/probe moved
  (none re-run; out of scope for this one-change task).
- **Misses: 0.** M1 20/20, M2 20/20, M3 identical on all 11 score fields,
  M4 0/0/0.
- **Deviations: 1 (environmental, reported).** Pre-panel 1-min load sat at
  81–101 (over the panel script's 60 guideline) and kept rising, so after
  ~6 min of waiting the rerun proceeded with strictly sequential
  OMP_NUM_THREADS=1 runs (1 process at a time, inside the 4-parallel
  rule). Free disk was 14 GB (over the 3 GB stop bar). Panel seal checked
  2/2 OK before the run; each of the 5 arms ran exactly once; no re-runs.
- Not a deviation: the 4 comparison arms (292, 280b, 281, 282b) reran
  byte-identical to the recorded files (4/4), confirming the rerun
  harness added no noise. Not a deviation: 292t passes M2's 3-tick bar
  here (3/3 ticks) while failing M1 — the reported comparison numbers.

## What it means / doesn't mean (plain high-school English)

- Before this fix, when the agent was due for sleep AND a user message
  was waiting, it always slept first and left the user hanging for a
  whole tick (shown: old code picked sleep 20 times out of 20). Now the
  waiting message is always heard first (20 out of 20), and sleep still
  happens right after the inbox is empty (1 tick later every time), so
  sleep is never skipped or starved.
- On the real 90-turn blind test the talking-line team already passed,
  the fixed version answers every single turn exactly the same as
  before — same words, same notebook writes (none new), same saved
  notes. The fix changes timing only, not answers.
- This does NOT test the reader/ear stages (deliberately untouched), it
  does NOT grade answer quality (the director checks that), and it does
  NOT prove anything about message wordings never tested.

## Detail (counts only, never quoted)

- M1 (scripts/claude_loop273_test.py, 20 seeded cases, sleep_due True
  20/20 on both arms before the step): 273 first-tick LISTENING 20/20;
  292t first-tick SLEEP 20/20, i.e. 0/20 listening.
- M2 (sleep due + 10 stream ticks + drain, cap 30): 273 stream ticks
  listening 10/10 in 20/20 cases, ticks-to-sleep 1 in 20/20; 292t stream
  ticks listening 8/10 in 20/20 cases (2 sleep ticks cut in line),
  ticks-to-sleep 3 in 20/20.
- M3 (same panel file, runner, scorer, and config the talking line used;
  273 in the 292t slot): score file panel-score273.json matches the
  recorded panel-score292t.json on all 11 fields (dialogs 78, turns 90,
  agree 90/90, by_cat, moved [], overlaps [], question writes [],
  smalltalk writes [], store diffs [], old-sheet hits [], owners
  {292:65, 280b:20, 282b:5}, verdict PASS).
- M4: 0 question-turn writes, 0 smalltalk-turn writes, 0 store diffs
  273 vs 292 → 0 new wrong saves.
- Local rerun evidence (not pushed):
  artifacts/claude-loop273-20260923/run273/ (5 arm outputs + probes +
  panel-score273.json); M1/M2 raw rows ran to /tmp (counts folded into
  results.json).
