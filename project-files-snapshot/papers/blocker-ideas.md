# Ideas for the learning blocker, from the papers (2026-10-05)

Written 8:20 PM ET Oct 4 (00:20 UTC Oct 5) by the Opus "ideas" thread, for the plateau thread (PR #34, branch `claude/project-thread-aya9pk`). No training was run here. Labels: **shown** = in a result file or the code; **suggested** = my reading, not tested; **untested** = an idea.

Inputs read: `papers/learning-blocker-papers.md`, `papers/arxiv-bangers-scan.md`, plateau diagnosis v1, fix screens v1 and v2 (v2 results on the branch by 00:07 UTC), the fix screen v3 spec (LM LoRA everywhere plus the shuffled-core lesion), `skills_pretrain_v1.py`, `sol_translator_english_v6.py`, the core loop code and the LFM config. I opened 16 papers myself (abstracts; full method sections for 2609.36585, 2609.01117 and 2510.00494). The paper table at the end corrects a few points in the Sonnet notes.

## Plain summary for Ben

The core talks to the frozen 1.2B through 8 "hint" vectors placed *in front of* the question. Theory (Petrov et al.) says hints in front can nudge the LM but can't change *where it looks* inside the question, so they can only bring out skills the LM already has. That fits what we see: tasks the LM can already do are near 100%, and chain-following tasks are stuck at about 15%. Screen v3 tests the bluntest fix, letting the LM itself change a little (a LoRA). My top two cheap ideas keep the LM frozen. (1) Put a copy of the hints *after* the question, where the LM reads them with the question in view and they can steer what it looks at. (2) Add a second loss where the LM sees *only* the hints, so the core is forced to carry the answer instead of letting the LM answer from the raw question. Each one has a pass mark and a result that would kill it.

## What the evidence says

**Shown:**
- Fit is about 43-54% on 2,000 practised rows across runs (mark 85). Reader width, 8 rounds, lr 3e-4, the pointer exit (screen v1) and exit hidden 32 to 256 (screen v2: +0.6 / +1.2 / +0.3, mean +0.7) all leave it there.
- Zeroing the 8 core vectors gives 0/1,360, even on copy_word and passage_qa, which are 98-100% intact (screen v2 Z). So the LM needs *something* in those slots. On its own this does not show that the slots carry anything specific to each question.
- With 8 rounds instead of 4, main2's answers at update 0 are identical on all 640 scored rows (screen v1).
- Order at the LM input is `[8 core vectors][prompt word embeddings][BOS][answer]` (`with_prompt` concatenates prefix then prompt; `human_loss` appends BOS and the target).
- LFM2.5-1.2B has 16 layers, but only 6 are attention (layers 2, 5, 8, 10, 12, 14). The other 10 are short convolutions with kernel 3 (config in `artifacts/sol-cloud-chat-delivery-20260930/cached-lm-header-v4/cloud-pinned/GITHUB-TRANSPORT.json`).
- Worst families are chain_ops 15, state_update 15, cipher_map 20, chain_story2 28 and var_chain 28. Best are copy_word, list_index, passage_qa and syllogism, all 98-100%.

**Suggested:**
- The 8 slots act as a learned "answer mode" instruction more than as a carrier of each question's content. That fits Z = 0%, rounds 8 = 4, and the helpers' finding that a swapped core state left new-kind answers unchanged. Screen v3's S lesion tests this directly.
- A prefix in front of the question cannot change how the frozen LM attends *within* the question. It only adds a fixed-direction push at each attention layer (Petrov, Torr, Bibi, arXiv 2310.19698). So it can draw out skills the LM has but cannot install new attention patterns. Following a chain of references needs exactly such patterns (2609.36585). With only 6 attention layers, the 1.2B's default chain reach is probably very short. The per-family split above is what this predicts.
- The loop is probably sitting at a fixed point by round 4. Weight-tied loops trained at one depth converge to fixed points, and standard measurements saturate there (2607.20594). So the loop isn't doing step-by-step work that reaches the answer.

## Free checks (no training, minutes on the PC)

- **C1. Does the core know the answer?** Run main2 over the 2,000 fixed worst-8 rows and the 320 held-out rows. Take the core state pooled into 8 slots the same way the exit pools it (8 x 256), at round 0 (reader output plus position codes, before any loop) and after rounds 1, 2, 3, 4 and 8. Fit a linear probe from that state to the first answer token, train on the 2,000 and score on the 320. Control: the same probe on the reader's input features (the LM's own contextual features, mean-pooled).
  - Marks: "loops compute answer information" if probe at round 4 beats round 0 by 10+ points; "loops add nothing" if under 3 points.
  - Marks: "core knows more than it says" if the round-4 probe beats main2's real held-out accuracy on the same rows by 10+ points. Then the exit or LM side is the limit (ideas 1 and 3). If it's at or below main2's accuracy, the core doesn't know the answer (idea 2).
  - A frontier signature (2607.20594) would be the probe rising round by round on chain families. A flat probe from round 2 on means a fixed point.
- **C2. Read v3's S correctly.** S swaps in the *previous* question's vectors. If `dev/in_dist.jsonl` is grouped by family (34 x 40 suggests it may be), S is a same-family swap for 39 of every 40 rows. That makes it a test of question-specific content, not of family mode. Report which it is. If it is grouped, a cross-family shuffle is a second one-line arm.
- **C3. Before keeping any LM LoRA, check English.** v3's A has no guard on the LM's general behaviour. 2609.36585 trains with a KL term on 8 WikiText passages per step and reports a perplexity change under 0.01. The LM is also the English talker, so score R4 English (92.6% today) or plain-text perplexity on any A checkpoint that passes.

## Ranked ideas

All use the same fit screen as v1-v3 unless noted: worst-8 families, 2,000 fixed rows x 3 passes, 6,000 updates, seeds 1-3, against F1-F3 at 6,000. The marks are v3's: **FIXES FIT** if mean fit gain is +15 or more with all 3 seeds positive; **HELPS** if +5 to +15 with all positive; **NO EFFECT** otherwise; **HURTS** at -5 or worse.

### 1. Add a copy of the exit that writes 8 vectors *after* the question (keep the LM frozen)
- **Change:** input becomes `[8 front vectors][prompt][8 back vectors][BOS][answer]`. The back vectors come from a second StatePrefix, initialised as a copy of the trained one, with fresh Adam state. The front set stays, because Z shows the LM depends on it. No LM weights change.
- **Papers:**
  - Latent Recurrent Thoughts (2609.01117) feeds a frozen Qwen3-8B `[instruction; question; latents]`, latents *after* the question, and beats earlier frozen-decoder latent methods with only answer loss.
  - Liu et al. (2412.17747) append the coprocessor's latents after the context in the frozen decoder's cache.
  - Petrov et al. (2310.19698) show a front prefix cannot change attention over the content.
- **Why it targets the blocker (suggested):** in a causal LM, slots in front can't see the question, so they can only push it in a fixed direction. Slots after the question are processed by all 6 frozen attention layers with the question in view, and the core's vector acts as the *query*. The core can then steer what the LM pulls out of the question at every attention layer, which is the missing ability for chain-following.
- **Kill test:** the fit screen. Prediction: the four chain families (chain_ops, var_chain, chain_story2, state_update) gain more than the other four. Wrong if NO EFFECT. Expect a lower start at update 0, because the back copy is new to the LM. If fit rises, run S on the trained model: a 20+ point drop says the core's content is now being used.
- **Cost:** about 20 lines in `with_prompt`, about 30 min per seed on the 5070 Ti.

### 2. Two-path loss: make the core carry the answer on its own
- **Change:** add a second loss on every update. The LM gets only `[8 core vectors][BOS][answer]`, with no prompt words, and the loss is that answer cross-entropy times 0.5. The normal loss is unchanged. One extra LM forward per update, about 1.6x time.
- **Papers:**
  - Wu et al. (2202.05306): two-input networks learn greedily from the easier input and under-fit the other. Here the easier input is the raw prompt the LM can read itself (suggested mapping).
  - 2510.00494: two-part latent designs mostly add compute unless the objective *explicitly shapes* the latents. A single model with the same soft-token budget nearly matched the best two-part design.
  - LRT (2609.01117) builds in a penalty to stop the latent drifting toward "a generic, instance-agnostic latent", which is the failure suspected here.
  - Kuratov et al. (2502.13063): one input vector can make a frozen LM reproduce 1,568 tokens when optimised per sample, while trained encoders reach only about 10x. Room in the slots isn't the problem; learning to fill them is (consistent with screen v2).
- **Why it targets the blocker (suggested):** today the core gets gradient only through an LM that can already answer the easy cases from the prompt, so the core settles on a generic mode signal. The second path has no shortcut.
- **Kill test:** the fit screen on the normal path is the registered measure. Also report prefix-only fit as a mechanism check.
  - If prefix-only fit rises but normal fit doesn't, the LM ignores the core when the prompt is present. Go to idea 1 or the LoRA.
  - If prefix-only fit stays under 25%, the core can't compute or hold the answers even with a direct route. Go to idea 4.
  - Wrong if NO EFFECT on normal fit.

### 3. If v3's LoRA helps: shrink it to the paper's one-layer residual edit, and check the core still matters
- **Change:** in place of rank-8 LoRA on every LM Linear (v3), use 2609.36585's exact form, `h <- s*h + B A h` on the residual stream at one layer's input. Rank 8, about 33k params, B = 0 at start. Sweep the input of layers 2, 5 and 8 (the first three attention layers) on 1 seed each, then run 3 seeds on the best. Add the paper's KL guard on plain text.
- **Paper:** 2609.36585.
  - Qwen3-8B goes from 15.5% to 99% on 24-line chains. Qwen3-1.7B unlocks 22+ lines, but Llama-3.2-1B only goes from 1.4 to 6, so small models gain less.
  - Placement is sharp: moving from layer 20 to 21 drops reach from 20.5 to 5.2 lines.
  - Recipe: batch 16, 1,200 steps, lr 1e-3, clip 1.0.
  - The mechanism is a "relay" through frozen parent-reading attention heads.
- **Why:** it tells whether v3's gain is the chain relay (chain families gain most, few parameters) or just more memorising capacity. It also keeps the LM change about 150x smaller than LoRA everywhere.
- **Kill test:** the fit screen. Also run S (shuffled core) on the best LoRA model. If shuffling no longer hurts, the LM is doing the work and the core is idle. Ben should hear that before it's kept, since the core is meant to be the thinker.

### 4. Make the loop actually iterate (only after C1 or idea 2 shows the core's state carries answer information)
- **Change:** train with a random round count per update (uniform 2-8) in place of a fixed 4. Optionally order rows operator-first: single-step rows of each chain family before multi-step rows.
- **Papers:**
  - 2607.20594: a weight-tied loop learns a frontier of about n_train / T_train positions per loop; extra test loops help only past that frontier; standard metrics saturate at fixed points; an operator-first curriculum removed the hard-operator wall in every seed.
  - 2603.21676: a depth-recurrent block stays stable for 20+ steps with final-output-only loss, LayerScale init and an identity-biased gate, and per-step supervision *hurt* extrapolation.
  - 2610.00673: converting a dense model to looped needs one input-mixing scalar plus a smoothed exit loss.
  - TRM (2510.04871): a 7M, 2-layer recursive net reaches 45% on ARC-AGI-1, with deep supervision (state carried and detached across up to 16 steps).
- **Why:** answers identical at 8 and 4 rounds suggest a fixed point, so the loop adds no serial steps. That matters only once the core's state is actually used, which is why this is fourth.
- **Kill test:** the fit screen, plus C1's per-round probe on the trained core. Wrong if chain-family fit doesn't rise when test rounds go from 4 to 8.

### 5. Batch 16 by gradient accumulation (lowest)
- **Change:** accumulate 16 rows per update. Keep lr 1e-3 and the same number of row visits (6,000 rows means 375 updates; also try 6,000 updates if time allows).
- **Backing (weak):** 2609.36585 trains with batch 16 at the same lr and clip. The plateau diagnosis saw held-out swings of up to 9 points between checkpoints of one run (batch-1 noise). No paper here addresses it head-on.
- **When:** only if v3's A and idea 2 both fail. That would put the ceiling in the training signal, and batch size is the one optimiser setting not yet varied.
- **Kill test:** the fit screen.

## Order after v3 lands

| v3 result | next |
|---|---|
| S says "core carries little", A FIXES or HELPS | C3 (English), then idea 3 (shrink, and S on the LoRA model), then idea 2 to bring the core back into the answer |
| S "core carries little", A NO EFFECT | C1, then idea 2, then idea 1, then idea 5 |
| S says "core carries question info", A NO EFFECT | idea 1 (the LM can't use what the core sends from the front), then a core-conditioned residual write at the best layer |
| S "core carries question info", A FIXES | C3, then idea 3 |

## What the papers say *not* to bother with

- **More latent slots or a wider exit.** Screen v2 already showed this. 2510.00494 found that scaling the latent budget past small values didn't help, and sometimes hurt from 8 to 16 slots on Countdown.
- **Writing into the KV cache at every layer while the LM stays frozen.** 2510.00494's H1 did exactly that and gained only +1.5 pp (GPT-2) and +4.4 pp (Qwen-3) over the input-only design, below unfreezing the base. Idea 1 is the cheaper form of "reach more of the LM".
- **Generic `--steps` with the current step text.** main4 tried it: 71 vs main2's 72, and many steps are bare labels like "compose". A fair serial-depth test would need worked steps with intermediate values (2609.33134: only content-bearing chains beat a shallow pass's ceiling; filler doesn't). That is a data job and conflicts with "talker decodes the final state", so it isn't ranked.
- **Per-round supervision of the loop's intermediate states,** if the goal includes running longer at test time (2603.21676). TRM's deep supervision is different: it supervises the *final output* at each outer step.

## Paper check (what I opened, and corrections to the Sonnet notes)

| paper | opened | what matters here |
|---|---|---|
| 2609.36585 Tiny LoRA | full method | The LoRA sits on the **residual stream at one layer's input** (`s*h + BAh`), not on attention projections; projection LoRA on all 7 projections of one layer also worked, at about 9x the parameters. Placement is set by a frozen-model patching measure and is sharp. Smaller models gain less (Llama-3.2-1B: 1.4 to 6 lines). KL on WikiText keeps perplexity within 0.01. Does not discuss soft prompts. |
| 2609.01117 LRT | full method | Latents go **after** the question as input soft tokens (32 in training, 4 at test). Answer loss only, two stages (a 4.2M task-dedicated proposer, then a 7M recurrent refiner, L2 penalty 0.01 on its correction), backprop through the last cycle only. Countdown-4: generic proposer 5.9%, task-dedicated 42.0%, plus recurrent refiner 56.7%; a 77M one-pass refiner 47.5%. |
| 2510.00494 System 1/2 | full method | H1 = KV-cache concatenation at every layer with the base frozen: modest gains. H2 = unfreeze the base: best. A single-model soft-embedding baseline nearly matches H2. GSM8K: soft-embed 26.5, H1 12.0, H2 31.5. More latents didn't help. |
| 2412.17747 cache augmentation | abstract | Frozen decoder; the coprocessor writes latents into the KV cache, trained with LM loss on pretraining data. |
| 2607.20594 convergence selection | abstract | Frontier v ~ n_train / T_train per loop; fixed points hide the algorithm from standard metrics; operator-first curriculum removes walls. |
| 2603.21676 depth-recurrent | abstract | Final-output-only loss, LayerScale and an identity-biased gate give stable 20+ step recurrence; per-step supervision hurts extrapolation. |
| 2610.00673 looped recipes | abstract | Input-mixing scalar plus smoothed exit loss to convert a dense model to looped; stronger exit-gate regularisation plus warmup for stability. No formulas on the abstract page. |
| 2607.20519 halting gates | abstract | Post-hoc readouts of trajectory states match or beat learned halting gates. |
| 2310.19698 Petrov et al. *(new)* | abstract | Prefix and prompt tuning cannot change relative attention over content, only bias attention outputs in a fixed direction; they elicit existing skills and can't learn new attention patterns. |
| 2104.08691 Lester et al. *(new)* | abstract | Prompt tuning matches full tuning only as models exceed billions of parameters. |
| 2110.07602 P-tuning v2 *(new)* | abstract | Input-only prompts are weak on normal-sized models; prompts at every layer fix it. |
| 2502.13063 Kuratov et al. *(new)* | abstract | Per-sample input vectors can carry 1,568 tokens; trained encoders reach about 10x, two orders of magnitude less. |
| 2202.05306 Wu et al. *(new)* | abstract | Multi-input nets lean on one input and under-fit the other. |
| 2510.04871 TRM *(new)* | method | 7M, 2 layers, 45% ARC-AGI-1; deep supervision up to 16 steps with detached carried state; full backprop through the last recursion. |
| 2603.22329 frozen-GPT-2 memory | abstract | At 1x capacity, prefix and KV-extension memories failed (under 0.4%) while cross-attention, Hebbian and slot-write worked; all worked at 10x. Weak support for "prefix is a weak interface". |
| 2411.16525, 2305.18787 prompt-tuning theory | abstract | Theory for 1-layer transformers: memorising a dataset needs exponentially long prompts, and prompt tuning is more constrained than LoRA. Weak relevance to a 16-layer LM. |
| 2609.33134 ceiling of a task | abstract | Serial tasks need content-bearing chains; filler or a restated question drops accuracy to a shallow pass's ceiling. |

Not opened, low value for this blocker: 2603.15051, 2602.00015, 2604.22565 (title only; it may be worth a look if idea 1 works, since it steers a frozen LM's attention to evidence), 2405.17052, 2509.22131, 2306.04933, and the looped-transformer snippets 2607.16051, 2605.20670, 2607.27656, 2604.17121.
