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

## FU2: pretrained SmolLM2-360M, STEPS targets, 3,000 steps — RESULT
RTX 4090 (Vast, Utah), 17 min wall, $0.15. Raw: results-fu2/smol/final.json, train.log. Pre-registered 21:58Z (commit
ed2fd52d56), box rented 22:03Z.

| Split | STEPS 6k (10.8M, scratch) | FU1 18k | **SmolLM2-360M** |
|---|---|---|---|
| dev | 49.8% | 53.6% | **80.7%** |
| heldout_template | 53.8% | 55.4% | **78.8%** |
| heldout_structure | 28.2% | 28.4% | **48.2%** |

By step count, heldout_template (scratch STEPS 6k -> SmolLM2): 1 step 85 -> 94%, 2 steps 63 -> 92%, 3 steps 42 -> 73%,
4 steps 23 -> 50%.

- Mark (shown): pass needed >= 70%; proves-wrong was < 60%. 78.8% -> **PASS.**
- Shown: a pretrained language backbone fine-tuned on the same data beats the from-scratch model by 25 points on unseen
  templates, after only 3,000 steps (about 1 epoch's first 90%).
- Caveats (untested): 34x more parameters as well as pretraining, so this does not separate "pretrained" from "bigger";
  one seed; 2,000-row samples (±~1.8 pts). Long chains (4 steps) are still the weak spot at 50%.
- Suggested next single change: same SmolLM2 recipe with a randomly initialised SmolLM2-360M (separates pretraining from size).

## FU3: same SmolLM2-360M architecture, random init (size control) — RESULT
RTX 4090 (Vast), 19 min, $0.19. Raw: results-fu3/smolrand/. Pre-registered in commit 2667e501 before the box was rented.

| Split | scratch 10.8M STEPS | SmolLM2 random init | SmolLM2 pretrained |
|---|---|---|---|
| dev | 49.8% | 42.0% | 80.7% |
| heldout_template | 53.8% | **45.7%** | 78.8% |
| heldout_structure | 28.2% | 20.8% | 48.2% |

heldout_template by step count (random init): 1 step 70%, 2 steps 56%, 3 steps 35%, 4 steps 19%.

- Mark (shown): pass needed <= 60%; proves-wrong was >= 72%. 45.7% -> **PASS: pretraining, not size, explains FU2's gain.**
  The 34x-bigger random model with the same recipe scores below the small scratch model.
- Caveat (stated in advance): the recipe was set for fine-tuning; a scratch 360M model might do better with a different
  schedule. Final train loss 0.011 vs 0.0055 pretrained.
