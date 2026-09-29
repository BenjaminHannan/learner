# Pond: charge the loop a tiny price per thinking round, so its stop fires

Written 2026-09-29 (`date -u` 00:08 at the last edit; work began 23:59 UTC 09-28) by helper "pond" (thread "Charge for thinking"), on main `4307fb572`. **Nothing here has been run on a practised net.** Order followed: DESIGN idea, then PASSMARKS.md (commit `548783a48`) before any code, then plug-in, marks script and selftests. Labels: **shown** = counted from a file or the code; **suggested** = my reading; **untested** = nobody has run it. Counts are "x of N". The small card experiments and the village model are not part of any claim.
Serves finish-line item 2 (decide its own thinking time on a new kind).

## 1. Plain words (for Ben)
Your idea: on a new kind of puzzle the loop never decides to stop (300 of 300 new mazes use all 48 rounds at most rungs, seed 0), so charge it a very small price for each extra round. Looping more only pays if it makes the answer better, so it should stop once more thinking stops helping. Keep the price tiny, just enough that "go on forever" stops being free.
One catch I built around: a price alone would push the stop to fire everywhere, right or wrong. So the same term also asks "how wrong am I if I stop here?" (the loop's own error at that round) and the stop learns the trade between the two. That is PonderNet's recipe (a stop that is a learned probability per round, trained on expected error plus a price on expected rounds), and it needs no "am I right?" label from the puzzle beyond the maze answers the adaptation already uses.

## 2. Facts this rests on (shown)
- The ruler's stop: from round 3, stop at the first round where the stop probability is above 0.5 **and** the last three predictions agree; otherwise the 48-round cap (`scripts/claude_fewex_bench.py:76-78`).
- The baseline maze adaptation has **no stop loss** (`claude_fewex_bench.py:205`, comment "no maze stop-head loss"); practice trained the stop only on sums and grids with "exactly right now" (`claude_fewex_net.py:171-172`).
- Baseline cap hits, dev 9x9, k = 64, 256, 1,024, 4,096, 16,384: seed 0 300, 300, 300, 300, 143; seed 1 265, 300, 61, 196, 194 (recounted in `PASSMARKS.md`; I checked them again in `claude_dir_pond_marks.py selftest`).

## 3. The one change (`scripts/claude_dir_pond_stop.py`, a plug-in for the equal-practice harness, used unedited)
`Net` **is** `claude_fewex_net.Net` (1,645,726 weights, same state dict, no new number). `Learner` subclasses the harness Learner and overrides only `maze_batch`. In each of the 4 optimizer updates per batch there are 5 rounds (3 free, 2 with gradient), as in the baseline. The plug-in keeps the baseline loss (mean of the 2 gradient-round cross-entropies) and adds one term:

    hazard_t = sigmoid(stop logit at round t)                        t = 1..5 of the update
    p_t      = hazard_t x (1 - hazard_1) x ... x (1 - hazard_(t-1))   (the last round takes the rest of the mass)
    term     = mean over mazes of [ sum_t p_t x CE_t   +   LAMBDA x sum_t t x p_t ]

CE_t is that maze's own mean cross-entropy over its fill cells at round t, treated as a constant; the state the stop head reads is detached. So **the term trains only the stop head's 257 numbers (weight and bias) and nothing else** (`selftest` check 3: gradient reaches exactly `halt.weight` and `halt.bias`), and the body's gradient is the baseline's. With clipping switched off the body is bit-identical to the harness Learner after 8 updates (check 4); with the real clip the largest body difference after 8 updates was 4.8e-07 (the clip norm is shared with the stop head's small gradient; suggested to stay negligible, and the marks read the fixed-16 body reading to catch it).
Sum-of-rounds times LAMBDA is the "extra compute" penalty. Everything else is the harness's: start net, pool, batches, 2,048 updates per rung, optimizer, sleep, scoring.

**Arms:** LAMBDA = 0.001 (a), 0.004 (b), 0.016 (c), and 0.0 (z, control, report-only). Cross-entropy per cell is what LAMBDA is compared with, so LAMBDA is "nats of error I will trade for one more round". I could not calibrate against a practised net here (untested), so I spread three values 4x apart around "tiny"; Ben's instruction is to use only as much as it takes, so a passing arm's recommendation is the smallest passing one.

## 4. How this differs from H12 and from "Stop without labels" (shown from their DESIGN files)
| | H12 (`h12-stop-1-dev`) | SL (stop without labels) | Pond (this) |
|---|---|---|---|
| Stop target | "answer exactly right now" (0/1 label, BCE) | "my answer equals my round-48 answer" | none: the stop is a hazard trained by expected error + LAMBDA x expected rounds |
| Where trained | maze adaptation | sums and grids practice (new source net) | maze adaptation |
| What is new | supervised stop loss | label-free target | a **price on rounds**, and an unsupervised halting distribution |
| Body touched? | yes (loss reaches shared blocks) | yes | no (stop head only, by construction) |
| Judged on | stop fires, no failure | same | cap hits < 150 of 300 on 4 of 5 rungs plus accuracy rows and a plain-net row |
H12 asks whether a labelled stop loss fires the stop; pond asks whether a *price on thinking* can do it without any "am I right" label and without touching the body. A passing H12 and a passing pond are compatible. The z arm (LAMBDA 0) separates "the price matters" from "training the hazard on expected error alone is enough" (the words in PASSMARKS).

## 5. Marks in one paragraph (full text in PASSMARKS.md, fixed before any code)
Per seed a rung passes S1 when cap hits < 150 of 300 (baseline: 1 of 5 rungs in each seed); 4 of 5 judged rungs needed. S2: learned read within 6 of its fixed-16 read, 4 of 5 rungs. A1/A2: F_eq and F_few not more than 7.0 / 8.5 points (2 x noise SD 3.33 / 4.17) below the baseline's higher read, both seeds. P: F_eq at least 10 points above the plain same-size net (which scores +0 by construction), both seeds. PONDER WORKS needs all of these in both seeds. **WRONG in this form** only if arms a, b, c all fail S1 in both seeds.

## 6. Compute
Mac CPU, strict fp32, 1 thread, $0, no vast, no rental, four jobs (a, b, c, z) of two processes each (seeds 0, 1), then one report-only doubt job (H12's `claude_dir_h12_doubt.py`, unedited). Baseline dev loop jobs took 10,149 s and 10,123 s (169 minutes) with eight running at once (H12 DESIGN section 6). The extra work per update is five stop-head evaluations and two head reads; the head is one 256-by-vocab layer on 81 cells, so I expect about the baseline's time (untested). On this box the harness smoke (one rung, 8 updates, plus its scoring) took 236 s (`SMOKE-harness.log`). Queue order: b first (the middle value), then a, c, z. Everything waits behind the jobs already queued.

## 7. What could not be tested, risks (all untested unless marked)
- No practised net exists here (source checkpoints are on the Mac). Selftests run on random-init nets: formula against a hand loop, gradient signs, gradient only to the stop head, body bit-identical without clipping, update counts, scorer runs (`SELFTEST-plugin.log`, `SELFTEST-marks.log`, and three mutations that each make it fail: `SELFTEST-mutations.log`). `smoke_harness.py` ran the harness's own `adapt_job` with arm b on a fake source net for one rung of 8 updates (`SMOKE-harness.log`). Nothing says how a practised net's stop learns.
- **Windowed, not whole-trajectory.** The halting distribution covers the 5 rounds of one update, not the 48-round run; the update's first round may really be round 1, 6, 11 or 16 of the carried state. A PonderNet over the whole trajectory would need every round with gradient; that is a different (and more expensive) test. Rounds 5, 10, 15, 20 get no direct hazard gradient (the last round of a window takes the rest of the mass), and the ruler reads the stop at every round up to 48, including rounds this term never trained (as in H12, where rounds 1-3, 6-8, ... have no stop loss).
- The stop head is one linear layer on the mean-pooled state. If "I am done" is not linearly readable there, no price will make it fire (H12 has the same limit); a WRONG in all three arms would say exactly that or "LAMBDA range missed", and I cannot tell those apart from the marks. Each arm's mean rounds and cap counts are reported for that reading.
- Per-cell cross-entropy is an averaged, soft error; a maze with one wrong cell has a small cost. If the cost curve over rounds is flat, the stop fires at the first round the ruler allows (round 3), which S2, A1 and P are there to catch.
- The ruler still needs three agreeing predictions, so the stop fires only where answers settle; this test does not touch that rule (changing it needs Ben and an addendum, H12 section 7).
- Two seeds, dev panel only, holdout unopened, one architecture. Three arms are three looks; the marks say how a single passing arm is read ("isolated").
- Sleep and old-kind rows are report-only (single sleep draws move by more than any gap; H12 PASSMARKS).

## 8. Files
`PASSMARKS.md`, this file, `SEAL-code.sha256.txt`, `SELFTEST-*.log`, `SMOKE-harness.log`, `smoke_harness.py`; scripts `claude_dir_pond_{stop,a,b,c,z,selftest,marks}.py`; queue jobs `handoff/queue/pond-{a,b,c,z}-dev.md` and `pond-doubt.md`. Explainer page: see the thread.
