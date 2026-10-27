# rd-379q: question notes, pointers that state no facts (Trustworthy notes thread, registered 2026-09-26 ~14:10 UTC)

Written while rd-378L runs, before any rd-378L or rd-379q number exists, and before any question is written over
LoCoMo. Development measurement on LoCoMo PRACTICE (labelled "after using LoCoMo for development"); nothing is trained
on LoCoMo or any other benchmark; no question, answer, turn, note or generated question is printed or pushed.

## Why
Problem #3: notes can't be trusted (rd-378's fact notes: 31% unsupported; the rd-371b checker kept 1 of 132 true notes).
Ben's design: notes are pointers to the raw chat, and answers come only from the original turns. A question such as
"When did Wren move to Oakvale?" points at a turn without claiming anything, so it cannot store an untrue fact. If
question notes help search as much as fact notes, the truth problem is avoided rather than trained away.

## The one change (vs rd-378L's store A)
Store A: every turn as a "heard" row (unchanged, identical to rd-378L's A). Store Q: the same rows plus, per turn, up to
3 questions the plain MiniCPM5-1B (commit 87179e5c, thinking off, greedy, no training) writes for that turn, each a note
pointing to its own turn (cites [0]). Prompt and parser: scripts/claude_rd379q_questions.py (same 6 earlier turns as
the rd-378 writer). Everything else is rd-378L's sealed scorer, unchanged: scripts/claude_rd378L_recall.py score,
LoCoMo conversations 0-4 (2,760 turns, questions of categories 1-4 with evidence), fused BM25 + MiniLM recall.

## Marks (fused mode, questions of categories 1-4)
| Mark | Bar |
|---|---|
| Q1 | Q any@10 >= A any@10 + 5 points overall |
| Q2 | no category (1, 2, 3, 4) more than 3 points below A on any@10 |
| Q3 | Q anyT@10 >= A anyT@10 + 5 points (same 10-turn budget; a question note covers only its own turn) |
PASS = Q1 and Q2 and Q3. Proved wrong: Q any@10 <= A + 1 point (also reported for anyT@10).
Sanity (not a mark): store A's counts must equal rd-378L's A exactly; any difference is reported and the run is not
compared with rd-378L's B.
Report only: bm25 mode, @5 and @20, all@k, mean turns@10, questions per turn, turns with no question, median write ms,
and Q next to rd-378L's B.

## What happens next (fixed now, before either result)
1. Q passes: question notes become the notes. They state no facts, so untrue notes cannot arise and the cut-only fact
   writer (371c step 4b) is not run for search, unless rd-378L's B also passes AND B's anyT@10 beats Q's by more than
   5 points (then 4b is worth its cost).
2. Q fails and rd-378L passes: 4b, the cut-only fact writer, as planned.
3. Both fail: notes stay off the store (it answers from heard turns only) and problem #3 closes as "notes not used";
   Ben is told in one line.
Whichever notes pass, Benchmarks may run its answer-level follow-up from that run's ranked_turns.jsonl.

## Seal
SEAL.sha256.txt covers this file, the question script, the smoke dialogs and rd-378L's scorer and its dependencies.
The rental runs the exact commit that added SEAL.sha256.txt.
