# Exp 274 — RESULTS (verdict: PASS M1–M4)

Never-deaf step A on the verified 273 base. ONE change in the NEW file
scripts/claude_loop274_agent.py (build_agent274, Loop274Daemon; no
existing file edited): turn() drains ticks only while the inbox is
non-empty (the listening ticks), returns/writes the reply, and leaves
any due sleep for the next idle tick (daemon idle loop / next
run_until_idle, both unchanged). The full talking stack is kept; skipped
SLEEP/WORK/THINKING ticks carry no sentences, so replies are unchanged.
273 step order kept (WORK vs SLEEP order NOT changed — pending ruling for
Ben); reader/ear stages untouched. Plus a deaf-seconds meter: per-turn
seconds from message arrival to reply written (loop.deaf_log274),
summarised as median/max. CPU only (GPU: no).

**Verdict: PASS.** With sleep due, the reply now comes back before any
sleep tick runs (20/20; 273 does 0/20), sleep still runs on the very next
idle tick (20/20), replies are byte-identical to 273 everywhere tested
(20/20 invented turns + 90/90 blind panel turns + 4/4 probes), the full
blind panel scores identically to recorded 273 (90/90, 0 overlaps,
0 wrong), and the deaf meter shows 274 answering in milliseconds while
273 waits out the sleep.

## Marks table (integer counts)

| mark | bar | result |
|---|---|---|
| M1 274 reply-before-sleep (sleep due + 1 message, slow 0.5 s stub sleep both arms) | 20/20 | 20/20 (0 sleep ticks during turn, inbox drained, every case) |
| M1 273 same cases (comparison) | report (expect 0/20) | 0/20 (1 sleep tick inside every turn) |
| M1 reply 274 vs 273 identical (diagnostic) | report | 20/20 |
| M1 preconditions sleep_due True both arms | 20 | 20/20 |
| M2 274 due sleep within next 3 idle ticks | 20/20 | 20/20 (tick 1 in 20/20 cases) |
| M3 agreement 274-slot vs mechanical owner | 90/90 identical | 90/90 identical |
| M3 overlaps | 0 | 0 |
| M3 wrong (moved turns + old-sheet hits) | 0 | 0 + 0 |
| M3 question-turn writes / smalltalk-turn writes / store diffs vs 292 | 0 / 0 / 0 | 0 / 0 / 0 |
| M3 per-category agreement identical | identical | identical (25/8/12/25/10/10 across ability/teach/called/smalltalk/mixed/control) |
| M3 mechanical owners identical | 292:65 280b:20 282b:5 | identical |
| M3 per-turn 274 vs recorded 273 (reply, writes, store) | 90/90 | 90/90 |
| M3 comparison reruns byte-identical to recorded (292, 280b, 281, 282b) | 4/4 | 4/4 |
| M3 probes 274 vs recorded 273 | report | 4/4 identical |
| M3 verdict field | PASS | PASS |
| M4 274 max deaf < 273 max deaf | yes | yes (0.20781 s < 0.53622 s) |
| M4 274 median deaf ≤ 2 s | yes | yes (0.00485 s; 273 median 0.51420 s) |

## Every move, every miss, deviations

- **Moves: 0.** No turn changed reply, writes, or store vs recorded 273
  (90/90 per-turn identical, 4/4 probes identical, 20/20 invented-turn
  replies identical across arms). No suite/probe moved (none re-run; out
  of scope for this one-change task).
- **Misses: 0.** M1 20/20, M2 20/20, M3 identical on all 11 score fields,
  M4 both bars met.
- **Deviations: 4 (all environmental/procedural, reported).**
  1. OPUS-RULES.txt not found at the tasked path; proceeded per the key
     rules restated in the task (additive-only, offline uv python,
     ≤4 parallel, disk check, counts-only reporting, panels run for M3
     only).
  2. Seal recomputed once before any mark run (turn-wrapper install moved
     after T292T._check following a smoke-build failure; slow stub sleep
     0.25 s → 0.5 s for M4 margin). Seal verified OK before runs; the two
     scripts unchanged since (hashes match the seal).
  3. Machine load 63–142 all evening; free disk 14–73 GB (over the 3 GB
     stop bar). Panel arms run strictly sequentially, one process at a
     time, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1.
  4. A second actor on this box deleted ~/.cache/huggingface/hub at
     ~22:02 (dir mtime) and restored the full MiniLM snapshot at ~22:17
     (files hashed). Run-1 panel (deviating driver: shared workdir,
     292t-config for the 292 arm) scored 76/90 on real replies; run-2
     panel (compliant driver) is VOID — 14–29 CRASH-marker replies per
     arm where the router's MiniLM snapshot load raised FileNotFoundError
     (harness exceptions, not agent replies); run-3 (compliant driver,
     model present, 0 CRASH in 450 turns) is the scored M3 run above.
     No agent file changed between runs (seal hashes hold); comparison-arm
     processes never load 274's code. Slot arm ran 3×, comparison arms 3×
     across the three attempts; only run-3 scored; nothing was tuned on
     any panel output.

## What it means / doesn't mean (plain high-school English)

- Before this fix, when the agent owed itself a sleep AND a user message
  was waiting, the user only got their answer after the whole sleep
  finished (shown: old code slept inside all 20 out of 20 turns, adding
  ~0.5 s each). Now the waiting message is answered first (20 out of 20,
  inbox empty, zero sleep ticks before the reply), and the owed sleep
  still happens on the very next idle tick (tick 1 every time) — sleep is
  never skipped.
- On the real 90-turn blind test the talking line already passed, the
  fixed version answers every single turn exactly the same as 273 —
  same words (90/90), same notebook writes (none new), same saved notes
  (0 diffs). The fix changes timing only, not answers.
- Timing measured: the fix answers in ~5 ms typical (worst 0.21 s) vs
  ~0.51–0.54 s waiting out sleep before — about a hundred times faster
  at the middle, and always faster at the worst.
- This does NOT test the reader/ear stages (deliberately untouched), it
  does NOT grade answer quality (the director checks that), it does NOT
  cover WORK-queue turns (none were pending in any test), and it does NOT
  prove anything about message wordings never tested.

## Detail (counts only, never quoted)

- M1/M2/M4 (scripts/claude_loop274_test.py m124, 20 seeded cases ×
  2 arms, sleep_threshold 5 + 5 prefilled rows, sleep_due True 20/20 both
  arms, 0.5 s never-accepting stub sleeper both arms): 274 turn() left
  counters["sleeps"] at 0 with inbox empty 20/20; 273 turn() ran exactly
  1 sleep tick 20/20. Replies 274 vs 273 identical 20/20. M2 first SLEEP
  tick: 1 in 20/20 (274). M4 deaf seconds: 274 meter median 0.00485 max
  0.20781; 273 wall median 0.51420 max 0.53622.
- M3 (same sealed panel, runner, per-arm configs and scorer the lines
  used; 274 in the 273 slot; seal 2/2 OK before the scored run):
  score file panel-score274.json matches recorded panel-score273.json on
  all 11 fields (dialogs 78, turns 90, agree 90/90, by_cat as above,
  moved [], overlaps [], question writes [], smalltalk writes [],
  store diffs [], old-sheet hits [], owners {292:65, 280b:20, 282b:5},
  verdict PASS). Per-turn 274 vs recorded 273: 90/90 identical (reply,
  writes, store). Comparison reruns byte-identical 4/4. Probes 4/4.
- Local rerun evidence (not pushed):
  artifacts/claude-loop274-20260924/run274/ (5 arm outputs + logs +
  probes + panel-score274.json); M1/M2/M4 raw rows ran to /tmp (counts
  folded into results.json).
