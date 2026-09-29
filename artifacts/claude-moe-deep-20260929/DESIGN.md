# Deep sparse-MoE loop: design

Written 2026-09-29 01:06 UTC (date -u), before any run. Ben approved the architecture change at 00:35 UTC 09-29 ("do a sparse moe (however many active experts frontier models have) for our model, and add many layers... even if its hard to train"; handoff/director-roadmap.md). Code: `scripts/claude_moe_deep_net.py` (plug-in), `scripts/claude_moe_deep_run.py` (driver), `scripts/claude_moe_deep_report.py` (scores and words from raw JSON). Marks: `PASSMARKS.md` in this folder.

## In plain words (for Ben)

The current reasoner is a loop: it runs the same 2 layers over and over (up to 48 rounds) and a stop signal decides when it is done. The new reasoner keeps the loop, but each round now runs **8 different layers** instead of the same 2. Each of those layers has **64 small specialists ("experts")**, and a small chooser picks the **8 best specialists for each grid cell**, plus **1 specialist that always helps**. That is the most common recipe in today's big open models (DeepSeek-V3, Kimi K2, GLM-4.5). So the net stores much more (19.5 million weights, 11.9x the loop) but only uses a slice of it for each cell (4.7 million per cell per round, 2.9x the loop).

## Research that set the choices (labels: shown / suggested / untested)

- **How many experts are active** (Sonnet research agent, primary configs and reports). Shown: 8 routed + 1 shared is the single most common setup among 12 large 2025-2026 open MoE models (DeepSeek-V3/V3.2, Kimi K2/K2.5, GLM-4.5 to 5.1, Qwen3.5-122B/35B). Routed-only mode = 8, median 8. Others: Qwen3 and OLMoE 8 + 0, DeepSeek-V4 6 + 1, Qwen3-Next 10 + 1, gpt-oss 4, Mixtral 2, Llama 4 1 + 1. Total experts range 16 to 512. Routers: softmax with the top-k weights renormalised (Qwen3) or sigmoid with a bias-based balancer (DeepSeek, Kimi, GLM). Most models have 0 to 3 dense layers.
- **Training small MoE stably** (second Sonnet agent). Shown: a balance loss of 0.01 (Switch; OLMoE, where turning it off collapsed layer 0 onto 1-2 experts); a router z-loss of 0.001 (ST-MoE: 3 of 3 runs stable); an fp32 router; a small router init (Switch 0.1 scale ~ std 0.02; OLMoE std 0.02); dropless routing (MegaBlocks, OLMoE). Suggested: at 8-16 layers of width 256 the init scheme matters little (Huginn). **Shown, and against us:** the Tiny Recursive Model paper (small Sudoku/maze sets) reports that swapping its MLPs for MoE "decreased generalization massively" and that more layers overfit (one sentence, no numbers). ST-MoE: on very small tasks dense beat sparse. MoEUT (2024): MoE layers made a weight-shared (looped) transformer match a dense one, using groups of unshared layers that repeat.
- **What this repo already found** (third Sonnet agent, files checked). Shown: the "sparse loop" (Test D: the loop with top-2 of 8 experts, same size as the loop) scored F_eq 54.88 and 45.04 against the loop's 51.00 and 51.29, NOT PROMOTED; it stopped late (141-155 of 200 grid puzzles hit the cap) and its fresh copy was unstable. The 358e family (frozen or grown experts for learning kinds one after another) failed: new experts learned 0-15 of 200 mazes. That is a different design (experts frozen, routing by kind), not a jointly trained MoE. lf-8 (8 distinct dense layers per round) beat the 2-layer loop 560 vs 421 of 600 (both seeds) on an older test, but with 3.9x the weights; the same-size check (lf-sz) never ran. So "deep, or just big?" is still open, and this test reports both.

## The design (one architecture change)

Kept from the loop (`claude_fewex_net.py`): width 256, 8 heads, the same 2-D relative-position attention (half the heads narrow), pre-norm residual blocks, the puzzle re-added every round, the state norm, answer head, learned stop head, 48-round cap, the practice loss (random 1-16 rounds, up to 6 with gradient, stop-head loss) and the harness's maze learner and sleep. Inputs: tokens and fill slots only, never the kind.

Changed:
1. **Depth.** Each round runs **L = 8 distinct layers** (the loop runs its 2 shared blocks). Rounds are not changed.
2. **Sparse experts in every layer.** Router: bias-free linear map from the normed cell state, fp32 softmax over E = 64 experts, top 8 kept and their weights renormalised to sum to 1. Experts: GELU MLPs 256 -> 64 -> 256 (fine-grained, a quarter of the width, DeepSeekMoE style; the 8 routed ones together are 512 = 2 x width wide). Plus 1 shared expert of the same shape, always on. Dropless: every chosen pair is computed, so a cell's answer never depends on which other puzzles share its batch (checked in the selftest: difference 0.0).
3. **Two small extra losses** on every update (practice, maze learning and sleep): balance loss 0.01 x E x sum_e f_e P_e (1.0 when even) and z-loss 0.001 x mean(logsumexp(router logits)^2), averaged over every layer call with gradient.
4. **Deep-stack start.** Each residual branch's last projection starts scaled by sqrt(2 / L) (so one round's total update starts at the loop's size; at L = 2 this is the loop's own init). Router init std 0.02. Everything else uses the loop's default init.

| config | layers per round | experts (active) | stored weights | active per cell per round |
|---|---:|---|---:|---:|
| loop (baseline) | 2 shared | dense | 1,645,726 | 1,645,726 |
| **L8-E64 (main entry)** | 8 | 64 (8 + 1 shared) | 19,517,438 | 4,694,014 |
| L2-E64 / L4-E64 / L16-E64 | 2 / 4 / 16 | 64 (8 + 1) | 4,928,798 / 9,791,678 / 38,968,958 | 1,222,942 / 2,379,966 / 9,322,110 |
| L8-E16 / L8-E32 / L8-E128 | 8 | 16 / 32 / 128 (8 + 1) | 6,713,342 / 10,981,374 / 36,589,566 | 4,595,710 / 4,628,478 / 4,825,086 |
| L8-dense-act | 8 | dense FFN 576 wide (= 9 x 64) | 4,546,558 | 4,546,558 |
| L8-dense-tot | 8 | dense FFN 4,224 wide | 19,517,950 | 19,517,950 |
| plain-big | 8, one pass, no loop | dense FFN 4,224 wide | 19,517,181 | 19,517,181 |

(From `selftest.json`, printed by `claude_moe_deep_run.py selftest`.)

## Depth: more unshared layers, keep the rounds (why)

Depth could mean more loop rounds, more distinct layers per round, or both. **Decision: the new depth is 8 distinct layers inside each round, and the rounds stay as they are (learned stop, cap 48).** Total depth is layers x rounds, up to 8 x 48 = 384 layer passes.
- More rounds cannot be tested fairly on this ruler. The harness fixes the cap at 48 (`claude_fewex_bench.py` MAX_ROUNDS), and the practised loop already uses all 48 rounds on most maze rungs (cap hits 300 of 300 at k = 64 to 4,096 in seed 0, RESULTS-EQ.md). Making the stop fire is its own open problem with three threads on it (H12, stop without labels, charge for thinking). Changing it here would be a second change. (shown)
- More rounds reuse the same 2 layers, so they add no new weights for experts to specialise in. Experts only pay off when there are distinct layers to hold them. (suggested)
- Distinct layers per round helped before: lf-8 beat the 2-layer loop 560 vs 421 of 600 in both seeds (with 3.9x the weights, so size is not ruled out). MoEUT reports that MoE layers are what made looped transformers competitive. (shown for those tests; untested on this ruler)
- Keeping the loop keeps what won here: the practised loop beat the practised plain net by +17.21 and +17.71 F_eq (RESULTS-EQ.md). (shown)

## How it is judged

On the fair few-example ruler (F_eq, 9x9 mazes, k = 1 to 16,384 different mazes, 2,048 updates per rung), unchanged: same pool, batches, panels, maze learner (lr 1e-3, 4 updates per batch, 3 free + 2 gradient rounds), sleep recipe and scoring. Source practice is the qualified recipe (12,000 batches of 64 sums/grids, 1e-3 warm-up and cosine, fixed depth chosen on source dev, V1 on the untouched source guard). The main entry is also compared with dense 8-layer loops at equal **active** and equal **total** weights, and with a same-size plain net. Scaling rows vary depth (2, 4, 8, 16 layers) and experts (16, 32, 64, 128). Marks: `PASSMARKS.md`.

## Machine

Measured on this 4-core cloud container, torch 2.14.0 CPU, one thread (suggested; the box was shared with other processes): the main entry takes 5.2 s per practice step, 20.7 s per maze batch (4 updates) and 21.1 s to score 32 9x9 mazes over 48 rounds. The loop takes 0.82 s, 2.8 s and 3.3 s on the same box. One config would take about 17 h of practice plus about 26 h per ladder on one CPU thread, so the runs go to BensPC's RTX 5070 Ti ($0, no rental). The same-GPU loop control re-runs the recorded loop on that GPU. The strict-fp32 CPU-vs-GPU smoke (`SMOKE_MARKS` in the driver) is checked before any maze rung. No vast rental without Ben's yes.

## Risks, said before any run

1. Overfitting or too much capacity for small puzzle data (TRM's MoE result; ST-MoE). The fixed practice amount and the dense controls will show it.
2. Router collapse or dead experts: maze cells come in few token types, so round 1 of layer 1 routes lopsidedly by construction. Logged as dead experts and busiest/mean load per stage (`routes.json`).
3. Late or never-firing stop (the Test D sparse loop's failure). Reported as cap hits and stop failures.
4. Hard to train at all: the source guard (V1) may fail. One source-only retry at lr 5e-4 is fixed in advance. No maze is seen before it.
