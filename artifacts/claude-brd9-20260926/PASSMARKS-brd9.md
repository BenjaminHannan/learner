# brd-9: do three nights in a row, each practised by the model that slept the night before, clear problem 7's bar? (registered 2026-09-26 15:56 UTC by `date -u`, before any run)

Source: problem 7 (turn lucky hits into lasting skill), still unsolved. brd-5, 6 and 7 each tested ONE night. In all
three, sleep beat no sleep (95% intervals above 0), but it cleared +24 of 240 in every seed only once (brd-6: +51 to +54;
brd-5: +13 to +22; brd-7: +11 to +23). Ben's loop runs every night, and each day's practice is done by the model that
slept the night before. brd-8 (verified, main 7462451bd; registered after its result) found that WHICH model collects
night 2's hits makes no clear difference at equal exposure (ITER − CTRL −9 / +9 / −1, NOT SHOWN), while two nights'
hits beat no sleep by +35 / +53 / +58 on a panel whose base reached only 108 (G7 met). brd-9 tests the loop as it
would really run, three nights, on a panel with less easy room.
Why the bar changes (thread manager's question, 14:21 UTC, decided by this thread): a fixed +24 of 240 mostly
measures how much room the panel leaves. The base model already reached 106/95/116 of the 160 three-number puzzles in
brd-5/6/7 but only 17/13/19 of the 80 four-number ones, and the three-number gain swung from +5 to +35 while the
four-number gain stayed +6 to +19. So brd-9's PASS bar is set on the puzzles the base model cannot reach, and its
panel leans toward four-number puzzles. The old +24 is still reported as its own line (G7).

Procedure: scripts/claude_brd9.py (docstring). ONE change against brd-5/6/7's one-night recipe: the loop runs for
three nights instead of one.
- Practice sets: A, B, C = puzzles(seed 9, 1200) split into three parts of 400. A and B are brd-8's sets; C is new.
- Night 1: the base model practises A. N1 = LoRA from base on A's examples.
- Night 2: N1 practises B. N2 = fresh LoRA from base on A + B examples.
- Night 3: N2 practises C. N3 = fresh LoRA from base on A + B + C examples.
- Every night retrains from base on everything kept so far, 3 epochs (replay of all earlier days).
- Hits: greedy answer when right, else the first of 30 rule-kept blurts at the DEV temperature (1.0 vs 1.5 rule,
  blurt-1 DEV panel); exact checker. LoRA r16, lr 2e-4, batch 8, seeds 0/1/2. 30 samples per test puzzle.
- One GPU run on a rental. That run is the registered result.

Test panel FIXED NOW: artifacts/claude-brd9-20260926/test_puzzles.jsonl (md5 9e07a74ebc5914b6f2cd86da219d1188):
240 puzzles (80 with 3 numbers, 160 with 4 numbers and target 24; 217 hands), built by `claude_brd9.py --make-panel` with seed 802.
It excludes all 1,200 practice puzzles, the DEV panel, and the brd-5, 6, 7 and 8 test panels. The 3-number world is
small (1,346 solvable puzzles with numbers 1-9 and targets 5-40); those sets use 1,180, so the 80 3-number test
puzzles are drawn from the 166 left (enumerated, shuffled with seed 802). The 4-number part is the usual recipe
(puzzles(seed 802, 1500), overlap dropped, first 160). Later tests need a wider puzzle world.

Measure: cov@30 = test puzzles with at least one correct sample in 30 (= distinct puzzles reached). Intervals: 95%,
bootstrap over number hands (2,000 draws), seed-averaged (claude_blurt5s.boot_ci).
Claims, all fixed now. "Unreached" = test puzzles the base model does not reach in 30 samples (240 − base cov@30).
The bar = 0.20 × unreached (a fifth of the room left; about +21 to +26 for the bases seen so far).
- PASS: N3's cov@30 ≥ base cov@30 + bar in EVERY seed (each seed vs the one base run), AND the 95% interval for
  N3 − base is above 0.
- G7 (problem 7's old bar, its own line, reported as met or not met): N3's cov@30 ≥ base cov@30 + 24 in EVERY seed,
  AND the 95% interval for N3 − base is above 0.
- NIGHTS (its own line, reported as met or not met; not part of PASS): N3's cov@30 ≥ N1's cov@30 + 12 in EVERY seed
  (seed k vs seed k), AND the 95% interval for N3 − N1 is above 0.
- Proved wrong: the upper 95% bound of N3 − base (in points of the 240) is below 100 × bar / 240, so three nights
  cannot reach the bar on this panel.
- Otherwise: NOT SHOWN.
- Inconclusive: fewer than 40 night-1 wins (blurt hits, not greedy answers).
Reported, not marks: for base, N1, N2 and N3, cov@1, cov@30 split by 3-number and 4-number (and each split's gain as
a share of its own unreached puzzles), lucky samples;
own/win/miss counts for every night and seed; the intervals for N1 − base and N2 − base. practice.json saves every
practice outcome.

Limits, stated now:
- N3 has seen three times the puzzles and three times the training steps of N1. That is what three nights are, so
  it does not weaken G7. It does mean NIGHTS cannot say whether the gain came from the slept model's practice or
  just from more hits; brd-8 found no clear difference between those at equal exposure.
- One panel. brd-5/6/7 showed the size of the gain varies a lot by panel (+11 to +54 for one night), so a PASS here
  is one panel's result and a replication on a fresh panel would be the next step.
Prediction (the thread's, written before the run): base cov@30 about 95 (unreached about 145, bar about 29);
N1 − base about +15 to +25, N3 − base about +25 to +35; PASS at a bit under even odds.
Smoke before sealing (not results): real MiniCPM5-1B on CPU (10 practice puzzles a night, 2 test puzzles, 4 samples,
1 seed, 1 epoch) ran base, N1, night-2 practice, N2 and night-3 practice before an 83-min timeout; a fake-solver run
(scratchpad b9_fake.py) ran every line of run() to the summary, CIs and transfer file.

## Addendum T (written 2026-09-26 15:43 UTC by `date -u`, before sealing and before any run): transfer row, report only
Asked by the Thread manager after Ben's 15:41 UTC goal ("apply skills learned to other places").
Question: does skill trained from hits on the practised kinds help on a kind that got NO hits?
- Transfer set FIXED NOW: artifacts/claude-brd9-20260926/transfer_puzzles.jsonl (md5 39ffe6e4d22da7bbd90bb613fece63de):
  80 puzzles, 4 numbers from 1-13 with a target from 10-40 OTHER than 24 (seed 803, `claude_brd9.py --make-transfer`).
  No practice set has this kind: every 4-number practice puzzle has target 24 and every 3-number one has numbers 1-9.
- Measured for base, N1, N2 and N3 (every seed), 30 samples each: cov@30 and the 95% interval (hand-grouped
  bootstrap) for N1 − base, N2 − base and N3 − base. Saved in transfer_streams.json.
- Report only: no PASS, no bar, no verdict. It is read as "transfer seen" only if the N3 − base interval is above 0.
