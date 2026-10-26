# Think-3 inner-state arms (proposed addenda for "Make the thinking block pay off")

Thread "Improve the thinking loop's inner state", 2026-10-25. Village model only, K2-Horizon-3.7B, Ben's PC only.
None of this edits the sealed `backbone/think3/PREREG.md`. Each arm below is meant to be copied into
`PREREG.md.addenda` by the owning thread before any Think-3 training, with its pass marks unchanged.
Labels: **shown** (a paper's table, or our own measurement), **suggested**, **untested**.
Sources: `research/A`-`H` in this folder (Haiku sweeps; F is a fact-check of the key numbers against the papers' tables).

## What the free CPU checks found (base K2-3.7B, no training, village validation shard 0)

### Check 1: how loud is the fed-back state, and does its form matter at the start? (`probe.py`, 12 rows, depth 2-4)
- Real token embeddings have RMS 0.030 (median over the vocabulary). The post-final-norm last state at the last prompt
  position has RMS 0.98, about **32x louder** than any real input token; the pre-norm last-layer residual is RMS 27
  (~900x). Layer RMS climbs from 2.3 after layer 0 to 18.7 at layer 34 and 27.4 at layer 35. **shown** (our measurement).
  So Coconut's remark that the post-norm state is "not too large" (2412.06769) does not hold for K2.
- Inserting K untrained laps inside the empty think block, then "</ifm|think>The answer is:", change in the gold
  answer's log-prob against thinking-off (mean over 12 rows; off = -3.76 nats, first-token hit 0.67):

| input for each lap | K=1 | K=3 | K=6 | first-token hit at K=6 |
|---|---|---|---|---|
| newline token (control) | -0.04 | -0.13 | -0.16 | 0.58 |
| post-norm state, raw (Coconut) | +0.00 | -0.16 | -0.23 | 0.58 |
| post-norm state, rescaled to embedding RMS | -0.14 | -0.22 | -0.26 | 0.67 |
| pre-norm last-layer residual, raw | -0.07 | -0.03 | -0.08 | 0.58 |
| layer-18 residual, rescaled | -0.07 | -0.16 | -0.19 | 0.67 |
| soft mix of all token embeddings (Soft Thinking) | -0.14 | -0.75 | **-5.63** | **0.08** |
| soft mix of top-8 token embeddings | -0.14 | -0.75 | -1.71 | 0.25 |

  Per-row spread is about 0.1-0.5 nats, so the five hidden-state forms are indistinguishable from each other and from
  the newline control; the soft mixtures clearly hurt. **shown** for untrained K2, 12 rows. The likely reason (**suggested**):
  K2 is pre-norm, so every layer re-normalises its input, and the latent position only reaches the answer through
  attention keys and values, which are computed from normalised inputs. Soft mixtures look like real thinking words,
  and closing the think block mid-thought confuses the model.
- Consequence: the scale of the lap input is not worth an arm. The soft-mixture input should not be used.

### Check 2: do the evidence lines help K2, and where does the teacher's state differ? (`probe2.py`, 24 rows)
Base K2, no training, the gold answer scored after "</ifm|think>The answer is:", with three think-block contents:

| think block | gold answer log-prob (mean) | rows better than off | first-token hit |
|---|---|---|---|
| empty (thinking off) | -3.53 | - | 0.67 |
| the row's evidence lines | **-2.36** (+1.18, 95% interval +0.56 to +1.87) | 16 / 24 | 0.58 |
| another row's evidence lines (control) | -4.07 (-0.54) | 2 / 24 | 0.50 |

- **shown** (24 rows, untrained): the right lines raise the gold answer's probability about 3x on average and the wrong
  lines lower it, so the lines carry real, row-specific signal that the student could learn to copy.
- Not yet shown: an exact-match gain. The untrained model's first-token guess did not improve (0.67 -> 0.58, 24 rows is
  too few to read). Gate 0-ev on the PC (1,000 rows, greedy exact match) is the real test.
- Where the teacher's state at "The answer is:" differs from thinking-off (relative L2 gap, mean over rows):
  layers 0-15: 6-13%; layers 18-35: 13-15%, last layer 22%. The part that is specific to THIS row's lines (right lines
  vs wrong lines) is almost absent in layers 0-15 (1-5%) and appears from about layer 18 (9-15%, last layer 23%).
  **shown**. So the copyable signal sits in the upper half. This matches "Hopping Too Late" (2406.12775), where the
  second hop resolves in middle-upper layers (**shown**, other models). It motivates arm `upper` below.

### Check 3: do a few giant dimensions swamp CODI's L1 match? (`probe2.py`, 20 rows)
After CODI's divide-by-teacher-std, the top 1% of dimensions (26 of 2,560) hold 4-5% of each layer's L1 gap
(1% would be perfectly even), at every layer. **shown**. So outlier dimensions do not dominate the gap at this
position, and CODI's plain per-layer normalisation is fine for K2. No special outlier handling is needed.



## Items from the brief that do not need an arm
- **Re-injecting the input each lap: not needed.** In CODI-style laps each lap is a new position in the sequence, and it
  attends to the whole question through the attention cache at every layer. That is the job input injection does for
  weight-looped models like Huginn (2502.05171), where the loop sees only its own state. **suggested** (follows from the design).
- **Noise in the state as a regulariser:** Huginn tried it and saw no gain (no numbers). Use noise only as a lesion (below). **shown** (no-gain statement).
- **A learned halting head:** a 2026 study of looped-LM exit gates (2607.20519) found post-hoc confidence rules match or
  beat learned gates. So test the free rule first (arm H). **shown** (abstract only).

## Arms, in the order to run them
Every arm is seed 0, LoRA r=16 on the same layers, the same N steps and batch order as `codi`. Each arm changes ONE thing
against the arm named in "vs". Scores on the 8,675 validation rows, greedy exact match, paired bootstrap 95% intervals.
One seed: a pass is a reason to run 2 more seeds, never a result. Think-1 showed seed spread of about 1 point on the
same task (a: 67.2 / 66.0 / 66.7), so no mark below is smaller than +2.0.

### Gate 0-ev (no training, ~1 h on the PC; run next to Gate 0)
Base K2 thinking-off, with the gold evidence lines written into the think block (teacher-forced, no generation),
against plain thinking-off, first 1,000 validation rows. The evidence lines are the story lines the generator records
for each question (`evidence_text_lines` in `raw/<split>/shard-*.jsonl`), in story order, one per line.
- Passes if S(ev given) - S(off) >= 8. If it fails, there is little to copy from the lines and the ev arms are dropped.
- This is an oracle input, so it is a ceiling on what the lines carry, not a model score.

### ev_write (control and ceiling for the ev arms)
LoRA trained to WRITE the evidence lines inside the think block, then the answer (plain written-reasoning SFT).
Needed because P1 needs a "thinking in words" ceiling that uses the same lines, and because this arm is itself a v2
candidate: about 3 lines (~40-60 tokens) is roughly 2 seconds at 30 tok/s on the Mac.
- Reported, no pass mark of its own. S_ev_write replaces S_on in P1 for the ev arms.

### codi_ev (vs codi). One change: the teacher's trace is the gold evidence lines, not K2's own thinking-on trace.
Why: CODI keeps most of the written gain on short traces and loses about 60-75% on long natural-language ones
(2607.16972: Qwen2.5-1.5B on MATH, written 52.8 vs CODI 12.4-14.5; KaVa 2510.02312: Qwen2.5-0.5B CODI 37.5 on
equation traces vs 20.2 on natural-language ones). **shown** (other labs, math). Evidence lines are short, exact, and
every row has one (no rejection sampling). Same 6 laps, same loss as codi.
- E1: (S_codi_ev - S_off) / (S_ev_write - S_off) >= 0.50.
- E2: S_codi_ev - S_codi >= +2.0, interval excluding 0.
- E3 (latents used): S_codi_ev - S_codi_ev(swap) >= +2.0.
- Wrong if: S_codi_ev <= S_codi, or the swap lesion costs < 1.0.

### step (vs codi_ev). One change: per-lap supervision (SIM-CoT, 2509.20317).
Lap i is matched to group i of the evidence lines, in story (file) order. The lines are stored in file order, not
chain order, and their count is not the depth (depth-1 rows have 1-8 lines; container lists give one line per item;
Step 0 data check, `backbone/think3/STEP0-data-check.md`). Fixed packing rule: if a row has n > 6 lines, split them in
order into 6 groups as evenly as possible (the first n mod 6 groups get one extra line); if n < 6, laps n+1..6 are matched to the answer text. A small decoder
(the same K2 with the LoRA turned off, teacher-forced) must rewrite line i from latent i alone; its cross-entropy is
added with weight 1. The decoder is used only in training. SIM-CoT on CODI: LLaMA-3.2-1B 52.7 -> 56.1, LLaMA-3.1-8B
61.1 -> 64.1 (**shown**, fact-checked); no ablation of the step loss itself was found.
- T1: S_step - S_codi_ev >= +2.0, interval excluding 0.
- T2 (each lap carries its own step): for rows with >= 3 evidence lines, swapping only lap 2's latent with another row's costs >= 2.0.
- Wrong if: S_step <= S_codi_ev, or T2's lesion costs < 0.5.

### randk (vs the best of codi_ev / step). One change: the number of laps K is drawn per row, uniform on 2..10, in training.
Why: fixed-K latent models do not get better past their training K, and McLeish et al. (2511.07384) call extrapolation
beyond the training depth unsolved; randomised loop counts reduce out-of-distribution variance (2606.29983, abstract).
**shown** / **suggested**. The village has depth up to 6 in validation but <= 3 in training, so more laps on deeper rows is the test.
- R1: S_randk(K=12) - S_randk(K=6) >= +1.0 on depth >= 4 rows.
- R2: S_randk(K=6) >= S_parent(K=6) - 0.5 (no cost at the trained setting).
- Wrong if: S_randk(12) <= S_randk(6) on depth >= 4 rows.

### upper (vs the best ev arm). One change: match only layers 18-35 instead of all 36.
Why: check 2 found the row-specific part of the teacher's state almost entirely in layers 18-35; matching layers 0-17,
each divided by its own small std, mostly asks the student to copy differences that do not depend on the story.
**suggested**. Low priority: run only if the slot is free.
- U1: S_upper - S_parent >= +2.0, interval excluding 0.
- Wrong if: S_upper <= S_parent - 1.0 (the lower layers were helping).

### H (eval only, no training). A free stop rule on the best checkpoint.
Stop after lap k when the answer distribution at "The answer is:" moves less than tau between laps
(KL(p_k || p_{k-1}) < tau), with K_max = 12. tau is chosen on the dev split, then frozen before validation.
Huginn uses the same rule at 5e-4 (2502.05171). **shown** (theirs, no accuracy curve).
- H1: accuracy within 0.5 of fixed K=6 at <= 60% of its mean laps, or >= +1.0 above fixed K=6 at equal mean laps.
- Wrong if: neither holds.

## Two implementation defaults (not arms; please build them in from the start)
1. **Lap input: CODI's projection (Linear-GELU-Linear-LayerNorm) plus a residual from the raw post-norm state, with the
   LayerNorm gain initialised to 0.03 (K2's embedding RMS) so a lap starts as loud as a normal token.** Check 1 says the
   untrained model does not care much, so this is cheap insurance, not a claim of gain. CODI's own ablation found the
   projection worth +1.2 (43.7 vs 42.5, GPT-2; fact-checked). Do not feed a soft mixture of token embeddings.
2. **Matching loss: keep CODI's form** (per-layer L1 or smooth L1, each layer divided by the teacher's batch std,
   teacher stop-grad). Check 3 found no outlier dimensions swamping it on K2, so there is nothing to fix here.



## Lesions and collapse checks for every lap arm (cheap, eval only)
- K=0 laps; swap (another row's latents); mean latents; Gaussian noise on the latents at 1x their RMS.
  2602.22441 found CODI on Llama GSM8K falls 55.57 -> 27.45 under large latent noise (**shown**, fact-checked), so
  noise is a sensitive "are the latents read" test.
- Collapse: mean cosine between the latents of different rows, and between successive laps of one row. SIM-CoT reports
  that failed runs have near-identical latents (**suggested**). Report both numbers; no pass mark.
- Logit lens: decode each latent with the output head; report how often lap i's top-20 tokens contain an entity
  (person, item, place) from evidence line i. Hopping Too Late (2406.12775) found the bridge entity resolved in early-middle
  layers (**shown**). Report only.

## What this does not cover
- The small card experiments are a different setup; nothing here is evidence about them.
- KaVa-style KV-cache matching (2510.02312) is the strongest long-trace fix found, but it only matters if we keep
  K2's long traces. With evidence-line traces it is not needed; revisit only if codi_ev fails while Gate 0-ev passes.
