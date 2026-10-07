# Research program

## Goal
Get B2's C2 first-try score (5 held-out rule kinds, greedy, no test-time search) to 70% on unseen questions, learning from the night's practice pool, within 5 hours of M1 Pro GPU compute (counted FLOPs), without harming old skills

## The goal as an experimental question
Starting from a C2 parent N (B2 after warm-up and stepping stones), and using only the practice pool's prompts (never answers), the parent's own
tries, its practised add/mult solver notes and skills replay, what learner reaches the highest greedy first-try accuracy on unseen questions of the
five held-out rule kinds, with at most 10,000 TFLOP of counted compute and at most 2 points of chain-5 skills harm? Target: 70% on the holdout.

## Benchmark (fill in during Phase 2)
- Primary metric and direction: `c2_right` (max), % right at greedy first try (the model's one program run on the query; no test-time search or check).
- Guard metrics: `chain5_harm<=2` (N's pooled chain-5 skills exact minus the learner's, points; the project's nightly guard) and `flops_tf<=10000`
  (torch-counted forward+backward FLOPs of everything the learner ran, plus 25.5 TF charged when it uses the parent's cached night of 32 tries per pool question).
- Dev split: creative/data/c2/dev.jsonl (256). Holdout: creative/data/c2rl/holdout.jsonl (512), fresh questions from the same generator over the same
  65 representable rules (new tag 'rlholdout', seed 7031), sharing no (kind, params, examples, query) with warm/dev/pool/labelled. Same capability (induce
  the rule from 3 examples, answer the query), same difficulty distribution, unseen instances. C2b's sealed test split is never read.
- Per-trial budget: per seed one full learner build + scoring, timeout 20 min. A seed is a parent model (8 parents; fresh seeds map onto s202-s205/s100/s101)
  and the learner's random seed.
- Reference points (creative/rl/refs.py): floor = N (no sleep); memory = C2b arm M; job6 = job 6's fine-tune on W (strong simple baseline);
  chainft = the 10-07 pilot (W + chain records); ceiling = job6's fine-tune on the 512 `labelled` questions with reference programs (reads the key: not a learner).

## Constraints
- Hardware: cloud CPU, 4 cores, 15 GB RAM, no GPU (job6 = 8.4 min per seed). Mac (C2b) and PC (q39) busy; Vast 5090 asked of Ben (cap $4).
- Files that may change: creative/rl/method.py and new modules under creative/rl/m/.
- Must not touch: creative/rl/eval_c2.py, refs.py, make_holdout.py, creative/data/, the parent checkpoints (~/rl/parents), every shared module the scorer
  imports (fastsleep, fewshot, programs, sleep, c2_pilot, c2_stones, rules_real, legal, nightchain, custom_io). Never read dev/holdout/labelled/test
  in a learner. No test-time search, executor calls or hand-built held-out kinds inside the model or its training data (synthetic tasks only from a generic
  prior or from programs the model itself found).
- Total budget / deadline: until 70% holdout is confirmed, or 11:00 PM ET 10-07 (03:00 UTC 10-08).

## Assumptions made without asking the user
- "5 hours of M1 Pro GPU" = 10,000 TFLOP counted: about 4.5 TFLOPS peak x 5 h = 81,000 TFLOP; small-model PyTorch on MPS is assumed to reach about
  1/8 of peak. A learner within 10,000 is within either reading. The parent's own warm-up and stepping stones (about 100 TF) are not counted.
- "it" = the C2 first-try score Ben had just asked about (32-44% on DEV).
- The night's cached 32 tries are charged at 25.5 TF (measured on one parent).
- Python-side search (no torch FLOPs) is limited only by the 20-minute timeout; its seconds are reported.

## Benchmark changes (every relock, with reason)

## Notes during the loop
- 10-07 ~17:00 UTC: coordinator relayed Ben's new rule (12:01 PM ET): everything is learned; hand-written code lives only inside outside tools. The loop's test-time model is fully learned (greedy program, no gate, no search). Sleep-time record making (night tries, chain/blind search, replay filters) is search/data tooling run during sleep; reported as such. The memory-sleep notebook gate is not used by any loop method (only by the fixed `memory` reference).
- 10-07 18:45 UTC, Ben's KEY RULE: everything must be doable by the model autonomously while deployed. Audit of the segment-1 recipe (72.7% dev; holdout 72.7% on 2 seeds, trial 6, d0d42517): it used (1) the cached night, whose temperature was picked with DEV answers, (2) replay inputs from C2's generator range (rules_real.DOMAIN), (3) C2 format filters (non-negative, never show 1/2/10/100). Fix (benchmark + base, relock, segment 2): eval_c2 now refuses ctx.night() and ctx.T for methods (references keep them; their code path is unchanged, so their numbers stand); the base method runs its own night at a temperature it picks from its own tries (most practice questions with a fitting try on a 256 x 8 probe), and replay takes inputs, output range and prompt text from the day's questions. Trial 7 (second night) was stopped mid-run and is not counted. The final 6-seed holdout check uses only segment-2 (compliant) code; segment 1's number is reported separately as non-compliant.
- 10-07 20:26 UTC, segment 2 calibrated (compliant base 543d8b87): dev 71.19 +/- 2.22 (4 seeds), holdout 71.73 +/- 1.84 (4 seeds). References from segment 1 stand (their code path is unchanged). Budget left allows about one trial before the final checks; trial 7 overrides the bandit's arm to re-test segment 1's best near-miss (top-up of rarely found programs) at the incumbent's 80 visits.
- Coordinator FYI 19:41 UTC: Ben's direction on sleep and creativity; the creative roadmap thread will spec it. Sleep must leave room for: rewarding/punishing the creative part's ideas by outcome, the worker learning from creative ideas that helped, and the worker getting faster at its own tasks.
- 10-07 20:47 UTC: loop stopped by Ben's $4 Vast cap (not by the harness budget: 4.2 of 6.5 h runtime used). What is left of the cap pays for the 6-seed holdout check and teardown. `confirm --final` on the compliant base (already holdout-confirmed by calibration, seeds 0-3); holdout seeds 4-5 are run after the loop, outside the harness, only to reach the project's 6-seed rule, and reported as such.
