# dl-4: does a KL anchor to the base on general text stop the slow forgetting of copy-practice nights?
(Fix-sleep thread. Registered when this file is committed, before the run.)

## Why
- dl-2 (registered PASS) learned the day's work well: lucky guesses went from 64 to 237 and 249. But it lost 26 of the
  base's 200 right general-panel items by night 7.
- dl-3 (registered FAIL; artifacts/claude-dl3-20260926/VERIFY.md) copied the base's own GREEDY answers to base-written
  general questions into each night. It did not cut losses: 20 and 36 lost vs 39 and 24 without it.
- dl-3 also raised drift from the base on general replies (KL 0.28 vs 0.13-0.17), already at night 1.
- Suggested cause: copying one greedy answer sharpens the model instead of holding it in place.
- Research points to matching the base's whole output distribution instead (REPORT.md Q1-Q3: forgetting tracks KL to
  the base; Dark Experience Replay keeps old output distributions).

Code: scripts/claude_dl4_anchor.py (the docstring is the method). It reuses claude_dl1_nights and dl-3's pool builder
unchanged. The model is plain MiniCPM5-1B, thinking off, no download.

## ONE change from dl-2's S arm: a KL anchor
Each night also trains as many anchor items as puzzle examples.
- An anchor item is a question written by the base plus the base's own answer tokens. It uses dl-3's pool recipe with
  a new seed, 3691.
- Its loss is KL(base ‖ current) over the full vocabulary at every answer position, weight 1.0.
- "Base" is the same network with every LoRA scale at 0.
- Puzzle items keep dl-2's cross-entropy. All items share dl-2's loop: 3 epochs, lr 2e-4, batch 8.

Arms:
- S = dl-2's night, unchanged.
- K = S + anchor.

Setup:
- Seeds 6 and 7, 7 nights each.
- New TEST seed 3690: 100 fresh puzzles × 20 guesses.
- HARM: the same 300 items. "lost" = right at base and wrong now.

## Marks: dl-3's F1-F5, unchanged, with K in place of A
- **F1 forgetting cut:** K's night-7 lost ≤ 0.5 × S's (sums over seeds), and each K seed is below each S seed.
- **F2 low forgetting every night:** at most 1 of K's 14 nights has lost > 10.
- **F3 still learns:** K's night-7 lucky ≥ 2 × L0 on each seed, and K's gain over L0 ≥ 0.8 × S's gain.
- **F4:** at most 1 of K's 14 nights has TEST lucky more than 15% below the night before.
- **F5:** K's night-7 puzzles reached ≥ base, on each seed.

Verdict:
- PASS = F1-F5.
- INCONCLUSIVE if L0 < 10, if S's night-7 lost sum < 20, or if the pool has < 100 items.
- Proved wrong: K's night-7 lost ≥ S's on both seeds.

Reported, not marked:
- lost vs the night before;
- the base's per-item panel (saved, so lost items can be broken down by kind);
- KL per night;
- anchor KL in training;
- gained and greedy solves.

## Limits stated before the run
- One kind of work.
- The panel is short general answers with a 16-token reply cut. A more wordy model can lose items it still knows.
  Losses are counted as registered either way; the kind breakdown is reported.
- The anchor adds training steps.
- Two seeds; dl-3 showed large seed-to-seed spread (39 vs 24 lost with the same night rule).
