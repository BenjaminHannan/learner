# Test 8a-G: does a Gemma-fronted model gain more from size than a plain model? (spec, 2026-10-08, 10:30 AM ET, before any run)

Owner: whole-model roadmap thread. Marks fixed here before anything is built or run. Any change after the first run needs
a dated addendum.

## 0. Why, and Ben's words

- Ben, 10:16 AM ET 10-08 (relayed by the coordinator, his own words): "It should scale more than a plain model. so from
  increased parameters, the benefit should be more than the plain model. Also, the model should have the gemma embedder
  as it's main inputting/ecoder or whatever. basicallly it should just be in our plans for the finished model. [...] if
  the reader being good is part of the model, that's fine. It's just that the thinker should learn more and be the
  driving intelligence. You don't have to ban any help from the gemma reader. Also, I don't care if you use the
  fineweb-edu text. [...] For the three cals waiting on me, just do what you want".
- 8a's result (`8A-10M-RESULT-2026-10-08.md`): today's B2 with the letter reader gained +0.49 from 3M to 10M; the plain
  step model gained +3.77 on the same pool (shown). So the letter-reader B2 fails Ben's bar. The 30M rung of that B2 is
  held (our call, as Ben allowed).
- EGE (B2 with the frozen EmbeddingGemma 2 in front of its letter window, `ledger.py` `eg_embed=True`) is our best
  Gemma-fronted model: 6-seed confirm on the q33 data +2.67 pooled-5 over B2, ahead on 6 of 6, failing only the
  zero-round leak mark (shown, q39). Ben's message allows reader help, so that mark no longer blocks it.

## 1. The one change

Against the 8a ladder, one thing changes: **both the model and the plain yardstick read the prompt through the same frozen
EmbeddingGemma 2 front.** Pool, rows, order, caps (addendum G), seeds, 24,000 updates of 256 rows, learning rate and
rung shapes (3M; 10M grown deep, blocks 2 -> 8) stay as in 8a, so 8a's letter-reader results stand beside these as a
reference (disclosed: the probe hinted that a wider shape did slightly better, +1.0 vs +0.2 on two seeds; it is not used
here, to keep one change).

## 2. Arms (per seed, per rung; both arms of a seed and rung on one rented RTX 5090)

- **Ours (G-B2):** EGE: B2 with `eg_embed=True` (linear adapter, letters kept). 3M = B2_S + adapter; 10M = 8a's deep 10M
  B2 + adapter. The adapter counts as trained parameters.
- **Plain yardstick (G-PT):** 8a's plain step model (`plain_tf_steps_g`, writes steps # answer) with the same front: each
  prompt character's input embedding gets `eg_proj(ln(H))`, H = the EmbeddingGemma state of the token holding that
  character, zero-initialised, nothing added past the prompt. Sized to within 2% of G-B2 at each rung, as in 8a. **Not
  built yet** (the 8a job refuses `eg_embed`; `custom_io/g8a/README.md`).
- Gemma's 271,002,624 frozen parameters are the same in every arm; whole sizes are reported with them counted (Ben's rule).
- Reported, not run again: 8a's letter-reader B2, PT and LLM at 3M and 10M on the same seeds.

**Why the step model is the yardstick** (default picked, Ben can override): it learns the same rows and writes the same
answers, so the difference is the design. The plain LLM recipe gained +15.8 from size in 8a, but it starts 26 points
lower; it stays reported.

## 3. Marks (6 seeds, 400-405; per seed d = 10M score minus 3M score, pooled-5 on the 6,040 dev rows)

1. **Ben's bar: ours gains more from size than the plain model.** Mean over seeds of d(G-B2) - d(G-PT) > 0, with its
   95% CI (t, n = 6) above 0.
2. **Ours grows at all.** Mean d(G-B2) has its 95% CI above 0.
3. **The thinker drives the gain** (Ben: "the thinker should learn more and be the driving intelligence"). With the
   thinker switched off (`loops:0`, zero rounds), the rest of the model (reader and talker) is allowed to help, but:
   (a) at both rungs, G-B2's full score minus its thinker-off score is at least half its full score; and (b) at least
   half of G-B2's mean size gain comes from the thinker: mean [d(full) - d(thinker-off)] >= 0.5 x mean d(full).
4. **Good enough.** G-B2 at 3M has a 6-seed mean of at least 72.0 (8a's mark 4).
5. **Guard.** Chain-5 >= 99 at both rungs (the calculator path is intact).

**Proved wrong** (for "a Gemma front lets our design out-scale the plain model"): mean d(G-B2) - d(G-PT) below -1.0
with its CI below 0.

**Reported:** per-dev-file and per-family gains (the rule and pattern families above all: fewshot_number_rule,
seq_next, order_chain, rule_apply); training-loss parts; thinker-off score per rung; G-B2 minus 8a's letter B2 per rung
(what the Gemma front is worth); G-PT minus 8a's letter PT; hours and dollars per arm.

## 4. Two-seed screen first (seeds 400 and 401; readout fixed now)

- **Go on to the other 4 seeds:** d(G-B2) - d(G-PT) >= +1.0 on both seeds AND d(G-B2) > 0 on both.
- **Stop:** d(G-B2) - d(G-PT) <= 0 on both seeds. The design change has to come from the thinker, not the reader.
- Otherwise **unclear:** run the other 4 seeds (the full marks then decide).
- Guard on the screen: chain-5 >= 99 on both seeds.

**Prediction (suggested, written now):** the screen stops. 8a's per-family table points at the thinker and its answer
writer (near 100% on calculator questions, flat on rule questions), and a better reader does not change what the thinker
can express. What would prove that prediction wrong: G-B2 passes the screen with gains on the rule families.

## 5. Build, money, order

- **Build** (8a build code, PR #51, branch `claude/project-thread-f1to6a`; routed to its owner through the
  coordinator): (1) the G-PT front in `plain_lm.py`, zero-initialised, with a unit test that at step 0 it computes exactly
  what PT computes; (2) the 8a job accepts `eg_embed` when every arm has a front; (3) the bands count the adapter; (4)
  the box installs a transformers version with EmbeddingGemma 2 (>= 5.19; 8a's box pins 5.17.0) and checks the 3 probe
  vectors (`python -m custom_io.models.eg check`).
- **Speed first:** one 5090 times 200 updates of each arm at 3M and 10M (about 20 minutes). The caps per box are set
  from it. Our estimate before timing: about 12 GPU hours a seed (Gemma's forward pass about doubles the 3M cost), about
  $6 a seed, about $12 for the screen and about $36 for all six seeds (could be off 2x).
- Rented 5090s (Ben's standing Vast OK; the account refills). Per-box caps from the speed check; boxes destroyed when
  done; checkpoints exported (one collector at a time).
- **Not in this test:** 30M; the learned stop (H1); the calculator as a tool (T1/2c2). Those belong to B3, which must
  pass this same bar at 3M -> 10M before the 8c ship build.
