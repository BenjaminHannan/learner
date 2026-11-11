# What is holding Premonition back (brainstorm, 2026-10-03)

Ben's ask (19:37 UTC): what is making the model perform worse than it could, and what limits does it have that other models don't? Design notes only. Nothing was trained or run.

Labels: **shown** = in the code or a measured result (cited). **Suggested** = reasoning. **Untested** = never tried on our model. Small card experiments and the village model are not used here. "Real model" = the 1.2B pipeline on BensPC (`pipeline/` on branch `claude/real-pipeline-code`). "Reimplementation" = the PR #29 cloud copy.

## Ranked by how much they matter for Ben's goals

### 1. The thinking core has barely been trained (biggest gap vs other models)
- **Shown:** the core's whole history is a synthetic numeric set and a few hundred updates. The real trainer is named "Bounded synthetic numeric capability: TRAIN256" (`pipeline/scripts/sol_cloud_capability256_v1.py:2`) and requires a warm start of 800 numeric updates (`:93`, `:672`). The English pilot then adds 96 frames, 48 of them questions (`TRAIN-FRAMES-v2.json`, 96 frames).
- **Compare:** LiquidAI trained the 1.2B LM we borrow on trillions of tokens (LFM2 report, arXiv 2511.23404; exact count not re-checked). Small reasoners that do well (e.g. HRM / TRM on ARC and Sudoku) still see thousands of puzzles times heavy augmentation. Ours has seen hundreds of items.
- **Shown consequence:** memorising, not generalising. English: 40-43/48 train fit, 2-7/48 fresh (LIVE.md, ~20:10Z). Calculator: all 113 wrong finals were training answers (PR #23 F1). English: 74% of wrong fresh answers are exact training answers (F-E1, PR #30).
- **Suggested:** "skills first" needs a skills curriculum at scale: millions of procedurally generated items across many skill types (reading, tracking who-has-what, counting, comparing, multi-step tool use, planning in a grid), never repeating. PR #29 already showed the cheap version works: varied wording took new-wording calls from 81.6% to 98.1%.

### 2. The training signal is thin
- **Shown:** the only loss on the core is the talker's cross-entropy on the answer, about 4.2 tokens per question (LIVE.md 17:50Z, item c). The balance term is 0.001 × a small number (`sol_spatial_attention_core.py:42`).
- **Compare:** LMs get a loss on every token of every document. Reasoning models (o-series, DeepSeek-R1) add reinforcement learning on checkable answers, which is where most of their reasoning gain came from.
- **Suggested:** two options. (a) Give the core its own dense self-supervised job on every input, e.g. predict masked words or the next step of a simulation from its state. (b) Reward-based training once the core can sometimes get answers right: we have checkable answers (calculator, puzzles), which is the setting where RL helps most. Untested here.

### 3. The two narrow doors (being tested now, don't duplicate)
- **Shown in code:** reader squeezes each token 2048 → 32 → 256 (`sol_translator_grounding.py:46-47`, `hidden=32`); the exit averages into 8 prefix vectors. Full write-up: `design/info-paths/information-paths.md` (PR #30). Five-arm test running on vast in the "More information into the model" thread.
- **Shown:** opening the exit for the calculator took unseen answers from 0-4% to 84-90% (PR #29).

### 4. Half the core does nothing
- **Shown:** 8 experts per MLP, top-2 routing, but only experts 0 and 1 are ever used, and they are identical clones, so the MoE acts as one plain MLP (LIVE.md 17:50Z and ~19:00Z). 64 of 114 tensors get no gradient; most are by design (halt, head, tool), experts 2-7 are not.
- Balance-loss run is on the PC now (`bal9216`).

### 5. Thinking depth is fixed, and the "stop" head is untrained
- **Shown:** the real pipeline trains and decodes a fixed 4 loops. The v6 code runs up to 48 rounds at inference with a stop check from an untrained head (PR #23 design doc, §"Stop", `sol_spatial_attention_core.py:107-131`). The calculator op is picked at loop 0 in 127/128 calls, so the core isn't thinking before it acts (PR #23).
- **Compare:** looped/recurrent-depth models that generalise to harder problems train with random depth and learn when to stop (e.g. Geiping et al. 2025, recurrent-depth LM; untested here).
- **Suggested:** random-depth training (PR #23 C4) is the one to run after data. "Think before calling" was not supported over 6 seeds (+1.9, CI -20 to +24, PR #29), so depth alone isn't the fix.

### 6. No learning from a few examples yet
- **Shown:** notebook learning is design only (PR #20); the notebook path is "mechanics-only, not qualified" (`sol_spatial_attention_core.py`, `begin_latent` docstring).
- **Compare:** in big LMs, few-shot learning appears from very diverse pretraining data. It isn't a separate module. **Suggested:** this ties back to item 1. A core trained on narrow data won't learn to learn.

### 7. Very short inputs
- **Shown:** English pilot input cap 64 tokens, answer cap 48 (`TRAIN-FRAMES-v2.json` caps); v6 reader caps question 48 + notebook 256 tokens.
- **Compare:** the borrowed LM handles 32k tokens. Minecraft guides and screen history need thousands.
- Fine for now; matters at the Minecraft stage.

### 8. No eyes, ears or hands yet
- Vision (PR #26) and audio (PR #25) are paused on Ben's word (15:07 UTC). No action output exists. Needed for the north star, not for the current proof of concept.

### 9. Slow, noisy measurement
- **Shown:** evals are 48 items; seed-to-seed SD on the reimplementation's new-wording call rate was 11.9 points (PR #29), so each claim needs ≥6 paired seeds. One PC GPU (RTX 5070 Ti, 16 GB) plus small vast boxes.
- **Suggested:** larger generated held-out sets (hundreds of items) would cut noise more cheaply than more seeds.

## Things that are *not* limits (or are deliberate)
- Attention inside the core is fine for 64 tokens (PR #30 §3).
- The frozen LM and thin talker are Ben's rule (09-29). Letting the LM read the passage would raise scores and break the design.
- Core size (~9M, width 256) is small, but nothing shows size is the binding limit yet: it memorises the training set easily. Data and signal come first (suggested).

## Questions for Ben
1. Does "beat bigger models at its size" count the 1.2B borrowed LM? If yes, the competition is 1-2B models trained on trillions of tokens, and item 1 dominates. If only the core counts, the fair comparison is small reasoners like HRM/TRM (27M / 7M) on puzzles.
2. OK to build a large generated skills curriculum (millions of never-repeating items, many skill types) as the core's pretraining? Default: yes, starting from the PR #29 generator.
3. OK to add a dense self-supervised loss for the core (item 2a)? Default: test it as one change after the door results.

## Ben's answer (19:41 UTC): "all"
Read as: the whole model counts toward its size, including the borrowed 1.2B LM, so the comparison is 1-2B models; and yes to both the generated skills curriculum and the dense self-supervised loss test. Item 1 (core pretraining data) is the top priority.
