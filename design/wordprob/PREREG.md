# Word problems: answer-only vs worked steps (pre-registration, written 2026-10-23 ~20:00Z BEFORE any run)

Research report item R5: https://claude.ai/artifact/JnL9CRkskZksidFTK7EiQZ . This is a separate small experiment, not the
village model and not capability256's LFM adapter.

## Data
/mnt/project-files/data/wordprob-v1/ (templates written by Claude, every answer computed by code; splits by TEMPLATE:
train / dev / heldout_template / heldout_structure). Hashes recorded in its MANIFEST.json before training.

## Model and the one change
Same small decoder-only transformer trained from scratch (~10M params, character-level), same data, steps, seed, optimizer
(AdamW lr 1e-3 warmup+cosine, wd 0.1). ANSWER arm: target = "Answer: 74". STEPS arm: target = the code-written scratchpad
"37 + 46 = 83. 83 - 9 = 74. Answer: 74". Score = exact final answer, greedy decode.

## Marks (fixed now)
- P1: STEPS heldout_template accuracy >= ANSWER's + 15 points.
- P2: STEPS heldout_template accuracy >= 40% (new wordings it never saw; contrast capability256's 0-3 of 64).
- Reported, not gated: dev, heldout_structure, accuracy by step count.
- Proves wrong: STEPS <= ANSWER + 5 on heldout_template.

## Budget
Two Vast boxes (one per arm) or one box sequentially, total cap $6.

## Follow-up FU1 (pre-registered 2026-10-23 ~20:55Z, after the first result, before this run)
One change: STEPS arm only, 18,000 steps instead of 6,000 (everything else identical).
- Pass: heldout_template >= 65% (first run 53.8%). Proves wrong: heldout_template < 58% (more training doesn't help).
- Reported: 4-step held-out accuracy (first run 23%) and heldout_structure (first run 28.2%).
