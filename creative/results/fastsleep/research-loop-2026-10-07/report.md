# Research report

Goal: Get B2's C2 first-try score (5 held-out rule kinds, greedy, no test-time search) to 70% on unseen questions, learning from the night's practice pool, within 5 hours of M1 Pro GPU compute (counted FLOPs), without harming old skills  
Branch: `research/get-b2-s-c2-first-try-score-5-held-out-r-20261007-1437` (the user's original branch was not modified)  
Generated: 2026-10-07T20:47:43

<!-- findings:start -->
## Findings

**Headline (compliant sleep, holdout, 6 parents s200-s205): 71.3 +/- 2.5% right at greedy first try** on 512 unseen questions of the
five held-out rule kinds (s200-s205: 71.1, 72.5, 73.8, 69.5, 67.2, 73.4). Target 70%: met on the 6-parent mean (95% interval about 68.6 to 73.9), not on every parent: 4 of 6 are at or above 70, s203 (69.5) and s204 (67.2) are below. Seeds 0-3 are the harness's calibration of the compliant base (543d8b87:
holdout 71.73 +/- 1.84); seeds 4-5 were run after the loop stopped, outside the harness, only to reach the project's 6-seed rule, with the same
command and code. Guards held on every seed: chain-5 skills harm -1.4 to -0.1 (none) (limit 2), compute about 2,250-2,450 TF counted per sleep (limit 10,000).

Reference points (DEV, 2 parents each; their code path never changed, so segment 1's numbers stand):

| | DEV first try | counted TF |
|---|---|---|
| floor: parent N, no sleep | 0.2 | 0 |
| memory sleep (C2b arm M) | 34.6 | 27 |
| job 6 fine-tune on W (strong simple baseline) | 37.5 | 64 |
| start of the loop: W + chain records, job-6 budget | 42.3 (holdout 41.6) | 59 |
| "ceiling": job 6 on the answer key's own programs | 45.7 | 51 |
| **compliant sleep (this loop)** | **71.2 +/- 2.2 (4 parents)** | **~2,360** |

The final sleep is far above the old "ceiling", because that ceiling used job 6's small budget; it was a ceiling for that budget, not for the task.

Per kind on the holdout (6-parent mean): a·x+b 15.5, x² 98.7, x²+k 76.6, x mod 10 93.1, 2(x+k) 72.5. a·x+b is the one kind still far from solved.

**Two numbers, kept apart (Ben's deployed-autonomy rule, 10-07 18:45 UTC).** Segment 1 reached 72.66 on the holdout (2 parents, trial 6,
d0d42517), but that recipe used three things a deployed model would not have: the parent's cached night, whose sampling temperature was chosen
with DEV answers; replay inputs taken from the test generator's range (3..29 without 10); and C2 format filters. Segment 2 removed all three
(eval now refuses `ctx.night()` and `ctx.T` for methods; relock): the model runs its own night at a temperature it picks from its own tries (most
practice questions with a fitting try on a 256 x 8 probe; it picked T = 3.0 on s200), and replay takes its inputs, output range and prompt text only
from the day's questions. The compliant version lands at about the same place (dev 71.2 vs 70.7 / 72.7 for segment 1; holdout 71.3 vs 72.7).

**Kept changes (segment 1, all carried into the compliant base):**
1. Train 3x longer on W + chain records (trial 2, kept; fresh seeds +1.5). Mechanism: the chain records were under-fitted at job 6's budget.
2. Execution replay at scale (trial 3, +21.9 on fresh seeds): every record's program is run on 3 fresh input sets to make 3 new prompts of the same
   rule, and the fine-tune runs at batch 1,024 with 40 visits per record. Mechanism (suggested): the controller must see each rule with many different
   example triples before it reads the rule from the digits instead of memorising the prompt; replay supplies those triples for free, keeps the pool's
   rule mix, and every replayed prompt is right by construction (its program made it). The ablation below supports this.
3. 80 visits per record instead of 40 (trial 6, +7.0 on fresh seeds; holdout 72.66 on 2 parents). Mechanism: still under-trained at 40.

**Failures (results too):**
- Dropping replay at the same number of updates (trial 4): -16.0 on the first parent, early stop. Replay, not extra steps, carries most of the gain.
- Per-program replay at the old small budget (trial 1): +2.6, a near miss inside noise.
- Top-up (trials 5 and 7): giving every rarely found program extra replayed prompts up to 32 lifts a·x+b on DEV (to 21-31%) but costs x mod 10
  and 2(x+k) about as much; net +0.2 and -0.5, never beyond noise.
- Night chaining into the notebook (earlier, 10-07 research): equal to blind search; a notebook cannot adapt constants.

**Caveats:**
- The holdout is "same rules, new questions": the 65 rules of the five kinds are all seen in practice (unanswered); what is tested is reading which
  rule a new example triple shows. It is not a test of inventing an unseen rule.
- About 2,400 TF is 40-90x the old sleeps (27-64 TF). It is within the 10,000 TF budget (Ben's "5 hours of M1 Pro GPU", assumed at 1/8 of peak),
  but not cheap.
- Sleep-time search (chain search over the model's own library, the fit check, replay filters) is hand-written code that the sleep itself calls as a
  tool. Under the deployed-autonomy rule this is the allowed form (outside tools the model chooses to call), but it is reported as such.
- The parents' warm-up and stepping stones (about 100 TF) were researcher-designed and are not counted.
- Holdout calls: 1 of 12 in segment 2 (calibration) and 1 in segment 1, plus the 2 post-loop seeds disclosed above.
- The memory reference ran on the cloud CPU (a device bug in a locked module on GPU); the others ran on the 5090. Same code, same counted FLOPs.
- The loop stopped at 4.2 of 6.5 hours to stay inside Ben's $4 Vast cap with room for the final seeds; box spend about $2.9 (5.8 h at $0.49/h, plus a few minutes on two boxes that failed to start).

**Next hypotheses:**
1. A second night by the slept model (expert iteration): it now solves most questions itself, so its own tries should add a·x+b records the chain
   search found only once. Pass mark: holdout a·x+b +10 with total within noise.
2. One canonical program per rule (shortest, fixed shape), so the 52 a·x+b rules stop being spread over about 4 shapes each.
3. A held-out-rules split (hold out some (a, b) pairs) to test real generalisation to unseen rules.
4. Cheaper: find the smallest visits/replay setting that keeps 70% (the gain may hold at a fraction of 2,400 TF).

**Room for Ben's sleep/creativity direction (coordinator FYI 19:41 UTC):** the sleep is "collect right records, replay them, fine-tune", so the three
asks fit without redesign: (a) records already carry their source arm ('S' own night, 'C' chain search, 'Y' replay), so a creative proposer's ideas can
enter as their own arm and be rewarded or dropped by whether they produced a fitting program; (b) the worker learns from any creative idea that
helped simply by training on the records that idea produced (as chain records are today); (c) "getting faster" maps to training the worker on its own
night successes (the 'S' records) and to measuring how many tries the night needs before its first fit (not logged yet; a small addition).
<!-- findings:end -->

## Benchmark

- Metric: `c2_right` (max); guards: `chain5_harm<=2`, `flops_tf<=10000`
- Dev: `bash creative/rl/run_eval.sh dev {seed}`  
- Holdout: `bash creative/rl/run_eval.sh holdout {seed}`
- Locked: `creative/rl/eval_c2.py`, `creative/rl/refs.py`, `creative/rl/make_holdout.py`, `creative/rl/run_eval.sh`, `creative/rl/remote.py`, `creative/data/`, `creative/fastsleep.py`, `creative/fewshot.py`, `creative/programs.py`, `creative/sleep.py`, `creative/c2_pilot.py`, `creative/c2_stones.py`, `creative/rules_real.py`, `creative/legal.py`, `creative/nightchain.py`, `custom_io/`; segment 2 (1 relocks, see program.md)
- Noise: pooled dev sigma 1.941; holdout sigma 1.842; 2 seeds per trial

## Where things landed

| | dev | holdout |
|---|---|---|
| baseline (start) | 71.1914 +/- 2.2183 | 71.7285 +/- 1.8417 |
| incumbent (#base, `543d8b87`) | 71.1914 | 71.7285 |
| last holdout-confirmed (#base, `543d8b87`) | 71.1914 | 71.7285 |

## Kept changes (0)


## Holdout checks (1 of cap 12)

- 2026-10-07T18:29:35: trial #6 `d0d42517` -> 72.6562 (gain)

## Arms

| arm | tried | kept | near-miss | crash |
|---|---|---|---|---|
| literature | 0 | 0 | 0 | 0 |
| tune | 0 | 0 | 0 | 0 |
| bold | 0 | 0 | 0 | 0 |
| simplify | 0 | 0 | 0 | 0 |
| combine | 1 | 0 | 0 | 0 |

## All trials

| # | arm | outcome | delta | hypothesis | prediction | reason |
|---|---|---|---|---|---|---|
| 7 | combine | discard | -0.4883 | Top-up (segment 1 near-miss #5, now compliant): every distinct found program wit | up 1 to 4 points: affine 12-21% -> 25-35%, other kinds withi | -0.4883 vs incumbent |

Runtime: 4.15 h of experiments across 1 trials. Refreshes: 0.
