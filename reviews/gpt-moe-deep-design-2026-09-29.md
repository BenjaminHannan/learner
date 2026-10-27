# Review a planned test: a deep sparse mixture-of-experts version of a small looped reasoner (no code or file access needed)

You are an expert in mixture-of-experts (MoE) models, looped/weight-shared transformers and small-data generalisation. You have **no access** to my code, files or machine, so everything you need is below. Do not ask me to run anything first; reason from what is here. If a fact you need is missing, say what it is and how it would change your answer. Label every claim **shown by the data below**, **suggested**, or **untested**. Two seeds is a screen, not a reliability estimate.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

The pass marks below are already sealed (written before any run) and will not change. I want your view on the design and on how to read the results. Do not suggest moving the goalposts. If you think a mark is wrong, say what a follow-up test (one change, its own marks) would look like.

## 1. The small puzzle ruler (this is separate from any language model)

- Puzzles are code-made grids of tokens. The model sees only tokens and which cells to fill, never the puzzle kind.
- **Practice ("source") kinds:** 1-4 digit sums laid out as grids, and 4x4/5x5 Latin squares. 12,000 batches of 64, AdamW 1e-3, warm-up then cosine.
- **New kind:** 9x9 perfect mazes (walls, start, goal). The answer marks the unique path.
- **The ruler (F_eq):** start from the practised net. For each k in {1, 4, 16, 64, 256, 1,024, 4,096, 16,384}, take a clean copy and train it on k different mazes for exactly 2,048 optimizer updates (512 batches of 32, 4 updates per batch). Every rung gets the same practice; only the number of different mazes changes. Score exact solutions on 300 held-out 9x9 mazes whose layouts never appear in training. F_eq = mean accuracy over the 8 rungs, in percent. F_few = the same mean over k = 1 to 64.
- Maze learning recipe for looped nets: each update runs 3 rounds without gradient and 2 with, carrying the state between updates. There is no stop-head loss during maze learning. Learning rate 1e-3.

## 2. Results so far (holdout, x of 300 at each rung)

| net | seed | 1 | 4 | 16 | 64 | 256 | 1,024 | 4,096 | 16,384 | F_eq | F_few |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| practised loop | 0 | 1 | 0 | 28 | 137 | 256 | 271 | 257 | 274 | 51.00 | 13.83 |
| practised loop | 1 | 1 | 0 | 3 | 190 | 262 | 236 | 284 | 255 | 51.29 | 16.17 |
| practised plain | 0 | 2 | 8 | 1 | 29 | 124 | 217 | 227 | 203 | 33.79 | 3.33 |
| practised plain | 1 | 0 | 0 | 0 | 12 | 134 | 213 | 223 | 224 | 33.58 | 1.00 |
| fresh loop | 0 | 0 | 13 | 34 | 49 | 144 | 67 | 85 | 104 | 20.67 | 8.00 |
| fresh loop | 1 | 0 | 1 | 36 | 166 | 167 | 0 | 128 | 18 | 21.50 | 16.92 |

- **The loop:** width 256, 8 heads, 2 shared transformer blocks (pre-norm; attention with a learned 2-D relative-position bias, half the heads limited to a narrow window; a 1,024-wide GELU MLP). The puzzle embedding is added back every round, then the state is layer-normed. A learned stop head (the stop fires when its probability exceeds 0.5 and the answer has been unchanged for 3 rounds), with a cap of 48 rounds. 1,645,726 weights.
- **The plain net:** 8 distinct width-128 blocks, one pass, 1,619,965 weights.
- The practised loop hits the 48-round cap on all 300 mazes at most rungs, so the stop rarely fires on mazes.
- **Noise:** F_eq run-to-run SD is 3.33 to 3.96 points; F_few SD 4.17 to 5.23.
- **An earlier sparse try** ("sparse loop"): the same loop with each MLP replaced by 8 experts, top-2 routed, the same total weights. F_eq 54.88 and 45.04 (+3.88 and -6.25 against the loop). It stopped late on grid puzzles (141-155 of 200 hit the cap, against 0-8 for the loop), and its fresh copy was unstable.
- **An earlier depth try** on a different, older test: 8 distinct dense layers per round against 2 won 560 vs 421 of 600 (both seeds), but with 3.9x the weights. A same-size check never ran.

## 3. The planned design (approved by me; sealed)

- **Main entry:** keep the loop, but each round runs **8 distinct layers** instead of the 2 shared blocks. Rounds, stop and the 48 cap are unchanged. Each layer keeps the loop's attention. The MLP becomes **64 routed experts** (GELU, 256 -> 64 -> 256), **top 8 per cell per round, plus 1 always-on shared expert** of the same shape. Router: bias-free linear map from the normed cell state, fp32 softmax, top-8 weights renormalised to sum to 1, init std 0.02. Dropless.
- **Extra losses** on every update: Switch-style balance loss 0.01 x E x sum f_e P_e, and z-loss 0.001. The residual branches' last projections start scaled by sqrt(2/L). Same optimizer and schedule as the loop.
- **Size:** 19.5M stored weights (11.9x the loop), 4.7M active per cell per round (2.9x).
- **Why depth as layers, not rounds:** the ruler caps rounds at 48 and the loop already uses all 48; the stop is being fixed elsewhere; more rounds reuse the same weights, so experts have nothing new to specialise in.
- **Known risk:** the Tiny Recursive Model paper (small Sudoku/maze sets) says swapping its MLPs for MoE hurt generalisation "massively", and more layers overfit.

## 4. Sealed marks (summary)

- **PASS:** F_eq of the main entry at least 51.29 + 10 in **both** seeds (the higher practised loop plus 10), on the holdout. **PROVED WRONG:** at or below 51.29 in both seeds. Otherwise NOT SHOWN.
- F_few is a required row. HELPS means at least +10.5 over 16.17 in both seeds.
- **Report-only rows (dev):**
  - scaling curves: depth 2/4/8/16 layers at 64 experts; experts 16/32/64/128 at 8 layers. Word SCALES UP if the largest beats the smallest by at least 8 with a positive slope in both seeds.
  - dense 8-layer loops at equal active and equal total weights.
  - a same-size plain (one-pass) net.
  - the MoE's fresh copy.

## 5. Questions

1. Is "8 distinct layers per round, rounds unchanged" the right place to add depth for this kind of task? Or would a grouped design (MoEUT-style: 2 unshared layers repeated) or more rounds be the better single change? Why?
2. Given the TRM result and the small data, what outcome do you expect on F_eq and F_few, and on the scaling curves? Give rough odds for PASS / NOT SHOWN / PROVED WRONG.
3. Maze cells come in only a few token types. In round 1, layer 1 routes almost purely by token type, so load is lopsided by construction. Is that harmful? Would a dense first layer (as in DeepSeek-V3 or GLM) matter here? What diagnostic in the routing logs (dead experts, busiest/mean load, how often a cell's top expert changes between rounds) would tell us routing is the problem?
4. If the result is NOT SHOWN, which **one** change would you test next, with what pass mark fixed in advance, and what result would prove that change wrong?
5. If it PASSES, what confound could still explain it (for example size, not experts), and which of the report-only rows settles it?

Please give: claims labelled shown / suggested / untested; one change at a time; pass marks fixed in advance with the result that would prove each wrong; and a plain-language summary for a high-school senior at the end.
