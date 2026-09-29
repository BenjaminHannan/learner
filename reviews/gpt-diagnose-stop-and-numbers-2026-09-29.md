# Two diagnosis questions about a tiny looped reasoner (no code or file access needed)

Written 2026-09-29 by the research lead for Ben to paste into GPT (web). Stand-alone: everything needed is below.

You are an expert in recurrent / looped transformers, adaptive computation (ACT, PonderNet, equilibrium models) and neural combinatorial solvers. You have **no access** to my code, files or machine; everything you need is pasted here. Do not ask me to run anything before answering; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer. Mark every claim **shown by the data below**, **suggested**, or **untested**. Two seeds is a screen, not a reliability estimate.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

## 1. The model
- A looped transformer: 2 shared blocks, width 256, 8 heads, about 1.65M weights, run on grid puzzles. Each cell is a token; "fill" cells are the answer cells.
- Each round: `z = h + e`, where e is the embedded puzzle (re-injected every round) and h is the carried state. The 2 blocks run on z, then a LayerNorm gives the new h. The state starts at zero.
- Heads read h each round:
  - a per-cell answer head;
  - a **halt head**, a single linear layer on the mean of h over all cells, giving a stop probability.
- **Practice:** on two kinds only, sums (1-4 digits) and Latin-square grids (4x4, 5x5), freshly generated each batch. Each step draws `total` in 1..16 rounds and `k` in 1..min(total, 6). The first total-k rounds run without gradient; the last k rounds are trained. Loss = mean cell cross-entropy + 0.5 x BCE(halt, "every fill cell is exactly right this round"). AdamW, lr 1e-3, weight decay 0.1.
- **Test read:** run up to 48 rounds (3x the longest practice). From round 3, stop at the first round where stop-prob > 0.5 AND the whole answer was identical for the last 3 rounds. Otherwise stop at the 48-round cap.
- **New kind, 9x9 mazes (mark the path from start to goal):** never practised. The net adapts by full fine-tuning on k mazes for 2,048 updates, with the same round draws. **The adaptation loss has no halt term.**
- **"Sleep":** 512 updates, each mixing 8 mazes + 4 old sums + 4 old grids. Cross-entropy only, **no halt term**.

## 2. Question A: why does the stop never fire on new mazes?
Held-out 300 mazes, practised net, seed 0:

| stage | right (learned stop) | right (fixed 16-round read) | mean rounds | runs hit the 48 cap |
|---|---:|---:|---:|---:|
| k=64 | 137 | 136 | 48.0 | 300 |
| k=256 | 256 | 245 | 48.0 | 300 |
| k=1,024 | 271 | 265 | 48.0 | 300 |
| k=4,096 | 257 | 243 | 48.0 | 300 |
| k=16,384 | 274 | 270 | 31.9 | 163 |
| after sleep at k=64 | 156 | 153 | 48.0 | 300 |
| after sleep at k=16,384 | 289 | 285 | 10.0 | **8** |

Seed 1's cap hits swing from 23 to 300 across stages. On practised kinds the stop works.

Candidate explanations:
1. The halt head's input (mean state) is off its practised distribution on mazes, so its fixed linear readout never crosses 0.5.
2. Rounds 17-48 are never trained, so the state drifts or never converges and the answer flickers, which breaks the 3-agree rule.
3. The "exactly right now" target is almost always 1 by the end of practice, so the head learned a shortcut that does not transfer.
4. Something else.

Please:
- Rank these with reasons, using especially the row "after sleep at k=16,384" (the stop fires on 292 of 300 although sleep never trains the halt head).
- Name the single cheapest measurement on the saved nets, with no training, that best separates them. Give pass marks fixed in advance and the result that would prove your top explanation wrong.
- Say which ONE training change you would then make, and why it would still work in a 10-100x larger model.

## 3. Question B: why can the loop not even fit the numbers puzzle?
- **Puzzle:** the 24-game. 4 numbers from 1-13 are shown in shuffled order, with target 24. The net writes a 7-token postfix expression in 7 answer cells, all filled in parallel each round.
- **Label:** the first solution found by a depth-first brute-force search over pairings of the *sorted* hand. Most hands have several valid answers (median about 8-22).
- **Grading:** any valid expression counts.
- **Results:**
  - With 1,062 practice hands (each seen about 2,410 times), every net reaches 1.0 on practice and 0-4 of 300 on held-out hands. A fixed-guess floor gets 12.
  - With a bigger pool (36,782 hand-target pairs), a plain 8-layer non-looped transformer of the same size fits practice at 1.0. The loop reaches only 0.38 / 0.56 practice exactness. Held-out: loop 4-6 of 300; no net beat the floor of 12.

Please:
- Weigh these readings:
  - (i) The label is a deterministic but search-dependent choice, so it can be learned only by lookup, and the weight-shared loop is a poor lookup table.
  - (ii) Parallel filling of 7 cells cannot commit to one joint answer.
  - (iii) Too few distinct hands for search to emerge.
- Propose ONE change, with pass marks fixed in advance and the result that would prove it wrong. My current candidate is a loss against whichever valid answer is nearest the net's current prediction (min-loss one-of-many), compared with a random valid answer per draw. Tell me if that is the wrong first move.

## 4. Rules for your answer
- Label every claim shown / suggested / untested.
- One change at a time, pass marks fixed before any run, and the result that would prove it wrong.
- Do not mix in other projects or models.
- End with a short plain-language summary for a high-school senior.
