# Word problems: answer-only vs worked steps — RESULT (2026-10-23)

Pre-registration: design/wordprob/PREREG.md (committed c0e166d2f before any run). One Vast RTX 4090, both arms back to back,
$0.30 total. Data wordprob-v1 (MANIFEST sha256 7bb380a7...), 10,853,760-param char-level transformer, 6,000 steps, seed 0.
Eval: 2,000 random rows per split (seeded shuffle), greedy, exact final answer. Raw: results/answer/final.json, results/steps/final.json.

| Split (2,000 rows each) | ANSWER only | STEPS (worked steps) |
|---|---|---|
| dev (seen patterns, new numbers) | 2.0% | 49.8% |
| heldout_template (patterns never trained) | 3.9% | **53.8%** |
| heldout_structure (4-step, 2 unseen topics) | 0.35% | 28.2% |

Held-out templates by number of steps (STEPS / ANSWER): 1 step 85% / 15%, 2 steps 63% / 2%, 3 steps 42% / 1%, 4 steps 23% / 0%.

## Marks (shown)
- P1 STEPS heldout_template >= ANSWER + 15 points: 53.8 vs 3.9 = +49.9 -> **PASS**.
- P2 STEPS heldout_template >= 40%: 53.8% -> **PASS**.
- Proves-wrong condition (STEPS <= ANSWER + 5): not met.

## Meaning
- shown: on this data, writing the steps is the difference between memorising and generalising to new wordings. The answer-only arm
  reproduces capability256's failure pattern (near zero on held-out); the steps arm gets most 1-2 step held-out problems right.
- suggested: capability256's successor should train on step targets with a large, template-diverse corpus. Errors grow with step
  count, so longer training / a bigger model or a calculator tool for the arithmetic are the next single changes to test.
- untested: one seed only; this is a fresh small model, not the village model, not capability256's LFM adapter.

## FU1: STEPS arm, 18,000 steps (3x) — RESULT
RTX 5090, $0.35. Raw: results-fu1/steps/final.json. Final train loss 6e-5 (train is fitted).

| Split | STEPS 6k | STEPS 18k |
|---|---|---|
| dev | 49.8% | 53.6% |
| heldout_template | 53.8% | **55.4%** |
| heldout_structure | 28.2% | 28.4% |

- Mark (shown): pass needed >= 65%; proves-wrong was < 58%. 55.4% -> **proved wrong: 3x more training does not help.**
- Error reading (suggested, from the 10 saved held-out samples): the 4 misses all do the arithmetic right but pick the wrong
  operation or operands ("12 more than" -> minus; "19 batteries at 9 dollars each" -> 19 + 9). The limit is reading the
  English, not computing. A from-scratch 10.8M char model has little language knowledge; the next single change to test is
  a pretrained language backbone on the same data and marks.
