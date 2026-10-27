# y1r RESULTS: a trained retriever for the memory store (Answering-from-memory thread, run 2026-09-27 11:14-11:23 UTC, written 11:26 UTC, corrected 11:31 UTC after a separate checker recounted every number)

All LoCoMo numbers here are **after using LoCoMo for development**.

## Verdict
**Stage 1 FAIL.** Arm R's fused all@20 on LoCoMo categories 1-4 (1,531 questions with evidence) is 62.8 against arm
U's 61.8 from the same session: **+1.0 point, where the sealed mark is at least +10.0** (PLAN.md). In counts: 961
against 946 questions with every evidence line in the top 20 (R found all of them on 32 questions where U did not, and
lost 17 that U had).

PLAN.md has no separate proved-wrong bar for stage 1: its sealed line says stage 1 below +10 means that retrieval
training on these practice chats does not carry over to LoCoMo's chats. So the claim that it carries over by the +10
points the plan asked for is **proved wrong as registered**, for this recipe (the fixed one, one run, 874 training
pairs) and this store (store v2, fused with BM25, k = 20). Stage 2 (right answers) does not run: it was only to run
if stage 1 passed.

Report only, not a registered test: the small gain may be real. An exact two-sided McNemar test on the 32 gained and
17 lost questions gives p = 0.044 (computed after the run). So "little carries over" fits better than "nothing
carries over". Suggested.

## The run (one run, ADDENDUM-1 order; run_y1r.sh and its output run_y1r.out)
- Seal checks: SEAL-y1r, SEAL-y1r-add1, SEAL-y1r-add2 and SEAL-y1r-add3 all OK. Items: glm2/items/items_train.jsonl
  (47e2e295...79e4) and items_dev.jsonl (c0288f2c...07e4), the files GATE-RESULT.md (GATE-PASS) names, both OK.
  LoCoMo file sha256 79fa87e9...8ff4 OK. Both selftests ok.
- Pairs: train 874 (888 answerable, 14 with no twin, 0 with no positive; 191 have no same-chat negative and use the
  other queries' turns only); dev 145 (146 answerable, 1 with no twin). Control shuffle (seed 4037): 874 pairs, 0
  queries left on their own chat.
- Training (recipe as sealed: InfoNCE, tau 0.05, lr 2e-5, batch 16, 2 epochs, 110 steps, seed 4035): arm R loss
  1.59 to 0.41, arm C (shuffled pairs) 4.61 to 3.38. Final weights used (no checkpoint choice). encoder.pt stays in the
  container, never pushed: R d0b85dd5...7e21, C dca30bda...243d.
- Machine: this cloud container's CPU, Python 3.11.15, torch 2.14.0+cpu, transformers 5.17.0, MiniLM snapshot
  1110a243fdf4706b3f48f1d95db1a4f5529b4d41 (the only one in the cache), HF offline. $0.

## Numbers
LoCoMo categories 1-4, 1,531 questions: percent of questions, with the count in brackets (U/, R/ and
C/store_recall.json; the differences are from the counts in store_recall_per_question.jsonl):

| Row | U (today's store) | R (trained) | C (control) | R - U | C - U |
|---|---|---|---|---|---|
| fused all@20 (**the mark**) | 61.8 (946) | 62.8 (961) | 62.1 (950) | **+1.0** | +0.3 |
| fused any@20 | 75.3 (1,153) | 76.4 (1,169) | 75.4 (1,154) | +1.0 | +0.1 |
| fused all@10 | 53.7 (822) | 54.3 (832) | 52.4 (803) | +0.7 | -1.2 |
| fused any@10 | 65.9 (1,009) | 66.9 (1,025) | 64.7 (990) | +1.0 | -1.2 |
| fused all@5 | 44.7 (685) | 46.6 (713) | 43.2 (661) | +1.8 | -1.6 |
| fused any@5 | 55.5 (850) | 57.5 (881) | 54.3 (831) | +2.0 | -1.2 |
| minilm-only all@20 | 55.6 (852) | 58.7 (898) | 46.2 (708) | +3.0 | -9.4 |
| minilm-only any@20 | 69.0 (1,057) | 72.2 (1,105) | 60.4 (924) | +3.1 | -8.7 |
| minilm-only all@10 | 45.4 (695) | 49.2 (753) | 37.2 (570) | +3.8 | -8.2 |
| minilm-only any@10 | 57.5 (881) | 61.9 (947) | 50.5 (773) | +4.3 | -7.1 |
| minilm-only all@5 | 37.2 (569) | 40.6 (622) | 29.1 (446) | +3.5 | -8.0 |
| minilm-only any@5 | 48.3 (739) | 52.3 (801) | 39.3 (602) | +4.0 | -8.9 |
| bm25-only all@20 | 53.2 (815) | 53.2 (815) | 53.2 (815) | 0 | 0 |

Report only, fused all@20 by category, U / R / C in counts: category 1 (281 questions) 51 / 52 / 54; 2 (320)
238 / 236 / 219; 3 (89) 27 / 29 / 26; 4 (841) 630 / 644 / 651. The control beat R in categories 1 and 4. Every other
row by category is in the three store_recall.json files.

Practice-dev positive-at-1 (145 GLM and Luna practice pairs, the right turn ranked first among its chat's turns):
119 before; 137 after training on the real pairs (R); 101 after training on shuffled pairs (C).

Report only, rd-378L's 759 questions (finding759.json; LoCoMo conversations 0-4, categories 1-4), questions with any /
all evidence among the top k, beside bm-398u's rows from its RESULTS.md:

| k | U | R | C | store B's top k (bm-398u) | the 1B's own top k of store B's 20 (bm-398u) |
|---|---|---|---|---|---|
| 5 | 440 / 365 | 459 / 382 | 422 / 345 | 495 / 408 | 539 / 448 |
| 10 | 520 / 437 | 527 / 439 | 498 / 418 | 577 / 476 | 601 / 504 |
| 20 | 584 / 491 | 591 / 500 | 577 / 485 | 639 / 541 | 639 / 541 |

These rows are across stores: U, R and C rank raw turns with store v2; store B is rd-378L's notes-assisted ranking,
whose notes come from a writer that is out of every build (ADDENDUM-2). Any comparison in this table is suggested,
not shown.

## Predictions (PLAN.md)
| # | Prediction | Chance | Result |
|---|---|---|---|
| P1 | Stage 1 passes (point guess +5) | 30% | no: +1.0 |
| P2 | Practice-dev positive-at-1 rises by at least 10% of the dev pairs (15 of 145) | 80% | yes: +18 (119 to 137) |
| P3 | Stage 2 passes if stage 1 does | 30% | not tested (stage 1 failed) |

## What it suggests (not shown)
- The retriever learned the practice task (+18 of 145 on practice-dev) but little of that reached LoCoMo. The plan's
  guess was the gap in chat shape: the practice chats are short one-speaker chats, LoCoMo's are long two-speaker chats.
  This run does not test that reason.
- The control gained +0.3 on the mark (4 questions net: 67 gained, 63 lost), less than R's +1.0, and its MiniLM-only
  rows fell 7.1 to 9.4 points while R's rose 3.0 to 4.3. So R's small gain is suggested to be more than getting used to the
  text format. But the control did better than R in categories 1 and 4, so this is not clear-cut.
- R's MiniLM on its own gained 3.0 to 4.3 points; after fusion with BM25, 0.7 to 2.0 points are left. Suggested: the
  fusion dilutes a MiniLM-only gain. The mark was on the fused ranking, as sealed, and stays FAIL.

## Deviations and disclosures
- Writer mix (ADDENDUM-3): GLM 5.3 Flash wrote 2,085 practice dialogs and GPT-6 Luna wrote 315. Report only: Luna's
  dialogs gave 123 of the 874 training pairs and 24 of the 145 dev pairs. No Claude-written text is in the pairs.
- LoCoMo was used in development before (bm-393c and this thread's check of arm U at 19:30 UTC on 09-26); arm U came
  out at 61.8 again. No choice was made on LoCoMo (ADDENDUM-1): one run, final weights.
- Files: U/, R/ and C/ hold store_recall.json and store_recall_per_question.jsonl (question ids, categories, the
  number of evidence lines and 0/1 flags; no question or answer text); R/ and C/ also hold train.json. run_y1r.out has the scratch paths replaced
  by SCRATCH.

## For Ben, in plain words
The memory can only answer from lines it finds. y1r taught the line-finder on 874 practice chats. It got much better
at the practice chats (137 of 145 right first, up from 119), but on the LoCoMo chats it found every needed line on
only 1 more question in 100 (62.8 against 61.8), and it needed 10 more. So very little of this teaching, on these
practice chats, carries over to real long chats. It cost nothing (it ran on a normal CPU in about 8 minutes).
