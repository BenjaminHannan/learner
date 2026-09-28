# T3 pass marks: does replaying the newest nights' puzzles more often help a three-night sleep?

Written 2026-09-28 22:13 UTC (`date -u`) by Director helper "sleep tests sealer" (Claude). Sealed before any run of this test: no `runs/` folder exists here and no `dirt3-seed*.json` exists anywhere in the repo (checked 22:13 UTC).
Marks are never changed after a score is seen. Marks as code: `scripts/claude_dir_t3_marks.py` (selftest: 9 cases pass). Reasons for every number: DESIGN.md. Seal: SEAL.md, SEAL-code.sha256.txt.

Scope: the full-size loop reasoner (the 4 checkpoints from 358u, seeds 13 to 16), code-made sums and Latin grids, H6's three-night design (300-step nights, lr 3e-5, batch 256, half the batches from the rehearsal stream, half from day puzzles).
Not the small card experiments, not the village model. Training data: code-made puzzles and code answers only. Reuses `scripts/claude_slp358n3_nights.py` unchanged; does not duplicate the keep-old-skills leads or "Deep or just big".

## Disclosure that shapes the test (stated first)
In slp-358n3's and H6's nights the day half of night n draws only from night n's own 300 puzzles per kind, and the three nights use the **same two kinds** (sums size 12, grids size 7). So there is no stored older night to weight, and no night-specific skill:
the draft's "newest-night skills gain" cannot be scored as drafted. The smallest testable version adds a night memory: the day half of night n draws from the puzzles of nights 1..n, and the arms differ **only in the weight of each night**. The tests are the fixed day tests (fresh puzzles of the same two kinds, never in any night).
So T3 can show that recency weighting helps or does not help **these** kinds; it cannot show a trade-off between different nights' skills (that needs a different kind per night: an untested follow-up, DESIGN section 6).

## The one change: the night weights (everything else identical, paired draw by draw)
| arm | weights of nights 1 : 2 : 3 (night n uses nights 1..n) |
|---|---|
| S | 0 : 0 : 1 (only the current night: slp-358n3's S recipe, run through this code) |
| U | 1 : 1 : 1 (uniform) |
| **W** | 1 : 2 : 4 (newest weighted) |
N (no night) is scored once per seed. 4 seeds (13, 14, 15, 16) x arms S, U, W x **3 draws** (rounds, batch plan and rehearsal stream re-drawn: seeds 59100 + seed + 1000 d, 59200 + 10 seed + day + 1000 d, 100 + seed + 1000 d). Grading after night 3, on slp-358n3's fixed tests (its `sizes.json`, test seed 58630).
Counts are right answers of N: day_sums, day_grids 400 each; harm_sums4, harm_grids5 300; rep_sums6/8/10, rep_grids6 200.

## Comparator (the fair one)
Per seed, the higher 3-draw mean of **S and U** on the test in question. (S is the loop with no memory, U the loop with a memory and no weighting: the baseline loop and the loop with the episodes.) N is a floor, not a comparator.

## Marks (day_grids is the gain row; d = mean of W's 3 draws minus the higher of S and U; margin = max(6, 2 x SE), SE = sqrt((var W + var of that comparator's draws) / 3))
- **M1 (the gain):** mean of d over the seeds >= **24 of 400 on day_grids** AND d > margin on at least 3 of 4 seeds (all of them if only 3 seeds finish).
- **G1 (sums, a gate, not a gain row):** W's day_sums >= the higher of S and U - 12 on at least 3 of 4 seeds. Sums have only 12 to 24 of 400 left above S (S after night 3: 376 to 388), so a +20 gain cannot exist there; the draft's +20 on both kinds is dropped.
- **G2 (a net with no night cannot pass):** W's day_grids >= N + 40 on every seed (S - N was +69 to +169, recounted).
- **G3 (no harm, slp-358n3's limit):** W's harm_sums4 and harm_grids5 (mean of 3 draws) >= N - 6 on every seed.
- **G4 (retention, slp-358n3's limit):** W lost <= 15 of 300 harm items after each night, every draw, every seed.
- **G5 (old skills not at the ceiling, H6's M3c):** W's rep_sums6, rep_sums8, rep_sums10, rep_grids6 (mean of 3 draws) >= N - 15 of 200 on every seed.
- **INTEGRITY:** the JSON flags `night1_batches_identical_SUW` and `plan_identical_U_W` are true for every draw (night 1 draws from one night, so S, U, W must be identical; U and W share every random number). Otherwise the run is VOID.
- A seed counts only if all arms, draws and nights finished; fewer than 3 seeds = VOID; a dead seed is reported, never replaced.
**PASS = M1, G1 to G5 and INTEGRITY.** It says: with the same steps and the same data, weighting the replay toward the newest night beats both no memory and a uniform memory on fresh grids, by more than noise, at no cost to old skills. It does not say more nights or different kinds behave alike.
**PROVED WRONG (every-seed reading):** W's gain d is <= +6 of 400 on every seed (INTEGRITY met). A gain on some seeds that fails a gate is NOT SHOWN, never "wrong".
**NOT SHOWN:** anything else. Report only: W clearly below the comparator (d < - margin) on how many seeds.

## Report only
Every arm and draw after nights 1, 2, 3 on every test, "x of N", 4-seed means and ranges; day tries; U minus S and W minus U per test; each arm's score on its own night-1, 2, 3 puzzles (first 100 per kind) after night 3; minutes, torch, GPU.

## What this does not license
Nothing about different kinds per night, more than 3 nights, the card experiments, the village model or product nights; nothing about the brain beyond "weakly stored items are replayed more" being a reading (untested here).

## Marks self-check (Ben's list, one line each)
1. **Bars above the measured noise.** Recounted from `artifacts/claude-slp358n3-20260927/runs/s13..s16/slp358n3-seed*.json`: S after night 3 across 4 seeds: SD 5.1 (day_sums), 6.4 (day_grids); the same arm on different nights (S night 1 or 2 against night 3, 8 cells): SD 11.2 and 11.7; arms that should barely differ (R minus N, 12 cells): SD 10.3 and 19.7 (range -12 to +49 on grids). Bar 24 = 2 x 11.7, above the same-arm night-to-night SD twice and above the R - N grids SD. "H6's re-run spread": **not available** (no dir-h6 run exists yet at 22:13 UTC); this test measures its own: 3 draws per arm, and margin uses their SD. The gain bar is below the room (day_grids S 353 to 366: 34 to 47 left).
2. **Every-seed reading:** PROVED WRONG only if no seed gains (<= +6 on all); gains that break a gate are NOT SHOWN. Yes.
3. **Fair comparator:** higher of S and U per seed. Yes.
4. **A row a plain net cannot pass, and not memorising:** G2 (N + 40: a no-night net cannot pass). The tests are fixed puzzles excluded from every night (`block` = tests, dev, panels; same as slp-358n3), so memorised night puzzles cannot pass them. No plain same-size net exists in this harness (only the loop checkpoints): limit disclosed.
5. **F_few (k = 1..64) beside F_eq:** **not applicable here.** F is the few-example maze score of the fewex harness; this harness has no maze and no k. The night's day sizes (12 sums, 7 grids, 300 puzzles a night) are not a few-example setting. If the Director wants a stand-in, a maze row needs the fewex nets and is T2's M3.
6. **Sleep gates use the mean of 3 draws, margin max(6, 2 x SE):** yes (M1, G-rows use the 3-draw means).

## Predictions (before any run; guesses)
PASS 8%. PROVED WRONG 60%. NOT SHOWN 32%. Reason: the kinds do not change between nights, so an older night's puzzles are exchangeable with the newest night's; weighting can only matter through how far the net has already drifted.

## Blind recount
A separate step, given only this file and the raw `dirt3-seed*.json`, recounts every mark before RESULTS.md is written; `python3 scripts/claude_dir_t3_marks.py report` is the same rules as code.
