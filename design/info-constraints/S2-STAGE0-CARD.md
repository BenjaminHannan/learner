# RUN CARD: S2 Stage 0, `decoder_raw_cards` on the far-fact toy (m02 protocol)

**Status: SEALED BEFORE ANY STAGE-0 NUMBER EXISTS.** Committed 2026-10-19 under ruling E3 ($0, CPU, this
session's container) and the 10-19 coordinator GO. Nothing in this card moves after the first run starts.
The code is DRAFT until the Claude Code built-in code review passes on the final diff (E6).

## 0. Read first: one correction to the REPORT before running

REPORT §S2 called this "the m02 ladder-toy protocol". **m02 is the far-fact toy** (`premonition.toy.ToySpec()`,
16 values), not the ladder toy (`scripts/premonition_m02_answer_path.py:79-81`, `:103-112`). The protocol below
is m02's, which is what the S2 design meant. It is also where D-card-bypass was shown: 1024/1024 vs D 112/1024.

The REPORT also proposed a second void rule ("the control must reproduce D's ≈ 11% within its Wilson
interval"). It is **dropped here, before running, and reported only**. m02 ran a frozen 09-18 source snapshot,
and this card runs `main` @ 73b8e0224 plus the flag. So "different from 11%" can come from the source drift.
It is not a validity failure. The coordinator's distinct-answer rule is the only void rule.

## 1. Question and arms
Does giving the decoder an unwashed copy of each inserted card (S2) let tiny D copy a supplied gold card that
plain D, after Think, cannot copy?
- **Control:** plain D, `MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64)`.
- **Treated:** the same, plus `decoder_raw_cards=True`. One change. 0 extra parameters. Identical init and
  RNG stream at the same seed (`tests/test_premonition_decoder_raw_cards.py::FlagOnTest`).
- **Seeds:** model seeds 0, 1, 2, paired: each seed trains both arms on the same batches.
- Per E4, the base is plain D (no fix has passed), so this pair is also the plain-D pair.

## 2. Setup (fixed here; m02 values)
- **Data:** far-fact toy v16 (`ToySpec()`), 16 visits per step, `label_free`.
  - Train stream `toy_stream(spec, 16, 101)`.
  - Test split `toy_set(spec, 16, 16, 303)`: 16 batches, 256 visits, 1,024 questions, scored once per
    checkpoint at the end.
  - No validation-based selection.
- **Training:** `model.forward(batch, mode="gold", loops=2, weights={"ans": 1.0})`, i.e. every gold card
  preloaded, 2 think loops, answer loss only. 800 steps.
  - AdamW lr 1e-3, linear warmup 100, betas (0.9, 0.99), eps 1e-8; weight decay 0.1 on tensors with
    dim ≥ 2, 0 otherwise.
  - Global grad clip 1.0.
- **Evaluation:** greedy decode as m02 `greedy_correct`: gold card preloaded, 2 think passes, no fetches,
  exact match against value + `<eos>`.
- **Machine:** this container's CPU, torch 2.14.1+cpu, 1 thread per run. Cost $0.

## 3. Readouts, every arm and seed
- `acc`: test accuracy with the gold card (primary), with its Wilson 95% interval.
- `acc_removed`: test accuracy with **no card** inserted, 2 passes (card-use check).
- `distinct_256`: distinct greedy answers over the first 256 test questions (first 4 batches).
- `distinct_1024`: the same over all 1,024.
- Training loss curve every 100 steps, wall seconds, steps run, finite-gradient flag.

## 4. Validity (VOID rule; coordinator 10-19)
- A seed's cell is **VOID** if the **control** gives only one distinct answer across the first 256 test
  questions (`distinct_256 == 1`). A void cell is evidence about nothing, for or against, and is left out of
  every count below.
- If all three seeds are void, Stage 0 is **VOID**. The next step is then to extend the protocol, which needs a
  new card. It is not a result about S2.

## 5. Pass marks (written before running)
Over the valid seeds (n ≥ 2 required; with n < 2 Stage 0 is INCONCLUSIVE). d_s = treated acc − control acc.
- **PASS** needs all of:
  1. treated `acc` ≥ 50% on every valid seed;
  2. d_s > 0 on every valid seed, and mean(d) − 2·SD(d)/√n > 0;
  3. card-use guard: treated `acc_removed` ≤ 9.25% (chance 6.25% + 3 points) on every valid seed;
  4. treated `distinct_256` > 1 on every valid seed;
  5. every run finished 800 steps with finite gradients.
- **FAIL:** treated `acc` < 25% on at least 2 valid seeds, **or** mean(d) ≤ +3 points.
- **INCONCLUSIVE:** anything else. Reported as is, with no re-run under changed marks.

## 6. The result that would prove S2 wrong
On the valid seeds, treated accuracy is within 3 points of control on at least 2 seeds, i.e. an unwashed card
copy does not help copying in the setting where D-card-bypass reached 1024/1024. Or the card-use guard
fails (treated answers as well without the card), meaning the gain does not come from reading the card.

## 7. What a PASS does and does not buy
- **Buys:** S2's mechanism works for reading one supplied card on the far-fact toy, from the main code path.
- **Does not buy:**
  - choosing among cards (m02: bypass falls to 43-66% with distractors);
  - own-retrieval use, where the reader-kv fetch-use guard applies;
  - anything on the village ruler.
- Next, only after a PASS: the distractor reading (gold + 2 random fact cards) as a reported second readout,
  then a Stage-1 bid priced by measured seconds per update (E5).

## 8. Raw outputs
`artifacts/claude-infoconstraints-20261018/s2-stage0/{control,treated}-seed{0,1,2}.json` and `.log`;
summary `artifacts/claude-infoconstraints-20261018/s2-stage0/summary.json`.
Runner: `scripts/info_s2_stage0.py`.
