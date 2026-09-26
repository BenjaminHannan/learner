# rd-378L: do notes help find the right message across a whole long chat? (step 4a of the 371c plan)

Thread "Fix: reading facts from chat". Written 2026-09-26 ~13:05 UTC, before any note was written over LoCoMo and before
any score. Development measurement on LoCoMo PRACTICE (labelled "after using LoCoMo for development"); nothing is trained
on LoCoMo; no question, answer, turn or note text is printed or pushed.

## Why
rd-378's finding test searched inside one 12-16 turn dialog, where top 10 is most of the dialog (heard-only found
150/150), so it could not show whether notes help. Ben's pasted report (12:00 UTC): measure whether notes help search
before spending on making them truer; if they don't, drop them. This is that test, before step 4b (cut-only writer).

## The one change
Store A: every LoCoMo turn as a "heard" row (exactly bm-393b's rows, ep-382 MemoryStore). Store B: the same rows plus
every note the rd-378 note writer (unchanged; merged sha256 dbcc8db5...) writes, greedy, one call per turn with up to 6
earlier turns of the same session, each note pointing to its cited turns. Same recall() (fused BM25 + MiniLM), same
questions. Chats: LoCoMo conversations 0-4 (2,760 turns, 759 questions of categories 1-4 with evidence).
Script: scripts/claude_rd378L_recall.py (dialogs, score). A question is found@k when an evidence turn is in the union of
the turn ids of the top k recalled items (a note counts as one item and points to its cited turns).

## Marks (fused mode, any@10, questions of categories 1-4)
| Mark | Bar |
|---|---|
| L1 | B >= A + 5 points overall |
| L2 | no category (1, 2, 3, 4) more than 3 points below A |
PASS = L1 and L2. Proved wrong: B <= A + 1 point overall.
If L1 fails, notes stay off in the store (it already answers from "heard" only) and step 4b is not run.
Report only: bm25 mode, @5 and @20, all@k, notes per turn, unparsed turns, write ms.
Reference (not a mark): bm-393b's heard-only fused any@10 on all ten chats was 62.9%.
