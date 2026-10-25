# Notebook-2: close the diary search gap with the real local models (pre-registration, 2026-10-25 ~22:05Z)

Labels: shown / suggested / untested. Neither the village model nor the card experiments. Follows Notebook-1
(`gaps/notebook1/`, branch claude/project-thread-p7b2wv), which used a Claude Haiku 5.5 stand-in reader on
LongMemEval-S: F full history 76.7, R BM25 top-10 turn pairs 71.7, O oracle sessions 86.7 (60 questions, 1 seed).

## The question
R - O = 15 points. In Notebook-1 the reader never searched: BM25 on the raw question picked 10 user+assistant pairs and
the reader only answered. So the gap is (a) search picking the wrong snippets plus (b) whatever the reader loses on
snippets vs whole sessions. A stronger reader cannot fix (a). Notebook-2 measures (a) without any model, then lets the
real backbones (K2-3.7B and Qwen3.6-35B-A3B q4) drive the search.

## Stage 0: retrieval only (CPU, free, no model)
Data: all 500 LongMemEval-S cleaned items; abstention items (`_abs`, 30) excluded from retrieval scoring (no evidence).
Units: user+assistant turn pairs, as in Notebook-1. Each arm fills the same budget: 8,000 tokens (chars/4), roughly
Notebook-1 R's mean prompt, best-scored first, shown in date order.
Evidence: a pair is evidence if either turn has `has_answer: true`.
Metrics: **AllHit** = question counts only if every answer session contributes at least one evidence pair to the
context (primary); EvRecall = share of evidence turns included; reported per question type and on the 60-item
Notebook-1 sample.
Arms (choices fixed now, no tuning):
- S0 BM25 on the question (Notebook-1 R, budget-filled).
- S1 dense: `BAAI/bge-small-en-v1.5`, each pair cut into 200-word windows, pair score = best window cosine. Query gets
  the bge query instruction.
- S2 hybrid: reciprocal-rank fusion of S0 and S1 (k = 60, equal weights).
- S3 S2 plus the pair just before and after each hit from the same session (inside the same budget).
Pass mark Z1: S2 AllHit >= S0 + 10 points (470 questions). **Wrong if** S2 <= S0 + 3: meaning-based search adds
little over keywords on this data, and the gap must be closed by the model's own search words instead.
Z2 (reported, not gating): S3 vs S2.

## Stage 1: real readers drive the search (GPU: Kaggle T4 or Ben's Mac/PC, whichever frees first)
Questions: the 60 Notebook-1 items plus 60 more (10 per type, `random.Random(1)` over the remaining ids sorted) = 120.
Readers (thinking off, greedy, answer <= 200 tokens): K2-Horizon-3.7B and Qwen3.6-35B-A3B 4-bit.
Retriever inside every searching arm = the Stage-0 winner (S2, or S3 if Z2 shows S3 >= S2 + 3 AllHit), 8k budget.
Arms (one change between neighbours):
- R  BM25 top-budget (Notebook-1 baseline, now with the local reader).
- Hy Stage-0 winner on the raw question.
- Q  model first writes up to 3 search queries (<= 40 tokens, closed book), fused with the raw question by RRF.
- T  two rounds: round 1 = Hy; the model reads the round-1 hits and replies ENOUGH or writes <= 40 tokens of new
     search words; if words, round 2 runs them and RRF-merges with round 1, trimmed to the same 8k budget; then answer.
- O  oracle sessions (ceiling for this reader).
Judge: `claude-sonnet-5-5` with Notebook-1's judge prompts, via the Message Batches API.
Pass marks (per reader; paired counts and exact McNemar reported):
- P1 (primary, Qwen3.6): best of {Hy, Q, T} >= R + 8 points (120 q).
- P2 gap closed: (best - R) >= 0.5 x (O - R) for that reader.
- P3 K2: same as P1 for K2 (reported separately; the small tier may be reader-limited).
**Wrong if** for both readers every searching arm is <= R + 2: better search does not reach the answer for local
readers, so the bottleneck is reading, and work moves to reading (e.g. whole-session expansion, notes) not search.
Descriptive only: Qwen3.6 R and O vs Haiku's 71.7 / 86.7 on the shared 60 items (answers "is the local model better?").

## Stage 2: recall-then-read (separate test, INVENT-1 pick 2)
Needs an add-on that slept on the diary, which LongMemEval does not have (one per question). It runs on the Week-2
world exactly as pre-registered in `mechanism/INVENT-1.md` section "Pick 2" (arms D0-D4, R, pass marks 1-5). Not mixed
into Stage 1 numbers.

## Noise and cost
120 questions, one seed: SE about 4 points per arm; differences under ~6 points are noise. Stage 0 has 470 questions
(SE about 2). API: judge only, about 1,200 Sonnet calls via Batches, cap $6. GPU: free sources only; no Vast before Oct 31.

## Amendment A (2026-10-25 22:12Z, before any Stage-0 result was looked at)
CPU embedding in the container runs about 1 question per minute, so 470 questions take ~8 h. Stage 0 now processes the
Stage-1 question set first. **Z1 is decided on the non-abstention questions of the 120-question Stage-1 set** (about 110;
SE about 4.5 points), and the retriever for Stage 1 is fixed from that. The full 470 is reported when it finishes and
does not change the Stage-1 retriever choice.
