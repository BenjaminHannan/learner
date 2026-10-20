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

---

## 9. Result (appended after the run; sections 0-8 above are unchanged since commit 7f4f10a9a)

Run 2026-10-19 in this container, CPU, torch 2.14.1+cpu, 1 thread per run, 800 steps per arm, $0. Raw:
`artifacts/claude-infoconstraints-20261018/s2-stage0/`; `summary.json` is the runner's verbatim application of
§4-§6.

| seed | control acc (/1024) | treated acc (/1024) | d | control distinct (256 / 1024) | treated distinct (256 / 1024) | no card: control / treated | train s (control / treated) |
|---|---|---|---|---|---|---|---|
| 0 | 10.94% (112) | **100.00% (1024)** | +0.891 | 2 / 2 | 16 / 16 | 5.66% / 7.03% | 178 / 180 |
| 1 | 12.60% (129) | **100.00% (1024)** | +0.874 | 2 / 2 | 16 / 16 | 6.93% / 6.64% | 184 / 181 |
| 2 | 10.94% (112) | **100.00% (1024)** | +0.891 | 2 / 2 | 16 / 16 | 5.27% / 0.00% | 182 / 180 |

- **Validity:** no cell is VOID. The control gives 2 distinct answers on every seed. That is valid under §4, but
  only just: plain D barely uses the card here.
- **Pass marks (§5):**
  1. treated ≥ 50% on every valid seed: yes, 100% each;
  2. d > 0 on every seed, and mean(d) − 2·SD(d)/√3 = +0.874 > 0 (mean +0.885): yes;
  3. card-use guard, treated with no card ≤ 9.25%: yes (7.03%, 6.64%, 0.00%);
  4. treated distinct > 1: yes (16, all values);
  5. all runs finished 800 steps with finite gradients: yes.
- **Verdict: PASS.** The fail rule and the proves-wrong rule (§6) did not fire.
- **Reported check (not a void rule, §0):** control seed 0 reproduces m02's 112/1024 exactly, on `main` + flag
  with the flag off.
- **Scope (§7):** this buys reading one supplied card from the main code path. It does not buy choosing,
  own retrieval or the village ruler.

---

## 10. Distractor reading (card §7's "reported second readout"); spec sealed before running, 2026-10-20

Coordinator GO 10-20: "exactly as card section 7 sets it out, with no changes to its marks". §7 defines this as a
**reported second readout with no pass marks**, so it gets **no verdict**. It is read, not judged. Fixed here
before any number:
- **Models:** the six Stage 0 arms (control / treated × seeds 0-2). Their weights were not saved, so each is
  retrained with the identical §2 setup at 1 thread (deterministic: shown for treated seed 0 in REPORT, review
  round 3). The runner **asserts** that each retrained arm reproduces its filed §9 gold-card score
  (correct/1024 and distinct counts) before reading it. If any assert fails, that arm is reported as "not
  reproduced" and is not read.
- **Reading:** the m02 `cmd_multi` condition at n = 2.
  - The gold card plus 2 other eligible fact cards of the same visit (non-gold, non-NULL), inserted in a random
    order (m02 `distractor_preload`, generator seed 7000 + 2 = 7002), then 2 think passes and greedy decoding.
  - Split: the §2 test split (seed 303, 1,024 questions), scored by §2's exact match (value + `<eos>`).
- **Readouts per arm and seed:**
  - `acc_d2` with its Wilson 95% interval;
  - `predicts_distractor_value` (the first answer token equals a distractor card's value and not the gold
    value, as m02);
  - `distinct_256` and `distinct_1024` over the predictions.
- **References** (context, not marks): copying a random card scores 33.3%. m02 bypass was 545/1024 at n = 2,
  but on the validation split with first-token match, so it is not directly comparable.
- **VOID rule (coordinator 10-19):** a seed's pair is VOID if the control's predictions under this reading have
  one distinct answer over the first 256 questions.
- **Raw:** `artifacts/claude-infoconstraints-20261018/s2-distract/`.
