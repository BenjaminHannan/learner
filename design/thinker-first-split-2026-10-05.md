# Thinker-first split: make the thinker the big part (2026-10-05)

Ask (Ben, 6:19 PM ET 10-05): today a huge model reads, a thinker about 100 times smaller thinks, and the same huge
model talks. How do we make the thinker most of the model, with the reader and talker as small parts that only read
and talk?

Labels: **shown** = measured in this repo or counted from a config, **suggested** = reasoned from results or papers,
**untested** = a guess. Times are US Eastern (ET).

## 1. Where the weight and the work sit today

| part | what it is | weights | share |
|---|---|---|---|
| hearer (reader) | frozen LFM2.5-1.2B-Instruct, all 16 layers, last hidden state | 1,170,340,608 | ~99% |
| door + thinker | reader 2048 -> 32 -> 256, ~9M looped core (4 rounds) | ~9M (about 1.6M live: the MoE router never learns) | <1% |
| talker | the same frozen LFM2.5-1.2B, run again over prefix + every question word + answer | (same weights) | |

- Shown (HF safetensors metadata): LFM2.5-1.2B-Instruct has 1,170,340,608 weights: a 134,217,728 tied word table
  and 16 layers (10 conv layers of 67,119,104, 6 attention layers of 60,821,632; counted from `config.json`, and the
  sum matches the total exactly).
- Suggested (estimate): per question word the big model runs 32 layer passes (16 to read, 16 to talk, because the talker
  re-reads every question word). The thinker does about 1-2% of the work.

### Why the big model is the real thinker today (shown)
- Copy-talker test (PR #37, `reasoner_ptr/real/english/RESULTS-CT.md`): feeding the LM talker another question's
  thinker states still scored 73.2% on unseen kinds, the same as the right states (73.2%); 334 of 384 answers did
  not change. On new kinds the 1.2B answers by re-reading the question.
- Without the question words the talker drops from 82.9% to 18.9% (R7, PR #30, `RESULTS-R7.md`). Speed: first answer
  token is 2.97x the bare LM, mostly from the second full LM pass.
- A 350M LFM as hearer and talker: 66.1% vs 92.6% (PR #36). The trained parts add about the same on top of either LM
  (+16 to +18 over its own 8-shot score), so the borrowed LM's skill sets the level.
- Growing the core: +1.9 only (fair scaling, PR #18).
- Ultracode lesions (PR #38): with LM-written steps the LM does the thinking and the core is a family switch; the
  plan route (thinker plans, exact calculator computes) is the one place the thinker decides every answer
  (plan_swap lesion -> chain 2-3 of 160).

So shrinking the reader and talker fails while they are also the thinker. The knowledge has to move into the thinker.

## 2. The shape we want already exists inside the big model (suggested, from papers)
- Lad, Gurnee, Tegmark (arXiv 2406.19384, NeurIPS 2025): across 8 model families, early layers turn tokens into
  ideas ("detokenization"), middle layers refine features, late layers turn ideas back into the next word. Deleting or
  swapping a middle layer keeps 72-95% of accuracy with no training; the first and last layers are fragile.
- Huginn-3.5B (Geiping et al. 2025, arXiv 2502.05171): 2 prelude layers, a 4-layer block looped up to 32 times,
  2 coda layers. That is Ben's picture: small reader, big looped thinker, small talker.
- Retrofitted recurrence (McLeish et al., arXiv 2511.07384): turned pretrained TinyLlama-1.1B, OLMo-2-1B and
  Llama-3.2-1B into prelude / looped block / coda, e.g. (4,6,4) for 16-layer Llama, and beat the plain post-trained
  model on GSM8K at equal training compute (TinyLlama 51.2 vs 46.2). They used about 52B tokens of training.
- Ouro (arXiv 2510.25741): looped 1.4B models, trained from scratch on 7.7T tokens, match 4B models.
- Caution: a probe of Huginn (arXiv 2507.02199) found little sign of step-by-step thinking inside the loop and only
  small gains from more loops on arithmetic. That matches our own finding that exact step values beat latent ones, so
  the looped thinker should keep the plan + exact calculator route.

## 3. Ways to get there

| | way | thinker share | keeps English | nothing pretrained | cost on our machines |
|---|---|---|---|---|---|
| A | **Cut the big model open** (recommended): reader = word table + first 2 layers, thinker = middle 12 layers looped, talker = last 2 layers. One pass; the talker only sees what came through the thinker. | 66% of weights, 86% of work at 2 loops | yes | no (for now) | 1.2B with 774M trained: suggested to fit the 5070 Ti with 8-bit Adam and checkpointing (untested) |
| B | **Teacher, then goodbye** (distill): train a thinker-heavy student with the big model as teacher, ship the student alone. | any we pick | if the distillation works | yes for the shipped model | large: many millions of teacher answers |
| C | **Build from scratch** (custom reader/talker thread owns it, PR #39): B2 at 3.3M beats a same-size transformer 73.7 vs 67.7 (2 seeds). | any we pick | must learn English from scratch | yes | fine at 3-100M; a 1B model from scratch is suggested at roughly a month of the PC non-stop (20B words), and still far short of the trillions LFM saw |
| D | Grow the tiny core inside today's sandwich | could reach a few % | yes | no | not recommended: +1.9 only, and the talker still re-reads the question |

Weights for A, counted from the config (shown): reader 268,455,936 (22.9%: word table 134.2M + 2 conv layers),
thinker 773,941,888 (66.1%: layers 2-13), talker 127,942,784 (10.9%: layers 14-15; it reuses the tied word table to
pick words). Work share at 2 loops: 24 of 28 layer passes per word (86%); at 3 loops 36 of 40 (90%). Today: 32
big-layer passes per question word.

### Recommendation
A first, then shrink, then C for the long run:
1. Map the big model (Test 1, no training) to find where reading ends and talking starts.
2. Cut it open and loop the middle (Test 2). Same total size as today, about half the reading work, and the thinker
   is 2/3 of the weights.
3. One change at a time after that: put the plan + calculator route inside the looped thinker; then cut open the
   350M LFM and try to match today's 1.2B model at a third of the size.
4. Long run (nothing pretrained): use the proven shape and the cut-open model as a teacher for the from-scratch line
   (way B into C). The custom reader/talker thread owns C.

## 4. Test 1: map the big model (no training; forward passes only)
Owner: a Sonnet implementation thread; machine per the compute rule (own machines first; this fits the M1 Pro).

- Model: `LiquidAI/LFM2.5-1.2B-Instruct`, revision `0f604ada3f766f9f257460c4c9f0b5d6f69d431b`, bf16, frozen.
- Questions: the round-6 bare 8-shot setup (`lm_fewshot` in `reasoner_ptr/real/english/run_english.py`, branch
  `claude/project-thread-utxkpw`) on FRESH-EN-R3 (192), NEW-KINDS-R5 (192) and NEW-KINDS2-R6 (192) = 576 questions.
  Bare 8-shot today: 75.0 / 67.7 / 77.6.
- Variants (33): the full model; **skip layer i** for i = 0..15 (a forward hook returns the layer's input unchanged);
  **repeat layer i** for i = 0..15 (run the layer twice in a row).
- Score: exact match, same scorer as round 6. If greedy generation is too slow, teacher-forced exact match on the gold
  answer for every variant (say which).

Marks, fixed now (F = full-model pooled exact; drop_i = F - skip_i):
- A layer is **critical** if drop_i >= 20 points.
- Reader = layers 0..k, k = the last critical layer among 0-5 (k = 0 if none). Talker = layers m..15, m = the first
  critical layer among 10-15 (m = 15 if none). Thinker = layers k+1 .. m-1.
- **GO** for Test 2: the thinker gets >= 10 layers.
- **KILL** for way A: the thinker gets < 8 layers. Switch the recommendation to way B.
- 8 or 9 layers: GO, with the smaller share stated.
- Loop readiness (read for Test 2's setup): mean drop when repeating a thinker layer <= 5 points -> start looping
  with a short heal; > 15 points -> heal first, as the retrofit paper did.
- Prediction written before running (untested): reader 1-2 layers, talker 1-2 layers, mean middle skip drop < 10.

## 5. Test 2: cut-open screen (2 seeds, then 6 to confirm)
Runs only after Test 1 says GO. Cut points come from Test 1 (default (2,12,2)).

- Data and budget: exactly round 6's `six` arm: allptr generator, 8000 generated examples, 2000 updates of 16 rows,
  `--kinds 6 --block-r6`, same seeds. Eval: FRESH-EN-R3, NEW-KINDS-R5, NEW-KINDS2-R6, GEN-HELDOUT-R4.
- **CO (cut-open):** reader and talker layers frozen; thinker layers trained (full weights, bf16, 8-bit AdamW,
  lr 1e-5 cosine, gradient checkpointing; LoRA only if memory forces it, and say so). Each round joins the reader's
  output to the thinker state with a learned adapter (input injection, as in the retrofit paper). Training samples
  loops from {1,2,3}; scored at 2 loops (main), also 1, 3 and 4. One pass: the talker sees only what came through the
  thinker. No prefix vectors, no second read of the question.
- **CO-0 lesion:** same checkpoints, thinker replaced by identity (0 loops).
- **FT control (same size, normal shape):** the same layers trained the same way, no loop and no adapter.
- Today (reference, not re-run): round 6 `six`: FRESH-EN-R3 92.2, NEW-KINDS-R5 81.1, NEW-KINDS2-R6 75.3
  (unseen pooled 78.2).

Marks, fixed now (screen means over 2 seeds; the confirm repeats them on 6):
- M1 practised kinds: CO FRESH-EN-R3 >= 89.0 (today - 3).
- M2 new kinds: CO unseen pooled (R5 + R6, 384) >= 75.0 (today - 3).
- M3 the thinker decides: CO-0 <= 10% on FRESH-EN-R3 and on unseen pooled.
- M4 cost: CO at 2 loops, time to first answer token at batch 1 <= 2.0x the bare LM on the same GPU (today 2.97x,
  R7). Suggested: 28 layer passes in one pass is about 1.75x bare.
- M5 loops help (confirm only): CO at 3 loops minus FT >= +2 points on unseen pooled, ahead on >= 5 of 6 seeds.
- **GO** = M1-M4 met on the screen -> 6-seed confirm. **Proved wrong** = CO below 86.0 on FRESH-EN-R3 or below 72.0
  unseen pooled on both seeds: a 2-layer talker cannot replace the re-reading LM. Next single change then: a 4-layer
  talker; if that also fails, way B.

Nothing here touches GOLD-PRIVATE, reserved or blind panels.
