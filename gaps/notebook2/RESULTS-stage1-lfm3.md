# Notebook-2 stage 1, small reader LFM3-1.7B (Amendment D) — 2026-10-30

Reader LFM3-1.7B QAD-Q4_0 GGUF, llama.cpp 338fce6511 on the M1, thinking off, temperature 0; retriever S2 (hybrid); 120 questions,
8k-token context. Judge Sonnet 5.5 via Message Batches (msgbatch_01XBEDV67VpZJPFQVx61AVn8, 600/600 succeeded). Rows and judgments in
results/lfm3q4/.

| arm | all | knowledge-update | multi-session | single-session-assistant | single-session-preference | single-session-user | temporal |
|---|---|---|---|---|---|---|---|
| R (BM25 on the question) | 46.7 | 65 | 30 | 80 | 10 | 65 | 30 |
| Hy (hybrid) | 50.8 | 75 | 30 | 80 | 15 | 75 | 30 |
| Q (model writes queries) | 49.2 | 60 | 35 | 65 | 15 | 80 | 40 |
| T (two rounds) | 50.0 | 75 | 30 | 75 | 15 | 75 | 30 |
| O (oracle sessions) | 57.5 | 65 | 55 | 85 | 25 | 80 | 35 |

(20 questions per type; type columns are rough.) Paired vs R: Hy 14 wins / 9 losses (+4.2, p=0.40), Q 15/12 (+2.5), T 13/9 (+3.3),
O 19/6 (+10.8, p=0.015).

Pass marks (PREREG.md, Amendment D):
- **P3 (LFM3): best of {Hy, Q, T} >= R + 8 — FAIL** (best Hy +4.2; shown at n=120, the +4.2 itself is not significant).
- **P2 for LFM3: gap closed >= 0.5 x (O - R) — FAIL** (4.2 / 10.8 = 0.39).

Reading (labelled):
- Shown: with perfect search (O) LFM3 answers only 57.5%, against Haiku's 86.7% in Notebook-1. For the small model the reader is the
  main limit, not search. The search gap that exists (R to O, +10.8) is mostly multi-session (30 -> 55).
- Suggested: the hybrid search helps a little in the same direction as stage 0 (+4); the model-written queries (Q) and the second
  round (T) add nothing over plain hybrid for a 1.7B reader.
- Untested: whether Qwen3.6 (P1, the primary) does better; that run is on the M3 and not finished.
