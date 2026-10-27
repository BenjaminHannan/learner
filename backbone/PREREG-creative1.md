# Creative-1: premonition's creative loop on a borrowed Qwen (pre-registration, 2026-10-24 ~00:50Z)

Not the village model, not the card experiments. Ben asked (2026-10-24 00:43Z) how the creative model carries over
to Qwen3.8-27B. Prototype: Qwen/Qwen3.5-0.8B (same architecture as the 27B).

Mapping (suggested): Qwen replaces the creative model's learned proposer; premonition keeps the loop:
propose many rules as tiny programs -> run each on the examples -> answer with one that fits, else abstain ->
sleep on fitting rules plus dreamed random programs -> better first guess.

## Data
- C2 dev: `creative/data/c2/dev.jsonl` from branch claude/v1-assembly (256 puzzles, kinds affine, square, sq_plus,
  last_digit, double_add). v1 FULL first try 34.8% (two-step kinds 0-2%). C2 test.jsonl is sealed: never read.
- HARD (new, code-generated, seed 0, 300 puzzles): rules composed of 3 steps from {+c, -c, *c, square, //c, %c,
  reverse digits, digit sum}, 3 examples each, like C2's prompt format. Held-out compositions (no step sequence used
  in sleep dreams is reused in HARD; checked in code).
- Sleep pool: unlabelled puzzles from C2's `pool.jsonl` (same 5 kinds, unlabelled by design, as in v1) plus dreams:
  random 1-3 step programs over the same primitives, labelled by running them, excluding HARD's step sequences.

## Arms (Qwen3.5-0.8B, greedy unless stated)
- F0: first try, Qwen writes one program (`lambda x: ...`), answer = program(query).
- C16: 16 sampled programs (T=0.8); answer with the first that reproduces all examples, else abstain.
- F1: first try after one sleep night: LoRA (r16) on (prompt -> program) pairs that fit (from C16 on the pool +
  dreams), with the KL guard on generic replay as in Sleep-1.

## Marks (fixed now)
- K1 checking: C16 accuracy >= F0 + 15 points on HARD, with wrong answers among answered <= 2%.
- K2 sleep: F1 >= F0 + 10 points on HARD.
- K3 C2 dev: F0 and C16 reported against v1's 34.8% first try (no mark: may be at ceiling).
**Wrong if** C16 <= F0 + 5 on HARD (checking adds little because Qwen's guesses rarely fit), or F1 <= F0 on HARD
(sleep on fitting rules doesn't transfer to held-out compositions).
Budget: one Vast A100 run, cap $3.
