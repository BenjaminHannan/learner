# rsn-353 results (builder, re-run rsn-353b): loop without the per-pass step embedding — registered verdict FAIL

Verdict first: **FAIL**. PASS needed L1, L2 and L3 on both seeds. Seed 1 fails L1 (last copy action_ce
0.1180 vs bar ≤ 0.05) and L2 (fresh panel296 v2 final 210 vs bar ≥ 215, miss by 5). Seed 2 passes L1
(0.0388), L2 (208 vs bar ≥ 207, +1) and L3. L3 passes everywhere (0 checked inventions on all 8
panel runs). The registered "proved wrong" clause (L1 action_ce > 0.5 on both seeds) did NOT trigger
(s1 0.1180, s2 0.0388).

Design: design/v3/30-modes/353-loop-no-step-embedding.md. One change from rsn-296's loop arm: no
`self.step.weight[t]` added in LoopThinker.forward (scripts/claude_rsn353_run.py). Arms, sizes
(~30.8M loop, 30771221 params), steps (6000 copy + 6000 practice), batches, LR, reward, fact-check,
seeds 1-2, eval code identical to 296. Reasoner code sealed and unpatched; all code/panel seals verified
OK on the GPU box before training (SEAL-code 6/6, panel296-v2 2/2, panel294-v3 2/2) and
`python scripts/claude_rsn296_gen.py` printed "selftest ok" (gold-action mismatches 0).

## Training (2 runs, one after the other, --workers 8, RTX 5090, torch 2.14.0+cu130, 72 vCPU host)

| run | minutes | copy loss first → last | copy action_ce first → last | practice reward first → last |
|---|---|---|---|---|
| loop-s1 | 36.2 | 4.0039 → 0.1324 | 3.7458 → 0.1180 | 0.6618 → 0.7785 |
| loop-s2 | 36.9 | 4.2743 → 0.0425 | 3.9925 → 0.0388 | 0.5904 → 0.8451 |

Copy action_ce every 1,000 steps: s1: 0=3.7458, 1000=0.5183, 2000=0.1990, 3000=0.1270, 4000=0.0959,
5000=0.2127, 5999=0.1180. s2: 0=3.9925, 1000=0.4922, 2000=0.3285, 3000=0.3150, 4000=0.0701, 5000=0.0395,
5999=0.0388.
Practice reward means per 1,000 steps (10-11 logged points each): s1: 0-999=0.7527, 1000-1999=0.8107,
2000-2999=0.8179, 3000-3999=0.8275, 4000-4999=0.8302, 5000-5999=0.8434. s2: 0-999=0.7560, 1000-1999=0.8099,
2000-2999=0.8163, 3000-3999=0.8049, 4000-4999=0.8296, 5000-5999=0.8216.
Unlike 296's loop (copy loss stuck 1.85/1.97), both 353 seeds learned to copy (loss 0.13/0.04).

## Panel totals (raw_right / checked_right; each checkpoint evaluated exactly once, 12/12 evals)

reasonpanel296 v2 (298 items):

| run | copy-only raw / checked | final raw / checked |
|---|---|---|
| loop-s1 | 178 / 177 | 206 / 210 |
| loop-s2 | 160 / 161 | 203 / 208 |

reasonpanel294 v3 (300 items):

| run | copy-only raw / checked | final raw / checked |
|---|---|---|
| loop-s1 | 203 / 203 | 237 / 237 |
| loop-s2 | 192 / 189 | 233 / 233 |

Per-category checked_right / n, fresh panel296 v2 finals: s1 — backwards 30/30, before_after 22/30,
comparing 16/30, counting 5/30, heldout_three_step 0/30, missing_fact 30/30, newest_correction 22/28,
one_step 30/30, two_step 25/30, yes_no 30/30 (raw_right 206, checked_right 210, checked_wrong 49,
checked_idk 39). s2 — backwards 30/30, before_after 18/30, comparing 16/30, counting 4/30,
heldout_three_step 0/30, missing_fact 30/30, newest_correction 24/28, one_step 30/30, two_step 26/30,
yes_no 30/30 (raw_right 203, checked_right 208, checked_wrong 56, checked_idk 34).
Copy-only fresh: s1 177 (backwards 30, before_after 8, comparing 0, counting 0, three-step 0, missing 30,
newest 25, one_step 30, two_step 24, yes_no 30); s2 161 (30, 1, 0, 0, 0, 30, 20, 30, 20, 30).
Transfer panel294 v3 finals: s1 237 (backwards 30, before_after 21, comparing 12, counting 9, big-notebook
15/15, three-step 0/15, missing 30, newest 30, one_step 30, two_step 30, yes_no 30). s2 233 (30, 19, 12, 7,
15/15, 0/15, 30, 30, 30, 30, 30). Copy-only transfer: s1 203, s2 189.

## Marks (loop arm, final checkpoints, integer counts)

| mark | bar | seed 1 | seed 2 |
|---|---|---|---|
| L1 last-copy action_ce | ≤ 0.05 | 0.1180 **FAIL** | 0.0388 **PASS** |
| L2 fresh panel296 v2 total (checked) | s1 ≥ 215, s2 ≥ 207 | 210 **FAIL** (miss 5) | 208 **PASS** (+1) |
| L3 invented answers (checked), per panel | ≤ 2 | fresh 0 PASS / transfer 0 PASS | fresh 0 PASS / transfer 0 PASS |
| L4 dev checked_right at 6 / 12 / 20 passes | report | final 902 / 901 / 899; copy 758 / 746 / 732 | final 890 / 888 / 777; copy 686 / 684 / 579 |

L4 detail (dev n=1200 each): s1 final flat across passes (902/901/899 checked_right); s2 final flat 6→12
(890/888) then drops at 20 passes (777, checked_idk jumps 102→271). Copy checkpoints decline with more
passes on both seeds. Thinking longer does not help; at 20 passes seed 2 gets worse.
296 twins for context: 296 loop copy loss 1.85/1.97, fresh finals 106/101, transfer finals 89/87.

## Money

1 rental (RTX 5090, 36 effective cores / 72 vCPU, $0.5667/h): started 2026-09-25 15:24:48 UTC, destroyed
2026-09-25 ~17:47 UTC (~2.4 h wall) ≈ $1.34 dph×hours; Vast credit meter 9.9619 → 8.5936 = $1.37 spent.
Under the $3.80 task cap and the $4 combined cap. 1/4 rentals used, 0 instances live after (only
rent-bm390f, another job, untouched).

## Checkpoints

Kept at ~/premonition-models/rsn353/loop-s1/ and ~/premonition-models/rsn353/loop-s2/ (copy_only.pt +
final.pt per run); all 4 local sha256 match SEAL-run.sha256.txt. Weights never pushed.
SEAL-run.sha256.txt:
2c88df6ebf5e89515fc6c44d3786f39cc5225a533efa22e53414ce2e6ec01cd7  W/loop-s1/copy_only.pt
1ceaa9904a56026fe9435bbb023136c783e99a3c541f79e481f318d166fd5a53  W/loop-s1/final.pt
9e384be02555808c05481c45c5e852e90a34a5f3577552a60b4a87bf3a0020b0  W/loop-s2/copy_only.pt
63f920bdc8b24ef295f7288fa709ae7e4052ed8942b69eba9cc902581bfa99a8  W/loop-s2/final.pt

## Deviations (all reported; code never patched, panels never read item by item)

1. OPUS-RULES.txt absent: the tasked scratchpad path
   (/private/tmp/claude-502/.../76c622f5-.../scratchpad/briefs/OPUS-RULES.txt) does not exist (empty
   scratchpad dir); followed the COMMON RULES restated in the brief itself (additive only, no panel reads,
   no secrets, ledger append-only).
2. Remote code transfer was a git-archive subset (scripts + the 3 sealed artifact dirs + the 353 design doc,
   21 MB) instead of the full 955 MB origin/main snapshot; every seal line verified OK from the repo root on
   the GPU box, so the check is intact.
3. Two-at-once pilot OOM'd (2× --workers 8 on one 5090: CUDA out of memory, one pilot crashed); single-run
   pilots fit (31 s and 41 s wall for 100 copy + 50 practice steps). Ran the 2 trainings sequentially — no
   batch/worker change, per the no-retune rule.
4. venv torch 2.14.0+cu130 (pip latest) instead of the 2.8.0 image default; new venv with torch+numpy only,
   CUDA verified True.
5. Polling overslept: progress polls ran ~12 min past seed-1 done and ~27 min past evals done (~$0.22 extra
   rental); still far under cap. Evals ran exactly once per checkpoint (12/12); polls only read files.
6. rsn-353 first rental (rsn-353, NO RESULT, host died, credit ran out) is a prior task's outcome, noted in
   the ledger (P353.0); this re-run (rsn-353b) is complete with all files back.

## What it means (plain high-school English)

Removing the step counter fixed the loop's copying: both models learned the copy task (loss 0.13 and 0.04
instead of 296's stuck 1.85/1.97) and jumped from 106/101 to 210/208 on the fresh blind test — basically
at the plain model's level (225/217). But it is still not a registered PASS: seed 1 missed both bars by a
little (copy 0.12 vs 0.05, fresh total 210 vs 215). Thinking longer never helps (seed 2 even gets worse at
20 passes), three-step questions are still 0 everywhere, and counting/comparing stay weak (4-16 of 30).

## What it doesn't mean

It doesn't mean the step embedding was innocent — killing it fixed copying, which was the diagnosed
problem. It doesn't mean the loop now reasons — it still fails every three-step question and guesses on
counting/comparing like 296's plain arm did. It doesn't mean seed 1 vs seed 2 disagree about the idea:
both seeds show the same big jump; seed 1 just landed slightly short of two fixed bars.
