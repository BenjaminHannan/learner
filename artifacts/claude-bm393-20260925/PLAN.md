# bm-393 PLAN: does search find the chat line that holds the answer? (benchmarks thread, 2026-09-25, before running)

Why: bm-390 showed that 0.1's relation facts were not enough (18 facts saved, F1 2.98), while the plain 1B reading
the 10 best BM25 turns reached 25.06 (VERIFY-bm390.md). The next build's memory keeps what was said and finds it
again (390r2-roadmap-update-2026-09-25.md). Before any GPU run, this measures the "find it again" half on its own.

What: scripts/claude_bm393_evrecall.py, $0 on CPU, no language model. For each LoCoMo question, are the turns LoCoMo
marks as evidence among a retriever's top k turns of that chat? R1 = bm-390's BM25; R2 = the stack's frozen MiniLM
(cosine, max 128 wordpieces). Recall "any" and "all" at k 5, 10, 20, per category. Rb's bm-390 F1 is split by
whether BM25's top 10 held an evidence turn. A measurement, not a pass/fail; nothing is tuned in this run.

Honesty: LoCoMo is practice after bm-390; every number is labelled "after using LoCoMo for development". Nothing is
trained on it; no question, answer or turn text is printed or written; outputs are counts and per-question 0/1 flags.

Predictions (written before the run):
- E1: BM25 recall_any@10 on categories 1-4 is between 50% and 80%.
- E2: MiniLM recall_any@10 is within 10 points of BM25's.
- E3: multi-hop (category 1) recall_all@10 is below 40% for both.
- E4: Rb's F1 where BM25's top 10 held an evidence turn is at least 15 points above where it did not.
What would change the plan: if both retrievers find the evidence for most questions (above 80%), the loss is in
answering, not finding, and the reader or reasoner is the next lever; if both are below 50%, finding is the lever.
