# 358b plan (draft, not registered): the loop reasoner on Sudoku-Extreme, the published way (sleep research, 2026-09-25)

Test owner: Benchmarks thread (bm-394s, artifacts/claude-bm394-20260925/PLAN-sudoku.md: only its 1,000 practice
puzzles with rule-keeping shuffles, one try, frozen weights sent first, ≤7M weights for the TRM-Att comparison,
plain twin scored too). Label: "protocol-matched, in-domain Sudoku result". Runs only after 358a has a result.

## What the published recipe costs (checked in the TRM paper, arXiv 2510.04871, pages 3 and 11; shown)
- Ablation table: TRM-MLP 5M 87.4, "w/ self-attention" 7M 74.7, HRM 27M 55.0, no EMA 79.9, 1-step gradient 56.5,
  T=2,n=2 73.7.
- Setup: AdamW (0.9, 0.95), 2K warm-up, batch 768, hidden 512, up to 16 supervision steps per batch, stable-max
  loss, EMA 0.999, one 2-layer net, n=6 latent updates and T=3 cycles per step; Sudoku: 60K epochs, lr 1e-4,
  weight decay 1.0. "Experiments on Sudoku-Extreme were ran with 1 L40S ... for generally less than 36 hours."
- So a full-recipe run is about a day of one GPU: over the $4 per-job rental cap, but free on BensPC if it gets a
  day. A cheaper run is allowed but must be labelled with its fraction of the published compute.

## How 358a's loop differs from TRM-Att (each a candidate change, one at a time)
358a already matches the outline (2 attention layers, width 512, repeated rounds, puzzle re-added every round,
a stop head). Missing: box offsets (Sudoku's third rule; needed, it is part of reading the puzzle), TRM's two
states (a latent z updated n times per answer update y), deep supervision that carries the state across 16 steps,
EMA of weights, weight decay 1.0, stable-max loss.

## Proposed order
358b-1: 358a's loop + box offsets, TRM's optimiser settings (EMA, wd 1.0, lr 1e-4, batch 768, deep supervision
with carried state), trained on the 1,000 practice puzzles only, on BensPC for as long as the queue allows; plain
twin with the same recipe. Pass marks are bm-394s's S1/S2 (Benchmarks owns them). If it falls short at reduced
compute, the next single change is TRM's two-state recursion.
