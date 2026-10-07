# Fast sleep screen: pass marks (written 2026-10-06 9:09 PM ET, before any screen run)

Thread: "fast sleep" (Ben 8:58 PM ET 10-06: the sleep step must learn quickly, without many FLOPs). Code: `creative/fastsleep.py` on branch
`claude/project-thread-2kevpk` (cut from the C2 build branch; job 6's code is not changed).

## Setup (same as Mac job 6, steps 0-2, rebuilt on this CPU)
N = raw B2 (s100, s101) -> warm-up (2,048 add/mult solver rows, 4 visits, lr 3e-4, skills replay) -> stepping-stone sleep (2,048 rows, same).
Pool temperature by job 6's rule. N samples the 1,024 pool questions 32 times. Record sets: W (tries that fit every example, <= 2 per question)
and PC (reference programs for W's questions, same count). DEV only (256 questions); test and labelled are never opened.

## Measures (per method, per record set, per parent)
- Sleep FLOPs: torch FlopCounterMode around the whole sleep (caching passes included). SDPA attention is not counted by the counter (about 3% of a
  forward pass by hand count); the same omission applies to every method.
- Gain: DEV greedy first try (fits every example AND equals the key) minus N's, in points. Per kind reported.
- Harm: pooled-5 skills exact (data_big dev in_dist, chain families) of N minus the slept model, in points. Limit 2 points (job 6's).

## Methods and their fixed grids (DEV is the tuning split: every setting is reported)
- **ft** (baseline, job 6's sleep): lr {3e-4, 1e-3} x visits {4, 8, 16}, half skills replay, updates = visits x |W| / 32.
  Short variants: lr {1e-3, 3e-3} x visits {1, 2}, with and without replay.
- **heads** (fast weights on the decision heads): reader and thinker frozen; one teacher-forced forward per record caches the head inputs; only the
  op, operand-query, slot-key, answer-query and mode heads are fitted on the cache (Adam), with as many cached replay rows as records.
  lr {3e-3, 1e-2} x epochs {10, 30}.
- **knn** (episodic memory the heads read, no gradient): keys = thinker state at each forced step; values = forced op and the key of the forced
  operand / answer slot; k = 16, tau = 0.05; strength c {5, 20, 50} x gate theta {0.8, 0.9}.
Each method's representative setting = best DEV gain among its settings within the 2-point harm limit (job 6's rule).

## Baseline B
Job 6's plain fine-tune at the dose job 6 picks on PC by its own rule (best DEV first try within the harm limit), measured here on the same N.
If job 6's pick is not known when the screen ends, B = this screen's own pick by the same rule on PC.

## Screen pass (W records, both parents)
1. Sleep FLOPs <= 1/10 of B's.
2. Gain >= 0.8 x B's gain (B's gain on W must be >= 3 points; if it is smaller, the comparison is made on PC and the label says so).
3. Harm <= 2 points.
Same three on PC are reported beside it.

## Proved wrong
No cheap method (<= 1/10 of B's FLOPs) reaches 0.5 x B's gain on either parent, on W or on PC.

## Not claimed by a screen
Two parents is a screen. A pass goes to a 6-seed confirm with the setting frozen (seeds 200-205 when their parents exist), and to the roadmap thread
as a proposed sleep for C2b. Selection on DEV favours methods with more settings; the grids above are fixed so the count is known (ft 14, heads 4, knn 6).

## Addendum 1 (10:00 PM ET 10-06, after seeing s100 numbers, before any s101 screen number)
- Memory v1 (operand pointers steered by shifting the query toward the stored slot's key) could not tell the constants apart (10 vs 2), so
  last_digit stayed at 0. v2 votes on slot ids instead (B2's own pointer targets). v2 is the knn method from here on; v1 is reported, never picked.
- The fixed gate (theta 0.8 / 0.9) fired on about a third of skills decisions, so strength c = 50 harmed skills (5-40 points). Added after seeing
  that: the gate threshold per step = the 0.99 quantile of the best memory similarity over as many skills TRAIN replay rows as records (never DEV,
  never the harm set); this calibration pass is counted in the method's FLOPs.
- FROZEN NOW for s101 and every later parent: "memory" = knn v2, k 16, tau 0.05, c 50, theta 0.9, cal 0.99. s101 is its first untuned test.
  The pre-registered knn grid (c x theta, no calibration) is still run and reported on s101 as written.
- Job 6's own picks are now known (Mac, 95df4f6d9): s100 lr 1e-3 x 16 visits (182 updates), s101 lr 3e-4 x 16 visits (105 updates).
  B = those settings, re-run here on the same N (FLOPs measured here).

## Addendum 2 (10:34 PM ET 10-06, after the s100 old-parts check, before any s101 old-parts number)
- Old-parts check added (the coordinator relayed that the stepping-stone sleep wiped add/mult): 256 fresh add/mult questions (job 6's practised set),
  reach@32 at T 1.0, first sample, and greedy first try (fits and right); plus DEV reach@4 / reach@32 at the pool temperature.
- s100: memory (frozen v3) cut practised reach@32 from 10.9% to 4.3% (job 6's W sleep: 7.0%). Added after seeing that: the memory also holds the
  warm split's add/mult solver programs (512 or 2,048 of them); 512 kept DEV gain at +34.4 and lifted practised reach@32 to 32.4%; 2,048 gave +28.1 and 40.2%.
- FROZEN NOW for s101 and later: "memory+old" = memory v3 plus the first 512 warm-split solver records. Their forward passes are counted in its FLOPs
  (with frozen weights they are made once per parent, so a real night pays them once). s101 is its first untuned test.
