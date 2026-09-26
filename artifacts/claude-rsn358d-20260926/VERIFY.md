# rsn-358d blind recount (2026-09-26)

## Verdict: INCONCLUSIVE on both seeds (G0 not met). Agrees with RESULTS.md.

G0 fails because the loop arm reaches 210/300 on only one of the three practised kinds (sums4) on each seed. By PASSMARKS-v2 the run is neither PASS nor FAIL. The proved-wrong clause needs G0 met, so it is not triggered. If G0 were set aside, the counts would satisfy it: loop minus plain is at most +5 on every bigger test on both seeds.

I counted from `tests.json` on origin/builder-outbox (commit 38134bc16) before reading RESULTS.md. Marks come from origin/main: `artifacts/claude-rsn358d-20260926/PASSMARKS.md` and `artifacts/claude-rsn358a-20260925/PASSMARKS-v2.md`. I did not open `artifacts/claude-rsn358a-20260925/tests/`.

## Marks table (counts /300)

| mark | seed 3 | seed 4 |
|---|---|---|
| G0: plain sums4/grids5/numbers4 | 300/236/16, 2 kinds at 210 or more | 300/241/10, 2 kinds |
| G0: loop sums4/grids5/numbers4 | 300/109/1, 1 kind | 298/91/1, 1 kind |
| **G0** | **NOT MET (INCONCLUSIVE)** | **NOT MET (INCONCLUSIVE)** |
| G1: loop−plain on sums6 / grids6 / numbers5 | 131−239 = −108 / 58−187 = −129 / 0−0 = 0 | 94−153 = −59 / 36−186 = −150 / 0−1 = −1 |
| G1 | fail | fail |
| G2: loop−plain on sums4 / grids5 / numbers4 | 0 / −127 / −15 | −2 / −150 / −9 |
| G2 | fail (grids5, numbers4) | fail (grids5) |
| G3: own stop vs (fixed 16 − 5) on sums6 | 131 vs 132, fail | 94 vs 83, pass |
| G3: grids6 | 58 vs 52, pass | 36 vs 31, pass |
| G3: numbers5 | 0 vs −5, pass | 0 vs −5, pass |
| G3: mean rounds on sums6 vs sums4 | 6.08 > 5.09, pass | 6.50 > 5.60, pass |
| G3 | fail | pass |
| Proved-wrong: loop−plain ≤ +5 on all 3 bigger tests | true (−108, −129, 0), but G0 not met | true (−59, −150, −1), but G0 not met |
| Overall | INCONCLUSIVE | INCONCLUSIVE |

Report-only tests: sums8 was loop 21 vs plain 120 on seed 3 and 6 vs 33 on seed 4; grids7 was 10 vs 69 and 3 vs 73.

## Disagreements with RESULTS.md

**None on any number.** I checked every count, difference and mark by script against tests.json: the G0 to G3 tables, the per-seed tables, all 16 rows of the fixed-round and any-round tables, mean rounds, right_v1_rule, final training exact_by_kind, ce, dev counts, weights and minutes. All match.

These RESULTS claims go beyond the numbers or cannot be checked:
1. **"The 75,972-puzzle pool lifted the plain arm above 358a's 0-5 range."** The seeds also changed (3 and 4 instead of 1 and 2). 16 and 10 out of 300 are small counts. The cause is suggested, not shown.
2. **"Giving both nets 70x more number practice cured memorising without creating real skill."** For the loop arm, "cured memorising" overstates it. The loop learned nothing on numbers4 even in training (0.001), and it also fell badly on numbers3, whose data did not change (see the training notes). The plain arm did gain a little held-out skill (16 and 10, against 0 to 5 before).
3. **"Undertrained at practised size."** This is the label the marks give an INCONCLUSIVE run, but the logs do not show a net that simply needed more steps. Loop grids5 went only 0.338→0.350 (s3) and 0.304→0.308 (s4) from step 50k to 60k, which is a plateau far below 358a's loop (about 0.81).
4. **"tests.json counts match the eval logs exactly (verified per run)."** Cannot be checked. By RESULTS' own deviation 4, the eval logs were thrown away with the rental.
5. **GPU model, utilisation, memory, rental IDs and dollar rates.** No record in the repo backs these. The arithmetic is consistent: 03:44:46 to 04:34:03 is 0.821 h, and 0.821 h × $0.4852 = $0.398, which rounds to about $0.40. The first rental to the destroy, 03:39:42 to 04:34:03, is 54 min.
6. **The wall-clock times do not fit the minutes.** `minutes` is timed from process start (scripts/claude_rsn358a_run.py lines 266 and 322). Launching at about 03:56Z plus 29.6 min puts plain final.pt at about 04:25:36, not 04:21. Adding 35.2 min puts loop at about 04:31, not 04:26. Either the launch was about 5 min earlier or the final.pt times are wrong. This does not change the cost figure, which comes from the rental window.
7. **Omission.** RESULTS does not compare the loop's training curves with 358a's. That comparison is the clearest finding in the logs (see below).

## Checks

- **SEAL-run.sha256.txt:** 4 lines, and every hash is 64 lowercase hex characters (`^[0-9a-f]{64}  W/(loop|plain)-s[34]/final.pt$` matches all 4). The checkpoints were discarded, so the hashes cannot be checked against files.
- **SEAL-code.sha256.txt (on main):** all 6 hashes match the files on origin/main, recomputed from the blobs. The local working tree matches main for these scripts. `scripts/claude_rsn358d_run.py` changes only `Source.four` (the 4-number practice pool), as registered.
- **Train settings:** all four runs have steps 60000, batch 256, lr 0.0003, warmup 1000 and latin_pool 20000. These equal 358a's loop-s1/s2 and plain-s1/s2 train_summary.json. Weights are the same too (loop 6,438,302; plain 6,385,149).
- **Minutes:** loop-s3 35.2, plain-s3 29.6, loop-s4 35.3, plain-s4 29.6, against 358a's 32.2/25.9/32.9/25.8. The extra ~3.5 min fits the pool build (the logs say "data ready in 29-30s") plus four jobs sharing one GPU. Costs: see item 5.
- **Timing:** PASSMARKS.md and the code were committed to main at 2026-09-26T03:17:10Z, before the first rental (03:39:42Z) and before training (about 03:56Z). The header's own "03:45 UTC" is later than its commit, a small header error. The results were committed 04:38:36Z.

## Training curves: did the loop learn every kind more slowly, or only numbers?

**Every kind (shown in the logs).** Each 358d run has 120 log rows. The plain arm's curves on sums, grids and numbers3 are almost the same as 358a's plain arm. The loop arm is much slower on every kind, including the ones whose data did not change.

First step where training exact reached 0.5 / 0.9 ("never" = not by 60k):

| kind | 358a loop s1 / s2 | 358d loop s3 / s4 | 358d plain s3 / s4 | 358a plain s1 / s2 |
|---|---|---|---|---|
| sums4 | 5000/7500 · 4500/6500 | 12000/19500 · 13000/19500 | 3500/4500 · 3000/4000 | 3000/4000 · 3000/4500 |
| grids4 (≥0.5) | 3500 · 3500 | 31000 · 34000 | 3000 · 3000 | 3000 · 3000 |
| grids5 (≥0.5) | 4500 · 4000 | never · never | 5000 · 5500 | 5000 · 5000 |
| numbers3 | 7500/10500 · 7500/11000 | never · 44000/never | 6500/8500 · 6000/8000 | 5000/7500 · 5000/7500 |
| numbers4 | 10000/18500 · 10500/18500 | never · never | never · never | 6500/10500 · 6500/10500 |

Final training exact at 60k (grids4 / grids5 / numbers3 / numbers4; sums4):
- 358a loop s1: 0.741 / 0.815 / 1.000 / 1.000; 1.000
- 358d loop s3: 0.548 / 0.350 / 0.457 / 0.001; 0.990
- 358d loop s4: 0.537 / 0.308 / 0.569 / 0.001; 0.991
- 358d plain s3: 0.745 / 0.831 / 1.000 / 0.278; 1.000
- 358d plain s4: 0.748 / 0.829 / 1.000 / 0.273; 1.000

At step 5000, 358d loop had sums4 at 0.010 and 0.004, against 358a loop's 0.517 and 0.728. Its training ce ends at 0.50 and 0.44, against 358a loop's 0.061. Loop numbers4 training exact stays at 0.000 to 0.001 for all 60k steps.

Notes:
- **Suggested:** the harder, larger 4-number pool damaged the loop arm's learning of everything, not only numbers. It was the one registered change, and the plain arm, which got the same change, was unaffected on the other kinds. **Untested:** the mechanism (for example, loud gradients from unlearnable number items flooding a shared recurrent block, or the stop head being trained on items it never solves), and whether seeds 3 and 4 alone could explain it. The fact that both loop seeds match each other and plain matches 358a argues against seeds.
- The loop's stop rarely fires on grids. It ran to 48 rounds on 195/300 grids5 and 267/300 grids6 items (s3), and on 300/300 of numbers4 and numbers5.
- The card-experiment results here say nothing about the village model.
