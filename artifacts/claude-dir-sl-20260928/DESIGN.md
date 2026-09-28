# SL ("stop without labels"): three steps toward a stop that works on a kind it never practised

Written 2026-09-28 21:48 UTC (`date -u`) by Director helper SL, on top of main commit `64f54de8b`. **Nothing in this folder has been run.** No plug-in, script or selftest for this task existed when this page and PASSMARKS.md were written; both were committed before any code. Labels: **shown** = counted from a raw file or the code (you can check it); **suggested** = my reading; **untested** = nobody has run it. Counts are "x of N". Source of the leads: `design/research/standing/02-stop-on-unpractised-kinds-and-knowing-when-wrong.md` (main `7271f571e`).

Serves finish-line item 2 (decide its own thinking time on a kind it was never told) and item 1 (say "I don't know" when unsure). Small card experiments and the village model are not part of any claim here.

## 1. Plain words (for Ben)
The reasoner thinks in rounds and has a small stop part. The stop was taught only on sums and grids with an answer key ("am I exactly right now?"). On mazes it mostly never fires: 300 of 300 mazes use all 48 rounds at most rungs in seed 0 (shown, `RESULTS-EQ.md:76-84`, recounted below). Three steps, in this order:
1. **Free read A (Lead 3):** on saved nets, does anything the net already computes say "this answer is wrong"? Five signals, no training.
2. **Free read B (Lead 1):** if we stop when the answer has not changed for 3 or 6 rounds, how much thinking time do we save and does accuracy hold? A hand-written rule, so it is a ceiling to beat, not a product piece (the goals page bans new hand-written rules).
3. **One change (Lead 2):** teach the stop with a target that needs no answer key: "my answer this round equals my answer at round 48". Everything else is as before.

## 2. How Lead 2 differs from H12 (shown from H12's files, `artifacts/claude-dir-h12-stop-20260928/DESIGN.md` sections 2-3)
| | H12 (queued, `h12-stop-1-dev`) | Lead 2 (this task) |
|---|---|---|
| Where the stop is trained | during the 2,048 **maze adaptation** updates | during **practice on sums and grids** (the 12,000-step source net) |
| Stop target | "answer is exactly right now" (needs the maze answer) | "answer equals my round-48 answer" (needs no answer) |
| Uses the new kind's answers for the stop | yes | no; the stop never sees a maze or a maze label (maze adaptation itself is unchanged and still uses labels for the answer loss, as in the baseline) |
| Start net | the baseline's qualified source net | a **new** source net, practised with the new stop target (so V1/V2 must be rechecked) |
| Maze adaptation | baseline plus stop loss | exactly the baseline (no plug-in Learner) |
So H12 asks "does the stop fire if it may use maze labels?"; Lead 2 asks "does it fire if it never saw a maze label, because the target it learned was label-free?". A H12 STOP LEARNED with a Lead 2 WRONG would mean the stability target does not transfer but the label target does. I do not wait for H12: nothing here reads or duplicates its output (its result is only a report-only extra column if it has landed by judging time).
The coordinator also pointed at H12's doubt script (`scripts/claude_dir_h12_doubt.py`, on PR #7 branch only). I reuse its record fields (`rounds`, `cap`, `right`, `right_fixed`, `changing`, `path_len`) so its `table` command can read my records, and add signals it does not have (stop probability, weakest-cell margin, flips, state movement, unchanged-for-N stops, round-48 answer). I did not import its file because it is not on main.

## 3. Steps 1 and 2: one no-training read job (`scripts/claude_dir_sl_read.py`, queue job `sl-1-read`, Mac CPU, $0)
Nets scored (all saved on the Mac, none retrained): the qualified sums-and-grids source net `runs/qual-loop-s{0,1}/source.pt` (calls it k0) and the baseline loop's adapted checkpoints `eq-runs/loop-s{0,1}-pre/k{64,256,1024,4096,16384}.pt`. Panels: the **dev** 9x9 mazes (300, the same panel the baseline `adapt.json` was scored on; the holdout stays unopened), and fresh sums (4 digits, 200) and grids (5x5, 200) from the guard seed `SOURCE_SEED+300` (`claude_fewex_source_qualify.py:19`, never used to pick anything). For every item the job runs the full 48-round trace with the ruler's own computation and keeps per-round answers, stop probabilities, per-cell top-two margins and state movement.
Consistency check (shown by the job, not assumed): the recomputed counts must equal the baseline `adapt.json` counts (`right`, `fixed_right`, `cap_hits`, `mean_rounds`) for every maze rung, and `source.json`'s `old` counts for the source net on sums and grids. A mismatch is a finding and stops any reading (INVALID).

**Lead 3, five confidence signals** (higher = more confident; each judged as "does it rank right answers above wrong ones?"):
1. `q_stop`: stop probability at the round the ruler's stop picks.
2. `q_last`: stop probability at round 48.
3. `margin`: the smallest top-two probability gap over the fill cells at the chosen round (the weakest cell).
4. `no_flips`: minus the number of rounds in 39-48 where the whole answer changed from the previous round.
5. `still`: minus the state movement in the last round, mean over items of |h48 - h47| / |h48|.
"Right" = the ruler's own stop answer is exactly right, the same target the harness counts. A sixth signal (disagreement of two runs from different starts) needs a second run from a start the net never saw; it is not run (untested, noted in section 7).
Outputs: AUROC per signal per (net, panel), a coverage-versus-risk table (keep the most confident 90, 75, 50 percent; report x of n wrong among kept and the all-answer error), and for comparison the 3 flags from H12's doubt script.
**Lead 1:** for N in {3, 6}: stop at the first round t >= N at which the whole-cell answers of rounds t-N+1..t are identical, else the 48-round cap. Report right, cap hits and mean rounds beside the ruler's stop and the fixed-16 read, per net and panel. The "answer" is the full arg-max of every cell, like the ruler's own 3-round agreement (`claude_fewex_bench.py:76-78`), so N=3 is the ruler rule with the stop-head condition removed.

## 4. Step 3, the one change (`scripts/claude_dir_sl_stop.py`, a plug-in for the sealed harness)
In practice (sums and grids only), `claude_fewex_net.train_loss` (`claude_fewex_net.py:161-172`) draws `total` rounds (1..16) and `k` gradient rounds (1..min(total,6)), runs `total-k` rounds free, and trains the last `k` with mean cross-entropy plus 0.5 x mean BCE(halt logit, exact-now), where exact-now = "every fill cell is right this round" (needs the key). The plug-in changes exactly one thing: the BCE target for each gradient round becomes **stable-now = the round's arg-max on every fill cell equals the round-48 arg-max**, where the round-48 answer is obtained by continuing the same state, without gradient, for `48 - total` more rounds. Everything else in `train_loss` (round draws, cross-entropy on labelled sums and grids, weight 0.5, mean over gradient rounds) is copied unchanged, as are `Net`, `Practice`'s optimizer, schedule, seeds and batches. The maze stage is the baseline's: the plug-in defines no `Learner`, so the harness falls back to its own baseline `Learner` (no maze stop loss).
The stop head thus gets no answer key for its target, but the answer loss on practised kinds still uses labels (shown by the loss above). "No labels" in this task means: the **stop's** target is label-free. Whether such a head can be adapted on unlabelled problems of a new kind is a later step (untested; not this test).
Run order: (a) `claude_dir_sl_stop.py` builds a source net per seed exactly as `claude_fewex_source_qualify.py` does (12,000 steps, batch 64, `torch.manual_seed(seed)`, `Random(7000000+seed)`), only with the new target; fixed depth chosen on source dev, guard on `SOURCE_SEED+300`, gradient check; (b) V1/V2 as in `RESULTS-EQ.md:11-14`; (c) the sealed equal-practice harness `claude_fewex_eq_bench.py adapt --plugin claude_dir_sl_stop --arm loop --seed S --init pre --source <new source dir>` (2,048 updates per rung, 8 rungs, dev panels, holdout untouched); (d) `claude_dir_sl_marks.py judge`.
Cost (measured once here, then projected): 25 practice steps of batch 64, one thread, on the cloud box took 0.68 s per step with the baseline loss and 2.38 s per step with the new target, so the new practice is about 3.5 times slower (record `SMOKE-cost.log`). The Mac ran the baseline's 12,000 steps in 2,773 s and 2,806 s (`source.json` `train_seconds`), so I project about 2.7 hours per seed there (untested; the ratio may differ on the Mac). The adapt stage is the baseline's cost (169 minutes, H12 DESIGN section 6). $0, no rental. On this cloud box the source stage would take about 8 hours per seed at one thread (0.68 -> 2.38 s per step x 12,000), so the Mac (about 3 times faster per step) is the better place; it is currently the queue bottleneck (Director board 21:32).

## 5. Why this is a fair single change (suggested)
The stop's job at test time is to say "more rounds will not change my answer". The exact-now target asks "is my answer right", which an answer-free stop cannot learn on a new kind. The stable-now target uses only the net's own later state, so the same question is well defined on any kind (idea from PABEE and the confidence-from-the-decision-process literature in note 02, abstracts only; untested here). The known risk: a net can settle on a wrong answer, which is exactly what Lead 3 measures, so the stop may fire early on wrong mazes; the accuracy mark F2 catches that.

## 6. Baseline reference (shown, recounted from `artifacts/claude-fewex-20260927/eq-runs/loop-s{0,1}-pre/adapt.json`, dev 9x9, "right / fixed-16 / mean rounds / cap hits", of 300)
| k | seed 0 | seed 1 |
|---:|---|---|
| 64 | 126 / 122 / 48.0 / 300 | 173 / 171 / 43.8 / 265 |
| 256 | 263 / 254 / 48.0 / 300 | 277 / 268 / 48.0 / 300 |
| 1,024 | 275 / 272 / 48.0 / 300 | 233 / 220 / 19.9 / 61 |
| 4,096 | 256 / 243 / 48.0 / 300 | 292 / 288 / 34.7 / 196 |
| 16,384 | 286 / 285 / 29.4 / 143 | 261 / 259 / 35.3 / 194 |
F_eq (mean of the 8 rungs) learned / fixed-16: 51.21 / 49.83 (seed 0), 51.67 / 50.42 (seed 1). F_few (k=1,4,16,64): 12.42 / 11.83 and 14.75 / 14.58. Round-48 accuracy on sums and grids at the source net: 400 of 400 at depths 16, 32 and 48 in both seeds (`source.json` `fixed_source_dev`), so the round-48 answer is not degraded by overthinking on the practised kinds (shown); on mazes it is unknown, which is why the job also records `right48`.

## 7. What could not be tested, risks
- Nothing has been run. The scripts are checked only by selftests on random-init nets on the cloud box (records committed with them); no practised source net exists here, so the read job and the whole Lead 2 result are untested.
- Lead 3/1 use dev mazes only; rungs and sums/grids panels are separate trainings, so pooling across rungs is descriptive.
- Sums and grids on the practised source net have 0 wrong of 200 (shown: `source.json` `old`), so no AUROC exists there; only the adapted nets (which forget some) can give wrong answers on them. If they too give fewer than 10 wrong, the read says "not eligible", not a number.
- The unchanged-for-N read is hand-written: a ceiling, not a product piece.
- The stability target is trained only for rounds 1-16 (`TRAIN_ROUNDS`), the same coverage as the exact-now head; behaviour at rounds 17-48 is extrapolation (untested).
- The two-runs-from-different-starts signal is not run.

## 8. Files, what was run here, jobs (added 2026-09-28 22:01 UTC with the code; sections 1-7 and PASSMARKS.md were committed before any code)
- `scripts/claude_dir_sl_read.py` (Leads 3 and 1: extract, judge, selftest), `scripts/claude_dir_sl_stop.py` (Lead 2 plug-in), `scripts/claude_dir_sl_source.py` (builds the two new source nets), `scripts/claude_dir_sl_marks.py` (Part C judge and selftest), `scripts/claude_dir_sl_selftest.py` (plug-in selftest), `PASSMARKS-ADDENDUM-1.md` (one floor added to Part B before any score), `smoke_read.py`, `SEAL-code.sha256.txt`.
- Run on this cloud box (torch 2.14.0 CPU, random-init nets only; records in this folder): `SELFTEST-read.log`, `SELFTEST-plugin.log`, `SELFTEST-marks.log`, `SMOKE-read.log` (extract on random-init nets: every consistency line true), `SMOKE-source.log` (the source script on 6 steps), `SMOKE-cost.log` (3.5 times slower per step). Mutation checks (each made the matching selftest fail): read script: unchanged-for-N window off by one, AUROC rank sum, flip sign, flip window, the Part B floor; plug-in: stop weight 0.4, final round 40, missing "off the fill" clause, one extra free round, a different round-draw range, "any" instead of "all"; marks script: cap bar, F1 rung count, F_eq bar, higher-of-controls, WRONG rung count, fixed-16 slack. The selftest of the marks script also reproduces the baseline numbers quoted here from the raw baseline files.
- Not run anywhere: any real extract, any practised source net, any adapt run. Every real result is future work; no claim about the model rests on these files.
- Queue jobs (all STATUS: HELD, all Mac CPU, $0): `handoff/queue/sl-1-read.md` (Leads 3 and 1; about 30 to 60 minutes, two processes; needs the Mac's qualified sources and the baseline loop's k*.pt), `sl-2-source.md` (the two new source nets; about 2.7 hours projected), `sl-3-adapt.md` (the two harness adapt runs; about 170 minutes; waits for sl-2). Order: sl-1 any time; sl-2 then sl-3.
- Waiting on H12 changes nothing here (section 2). If H12's `adapt.json` lands, `claude_dir_sl_marks.py judge` prints its judged rungs as a report-only column.
