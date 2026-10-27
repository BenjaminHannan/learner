# blurt-2 learning loop: registered pass marks (creative thread, written 2026-09-25 ~02:45 UTC, before any run)

Question (Ben 00:51 UTC): when the reasoner can't solve something, can the creative part's lucky guesses be written into
the model so that next time the reasoner solves that kind of problem alone?

Setup (scripts/claude_blurt2.py `loop`, MiniCPM5-1B, thinking off, every answer rule-kept by constrained decoding):
- Reasoner = the 1B's single greedy answer. Creative = N=30 sampled blurts on each practice puzzle the reasoner misses.
  Judge = the exact checker (code). Sleep = a LoRA (r16, q/k/v/o, lr 2e-4, 3 epochs) trained on the kept answers.
- Temperature: picked on DEV only (artifacts/claude-blurt1-dev-20260925/puzzles.jsonl, seed 1) from {1.0, 1.5}, by
  most lucky blurts on the DEV puzzles the reasoner misses; ties go to 1.0. Rule fixed now.
- Practice: 400 puzzles, seed 2. Test: 150 puzzles, seed 777, made inside the run, never printed or read by anyone;
  any test puzzle identical to a practice or DEV puzzle is dropped. Same recipe for all (two thirds 3-number, 1-9,
  target 5-40; one third 4-number, 1-13, target 24).
- Arms (one change: the creative wins): W = the reasoner's own right answers + creative wins. C = own right answers
  only, repeated to the same example count. Each arm trained twice (LoRA seeds 0 and 1); marks use the mean.
- S0 = test right before sleep (greedy, base model).

Pass marks (all on the fresh test set, reasoner alone, one greedy answer each):
- **L1 learning:** mean S_W_after − S0 ≥ +8.
- **L2 the creative wins caused it:** mean S_W_after − mean S_C_after ≥ +5, AND each W seed beats each C seed.
- PASS = L1 and L2.
- **Proved wrong** (the loop does not teach the reasoner): mean S_W_after ≤ mean S_C_after, or mean S_W_after ≤ S0.
- **INCONCLUSIVE, not a pass or a fail:** fewer than 20 creative wins in practice (then the blocker is luck, and the
  next step is raising luck, not the loop). Also inconclusive if the reasoner already gets ≥ 60% of the test right
  before sleep (no room).
- Reported, not marked: lucky blurts per 30 on misses (the luck rate), practice misses solved after sleep, the gap
  between the two seeds (differences smaller than that gap are noise).

Where it runs: the same command with the same seeds, on the thread's CPU container ($0) and, if the director gives a
slot, on a GPU. Whichever finishes first is reported first; if both finish, both are reported and PASS needs both.

Honest limits, stated now: this tests learning on the same kind of puzzle (fresh puzzles, same family), not transfer
to other problems. A PASS says lucky guesses can be written into weights and help on new puzzles of that kind. The
loop reasoner (294 line) is the sleep thread's; wins also go to <out>/wins/wins.jsonl in the agreed format.

## Idea self-judge (same job, DEV only, decision rule fixed now)
scripts/claude_blurt_selfjudge.py on the 300 blurt-1 idea blurts (10 DEV requests x 30), against blind Opus labels
(labels/labels0.jsonl, labels1.jsonl in artifacts/claude-blurt1-dev-20260925; 44/300 good; 9/10 requests have a good one).
- If the 1B's own top pick is good on ≥ 6/10 requests: 333g uses the self-judge.
- Otherwise the judge must be trained or replaced; 333g waits for that decision (label source is Ben's call).
