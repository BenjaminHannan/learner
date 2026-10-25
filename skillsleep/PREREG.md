# Skill-Sleep 1: can a night of sleep make the model better at a job, not just remember facts?

Preregistered 2026-10-25 before any run. Requested by Ben (15:14Z, 15:15Z): sleep should improve skills
(tool use, diligence, finishing the job, asking the person), learning from both good and bad examples.

## Setup
- Model: K2-Horizon-3.7B (small tier), bf16, thinking off (skillsleep/templates/k2_nothink.jinja). Served by vLLM.
- Job: tau2-bench retail (commit cc1df47 + Haiku judge patch). Customer simulator and NL judge: claude-haiku-5-5.
  Pass = tau2 reward 1 (database end state + required info said), checked by tau2, not by us.
- Day: the official retail TRAIN split (74 tasks) x 2 tries each, normal serving settings. 148 runs.
- Held-out test: the official retail TEST split (40 tasks, none seen during the day) x 4 trials = 160 runs per arm.
- Transfer and harm: airline TEST split (20 tasks) x 2 trials = 40 runs per arm (a different store, same skills);
  ARC-Easy 200 questions (choice log-prob) for general knowledge.

## The night (what sleep does with the day)
1. Sort every day run by its check: pass = good, fail = bad.
2. Fix failures offline: for a train task with no passing run, Sonnet 5.5 reads the failed transcript and the store
   policy and writes a short critique (what went wrong, no answer key). The model retries the task with the critique
   added to its instructions, up to 3 times. A retry counts only if tau2's check passes. Training never shows the
   critique: the fixed run is trained under the normal instructions.
3. Build the night's lessons:
   - positives = passing day runs + verified fixed retries (SFT, loss on the agent's own turns only);
   - pairs = (pass, fail) on the same task, using a passing sibling or a verified retry (trajectory-level DPO, beta 0.1);
   - lone negatives = failures with no fix (KTO-style undesirable term);
   - anchor = KL to the untouched model on 100 general prompts (weight 0.1), the same in every arm.
4. LoRA r16 on attention + MLP, merged for serving. Morning gate is report-only in this test (no revert),
   so the raw effect is measured.

## Arms (one change between neighbours)
- A0 no sleep: the base model.
- A1 good only: positives + anchor (Ben's "keep good examples to copy").
- A2 good + bad: A1 + pairs (DPO) + lone negatives (KTO) (Ben's "both"). Same positives, steps and anchor as A1.

## Pass marks (fixed now)
Paired by task (mean pass over trials per task), two-sided sign-flip permutation test over the 40 test tasks.
- P1 sleep teaches skill: A2 retail-test pass rate >= A0 + 6 points and p < 0.05.
- P2 bad examples add something: A2 >= A1 + 4 points and p < 0.05. A gap >= 4 with p >= 0.05 is "suggested", not shown.
- P3 skills carry over: A2 airline-test pass >= A0 (label only; 40 runs is too few to prove a gain).
- P4 no harm: A2 airline >= A0 - 7.5 points (3 of 40 runs) and ARC-Easy >= A0 - 2 points.
- Wrong if: A2 <= A0 on retail test (sleep on skills does nothing), or A2 < A1 - 4 (bad examples hurt).
- Day-1 sanity: the base model's held-out pass rate should land near Swap-1 (51/80 = 64% on tasks 0-39);
  a gap over 15 points means the stack changed and results are reported with that caveat.

## Not claimed by this test
One training seed. A real deployment day has one try per task and a real person instead of Haiku; both are
later tests. The q4 base and the big tier (Qwen3.6-35B-A3B) come after a pass here.

## Compute
One Vast RTX 5090 (coordinator approved 15:20Z, hard cap $2.00, destroyed after results). Haiku and Sonnet calls
from the API credit, concurrency capped with retries on 429.
