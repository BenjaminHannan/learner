# blurt-3: does sleeping on lucky hits raise the luck itself? (registered ~13:00 UTC 2026-09-25, before running)

Why: blurt-2/2p/2b (all registered FAILs) asked whether the reasoner (greedy answer) solves more fresh puzzles after
sleeping on lucky hits; the gain was small and unstable. Ben's stated aim is to "maximize the number of times it gets
lucky", and the 333g DEV rehearsal showed weak guesses sink replies. So the question moves to the guesser: after
sleep, are its random rule-keeping guesses right more often on fresh puzzles?
Same procedure as blurt-2 (arms W = own right + first lucky hit per won puzzle; C = own right repeated to the same
count; LoRA r16 3 epochs, seeds 0 and 1; DEV temperature rule; 30 blurts). New measure (--luck): on each fresh test
puzzle, 30 sampled blurts at the chosen temperature, before sleep (L0) and after each arm; count right blurts.
New practice set (seed 5) and fresh test set (seed 780, 80 puzzles before overlap drops), never printed.
One CPU run on the thread container ($0); it is the registered result.

  python -B scripts/claude_blurt2.py loop --model BASE --out artifacts/claude-blurt2-20260925/cpu-3 --temps 1.0,1.5
      --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 5 --test-seed 780 --n-test 80 --luck

Marks (lucky blurts on the fresh test set, mean of the two seeds):
- U1 luck rises: mean W ≥ 1.5 × L0.
- U2 the wins caused it: mean W ≥ 1.3 × mean C, and each W seed beats each C seed.
- PASS = U1 and U2. Proved wrong: mean W ≤ mean C. Inconclusive: fewer than 20 won practice puzzles, or L0 < 10.
- Reported: puzzles with at least one lucky blurt (before/after), greedy solves (as in blurt-2).

## Replication blurt-3r (registered 15:10 UTC 09-25, after blurt-3 PASSED, before 3r runs)
Same command and marks, new seeds: --train-seed 6 --test-seed 781 --n-test 80, out gpu-3r, on BensPC ($0).
It reports on its own; the blurt-3 verdict stands either way, and "replicated" is claimed only if 3r also passes.
