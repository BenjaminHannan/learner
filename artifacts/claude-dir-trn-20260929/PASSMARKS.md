# Translator check: pass marks (sealed before any run of scripts/claude_dir_trn_decode.py on real checkpoints)

Written 2026-09-29 (helper "trn", thread "Translator check"). Brief: handoff/director-briefs/translator-check.md. Ben's design: words -> state, the reasoner does everything, state -> words; credit must go to the loop, not the talker.

## Question
Given the FROZEN practised loop's round-48 state on a puzzle it solved, can a small decoder that sees only that state (plus fixed cell positions and the fill-slot flags, never the puzzle tokens) write the right answer tokens?

## Setup (fixed here)
- Tasks: `sums4` (4-digit sums, nets `runs/{loop,plain}-sS/source.pt`) and `mazes9` (9x9 mazes, nets `eq-runs/{loop,plain}-sS-pre/k16384.pt`, the practised-then-maze-adapted nets). Source seeds S = 0 and 1. Reasoner nets are never trained or touched (eval mode, no grad).
- Dev panels only. Sums: 300 fresh code-made items (seed 9302901). Mazes: the 300-maze dev 9x9 panel of claude_fewex_data. The holdout and every blind panel are never opened. Decoder training pool: 8192 fresh sums / 4096 fresh mazes (seed 9302900 family), asserted disjoint from dev by sum operands / layout hash.
- Decoder: 2 layers, width 64, 4 heads (self-attention among answer cells, cross-attention to the state), non-autoregressive, one query per cell (learned position + slot flag), output over the token vocabulary. Trained 3000 steps, batch 64, AdamW lr 2e-3, cosine, on cross-entropy at fill-slot cells. **Size cap: at most 10% of the loop's 1,645,726 weights = 164,572 decoder weights** (asserted in code; the actual count is printed and reported). Nothing else is tuned.
- Score: exact answer, every fill-slot cell right (sums have a unique answer; a maze has a unique path). Counts "x of 300".
- Sources of state fed to the same decoder recipe (memory), per source seed and per decoder seed (two decoder seeds: 0 and 1):
  - **L**: loop, round-48 state (the test).
  - **A**: talker-alone control, no state: the loop's own input embedding of the puzzle (token + slot embedding, i.e. the words turned into vectors, no reasoning).
  - **B**: talker-alone control, state of an UNTRAINED loop (random init, 48 rounds).
  - **C**: talker-alone control, state of the trained loop with every weight tensor randomly permuted (shuffled weights, 48 rounds).
  - **P**: plain net row: the same-size plain transformer's final-layer state (before its output norm).
- Reference: **H** = the loop's own output head at round 48 (the reasoner's answer; the ceiling).
- All decoders also get a fixed learned position added to the state, so A/B/C are not handicapped on position.

## Gates
- **G0 reasoner solved it.** H >= 250 of 300 on dev for each task and seed (loop). If not, that task/seed is INVALID (not a decoder failure).
- **G1 controls fail.** max(A, B, C) <= 150 of 300 in every run. If a control exceeds this, the decoder can solve the puzzle by itself: the translator claim is NOT SHOWN for that task (the ratio and the control prove the size cap did not bind).
- **G2 real run.** In every one of the 4 runs of a task (2 source seeds x 2 decoder seeds): L >= 0.9 x H (rounded up) AND L - max(A, B, C) >= 90 of 300 (30 points).
- **G3 noise.** The two decoder seeds' L counts on the same source seed differ by <= 15 of 300 (5 points); more than that makes the pair INCONCLUSIVE. Binomial SE at n=300 is at most 2.9 points, so 5 points is about 1.7 SE, and 30 points is over 10 SE; the margin is far above noise.
- **G4 no memorising.** Train-pool exact (first 300 pool items) minus dev exact <= 20 points for L in every run; otherwise flagged.

## Verdicts per task
- **TRANSLATOR SHOWN** (label "shown"): G0, G1, G2, G3 and G4 all hold for both source seeds.
- **REJECTED**: G0 holds and L fails G2's first clause (L < 0.9 x H) in all 4 runs ("every seed" reading).
- **NOT SHOWN**: anything else (some runs fail, a control passes, or noise too large). Also reported plainly, never rounded to a win.
- **Loop-vs-plain claim** (separate, label "suggested" at best): "the loop's state carries the answer more readily than the plain net's" is SHOWN only if L - P >= max(15, 2 x SE) of 300 in all 4 runs of the task; otherwise "not shown". If P >= L - 15 in every run, report "plain state decodes just as well".

## Result that would prove the design wrong
G1 fails (a control decodes >= 50%): the decoder, not the loop, is doing the work. Or REJECTED: the loop's final state does not hold the answer in a form a small decoder can read.

## Self-check (Ben 21:37 09-28, H8 checklist)
1. Every bar above noise: bars are 15 and 90 of 300; noise = binomial SE <= 2.9 points plus the two-decoder-seed spread (G3, limit 5 points). Yes.
2. "Every seed" reading: REJECTED needs all 4 runs to fail; a partial failure is NOT SHOWN. Yes.
3. Fair comparator: L is compared with the loop's own head H (the ceiling), and with A, B, C and the plain P. There is no episode/baseline loop pair here, no adaptation is involved. Yes.
4. Plain-net row: P is required and reported; controls A, B, C prove the decoder alone cannot pass; G4 checks memorising. Yes.
5. F_few (k=1..64): NOT APPLICABLE, nothing is adapted and no few-example score is taken (stated, not silently dropped).
6. Sleep gates: NOT APPLICABLE, no sleep.
Untested and out of scope: the sums/grids-and-mazes joint model, text words (this decodes to puzzle tokens, not English), the talker reading raw natural-language questions.
