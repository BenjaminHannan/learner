# Aha-1: replace the branch ban with a "predict what you weren't shown" check (pre-registration, 2026-10-24 ~04:10Z)

Small puzzle model only (Qwen3.5-0.8B program puzzles). Not the village model, not the card experiments.
Thread "Design the creative model like a brain". Follows Creative-2 (`RESULTS-creative2.md`).

## Why
Creative-1 failed because lookup-table programs (`900 if x == 29 else ...`) fit the shown examples. Creative-2 fixed it
with a hand-made ban on if/else, comparisons and and/or. That works here, but a real assistant can't ban every cheat in
advance, and some true rules need branches. The brain's test for an idea is that it predicts something new. So:

**One change (arm `aha`, flag `--aha`):** branches are allowed again (no `--no-branch`). When the creative loop samples its
16 programs (C16 eval and choosing sleep data from the pool and dreams), sample i is written from a prompt that hides
example i mod 3, showing only the other two plus the query. The checker is unchanged: a program counts only if it
reproduces all three examples, so it must predict the one it never saw. Sleep pairs still use the full 3-example prompt.
F0/F1 (greedy first try, full prompt) are unchanged.

Control (arm `nb`): Creative-2 exactly (`--no-branch`), rerun on the same box and seed so hardware and sampling match.
Everything else identical: same HARD set (seed 0), C2 dev (256), pool (1024), 1000 dreams, LoRA r16, 300 steps, KL guard.

## Marks (fixed now, before any run), on C2 dev, post-sleep C16
- P1: acc(aha) >= acc(nb) - 2 points.
- P2: precision among answered (aha) >= 95%.
- **Wrong if** precision(aha) < 80% (hiding one example does not stop false fits), or acc(aha) < acc(nb) - 10.
- Reported, no mark: HARD, pre-sleep C16, F0/F1, and the share of answered programs that contain a branch, with their precision.

Plain reading of a pass: a general check ("predict what you weren't told") does the job of a hand-written cheat list.
A fail on P1 with P2 passing means the check is safe but costs too much (two examples are too few to find the rule).

Budget: one A100 run (~40 min for both arms, under $1) with the coordinator's OK, else Ben's PC queue. Seed 0 only.
