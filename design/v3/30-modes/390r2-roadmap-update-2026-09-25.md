# 390r update after bm-390 and Ben's note on relations (Benchmarks thread, 2026-09-25 ~19:40 UTC)

Updates 390r-best-in-class-roadmap.md (that file stays as written; where they differ, this one wins).

Ben, 19:22 UTC (Fix sleep thread): relation facts are "genuinely 1% of the work this model will do ... a
foundation", not the focus; threads should partly overlap and work with each other directly.
bm-390 (VERIFY-bm390.md, registered FAIL): 0.1 saved 18 relation facts from 5,882 LoCoMo turns and scored 2.98 F1;
the plain 1B reading the 10 best-matching raw turns scored 25.06. The facts layer was the whole memory, and it was
not enough.

## What changes
1. **Memory tests measure episodic memory, not relation facts.** What moves LoCoMo and LongMemEval is: keep what was
   said (every turn, verbatim, with its date), find the right turns when asked, and reason over them. The notebook's
   relation facts stay as the exact-recall foundation (names, "I don't know", provenance), not the lever. The table
   "which part moves which score" in 390r now reads: single-hop and open questions = find the turn; multi-hop =
   find several turns and join them (reasoner); temporal = the turn's session date plus date arithmetic (reasoner);
   knowledge update = the newest turn wins; "what did the assistant say" = the turn log.
2. **Dates go on episodes.** The Sept 26-29 asks "dates on saved facts" and "updates without the word
   correction" become: every stored turn keeps its session date, and the newer of two conflicting turns is preferred.
   Fact-level versions stay the Reading thread's call.
3. **CLUTRR is dropped** as our public reasoning test: it is kinship-relation chains, the same narrow thing, and our
   practice worlds already use family chains. The reasoning test is chosen with the Sleep research thread from tests
   that are not relation puzzles (candidates, unchecked: BIG-Bench Hard subsets; licence, rival reports and overlap
   with the practice ladder to be checked before anything is downloaded).
4. **Assistant work gets public tests.** The creative thread's practice plan (assistant-practice-plan-2026-09-25.md)
   already keeps BFCL (tool calls), HumanEval (code) and IFEval (instructions) as test sets. This thread owns that
   test side: before any practice run, a registered overlap check between every practice set and those tests
   (exact and near-duplicate items), and a task-type note where practice and test share a format (e.g. zebra
   puzzles in Reasoning Gym), so a test result is never targeted practice.

## Next steps for this thread (in order)
- Finish bm-390's plain baselines (rent-bm390f, released 17:32 UTC): the bar for every later build.
- **Evidence recall on LoCoMo practice, $0 on CPU, no language model:** LoCoMo marks the turns that hold each
  answer (1,982 questions have evidence ids). For each question, does a retriever's top 10 contain the evidence
  turn? BM25 (Rb's retriever) versus the MiniLM already in the stack. Counts only, labelled "after using LoCoMo for
  development", never trained on. It tells whoever builds episodic memory which way to find turns before any GPU
  run, and it separates "did not find the turn" from "found it but answered wrong".
- The practice-versus-test overlap checker for the assistant tests (with the creative thread).
- bm-391 = 0.2 on LoCoMo practice with its episodic memory, same arms and marks as bm-390.

## Overlaps (each thread works with the others directly)
| Thread | Where our work overlaps |
|---|---|
| Reading facts | LoCoMo is real overheard chat for their reader; the evidence-recall check scores any "keep and find what was said" design they build; their facts stay the exact layer on top |
| Fix sleep | sleep attempted learning 0 of 272 times on LoCoMo (0 of 360 in 336b): ordinary chat gives it nothing to learn from. Replaying the day's raw turns is the input sleep could consolidate; LoCoMo practice is a ready test of "does a night make answers better" |
| Sleep research (reasoner) | multi-hop and temporal questions over found turns are the reasoner's job on text; we pick its public reasoning test together |
| Creative (assistant practice) | they own practice, we own the clean test side and the overlap check |
| Month-end (0.2) | bm-391 is 0.2's public scorecard; the general-question route ("I'm not sure" on 134 of 300 MMLU items) is 0.2's to fix |
