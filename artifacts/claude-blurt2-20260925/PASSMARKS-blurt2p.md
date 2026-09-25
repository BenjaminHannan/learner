# blurt-2p: placebo check of the learning loop (registered ~05:50 UTC 2026-09-25, before running)

Why: the blurt-2 loop PASSED on CPU (RESULTS-cpu.md): fresh puzzles 6 -> 15/19 after sleeping on creative wins, 6/6
without. Sleep research round 2 asks for a placebo: maybe any extra practice on new puzzles helps, right or not.
One change: arm P replaces arm C. P = the reasoner's own right answers + one WRONG legal blurt from each puzzle that
had a win (same puzzles as the wins, same example count as W). W and P differ only in whether the guesses were right.
Also a replication: new practice set (seed 3) and new fresh test set (seed 778), never printed. Everything else as
PASSMARKS-blurt2.md (temperature from the same DEV rule, 30 blurts, LoRA seeds 0 and 1).

  python -B scripts/claude_blurt2.py loop --model BASE --out artifacts/claude-blurt2-20260925/cpu-p --temps 1.0,1.5
      --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 3 --test-seed 778 --arms W,P

Marks:
- P1 the right answers matter: mean W − mean P ≥ +5, and each W seed beats each P seed.
- P2 replication: mean W − S0 ≥ +8.
- PASS = P1 and P2. Proved wrong: mean P ≥ mean W (then the gain was from practice, not from the lucky answers).
- Inconclusive: fewer than 20 wins, or S0 ≥ 60%.
