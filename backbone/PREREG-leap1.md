# Leap-1: does "leapfrog" learning keep a small worker climbing? (pre-registration, 2026-10-24 ~01:40Z)

Labels in the results: shown / suggested / untested. Not the village model, not the card experiments: this is the
borrowed Qwen model on checkable program puzzles (the Creative-1 puzzle family).

## Ben's idea (2026-10-24 01:22Z)
The creative model pushes past what the worker can do, the worker sleeps and learns what the creative found, then
the creative pushes again from the new frontier: leapfrogging. Ben's goal: the small model should punch above its
weight, so the headline comparison is "small worker after leapfrog vs a much bigger plain model".

## Task (code-generated, no human labels)
Puzzle = 3 input/output examples + 1 query; the rule is a chain of d steps from {+c, -c, *c, square, //c, %c,
reverse digits, digit sum} (creative1.py primitives and checker, unchanged). Difficulty = d, levels 1..6.
The model answers with one `lambda x: ...`; a program is **verified** if it reproduces all 3 examples (no gold used).
- EVAL (scored, never trained on): 100 puzzles per depth 1..6 = 600, seed 1000. For d >= 2 every EVAL step
  sequence (signature) is held out: no training pool at any round contains it (checked in code). d = 1 has only 8
  signatures, so its EVAL puzzles are fresh inputs/constants only.
- DEV (frontier probe, never trained on): 30 per depth, seed 2000, also held-out signatures.
- POOL: fresh puzzles each round (seed = 100*round + seed), never EVAL/DEV signatures. Only verification is used.
- Old skills: ARC-Easy, first 500 test questions (sleep1.py scorer).

## Arms (Qwen/Qwen3.5-0.8B worker, 5 rounds, seeds 0 and 1)
Every round: explore on a 1000-puzzle POOL -> keep verified (prompt -> program) pairs, at most 2 distinct programs
per puzzle -> sleep: fresh LoRA r16 trained 150 steps (bsz 16, lr 1e-4 cosine) on this round's pairs plus all earlier
rounds' pairs, KL guard (weight 1.0) on 200 generic replay prompts against the start-of-round model -> merge LoRA
into the weights -> score. One change between neighbours:
- SELF (plain sleep on own work): the worker itself, 4 samples (T 0.8), uniform depths 1..6.
- LEAPU (creative explorer, no frontier): explorer = same current model with a bigger search: 16 samples (T 1.0),
  then one repair turn for puzzles with no verified sample: up to 2 failed programs are shown with what they output
  on the examples and the wanted outputs, 8 more samples. Uniform depths 1..6. The pair kept is
  (original puzzle prompt -> verified program), so the worker learns to find it on the first try.
- LEAP (Ben's leapfrog): LEAPU's explorer, but the pool sits just past the worker's frontier. Frontier f = largest
  depth whose DEV first-try accuracy >= 50% (f = 0 if none). Pool depths: 40% f+1, 30% f+2, 30% uniform 1..f
  (consolidation; if f = 0 the 30% goes to depth 1), capped at 6.
- BASE: round 0 scores of the untouched worker.
- References (no training, greedy first try on EVAL): Qwen3.5-4B, Qwen3.5-9B, Qwen3.6-35B-A3B (vLLM box, if it fits
  the budget).

Scored after every round: worker first try (greedy, one program) on EVAL, per depth and mean over 6 depths; DEV
frontier; ARC-Easy.

## Pass marks (fixed now; must hold on both seeds unless stated)
- L1 climb: LEAP mean EVAL accuracy after round 5 >= round 1 + 8 points, and rises (>= +1 point) in at least 3 of
  the 4 rounds after round 1.
- L2 leapfrog beats own work: LEAP round-5 mean >= SELF round-5 mean + 8 points.
- L3 the frontier is the reason: LEAP round-5 accuracy on depths 4-6 >= LEAPU + 5 points (seed average).
- L4 no forgetting: LEAP ARC-Easy after round 5 >= BASE - 2.0 points.
- L5 punch above weight: LEAP 0.8B round-5 mean >= plain Qwen3.5-4B first try (reported for 9B and 35B-A3B too).
**Wrong if** LEAP round 5 <= SELF round 5 + 3 points (the creative adds nothing over sleeping on own work), or LEAP's
rounds 2-5 add < 3 points in total over round 1 (it does not keep climbing: one-shot distillation, not leapfrog).

Caveat fixed in advance: LEAP/LEAPU spend about 6x more exploration samples than SELF; the arms test "what the worker
would do by itself" vs "a creative search", not equal compute. Budget: Vast, cap $12 for all boxes.
