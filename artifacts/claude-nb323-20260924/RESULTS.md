# Exp nb-323 — RESULTS (verdict: PASS M1–M4, M5 report-only)

A durable, hash-chained turn log on the verified 274 base. ONE change in
the NEW file scripts/claude_nb323_turnlog.py (TurnLog323, read_turns,
install_turnlog323, build_agent323, Loop323Daemon; no existing file
edited): every `loop.turn` writes one BEGIN (full text) before the saved
274 stack runs and one END (full reply lines + the daemon.log fields +
mode + `deaf_s`) after the reply exists, each line flush + fsync +
read-back, chained from the contract's GENESIS. The wrapper is installed
LAST, so it captures the final reply; replies pass through unchanged and
`daemon.log.jsonl` is written exactly as before. CPU only (GPU: no).

**Verdict: PASS.** The 90-turn blind panel scores identically to 274
(90/90, 0 overlaps, 0 wrong) with every reply and store byte-identical;
600/600 turns survive 40 restarts and 40 sleeps with full text and
reply; 30 SIGKILLs lose 0 returned replies (0 missing ENDs, 0 duplicate
ENDs, 0 failed opens, 24 interrupted turns listed); 20/20 tampered
copies are caught on open. Per-turn cost is ~0.2 ms median.

## Marks table (integer counts)

| mark | bar | result |
|---|---|---|
| M1 agreement 323-slot vs mechanical owner | 90/90 | 90/90 |
| M1 overlaps | 0 | 0 |
| M1 wrong (moved turns + old-sheet hits) | 0 | 0 + 0 |
| M1 question-turn writes / smalltalk-turn writes / store diffs vs 292 | 0 / 0 / 0 | 0 / 0 / 0 |
| M1 per-turn 323 vs recorded 274 (reply, writes, store) | 90/90 | 90/90 |
| M1 dialog stores 323 vs recorded 274 | 78/78 | 78/78 |
| M1 probes 323 vs recorded 274 | identical | identical |
| M1 all 11 score fields identical to recorded 274 | identical | identical |
| M2 exact BEGIN+END per turn, in order, text/reply matching | 600/600 | 600/600 |
| M2 dialogs fully ok | 20/20 | 20/20 |
| M2 kill-free restarts | 40 | 40 |
| M2 forced sleeps (sleep_threshold 6) | 40 | 40 |
| M2 records lost to sleep or restart | 0 | 0 |
| M3 SIGKILLs | 30 | 30 (5 early, 25 mid-run) |
| M3 returned replies missing an END | 0 | 0 (344/344 returned replies have ENDs) |
| M3 reply mismatches | 0 | 0 |
| M3 duplicate ENDs | 0 | 0 |
| M3 failed opens | 0 | 0 (30/30 opens ok) |
| M3 interrupted turns listed by read_turns | report | 24 |
| M4 tamper copies caught on open | 20/20 | 20/20 |
| M5 per-turn overhead median / max | report | 0.197 ms / 0.904 ms |
| M5 open a 10,000-turn (20,000-line) log | report | 0.071 s |

## Every move, every miss, deviations

- **Moves: 0.** No turn changed reply, writes, or store vs recorded 274
  (90/90 per-turn identical, 78/78 dialog stores identical, probes
  identical, all 11 score fields identical: dialogs 78, turns 90, agree
  90/90, by_cat 25/8/12/25/10/10, moved [], overlaps [], question
  writes [], smalltalk writes [], store diffs [], old-sheet hits [],
  owners {292:65, 280b:20, 282b:5}, verdict PASS).
- **Misses: 0.** M1 identical everywhere, M2 600/600, M3 0/0/0, M4 20/20.
- **Deviations: 3 (all reported, none silent).**
  1. OPUS-RULES.txt not found at the tasked path; proceeded per the key
     rules restated in the task (additive-only, offline uv python, disk
     check, counts-only reporting, sealed panel run once for M1 only).
  2. Seal recomputed once: the first M4 run exposed a real bug in the
     new file — a tamper byte that breaks UTF-8 raised a bare
     UnicodeDecodeError instead of TurnLog323Corrupt. Fixed minimally
     (undecodable bytes fail closed as TurnLog323Corrupt in `_verify`
     and `repair_torn_tail`; writer output is always valid UTF-8 so a
     clean torn tail still repairs). Only the turnlog file changed; the
     test file and PASSMARKS.md hashes are unchanged. Every mark above
     was then run fresh on the final sealed code (M1/M2 first-run rows
     on the pre-fix code are VOID and not reported).
  3. M1 comparison arms reused from 274's verified run274 (292, 280b,
     281, 282b + probes) instead of rerunning all five arms: 274's M3
     already proved those reruns byte-identical 4/4 to gold, the scorer
     is deterministic on fixed inputs, and only the 323 slot arm is new
     (run with the same runner, config, and panel). Per-turn 323 vs
     recorded 274 is 90/90, which is the behaviour-change check.

## What it means / doesn't mean (plain high-school English)

- The agent can now be killed at any moment — crash, power loss, sleep —
  and the turn history is still complete: every answer it actually gave
  is on disk with its full text, and every turn cut off mid-answer is
  listed as interrupted instead of silently lost (shown: 344 out of 344
  returned answers kept, 24 cut-off turns listed, 0 opens failed over
  30 kills). Any edit to the file is caught when it is opened (20 out
  of 20).
- Restarts and sleeps lose nothing: 600 out of 600 turns kept exactly
  one BEGIN and one END, in order, across 40 rebuilds and 40 sleeps.
- The log changes nothing about answers: on the real 90-turn blind test
  it answers every turn word-for-word like 274 (90/90) with identical
  notebook stores (78/78).
- Cost is tiny: about 0.2 ms extra per turn (worst 0.9 ms), and opening
  a 10,000-turn history takes 0.07 s.
- This does NOT test the reader/ear stages (untouched), does NOT grade
  answer quality (the director checks that), and does NOT cover daemon
  mailbox mode beyond the same `loop.turn` path the daemon calls
  (daemon.log.jsonl itself is byte-for-byte unchanged).

## Detail (counts only, never quoted)

- M1 (scripts/claude_nb323_test.py m1; same runner
  scripts/claude_join292t_run.py, same config
  artifacts/claude-join292t-20260923/loop292t-config.json, same sealed
  panel artifacts/claude-joinpanel292t-20260923/panel.jsonl with seal
  2/2 OK before the run; 323 in the 274 slot; same scorer
  scripts/claude_join292t_score.py; comparison arms + probes from
  274's verified run274): score matches recorded panel-score274.json on
  all 11 fields; 90/90 per-turn identical; 78/78 stores identical;
  probes identical; scorer rc 0; run elapsed 10.4 s.
- M2 (20 seeded dialogs x 30 turns, invented names, teach/question/
  smalltalk rotation; sleep_threshold 6; rebuild on the same state_dir
  after turn 9 and turn 19; run_until_idle after turn 19 and turn 29):
  40/40 restarts done, 40/40 sleeps observed (counters["sleeps"] +1 at
  each forced point), 600/600 turns with exact BEGIN+END in order and
  full text/reply matching what turn() returned, 20/20 dialogs fully
  ok, 0 lost.
- M3 (one shared state_dir, loop mode, fresh subprocess per iteration,
  seeded kill delays; 25 kills after the first reply landed, 5 kills
  within 0.4 s of spawn): 344 returned replies, all with matching ENDs
  (0 missing, 0 mismatched), 0 duplicate ENDs, 30/30 opens ok (0 torn
  tails hit: appends are sub-millisecond, kills landed mid-turn), 24
  interrupted turns listed.
- M4 (finished 60-line log, 20 copies, one random byte each outside the
  final line, seed 32304): 20/20 raise TurnLog323Corrupt on open,
  including copies whose byte change broke UTF-8 decoding.
- M5 (300 BEGIN+END pairs with representative record sizes; 10,000-turn
  generated log): per-turn append overhead median 0.197 ms, max
  0.904 ms; open of 20,000 lines 0.071 s.
- Local run evidence lived under /tmp/nb323/ (panel-323 run, per-mark
  jsons) and was deleted at the end, per the task.
