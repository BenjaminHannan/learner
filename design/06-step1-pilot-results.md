# 06 — Step 1 pilot results (2026-09-19)

Three 600-second runs on BensPC (RTX 5070 Ti), village v0, 20,000 train visits ("medium"), pattern bank v1.
Reports: `artifacts/benspc/<run>/artifacts/premonition-step1-*.json`.

| Run | Model | Windows | Train tokens | Final loss | Train-split Qs | Held-out Qs |
|---|---|---|---|---|---|---|
| 20260919T090156Z-ddb74eb1 | 4M | 768, cut anywhere in the stream | 396M | 0.734 | 36% | 17.9% |
| 20260919T091253Z-7e81df09 | 28M | 768, cut anywhere in the stream | 119M | 0.735 | 36% | 16.7% |
| 20260919T092801Z-1330ff6a | 4M | 2048, one visit per row (new) | 332M (~200M real) | 0.656 | 44% (rising) | 23.4% (rising) |

Gate: FAIL on every accuracy item (needs 90%). The forgetting baseline and the world-speed check pass (data stall 0.2–0.9%).

## What we learned

1. **Windowing was the main bug.** A visit is about 1,160 tokens (90% are under 1,580), but training cut the stream into 768-token rows at random places, so most questions were trained without the scene introduction that answers them. The model learned to guess, and 28M did no better than 4M. Now every training row is one whole visit, starting with `<eos>` like an eval prompt and padded (masked) to 2048. Only 8 of 162,049 visits were cut short. The loss dropped and "not told" rose from 4% to 30%.
2. **Held-out question wording is the next wall.** On held-out questions the model often cannot tell what kind of answer is wanted. For direction questions it says "not told" or "yes" (1% right); for why questions it says "not told" or "no" (0%). Each question type has only 2–7 train phrasings, and the held-out phrasings are new. A from-scratch 4M model cannot map a new phrasing to the right question type from so little variety.
3. **It still learns slowly even in distribution.** Answer tokens are about 1–2% of all tokens; the rest is narration.

## Decisions for Ben

- **Held-out question wording** (pick one):
  - (a) Write many more question phrasings (Qwen top-up, perhaps 60+ per type), so train covers the space.
  - (b) Keep held-out wording for narration and teacher lines, but use a fixed set of question phrasings in all splits for the Step 1 gate, and test new question wording as a separate, later skill.
  - (c) Both.
- **Answer signal:** weight answer tokens more in the loss, or add more questions per visit.

## Other changes made this session

- **Pattern bank v1** (`data/village/patterns/bank-v1.json`):
  - 1,619 written patterns are in use. 16 thin banks use the hand-written fallback for the whole bank.
  - The Bonsai audit is advisory only: it said yes to only 18% of sentences, and about 22 of the first 25 patterns it vetoed were fine.
  - Teacher lines get a lead-in-only Qwen check that reasons briefly before answering. On 6 good and 6 bad test lead-ins, it passed all 6 good and caught 4 of the 6 bad.
  - New filters remove manner adverbs on states, on events nobody performs, and on questions, and doubt words in teacher lead-ins.
  - I vetoed 24 wrong question patterns by hand (`crosscheck/claude-review.jsonl`).
  - Train teacher lead-ins that match a held-out lead-in are dropped.
- **Village:** objects get plausible materials, and food has none (`vocab.KIND_MATERIALS`). The independent reference check gives 0 disagreements.
- **Tokenizer:** `data/tokenizer/premonition-tok-v2.json`, fitted on 60M train characters plus the simple-English texts.
- **Not yet done:** 181 t.quiz_later lead-ins did not get the new check because the PC dropped off the network (the bank uses the fallback). There are residual leak cues for "who has", "what is in" and "what if" answers.
