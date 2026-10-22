# Model-shape ideas from looped, recursive and latent-reasoning work (2024-2026)

Written 2026-10-03 by a research subagent. Design only: nothing was trained or run, and no repo file was edited.

Labels:
- **shown**: measured in the cited paper, by the authors only unless noted.
- **suggested**: reasoning.
- **untested**: never run on our setup.

"Fetch" means I read the page through a summarising tool, not the PDF. Re-check a number before any pass mark rests on it. The puzzle ruler (F_eq) and the English path are kept apart. The village model and the card experiments are not used.

## Plain summary for Ben
- **Three cheap changes:** 2026 papers point to (a) each round moves the thinking only part of the way, (b) carry a few parallel copies ("lanes") of the thinking state instead of one, and (c) put one unshared block in front of the loop.
- **Skills, not facts:** looping helps a lot on "use what you know" and not at all on "know more facts". That supports skills first, facts in the notebook.
- **Not worth it at our size now:**
  - HRM's two-level loops.
  - MoR's depth per word.
  - Coconut's latent chain-of-thought.
  - EBT's energy settling, which is already on the forbidden list.

## Idea 1: Damped round update
1. **What it is:** each round moves the state only part of the way: `h ← h + α⊙(f(h) − h)`, with 0 < α < 1.
2. **Sources:**
   - "Right Direction, Wrong Step", arXiv 2609.16665 (abstract only).
   - Parcae, arXiv 2604.12946 (HTML, fetch).
   - Residual scaling, arXiv 2606.18524 (abstract only).
3. **Evidence:**
   - **Shown:** a fixed quarter step at inference turns harmful extra rounds into gains on 72.2-83.2% of selected failures, across 4 settings.
   - **Shown:** Parcae keeps the carried state contractive (spectral radius < 1). It trains at learning rates up to 1e-3, where the earlier looped design failed at 4e-4 or higher. It gets up to 6.2% lower perplexity than earlier looped models at 100M.
   - **Suggested:** our per-round LayerNorm already stops the state blowing up, so only the "settle down" effect could transfer.
4. **Our core:**
   - Today `step()` returns `LN(blocks(h+e))` (`claude_fewex_net.py:77-81`, shown).
   - The change returns `h + α⊙(that − h)` instead.
   - Fixed α = 0.25 costs 0 weights. A learned per-channel α costs 256.
5. **Cheapest test (no training, CPU):**
   - **Setup:** saved practised-loop checkpoints. Run rounds 1-16 as now, then rounds 17-48 with α = 0.25. Held-out mazes, both seeds.
   - **Pass (all three):**
     - un-solving (right at round 16, wrong at round 48) at least halves;
     - F_eq at round 48 ≥ F_eq at round 16;
     - the stop fires before the cap on ≥ 90 of 300 mazes at k = 256 (today: 0 of 300).
   - **Wrong:** cap hits ≥ 290/300 and un-solving within ±20% of today, on both seeds.
   - **Skip it if** sweep test 2 finds CONVERGES with un-solving under 2%.
   - **After a pass:** train α as a practice-side change (3 seeds, +8 F_eq bar).
6. **Risk:**
   - This is the plainest form of E2-R1-A Surprise-Gated Carry (kept, never run) and is close to the TRN Relay Gate. It should serve as their control.
   - It is not energy settling: there is no energy and no inner optimisation.

## Idea 2: State lanes (loop-level hyper-connections)
1. **What it is:** carry n = 4 copies of each position's state. Each round:
   - reads a learned mix of the lanes;
   - runs the shared blocks once;
   - writes back to each lane with its own gain and keep-rate.
2. **Source:** Hyperloop Transformers, arXiv 2604.21254 (HTML, fetch).
3. **Evidence:**
   - **Shown (LM perplexity):** at all three sizes, Hyperloop beat a plain Transformer with about 2× its weights at equal depth.

     | Hyperloop size | Hyperloop | Plain size | Plain |
     |---|---|---|---|
     | 136M | 14.40 | 238M | 14.65 |
     | 580M | 9.65 | 990M | 10.19 |
     | 991M | 8.49 | 2.0B | 8.60 |

   - **Shown:** looped models without lanes (14.85, 10.02, 8.68) beat the plain model only at the middle size.
   - **Shown:** the lanes cost 150-300k weights. Mixing once per loop beat mixing every layer (14.40 vs 14.45).
   - **Untested** on reasoning.
4. **Our core:**
   - The state grows from [B,N,256] to [B,N,4,256].
   - The mix weights are sigmoids of small linear maps, about 12k weights (0.14%).
   - Attention and MoE cost stay the same.
   - It grows state, not weights, which the plan already prefers.
5. **Test (puzzle ruler, practice-side, 3 seeds):**
   - **Pass:** F_eq ≥ +8 over baseline (each seed ≥ +4), and F_eq at round 48 ≥ F_eq at round 16.
   - **Wrong:** mean gain < +4.
   - **Later:** the §7 ladder is the real check, because the paper's claim is our pass mark 1.
6. **Risk:**
   - Lanes with different keep-rates resemble E2-R2-C Dual-Timescale Integrator (marked FIX), so it needs the same reset proof: lanes start at zero for every puzzle.
   - Nothing carries between puzzles.

## Idea 3: Unshared entry block before the loop
1. **What it is:** one ordinary block runs once on the inputs, then the 2 shared blocks loop.
2. **Sources:**
   - Mixture-of-Recursions (MoR), arXiv 2507.10524 (HTML, fetch).
   - Huginn, arXiv 2502.05171 (HTML, fetch).
   - Parcae and Hyperloop (above).
3. **Evidence:**
   - **Shown:** in MoR, "Middle-Cycle" sharing (first and last layers unshared) had the lowest validation loss of the 4 sharing schemes.
   - **Shown:** MoR lost to the plain model at 135M, which the authors put down to a "recursive capacity bottleneck".
   - Huginn, Parcae and Hyperloop all keep unshared ends.
   - **Untested** for us.
4. **Our core:**
   - The reader is per-token with no context (plan §2, shown), so `e` sees no neighbours before round 1.
   - A dense block adds ~0.79M weights (+9% stored, +29% active).
   - It sits inside the reasoner, so the talker stays thin.
5. **Test (puzzle ruler, practice-side, 3 seeds):**
   - **Arms:** baseline; + entry block; + the same block as a third shared loop block (equal stored weights).
   - **Pass:** the entry arm is ≥ +8 over baseline and ≥ +4 over the third-block arm.
   - **Wrong:** the entry arm is within +2 of the third-block arm. That would mean the gain is just extra weights.
6. **Risk:** it adds weights, and §7 counts them.

## Idea 4: Grade every round equally and train the stop on its own (English path)
1. **What it is:**
   - Replace the PonderNet expected loss (each round's loss weighted by the stop distribution) with fixed equal weights per round.
   - Train the halt head with its own loss on a detached state.
2. **Sources:**
   - "Adaptive Depth in Looped Transformers", arXiv 2607.20519 (abstract only).
   - "Learned Stochastic Stopping", arXiv 2606.29983 (abstract only; the collapse claim is from a search snippet).
   - Ouro, arXiv 2510.25741 (HTML, fetch).
3. **Evidence:**
   - **Suggested:** using one exit distribution both to stop and to weight training is one cause of poor adaptive depth. Fixed-weight depth supervision gave usable stop signals on Ouro-1.4B/2.6B.
   - **Search snippet only:** the PonderNet objective often collapses to an almost fixed stop round.
   - **Shown:** Ouro trains its gate in a separate stage with the target "next round lowers the loss by more than 0.005".
   - **Shown:** Ouro peaks at its trained depth (MMLU 67.45 at 4 rounds, 64.49 at 8).
4. **Our core:**
   - Today v6 weights each round's loss by survival × q, plus 0.001 × r (`sol_translator_grounding_v6.py:185-188`, shown).
   - The change is a mean over rounds, plus a BCE on the detached halt with the Ouro-style target.
   - It costs 0 weights.
5. **Test (one row after C4, on the C1 round-trip items):**
   - **Pass:** exact match at 16 rounds minus exact match at 4 rounds ≥ +5 points on both seeds, and final-round exact match no more than 2 points below the PonderNet arm.
   - **Wrong:** that 16-minus-4 gap is within 2 points of the PonderNet arm's on both seeds.
6. **Risk:** none with the rules. It must come after C4 so it stays a single change.

## Idea 5: Short local mixing inside the experts
1. **What:** a tiny depthwise convolution over neighbouring positions inside each expert (URM's "ConvSwiGLU").
2. **Source:** Universal Reasoning Model, arXiv 2512.14693 (HTML, fetch).
3. **Evidence (shown, ARC-AGI-1 pass@1):** 53.8 with the convolution, 45.3 without. Their looped model at 4× the weights scored 40.0; plain models reached at most 8.5 even at 32×. Untested for us.
4. **Our core:** after the GELU, kernel 2 on sequences, 3×3 on grids, placed by the §6 coordinates; positions without coordinates skip it. About 150k weights (1.6%).
5. **Test (puzzle ruler, practice-side, 3 seeds; convolution added to loop and plain):** pass if the loop gains ≥ +8 F_eq and ≥ 4 more than plain. Wrong if the loop gains < +4, or plain gains as much.
6. **Risk:** half our heads already see ±1 neighbours, so the gain may be smaller (suggested). It may read only coordinates, never a modality id.

## Folded into existing plan items (not new)
- **F4 multi-start:**
  - Probabilistic TRM (arXiv 2605.19943, abstract only) adds noise every round and picks the answer with the halt head. **Shown:** Sudoku-Extreme 87.4% → 98.75%, no retraining.
  - Report a "pick by halt head" column next to the plurality vote.
- **Sweep test 2:** add a label-free stop: "KL between successive rounds < τ".
  - Huginn uses 5e-4.
  - Looped Actor (arXiv 2609.37432, HTML) uses 1e-3. **Shown:** it matched a fixed 16 loops while over 95% of runs stopped earlier.
- **C2a registers:** in TRM, the answer state updates from (answer, scratch) only, never from the question, once per 6 scratch updates.
  - **Shown:** two states beat one or seven (87.4 / 71.9 / 77.6).
  - The question-blind update itself was not ablated.
  - Once the registers exist, adding it is a zero-weight mask.

## Checked and not proposed
| Shape | Why not now |
|---|---|
| HRM fast/slow | ARC Prize rerun (arcprize.org/blog/hrm-analysis): the hierarchy is worth about 5 points over a same-size transformer, and changing the cycle counts made it worse. Refinement during training was worth +13 points, and our random-depth training already covers that. |
| MoR per-token depth | Lost to the plain model at 135M, and its gains are speed. Revisit for the many vision tokens Minecraft will bring. |
| Coconut (arXiv 2412.06769, abstract) | Needs chain-of-thought text to start from. Our loop is already latent. |
| EBT (arXiv 2507.02092, HTML) | Forbidden (energy settling). For the record: +29% on out-of-distribution text only, at ≤800M, with unstable hyperparameters by the authors' own account. |
| MixerLoop (arXiv 2608.18230, abstract) | Won at 15M but kept only 41.5% of the gain at 110M. A small-size win that fades. |

## What this means for §7
- **Where loops win:** using knowledge, not storing it.
  - Ouro stores ~2 bits per weight whether looped or not.
  - Ouro-1.4B beat Qwen3-4B on MATH500 (82.4 vs 59.6) but lost on MMLU (67.35 vs 73.19).
  - Looped Actor at 0.5M weights got about 2× the Boxoban success of an 8M non-looped net.
- **Plain LM loss rarely beats 2× plain:** looping without lanes did it at only 1 of 3 sizes.
- **So:** §7's held-out set should be skill-heavy, with facts supplied in the notebook (suggested).

## Top 2
1. **Damped round update.**
   - It can be tested free on saved nets.
   - It targets the known failure where the stop never fires and answers wander past round 16.
   - It costs 0 to 256 weights.
   - Three separate 2026 groups point the same way.
2. **State lanes.**
   - It is the only idea with a published "beats a plain model 2× its size at three sizes" result.
   - It adds about 0.1% more weights.
   - It grows state, not weights, which is what the plan says to grow first.
