# y1r PLAN: a trained retriever for the memory store (Answering-from-memory thread, 2026-09-26 19:35 UTC)

Code: scripts/claude_y1r_retriever.py (docstring has the recipe). Sealed in SEAL-y1r.sha256.txt before any run on
real data. Runs on free machines only (this cloud container's CPU or the Mac; no rental, $0).

## Why this test
- bm-398d (artifacts/claude-bm398d-20260926/RESULTS.md) showed on LoCoMo's 297-question sample:
  - the plain MiniCPM5-1B given only the right lines is right on 137, which ties Qwen3.5-2B on the whole chat (138);
  - given the store's top 20 lines it is right on 88;
  - on the 111 questions where the store's top 20 missed an evidence line, adding the lines back gained 30.6 points.
- The store (scripts/claude_ep382_store_v2.py) ranks with an off-the-shelf MiniLM-L6-v2 fused with BM25. Nothing in
  it was ever trained to find the line that answers a question.
- The textbook fix for this (the "obvious fix first" rule, Thread manager 19:24 UTC) is a retriever trained on
  question-to-evidence pairs (the dense-retrieval recipe: contrastive training with in-batch negatives). It has not
  been tried in this project.

## The one change
The MiniLM weights inside the store's fused ranking. BM25, the fusion (RRF, k=60), the key text
('<speaker> said, "<text>"'), the store, k=20 and the LoCoMo harness (scripts/claude_bm393b_store_recall.py run,
with store v2 as bm-393c does) stay the same.

## Training data (no LoCoMo, no Claude-written text)
- y1t's GLM practice items: code chose every fact, GLM 5.3 Flash wrote every word, lis-320's check kept the turns.
- Positives for an answerable item: the earlier turns its never-told twin drops (the turns carrying a fact on the
  asked person and relation). Negatives: the turns the twin keeps (the same chat's other turns).
- The labels come from what GLM was asked to write, so y1r uses only items that pass y1t's data gate
  (artifacts/claude-y1t-20260926/GATE-data.md: G1 code leak check, G2/G3 blind sample). It waits for
  artifacts/claude-y1t-20260926/gate/GATE-RESULT.md saying GATE-PASS and uses exactly the items file that result
  names: items_train for training, items_dev as practice-dev.
- Test-hygiene rules (design/v3/30-modes/test-hygiene-2026-09-26.md): rule 1, there are no generated targets (the
  key frame is the store's own input format, used the same way at test); rule 2, the data gate above; rule 3,
  the smoke run used made-up pairs only, never LoCoMo or practice items.

## Recipe (fixed)
Multi-positive InfoNCE, temperature 0.05, AdamW lr 2e-5, weight decay 0.01, batch 16, up to 7 same-chat negatives
per query plus every other query's turns, 2 epochs, seed 4035, max 128 tokens, mean-pooled and normalised as the
store embeds. MiniLM snapshot 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 (already in the stack).

## Steps
1. `sha256sum -c artifacts/claude-y1r-20260926/SEAL-y1r.sha256.txt`, then the selftest.
2. `pairs` on items_train and on items_dev (counts only).
3. `train` (writes encoder.pt, never pushed; its sha256 goes in RESULTS).
4. `locomo` twice in the same session, same code: without --encoder (today's store, arm U) and with it (arm R).
   LoCoMo file sha256 79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4.
5. RESULTS.md in artifacts/claude-y1r-20260926/run/ with train.json, both store_recall.json files and the
   per-question 0/1 rows (ids and flags only; no question or answer text).

## Pass marks (fixed now, before any real run)
- **Stage 1, finding the lines (CPU, no generation).** LoCoMo categories 1-4 (1,531 questions with evidence):
  arm R's fused all@20 (every evidence line in the top 20) is at least **+10.0 points** over arm U's.
  Arm U was 61.8 when reproduced in this container at 19:30 UTC (bm-393c got 61.8); the mark is against arm U from
  the same session as arm R.
  - Report only: any@10, any@20, the minilm-only rows, each category, practice-dev positive-at-1 before and after.
- **Stage 2, right answers (only if stage 1 passes).** On bm-398d's 297-question sample at the same 20-line budget,
  the plain 1B's blind-judged right answers (label A) with arm R's top 20 are at least **+5.0 points** over arm U's
  top 20. Both arms are generated on the same machine with the same code, and judged by fresh blind Opus judges in
  bm-398d's way. Report only: the by-conversation 95% interval and gained/lost counts.
  Stage 2's runner is written, agreed with the Benchmarks thread and sealed before it runs; these marks do not change.
- **Proved wrong:**
  - stage 1 below +10 means retrieval training on GLM practice chats does not carry over to LoCoMo's chats;
  - stage 1 passing and stage 2 below +5 means better recall is not the lever for right answers at this budget.
- FAILs stay FAILs. LoCoMo numbers carry the label "after using LoCoMo for development". LongMemEval is not touched.

## Predictions
| # | Prediction | Chance |
|---|---|---|
| P1 | Stage 1 passes (point guess +5; the practice chats are short one-speaker chats, LoCoMo's are long two-speaker chats) | 30% |
| P2 | Practice-dev positive-at-1 rises by at least 10% of the dev pairs | 80% |
| P3 | Stage 2 passes if stage 1 does (a +10 recall gain predicts about +3 answer points from bm-398d's +30.6 on misses) | 30% |

## How the brain does it (a guess)
A cue finds a memory because the hippocampus has learned which cues go with which stored events; retrieval gets
better with practice at recalling, not only with storing. y1r gives the store that practice. It is a guess that
this is the right mapping.

## For Ben, in plain words
The memory can only answer from lines it finds. Right now the part that finds lines was never taught to find
answers; it just matches similar-looking words. y1r teaches it on practice chats GLM wrote, then checks on the
LoCoMo chats whether it finds the right lines more often (needs +10 points), and only then whether the model gives
more right answers (needs +5 points). Free: it runs on a normal CPU.
