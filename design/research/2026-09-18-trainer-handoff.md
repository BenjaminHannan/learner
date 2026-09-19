# Premonition-mini trainer: handoff (2026-09-18)

This covers build steps 4-6 of design/06: `premonition/train.py`, `premonition/toy.py` and `tests/test_premonition_train.py`. No other module was edited.

## Status in one line

The trainer, curriculum, FLOP stop, label-free stream, evaluation, checkpoints and CPU smoke all work and are tested. D does **not** learn the far-fact toy: its retrieval reaches 100% recall@4, but its answers stay at chance, even when the gold card is loaded before loop 1. The toy gate (D ≥ 95%) is not met. It is kept unweakened behind `PREMONITION_SLOW=1`.

## What works (tested)

`tests/test_premonition_train.py` has 10 tests. Nine run by default (about 35 s including the smoke test) and the toy gate is skipped unless `PREMONITION_SLOW=1`. The model and data suites still pass: 41 tests in 62 s.

- **`MiniTrainer(Trainer)`** keeps `Trainer`'s AdamW groups, warmup, clipping, bf16 autocast (CUDA only), `read_only` evaluation and the memory guard.
  - **Curriculum by FLOP share** (§3):
    - 0-5%: gold mode.
    - 5-30%: teacher mode.
    - 30-100%: own mode, with p_own rising 0 → 0.75 by 60%, then flat.
  - **FLOP stop.** `calibrate()` fits a·tokens + b·Σ(questions × loops) with `flops.measure_mini`. The loop count of each batch is known before the step (`planned_loops` equals the model's `question_loops`; tested). Training stops at F and never trains a batch past F·1.05. Tested: stop reason "flop budget", `budget_ok`, 0 loop mismatches.
  - **Logs** every `log_every` steps: every loss, gold recall@4, answer accuracy, loops per question, HALT rate, tokens/s, FLOPs, grad and weight norms, and dead-MLP fraction. Card risk counts come from `card_stats` via `InsertLog`, a recording wrapper on `model._insert` that is removed afterwards.
- **`label_free(batch)`** (§9.1) drops every answer and feedback span from D's reader stream and rebuilds all token and line indices. It is applied in `train_toy`, `train_d`, `smoke` and the D scorer. Tested.
- **`entity_text`** writes an unknown entity id as `<entK>`, which scores wrong instead of raising (§9.12). Tested.
- **`validate()`** reports:
  - own-retrieval exact match;
  - `answer_with_gold` accuracy (gold cards before loop 1: the teacher-forced number);
  - recall@4 against a random-fetch baseline;
  - loops and halting by depth, and per-slice accuracy;
  - card risk counts: full gold set fetched, gold evicted by the 16-row FIFO, and the L_ans early-weight share.
- **Experiment-1 scoring for D.** `exp1` scores only `Core` models, so `d_scorer(cache, ...)` is passed into `exp1.evaluate_directory(scorer=...)`. `evaluate_d_checkpoint()` produces exp1's report shape, so `exp1.verdict` accepts it. The smoke test checks that every decision slice is present.
- **Checkpoints** go through `learnlab.ckpt`: `checkpoint_config`, `save_mini_checkpoint`, `load_mini` and `resume_trainer`. They carry the mini config, train config, curriculum, FLOP budget, spend and fit, the tokenizer and detector digests, and the data tag. The round trip is tested and gives the same answers.
- **CLI entry points:**
  - `train_d(budget, data_rel=, tokenizer_path=, flop_budget=, variant=, device=, checkpoint=)`;
  - `evaluate_d_checkpoint(budget, ckpt, split=, wipe=)`;
  - `smoke()`;
  - `train_toy(variant, steps=)`.
- **Smoke run** (tiny village: 60 train and 24 validation visits; d = 32; 49 steps; 26 s). Every check passed:
  - L_lm fell from 7.02 to 3.10, and L_ans from 6.19 to 1.96;
  - held-out recall@4 was 8.3%, against 4.9% for random fetching;
  - `answer()` works, `read_only` held, and every exp1 slice is present;
  - the FLOP share was 1.006, and the checkpoint round trip matched.
  - Held-out accuracy was 0% (expected at this budget).

## Toy results (`premonition/toy.py`, the tiny preset, W = 64, chance 6.25%)

**The toy.** Each visit has 12 fact lines "ENT REL VAL", over 6 entities × 3 relations with 16 values. Four questions each ask about a fact at least 132 tokens back (always > 2 W). The other facts act as distractors.

| # | Experiment | Result | What it rules out |
|---|---|---|---|
| 1 | `train_toy`: spec curriculum, lr 3e-3, 60 steps | acc 9%, recall@4 32% | – |
| 2 | Same, 446 steps (71 s) | acc 7%, recall@4 34%; L_ans stuck at 1.10 (VAL cross-entropy ≈ ln 16) | Not just too few steps |
| 3 | `train_toy`: lr 1e-3, warmup 100, 1,150 of 1,500 steps (stopped) | **recall@4 reaches 100% by step 600**; answer acc 4-7% throughout; gold-card acc = own acc = 5.5% | Retrieval is fine; the answer path is broken |
| 4 | Plain loop, gold mode only (cards preloaded), d 32 / 64 / 128, lr 1e-3 to 1e-2, 200-1,000 steps | acc 5-9%; L_ans 1.39 = chance in every run | Not width, lr or duration |
| 5 | Gold mode, 1 loop; answer loss only; 4 values instead of 16 | still chance (4 values: 27% vs 25%) | Not loop count, not LM interference |
| 6 | Linear probe on `store.values` at the gold line (untrained model) | 97% test accuracy for VAL | The card value *does* carry the answer |
| 7 | After 100 answer-only steps: probes on the card value / card row before think / after think / decoder cross-attention output | 91% / 84% / 67% / **5.6%** | The information dies between the think rows and the decoder |
| 8 | Decoder cross-attention to rows after training | uniform, about 1/15 per row (card 0.068), unchanged from init | The decoder never learns to attend to the card |
| 9 | `Decoder` alone (random rows, card = 0.2·E[y]); `Think` + `Decoder` on random rows | 100% by step 50 / step 100 | The modules can learn copying in isolation |
| 10 | Decoder on the model's *real* rows with a clean card, no think | 100% by step 250 | The real question, slot and register rows are not the problem by themselves |
| 11 | Same, **with one `Think` pass** in between (all trained) | 31% at step 300; every row norm grows from 0.2-5.7 to **17-20** | **Think is the bottleneck** |
| 12 | Replica: mask question rows (keep cards, slots, registers) | starts learning at about step 180 | Question rows make it worse, as in 11 |
| 13 | Replica: layer-normed card values (norm √d) or oracle card = E[VAL] | still chance, with question rows valid | Card scale alone is not the fix |

## Best current hypothesis

**The think block collapses the rows into one shared vector before the decoder can learn to read the card.**

1. At initialisation the think self-attention is uniform, so every row receives the same update, proj(mean V).
2. The learned loop-step embedding (`Think.step`) is also added to every row, every loop.
3. The fastest way to fit the answer marginal is to grow this shared component. That happens in the tens of steps it takes to learn the marginal; experiment 11 shows row norms of 17-20 against a card-specific part of about 0.3-2.7.
4. After the decoder's per-row LayerNorm, every row then looks alike, and cross-attention stays uniform (experiment 8).
5. The card's signal becomes a few percent of the attended vector and is lost among the question-dependent content that think mixes into every row (experiment 7: 67% probe accuracy on the think row, 5.6% after cross-attention).

Retrieval is unaffected because L_ask trains the query and key heads directly on register 0. That is why recall@4 reaches 100% while answers stay at chance.

**Consequence for the village runs:** gold recall@4 will look healthy while answer accuracy stays near D-noask. So the step-5 gate "gold recall ≥ 80%" cannot on its own tell whether the store works. The gold-card accuracy (`accuracy_gold_cards` in `validate`) must be watched too.

## Next 3 things to try (all in `model.py`, owned by the model builder)

1. **Make the answer path's access to cards independent of the think collapse.** Options: let the decoder cross-attend to the *pre-think* card rows (or to the concatenation of pre- and post-think rows); give card rows a per-row-type LayerNorm with gain; or zero-initialise, or gate, the think residual (a ReZero-style α = 0 start) so rows start as their own content. Rerun experiments 11 and 3; expected: gold-card accuracy near 100% within a few hundred steps.
2. **Remove the shared-offset path:** subtract the mean over valid rows before the decoder's LayerNorm, or add the loop-step embedding to the registers only. Put the step and row-type embeddings in the weight-decay group, which `Trainer` already does for 2-D parameters, and check whether decay alone helps at lr 1e-3.
3. **Then rerun the toy gate** (`PREMONITION_SLOW=1`, `train_toy("D", steps=1500, lr=1e-3, warmup_steps=100)`, about 4 min on the M1). If D passes, measure D-noask (the other half of the gate) and the steps needed. If gold-card accuracy is still at chance, bisect with `answer_with_gold` and the probes above; the scripts were in the session scratchpad and are easy to recreate from this table.

## Notes for whoever continues

- **§9 revisions not in the trainer yet** (they need model support first):
  - reachable-gold L_ask and rollout HALT targets (9.9) belong in `forward`;
  - D-no-oracle (9.3) needs straight-through top-k in the model;
  - the new lesion switches (9.5) need `answer()` changes. `d_scorer` passes `wipe`/`window_line` only when a wipe is requested, so it will need a small update when that signature changes.
  - The FLOP additions for elementwise work (9.7) get picked up automatically if they land in `flops.measure_mini`.
- **Risk counters to read on the first real run** (`cards` in logs and validation):
  - `full_gold_fetched` versus `any_gold_fetched`: the set cross-entropy is satisfied by one gold card. In the smoke run 39% of told questions fetched some gold card but only 7% fetched all of it; for multi-gold questions it was 1.7%.
  - `fifo_gold_evicted_questions`: 0 in the smoke run; 2 questions had |G| > 10.
  - `ans_early_weight_share`: 0.93 in the smoke run. Nearly all answer terms sit at the ×0.2 early weight once own retrieval misses gold, and the model counts an evicted card as fetched.
