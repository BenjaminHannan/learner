# Sweep test 2 "Watch it think": marks (written 2026-09-29 02:20 UTC, before any real net was read)

Source of the classes and thresholds: design/research/lead-sweep-2026-09-29/SYNTHESIS.md section 3, test 2 (marks from angle 4, `angle-4-stopping.md` T1). Nothing here is changed after a score is seen.

## What is done (one change: none)
No net is changed, trained, tuned or selected. Script `scripts/claude_sweep_s2_think.py` runs each saved loop net for 48 rounds on the 300 **dev** 9x9 mazes (holdout and blind panels are never opened). Per item and round it records: state movement |h_t - h_(t-1)| / |h_t|, stop logit (q > 0.5 means logit > 0), whether the last three whole answers agree, whether the whole answer is exactly right, whether it flipped. Second pass: start from a small random state (std 0.1 x the round-1 state's own std, fixed seed 2929) instead of zeros and compare the round-48 answer with the zero-start one. For a sleep pair the script also applies the OTHER net's stop head to these states.

Nets: `source.pt` (k0), practised loop `k64, k256, k1024, k4096, k16384` for seeds 0 and 1 (the ten "adapted nets"), and `sleep64`, `sleep16384` for both seeds. A net counts only if its recomputed dev counts (right at the ruler's stop, right at fixed depth 16, cap hits, mean rounds) equal the committed `eq-runs/loop-s{seed}-pre/adapt.json` exactly. A net that does not match (for example a rebuilt one, which the distill rebuild showed is not bit-identical) is shown, labelled MISMATCH, and left out of every verdict word.

## Definitions
- "Right at 16": the exact answer at round 16. All of b, c, d are shares of these mazes.
- b = share with stop probability above 0.5 at some round 3..48. c = share where the 3-agree rule is met at some round 3..48. d = share where the ruler's stop fires (both at the same round).
- Movement: pooled median over mazes and rounds. early = rounds 2-6, mid = rounds 14-16, late = rounds 44-48.

## Per-net words (reading of each net)
- HEAD: b under 30%. FLICKER: b at least 70% and c under 30%. MIXED: anything else. (Fewer than 10 right-at-16 mazes: TOO FEW.)
- Movement: CONVERGES-like if late <= 0.25 x early (also reported: late <= 0.05). DRIFTS-like if late > 0.5 x mid. Otherwise "between".

## Aggregate marks (the ten practised-loop adapted nets; a verdict is given only if all ten match the committed nets)
- CONVERGES: late <= 0.25 x early on at least 8 of 10 nets, AND the two starts agree on the round-48 answer on at least 90% of right-at-16 mazes (pooled over the five rungs, in each seed).
- DRIFTS: late > 0.5 x mid on at least 5 of 10 nets, OR the two-start agreement is under 70% in either seed.
- Blocker reading (for Pond / SL / read-rule decisions): the counts of nets that are HEAD, FLICKER, MIXED. A clear reading needs at least 8 of 10 nets in one word; fewer is "mixed, report only".
- This test proves its reading wrong if CONVERGES holds AND at least 5 of the 10 nets have b > 70%, c > 70% and d < 30% (each condition passes but they rarely happen together, which would point at a timing effect not yet found). The SYNTHESIS wording "HEAD and FLICKER both pass on more than 70%, stop under 30%" is read this way.
- What each word points to: HEAD to Pond and SL; FLICKER to a read-rule change; DRIFTS to training past 16 rounds or a contraction penalty; CONVERGES with a HEAD word to head recalibration.

## The sleep16384 cap hits (dev, report-only decomposition with a fixed reading)
For each seed and pair (k64 to sleep64, k16384 to sleep16384) the script fills a 2 x 2 of cap hits on the 300 dev mazes: states of the before-net or after-net, read with the stop head of the before-net or after-net (answers always come from the state's own net). drop = cap(before, before) - cap(after, after). If drop is under 30 of 300 the word is "no drop to explain". Otherwise the drop is split order-fairly (the two parts add to it): head part = mean of the effect of swapping heads on each state set, body part = mean of the effect of swapping states under each head. Word: HEAD SHIFT if only the head part is at least half the drop, BODY/STATE SHIFT if only the body part is, BOTH if both, NEITHER otherwise. Note: the RESULTS-EQ numbers (8 of 300 cap hits, seed 0) are on the holdout, which this test does not open; the dev equivalent is 11 of 300 (adapt.json, seed 0 sleep16384 dev 9x9) and is what gets explained.

## Marks self-check (thread-helper-common.md list)
1. Noise: no gain claim, so no bar to clear; the nets are fixed files, so there is no run-to-run noise. The only stochastic input is the random start (fixed seed 2929, one draw); agreement is a share of 300 mazes, and the 90% / 70% lines are far from each other so a single draw does not decide a verdict near them (untested: a second draw is not run).
2. Every-seed reading: CONVERGES needs both seeds' agreement; DRIFTS is triggered by either seed. Rejection of the reading needs 5 of 10 nets, not one.
3. Comparator: none needed; the test compares each net with its own earlier rounds (early / mid / late), and each sleep net with its own before-net.
4. Plain-net row: not applicable (the plain net has no rounds or stop head); this test says nothing about plain vs loop.
5. F_few: not applicable, no adaptation is scored.
6. Sleep gates: not applicable to a pass/fail; the sleep decomposition is a single dev read of the committed sleep nets (three-draw means are for new sleeps, none are run here).

Scope: mazes only, dev only, practised loop only. Claims stay labelled "diagnostic, dev panel". Keep the small card experiments and the village model out of every claim.
