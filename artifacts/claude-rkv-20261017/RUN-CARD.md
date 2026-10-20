# RUN CARD: decoder_reader_kv (the decoder sees the reader's finished state)

Written 2026-10-17 (UTC), before any training. **Status: DRAFT, UNSEALED.** The code is a draft until the
coordinator's code review (Q11) passes. Nothing has been booked and nothing has run.

**Coordinator rulings Q11–Q13 (Muse, received 2026-10-17) are filled in below**, each marked *[filled: Qn]*.
Order from here: (1) Q11 code review of the PR #79 diff passes → (2) seal this card (`shasum -a 256
RUN-CARD.md > SEAL.sha256.txt`) → (3) stage 0 may run → (4) stages 1+2 book only if stage 0 passes its gate.

Directed by Ben on Oct 17, relayed by the coordinator: "make it so that the decoder can see the reader's
finished state." The idea comes from DeepSeek V4.1's causal encoder-decoder, where the decoder's
cross-attention KV is projected from the encoder's final hidden states.

## 0. Read first: what I found that the brief assumed

| # | Brief assumes | What the repo shows (branch `main` @ 73b8e0224, plus `claude/learner-new-g2`) | Consequence |
|---|---|---|---|
| F1 | "same parent checkpoint" | **No PremonitionMini checkpoint exists.** 0 of the 49 `.pt` files in the repo have its keys. No D training run is recorded. | There is no parent to fork from. Section 3 offers P1 (paired fresh start) and P2 (a parent the coordinator names). |
| F2 | D is a working model to improve | `design/research/2026-09-18-trainer-handoff.md:7`: "D does **not** learn the far-fact toy … its answers stay at chance, even when the gold card is loaded before loop 1." Row 8 of that handoff: "The decoder never learns to attend to the card". Row 11: "Think is the bottleneck". | The new path gives the decoder a road around Think. A rise in score here is exactly as likely to be a bypass as a real gain, which is why the guard (section 5) carries the verdict. It also means a $0 toy stage should come before any GPU (BID.md, stage 0). |
| F3 | "held-out join score", "house-form bars", "DEV slip", "house family rule", "$50/week cap" | None of these is defined anywhere in either branch. The repo has: the **family rule = "≥ 2 of 3" seeds, never averaged** (`artifacts/fable-dispatcher-probes26-20260921/AUDIT-26.md:306`); **bars = 2 × the measured noise SD** (`artifacts/claude-dir-lr-20260928/NOISE.md`); a **−3 point** non-inferiority bound (`design/06-premonition-mini-spec.md` §9.4); `learnlab/policy.py` `MIN_EFFECT = 0.03`, `ALPHA = 0.01`. | Sections 4–6 proposed these; the coordinator's Q13 ruling confirmed them (marked *[filled]*). "Join score" = the card's fallback, exp1 overall accuracy. |
| F4 | editing `premonition/model.py` is fine | `handoff/HANDOFF.md:33`: "never edit `archive/`, `premonition/`, `learnlab/`". | I made the edit because Ben directed this specific change. The coordinator should confirm the override in the code review. |
| F5 | a launcher exists | There is no training CLI. The spec's `python run.py premonition train` is not wired. The entry point is `premonition.train.train_d(...)` (`premonition/train.py:1041`). | A small launcher (a new file) gets written after gating, at $0. It is not part of this card's code. |

## 1. Question and arms

Does giving the answer decoder a second cross-attention, onto the reader's finished hidden states, raise
held-out answer quality **without** the thinker giving up its own ASK/fetch work?

- **Control (A0):** `MiniConfig.preset("D", "full", vocab_size=VOCAB_V2)` with `decoder_reader_kv=False`, the model as it is today.
- **Treated (A1):** the same config with `decoder_reader_kv=True`. That is the only difference.

Size: d = 128, 2,102,228 parameters for control and 2,168,532 for treated (+66,304, +3.2%). Treated costs
about +3.4% training FLOPs per step (hand count on a 48-visit, 1,058-token batch). Both numbers are
reported. Neither is matched, because "one change only" means the architecture change, and adding a
capacity-matched control would be a second change.

## 2. The change (code under review)

`premonition/model.py`, class `ReaderAttention`, inside `Decoder`:

- Block order: causal self-attention → cross-attention to the think rows (unchanged) → **cross-attention to the reader states (new)** → MLP. Each step is a pre-norm residual, like the existing blocks.
- Memory: the post-norm `hidden` returned by `Reader`, which is the same tensor the card writer reads. KV is projected once per visit (`reader_attn.kv`, d → 2d) and gathered per question.
- Mask: real tokens only (`line_of >= 0`), and only positions before the question's `q_span` end. So the decoder sees the question up to and including `[answer]` and nothing after it. After `wipe="store"`, the mask also drops reader states before the window start, so the store-wipe probe still wipes. *[filled: Q11b]* CONFIRMED as proposed; the review verifies the mask code does exactly this.
- `premonition/` no-edit rule (F4): *[filled: Q11a]* override CONFIRMED as a single directed exception for this flagged change only; the review verifies the diff touches only the flagged path.
- Init: from its own generator, `Generator(7100 + seed)`, using the house stds (0.02, and the residual std on the output). Construction runs under `fork_rng`, so the **global RNG stream and every shared weight are bit-identical to control** at the same seed.
- Thinker, card store, ASK, HALT and reader: not changed. Subclasses that override the decoder path (`QReadMini`, `CardBypassMini`, …) refuse the flag rather than ignore it.

## 3. Setup (fixed here)

- **Parent:** *[filled: Q13.2]* **P1, paired fresh start** (no PremonitionMini checkpoint exists to name for P2; P1's identical init and data order is the fair comparator).
  - **P1 (chosen):** paired fresh start. Both arms are built with `torch.manual_seed(s)`. A test shows that every shared weight and the RNG state after construction are identical between arms, so the pair differs only in the new path.
  - **P2 (not used):** a parent checkpoint the coordinator names. Both arms load it. Treated loads with `strict=False`, and a test shows the only missing keys are `decoder.reader_attn.*`. The new weights then come from `reset_reader_kv(seed)`.
- **Recipe:** `train_d` defaults. AdamW, lr 1e-3, warmup 100, clip 1.0, bf16 autocast, `max_tokens=55_000`, `max_visits=48`. Curriculum: gold 0–5%, teacher 5–30%, own 30–100%. Data: the v2 tokenizer and the village visits named in the spec.
- **Length:** both arms train the **same number of steps**. That is the control's step count at budget F (spec §5: F ≈ 3.15e16 FLOPs). `train_d` stops on FLOPs, so treated would otherwise stop about 3% early on different data. Data order is identical (same seed, same loader). Treated's extra FLOPs are reported.
- **Seeds:** 3 pairs, s ∈ {0, 1, 2}, precommitted. Reasoning: no D run has ever produced a held-out score, so sigma is unknown. The nearest house noise figures are 3.3–4.2 points SD per seed on other lines (`handoff/director-briefs/sweep-tests.md`, NOISE.md). Paired differences on a shared init and data order should be tighter. Three pairs is the minimum at which the family rule (2 of 3) can be read and an SD of the paired differences exists at all. **Extension rule, fixed now:** if the result sits within 1 SE of the bar, add pairs 3 and 4 once, then stop.
- **Machine:** one vast RTX 5090, on-demand only, never interruptible.

## 4. Primary readout and bars (written before training)

- **Primary score ("held-out join score"):** *[filled: Q13.1]* the card's fallback. Primary = held-out `exp1` **overall** accuracy from `train.evaluate_d_checkpoint`; all decision slices reported (`premonition/slices.py:57`: overall, near, far, far_deep, multi_hop).
- **Per pair:** d_s = score(A1, s) − score(A0, s).
- **Bar (sized from the run's own paired differences, house 2× rule; *[filled: Q13.1]* stands as written):** mean(d) − 2·SD(d)/√n > 0, **and** mean(d) ≥ 3.0 points (`MIN_EFFECT`), **and** d_s > 0 in at least 2 of 3 pairs (family rule).
- **Verdicts:**
  - **PASS:** all three bar conditions hold **and** the guard holds.
  - **NOT SHOWN:** the bar fails.
  - **PROVED WRONG:** mean(d) + 2·SD(d)/√n < 0, meaning the treated arm is worse.
  - **"gain not counted (writer bypassed the thinker)":** the bar passes but the guard trips.
  - **DID NOT TRAIN:** either arm's loss is not finite, or the run stops early.

## 5. Guard metric (this is what makes a gain count)

Computed with `scripts/premonition_reader_kv_guard.py` on the model's own greedy answers (`answer()`),
on the same held-out questions as the score, for both arms and every seed:

- **asks per question:** loops on which the ASK logit is > 0 on a loop that did not end. This is exactly the condition under which `answer()` fetches.
- **cards fetched per question:** distinct real cards. NULL fetches are counted separately.
- Also reported: `asked_rate`, `loops_mean`, `halt_rate`, and gold recall@4 from `train.validate`.

**Rule:** the guard trips when treated's mean cards fetched per question, pooled over the paired seeds,
is **more than 20% below** control's. Then the verdict is "gain not counted (writer bypassed the thinker)"
whatever the score. If control fetches no cards at all, the guard cannot be read, and the gain is not
counted either. *[filled: Q13.4]* **POOLED** for the verdict: the 20% trip is computed on the pooled mean
cards/question. Per-seed drops are reported alongside as evidence, not as a second verdict.

## 6. Forgetting: DEV slip

- *[filled: Q13.3]* As proposed: DEV is the validation split (`train.validate`, the spec's "validation for development"). Treated **fails the arm** if its DEV accuracy is more than 3 points below control's (spec §9.4 bound) in at least 2 of 3 paired seeds (family rule). Per-seed verdicts, never averaged.
- DEV accuracy is reported for both arms at every eval, plus the final value.

## 7. Required rows (per seed, both arms)

seed · arm · steps · tokens · FLOPs · wall s · final losses (lm, ask, ans, halt) · primary score and every
slice · DEV accuracy · asks/q · cards/q · null/q · asked_rate · loops_mean · halt_rate · gold recall@4 · d_s.

## 8. Raw outputs

Every rented box writes `RESULT.json`, the logs, the eval JSONs and the final checkpoints under
`artifacts/claude-rkv-20261017/run/<arm>-s<seed>/`. These are **copied off the box with `rsync` and checked
against `sha256sum` before the box is destroyed**, then committed. A RUN-NOTE.md (start `date -u`, PIDs,
machine, torch version, expected steps, ETA) is committed within minutes of the start.

## 9. The result that would prove it wrong

mean(d) + 2·SD(d)/√n < 0, or the guard trips while the score rises. The second would mean the new path
answers instead of the thinker, not alongside it.

## 10. Predictions (guesses, not results)

Given F2, my guess is that treated scores higher on near and overall, because the decoder can now copy
from the question-time reader states it previously could not use. I also guess fetch use falls, and that
the guard decides the verdict. P(guard trips | score rises) ≈ 0.5.

## 11. Self-check (house marks, Ben 21:37 UTC 09-28)

1. Bars above the measured noise: the bars come from the run's own paired SD. No outside noise figure exists for D (F3).
2. Rejections use the every-seed reading: yes (family rule, 2 of 3).
3. Fair comparator: same init, same data and same steps. The only difference is the flag.
4. A row a plain same-size net cannot pass, and a memorisation check: *[filled: Q13]* **not applicable** to this card. A single-change paired A/B does not add a second change at seal time.
5. F_few beside F_eq: not applicable (no few-shot split here).
6. Sleep gates: not applicable.
