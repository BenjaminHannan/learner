# bm-398n PLAN: do the reader's notes give more right answers? (benchmarks thread, written 2026-09-26 16:39 UTC)

Registered and sealed before any scored reply exists. A 2-question smoke run (not scored) and a dry run of score,
prep and jscore on made-up replies and labels ran every step. Every LoCoMo number is "after using LoCoMo for
development". Counts only: no question, answer, turn, note or reply is quoted.

## Why
- rd-378L (Trustworthy notes; blind recount 274fae558) showed that the reader's notes help the store find the right
  message. On 759 LoCoMo questions (conversations 0-4, categories 1-4), fused any@10 rose from 496 (store A, heard
  turns only) to 583 (store B, heard turns plus notes that point to the turns they cite).
- Finding the message is only half of recall. The brain's version is an index pointing back to the episode, which is
  then re-read, and the answer depends on the re-reading. bm-398d showed that the plain 1B, even with only the right
  lines, is right on 137 of 297.
- So this asks the question that matters for the design: do the notes give more right answers? It is the follow-up
  agreed at 12:50 UTC (rd-378L addendum C) and registered only because L1 passed.

## The one change
- The plain MiniCPM5-1B answers every one of rd-378L's 759 questions twice:
  - **AN:** from store A's first 20 distinct turns;
  - **BN:** from store B's first 20 distinct turns.
- The turns come from origin/builder-outbox:artifacts/claude-rd378L-20260926/ranked_turns.jsonl (sha256
  2792906c…97d4, pinned in the script, which refuses any other file).
- Everything else is fixed, and bm-398d laid out its store arms the same way:
  - the turns are shown in chat order under their session dates;
  - bm-390's system prompt and QA prompt, and 50 new tokens;
  - greedy decoding, thinking off, CPU fp32.
- Script: scripts/claude_bm398n_notes.py (selftest 11/11).

Already known from the turn lists, computed before any reply:
- An evidence turn is among the 20 for 573 questions in A and 639 in B.
- All evidence turns are among the 20 for 479 in A and 541 in B.
- No question has the same 20 turns in both stores.

## Blind check
- bm-398d's rubric, INSTRUCTIONS.md copied unchanged, so judges see the evidence lines. Labels run A (right) to E
  (doesn't know).
- Latin square with two groups: each group holds every question once, in one arm, and the two arms of a question
  are in different groups. That gives 32 batches of up to 50 items. random.Random(3995) sets the order.
- 8 main Opus judges, each taking 4 batches of one group, plus 1 relabel judge who takes X1 (the first 60
  questions as group L0 has them) and no group.
- Each judge works in a private folder outside the repository. Then a separate agent does a blind recount.
- If the two replies to a question are byte-identical, they are one answer. Both arms take group L0's label and the
  question is a tie. How often the two judges agreed on such pairs is reported.

## Marks (fixed now; coded in verdict())
- **N1 (more right answers):** BN's A-count ≥ AN's + 15, with more gained than lost and a two-sided exact McNemar
  p < 0.05 on the questions that changed. The McNemar test replaces the conversation bootstrap because there are
  only 5 conversations. The bootstrap is reported only.
- **N2 (no category hurt):** in each of categories 1-4, BN's A-count is at most max(3, 3% of the category's
  questions) below AN's.
- **PASS** = N1 and N2. Anything else is a registered FAIL.
- **Proved wrong:** BN's A-count ≤ AN's. The notes would find more but answer no better.
- **Report only:**
  - F1 with the sealed bm-390 scorer, abstentions and confident-wrong counts;
  - A by category and gained/lost;
  - the AN-by-BN label table;
  - relabel agreement and agreement on identical pairs;
  - the conversation bootstrap.

## Predictions
- P1 (45%): N1 passes. Point guess: BN − AN = +18 A. The reasoning: B has the evidence for 66 more questions,
  and bm-398d converted found evidence into right answers about 31% of the time.
- P2 (85%): N2 holds.
- P3 (40%): PASS.
- P4 (80%): not proved wrong.
- P5 (65%): BN's F1 is above AN's (report only).

## What it leads to
- **PASS:** the notes pay off at the answer. Store B becomes the memory path's store for long histories in the
  joined build, handed to Month-end and Answering from memory as one change. Trustworthy notes' pointer step
  keeps going.
- **FAIL, not proved wrong:** better finding is not yet turning into right answers at this size. The next learned
  change is the re-reading (bm-398r's reader adapter), not more notes work.
- **Proved wrong:** notes stay out of the answer path. Store A stays, and the notes thread is told the finding
  does not carry to answers.
- **Scope:** this measures the store path, which matters when a history is longer than the model can read at once.
  On LoCoMo the whole chat still fits, and bm-398d found the whole chat beat the store's top 20 (109 vs 88 of 297).

## Run and files
- CPU, $0. Starts after bm-398e's CPU steps; 1,518 generations at about 6 seconds each.
- The repository gets counts only: RESULTS.md, score.json, the judge key and labels.
- Replies and judge folders stay in the scratchpad.
