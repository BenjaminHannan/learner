# Blind recount, slp-358n3 (read only PASSMARKS.md, 4 seed JSONs, resume.json, resume.log; arithmetic in score.py)

Labels: shown = read or computed directly from the records; suggested = inference; untested = the record cannot show it.

## Setup (shown)
- Graded arms: S, R, Z, N on seeds 13, 14, 15, 16 (PASSMARKS lines 46-49, 59). Grading is "after night 3" (line 59), i.e. morning["3"]. L (6,000-step night) is report only, seeds 13 and 14 only (lines 20, 48-49); seeds 15 and 16 hold no L (4 of 4 JSONs: L present in 2 of 4, as designed).
- Day sizes in all 4 JSONs: sums 12, grids 7 (the largest candidates). Base 4-seed mean on day tests (morning.base, 400 items): sums 263, 228, 240, 298 = mean 257.25; grids 293, 279, 284, 184 = mean 260.0. Both above 240, so the "none qualifies, take largest" rule is consistent with the records (shown, on the 400-item test; the dev-set 300-item scoring that actually chose the size is not in the JSONs, untested).
- Excluded day items: 0 of 4 seeds nonzero (shown). Night settings in cfg: 300 steps, batch 256, lr 3e-5 on 4 of 4 seeds (shown). torch 2.11.0+cu128, NVIDIA GeForce RTX 3090 on 4 of 4; minutes 53.5, 53.3 (with L), 14.6, 14.7 (shown).

## M1 learns from the day: S - R after night 3 (PASSMARKS line 62)
Mark: mean >= +20 and >= +20 on 3 of 4 seeds, each kind; ceiling (S and R both >= 360) and floor (both <= 40) make a seed uninformative.
| kind | s13 S/R (diff) | s14 | s15 | s16 | mean | seeds >= +20 | informative seeds |
|---|---|---|---|---|---|---|---|
| day_sums | 381/271 (+110) | 388/208 (+180) | 379/250 (+129) | 376/300 (+76) | +123.75 | 4 of 4 | 4 of 4 |
| day_grids | 366/281 (+85) | 361/315 (+46) | 353/279 (+74) | 353/222 (+131) | +84.0 | 4 of 4 | 4 of 4 |
No seed hit the ceiling for both arms (R was below 360 everywhere) and none the floor. M1 met on both kinds (shown).
Report-only mornings (shown): S-R after night 1 sums +97/+110/+116/+53, grids +30/+59/+34/+156; after night 2 sums +105/+138/+120/+70, grids +34/+72/+36/+130 (seeds 13-16). All 16 of 16 values >= +20.

## M2 not a placebo: S - Z after night 3 (line 63)
Mark: >= +20 on 3 of 4 seeds, each kind, same ceiling/floor rules.
- day_sums S - Z: +381, +388, +379, +376 (Z = 0 of 400 on 4 of 4 seeds). 4 of 4 pass.
- day_grids S - Z: +366, +361, +353, +353 (Z = 0 of 400 on 4 of 4 seeds). 4 of 4 pass.
Ceiling/floor: floor needs both arms <= 40; S is >= 353, so all seeds informative. M2 met (shown).
Caution (suggested): Z scoring exactly 0 of 400 on day tests, and 0 of 200 on several report sizes, means the placebo night wrecked the net rather than acting as a mild control. The mark as written is met, but it is a very easy bar here. Z's harm sums after night 3: 252, 300, 300, 298 of 300 (recovering from big night-1 losses of 175, 17, 229, 138). Why Z collapsed is untested.

## M3 no harm: S on harm_sums4 and harm_grids5 (line 64)
Mark: S >= N - 6 every seed, each test.
- harm_sums4: S = 300 on 4 of 4 seeds, N = 300 on 4 of 4 (need >= 294). Pass 4 of 4.
- harm_grids5: S = 300 on 4 of 4, N = 300 on 4 of 4 (need >= 294). Pass 4 of 4.
M3 met (shown). Note (suggested): both tests sit at 300/300 for N, so they are at the ceiling and can detect only large harm; the marks define no ceiling rule for M3, so it stands as written.

## M3b retention: S "lost" <= 15 of 300 (line 65)
S lost = 0 on harm_sums4 and 0 on harm_grids5 for every seed (4) and every night (3): 24 of 24 test-night cells at 0, max 0 <= 15. M3b met (shown).
(Report, shown: R lost max 1; N lost 0; Z lost up to 229 on sums4 after night 1; L lost max 1, seed 13 night 1 grids5.)

## RESUME (line 66)
Mark: weights and optimizer identical after night 2 (torch.equal on every tensor) AND hashes of the 150 batches after the resume equal the straight run's batches 150-299; settings: CPU float32, deterministic algorithms, 4 threads, arm S, seed 13, nights 1-2, 300 steps, batch 256, lr 3e-5; run 2 stops at step 150 of night 2.
resume.json / resume.log (identical content, shown): weights_identical true, optimizer_identical true, batches_after_resume_identical true, first_resumed_batch [2, 150, "86558c6a004c1c67"], return_codes [0, 3, 0], stop_step 150, night_steps 300, batch 256, torch 2.11.0+cu128, RESUME_identical true.
- Meets the mark as written on its recorded booleans (shown): 3 of 3 flags true; 3 processes ran; run 2 exited with code 3 (consistent with a deliberate stop; the meaning of code 3 is not in the record, suggested); resumed batches start at night 2, step 150 (matches "150 batches after resume", from step 150 to 299).
- The record cannot show (untested): device (CPU vs GPU), float32, use_deterministic_algorithms(True), 4 threads (torch string "+cu128" is only the build), that arm was S and seed was 13 (no such field), that torch.equal covered every tensor, that all 150 hashes rather than only the first (one hash shown) were compared, the atomic-save method (tmp, fsync, os.replace), and that every random-number state was restored. These are asserted only by the booleans.

## Proved-wrong condition (lines 70-72)
Condition: S - R <= +5 on both day kinds, on 3 of 4 seeds, neither kind at ceiling/floor. Seeds meeting it: 0 of 4 (smallest S-R is +46 on grids, +76 on sums). Not proved wrong (shown).

## L arm, report only (seeds 13 and 14; shown)
After night 3, L / S / N:
- s13: day_sums 388/381/263; day_grids 290/366/293; harm_sums4 300/300/300; harm_grids5 300/300/300; rep_sums10 196/194/167; rep_grids6 194/196/194.
- s14: day_sums 391/388/228; day_grids 267/361/279; harm_sums4 300/300/300; harm_grids5 300/300/300; rep_sums10 198/197/151; rep_grids6 192/198/192.
L is higher than S on day_sums (2 of 2 seeds, +7 and +3) but far lower than S on day_grids (2 of 2 seeds, -76 and -94) and at or below N on day_grids for s14 (267 vs 279). L lost counts: 1 total (s13 night 1 grids5). Cause of L's grid result is untested. Night minutes for L: 12.6-19.9 per night.

## Verdict
**PASS (H-B)**: M1, M2, M3, M3b and RESUME each met as written (5 of 5). Proved-wrong condition not met (0 of 4 seeds). Standing caveats (suggested/untested): placebo arm collapsed to 0; harm tests at the 300/300 ceiling; RESUME device/determinism/thread settings and per-batch hash comparison are asserted by the record, not shown by it; day-size dev scoring is not in these files.
