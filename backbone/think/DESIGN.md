# Think-1 design: Gated Silent Think Slots (G-STS)

Chosen 2026-10-24 by a six-designer judge panel (`panel/`), then changed by the completeness critic, by Loop-1L's
results and by the Barron et al. cross-entropy fix. Labels: **shown** / **suggested** / **untested**. Pass marks:
`PREREG.md`. Full panel reasoning: `panel/SYNTHESIS.md`; critic: `panel/CRITIC.md`; scores: `panel/SCORES.json`.

## In one paragraph
Before answering, the model gets 16 "thinking slots": vectors that look like word embeddings. The frozen backbone reads
the question and its context once. Then, lap after lap, it runs only those 16 slots through all of its layers (they can
look at the whole prompt but the prompt never looks at them), and a small 2.6M-parameter refiner reads what each lap
found and nudges the slots. The refiner cannot see the prompt itself, so anything new it learns must come back through
another lap of the backbone. That is what makes a second hop need a second lap. When it is done, the answer's attention
layers glance at the final slots through gates that start fully closed, so at step 0 the model is exactly plain arm A.
Nothing is written as words, and ordinary tokens never loop.

## Why this design won
| design | angle | weighted score | judges' rank (3 ballots) | attack verdicts (pilot / scale) | main reason it lost |
|---|---|---|---|---|---|
| **D6 Silent Think Slots** (rebuilt) | contrarian, evidence-maximal | 6.40 | 1, 1, 1 | dead 0.07 / wounded 0.10 | **chosen**: the strongest frozen-backbone evidence (LRT, INTACT, cache augmentation), every fatal point had a fix |
| D5 Decision-Point Board | halting-first | 6.73 | 2, 2, 3 | dead 0.05 / wounded 0.12 | one frozen layer applied to its own output (the pattern that failed in Loop-1L and Newt); weakest laps; only design with a per-token cost |
| D2 Slot Laps | board-centric | 6.45 | 4, 4, 2 | dead 0.07 / wounded 0.15 | re-runs a band on its own output; not arm A at step 0; its untrained lap curve already rises (CPU probe), so "rises with laps" would be free |
| D1 Forked Soft Board | minimal adapter | 6.12 | 3, 3, 4 | not attacked | only a rank-64 linear feedback path; kept: its exact-A gated read |
| D4 Draft-Check-Revise | refinement + self-check | 5.13 | 5, 5, 5 | not attacked | its draft curve rises by construction (Jacobi); six new parts on ~27k answer tokens |
| D3 Lap-Routed Thought Layers | MoE-of-thought | 4.88 | 6, 6, 6 | not attacked | evidence runs against routed thought experts on a frozen backbone |
Weights: gain .35, speed .20, trainability .20, decoration risk .25. The weighted score and the judges' own rankings
disagreed (speed), so the top three were all attacked. Attack probabilities are each attacker's P(pass the pilot).

What the rebuilt D6 took from the others: D1's zero-start gated read (exact arm A at step 0); D2/D5's control trained at
one lap (t1); D6's attackers' fixes (no refiner access to the context, a frozen arm-A adapter so the LoRA cannot take the
signal first, loss at every lap so a weak lap 1 cannot fake a rising curve); D4's per-lap flip counts as diagnostics.

## Changes after the synthesis (all fixed before any run)
- Every slot pass and every teacher-forced answer pass gets its own copy of the prompt cache (critic A1: HF 5.20.2
  `update_recurrent_state` always writes with `copy_`, so a shared cache would let later laps read the gold answer).
- e0 is learned in units of rho (rho = 0.0195, the embedding RMS) and clamped like every board (critic A3).
- Learning rates lowered after Loop-1L's board diverged at 1e-3 (Ben's note): gates 3e-3, refiner 5e-4, e0/eta 5e-4;
  gradient clipping per parameter group; a divergence guard aborts a run whose loss doubles.
- Fixed cross-entropy (Barron et al. 2026, arXiv 2610.31642) for every arm (`xent.py`).
- aplus on all 3 seeds; bplus seed 0; a compute-matched wide control `tw` (144 slots, one refinement) on seed 0.
- Futility line 68.0 instead of 68.7, because same-seed reruns differed by 1.84 points (critic B9).

## Exact pilot spec (Qwen3.5-0.8B)
- Backbone frozen; arm A's LoRA (same seed, 418 steps) loaded and frozen. Full attention at layers 3/7/11/15/19/23,
  Gated DeltaNet elsewhere [shown, config].
- Board: K=16 x 1024, e0 = rho * e0_hat. Clamp: per-slot RMS <= rho.
- Laps: prefill prompt[:-1] once (no gradient). Slot pass t: `inputs_embeds = e_t` on a fresh fork of that cache, all
  slots at the RoPE position of the held-back last prompt token, causal among slots. Refiner input: rms(h_11), rms(h_17),
  final-norm h at the slot positions -> W_in (3072->256) -> 2 pre-norm blocks (4-head self-attention over the 16 slots
  of ONE row, GELU MLP 256->1024->256) -> W_out (256->1024, default init) -> e_{t+1} = clamp(e_t + rho * eta * tanh(.)),
  eta per channel, start 0.1. No lap embedding.
- Read: at each attention layer l and head h, answer-side queries add tanh(alpha_lh) x SDPA(q, slot K_l, slot V_l) to the
  normal attention output before the layer's sigmoid output gate and o_proj. Slot K/V = the keys/values the slots wrote
  at layer l in the final pass (post-norm, post-RoPE). alpha starts at 0.
- Loss: mean over t = 0..L_max of the answer cross-entropy read from board t, + 0.01 x the elementwise mean of (delta/rho)^2.
  L_max = 8 (p 0.8) or 12 (p 0.2). Backprop through all laps.
- Parameters: 2,644,016 (e0 16,384; gates 48; eta 1,024; W_in 786,688; blocks 1,576,448; W_out 263,168; norm 256) [shown].

## What it would cost on the Mac (LFM2.5, suggested; see SCALEUP.md)
Decode: the gated read is one small extra attention over 8-16 slot keys at 10 layers per token (~0.5-2%; measure).
Thinking burst: one 8-16 token pass of the whole model per lap, ~90-139 ms at the 64 GB/s fitted from Ben's bench, so
K=8 and L=4 adds ~0.45 s per generation, against several seconds of written thinking.
