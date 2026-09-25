# 380 road map: the joined agent, from 0.1 to best in class (month-end thread, 2026-09-25 ~03:00 UTC)

Ben 02:18 UTC: "Try to get as much done tonight as possible. You should architect a road map for how you plan to
get to better on class." This thread owns the joined agent (Premonition 0.x), its end-to-end tests and the Sept 30
report. The parts have their own road maps; this file says how they come together and how we know it worked.

## Where 0.1 stands (shown, 336 on bank A; VERIFY-336.md)
| Row | 336 result | Plain 1B twin | Main cause | Owner and road map |
|---|---|---|---|---|
| Conversation | grammar 87% / 56% (bar 99%); preferred over old base 39/40 | not judged | fill-in lines paste raw slots | grammar thread, 360-grammar-roadmap.md |
| Memory | saved 57% of taught facts; answerable asks right 22% | 4% right (8/193) | the reader misses chatty teachings | reading thread, 370-reading-roadmap.md |
| Safety | wrong answers 3; wrong saves 33 turns | 187 wrong answers | "is that right?" checks about vague guesses | this thread (below) + reading thread |
| Learning over time | kept 121/125; sleep learning most likely never ran | none | missing sleep file; sleep only learns word routes | Fix-sleep thread, 360-sleep-plan.md |
| Reasoning | two-step asks 8/37 | 1/37 | reasoner not joined; learned reasoners all FAIL so far | sleep research thread, reasoner-roadmap-2026-09-25.md |
| Creative | useful 12/40; 11 made-up person facts | 10/40 useful (333 panel) | the 1B is the limit; 333e FAIL | creative thread |

## What "best in class" means (not defined here)
Public-benchmark "best in class" belongs to the Benchmarks thread, which registers its own marks: LoCoMo against
Qwen3.5-2B, LFM2.5-1.2B and plain MiniCPM5-1B, with LongMemEval as the final exam. This file's marks cover only the
six month-end rows on the 331-style banks (the 336 marks M1-M11), so there is one definition of best in class.

## How parts come in (the rule for every 0.x)
1. A part joins only after its own registered PASS on its own blind test.
2. Joining is one change per step: 0.x plus that part, rehearsed on DEV, then a registered run on a fresh blind
   bank against 0.x without it and the plain twin. Banks A and B are spent; C and D are being written blind tonight
   (331-bank-CD-addendum.md); later banks follow the same spec.
3. Every rented or BensPC run rebuilds sleep's base file and runs under scripts/claude_sleepcheck_wrap.py.
4. A registered FAIL stays FAIL. A part that fails end to end goes back to its thread with the counts.

## Steps (in order; each has marks fixed before it runs)
| Step | What | Waits on | Pass mark (short) |
|---|---|---|---|
| 336b | 0.1 + gram-360 fill-in finisher, bank B | done 03:40 UTC | FAIL on M1-M11 (same 3 pass as 336); grammar gain B1 PASS (+10.3 and +7.9); sleep B2 FAIL (0/360 sleeps tried to learn). VERIFY-336b.md |
| 381 | stricter test harness: "is that right?" answered yes only when owner, value AND relation are right | DEV check | on DEV, 0 wrong "yes"; right "yes" kept ≥ 95% |
| rd-373 | confirm questions only for clean facts (reading thread owns it, 370-reading-roadmap.md); 381 gives it an honest "yes" | 381 | 0 wrong saves after a confirm |
| 0.2 | 0.1 + every part with a registered PASS by Sept 29 (candidates: gram-360, lis-318 reader, slp-360 scrap + 361 undo, rd-373) | parts' verdicts | 336 marks on bank C vs 0.1 and twin b |
| 0.2b | one follow-up on bank D | 0.2 | same |
| Sept 30 | report: 6 rows, pass/fail, what 0.2 adds over 0.1 | 0.2 | counts only |
| 0.3 (Oct) | trained reasoner joined (after a PASS), sleep practice school on, creative as a tool call | reasoner + sleep lanes | beats twin on two-step asks by +20 |

## Tonight (Ben asleep; no rentals)
- 336b is running on the rental the watcher launched at 01:42 UTC, before the move to BensPC; benspc-336b stays held
  unless the rental fails. Verify when it lands.
- Banks C and D being written blind into /mnt/project-files/escrow-331/C and D; blind audit after.
- 381 harness (scripts/claude_e2e381_harness.py, runner claude_e2e381_run.py) built on DEV; held-out check with two
  blind judges on 73 other DEV confirm questions (marks in artifacts/claude-e2e381-20260925/PASSMARKS-381.md).

## Honest limits
Memory (57% saved, 22% right) is the biggest gap, and it belongs to the reader, not the joining. Reasoning and
creative will not pass by Sept 30: no learned reasoner has passed yet, and the 1B writes the creative replies.
The Sept 30 report will say so.

## Update 2026-09-25 ~03:40 UTC (336b verified)
- gram-360 is a candidate for 0.2: end to end it adds 8-10 grammar points and changes no memory count. It still needs
  its own PASS on bank G (grammar thread) before it joins.
- Sleep as sealed in 0.1 never learns on ordinary chat: its only recipe needs 8 questions using a new family word.
  "Learning over time" joins through the Fix-sleep thread's new sleep (365 road map) after its own PASS; 0.2 keeps
  the old sleep unchanged unless Ben says otherwise.

## Update 2026-09-25 ~17:45 UTC: episodic memory proposed for 0.2 (from bm-390; waits on Ben's yes)
bm-390 (artifacts/claude-bm390-20260925/VERIFY-bm390.md) is a registered FAIL for 0.1: LoCoMo 1-4 F1 2.98 vs 25.06
for the plain 1B reading the 10 best BM25 turns. 0.1 saved 18 facts from 5,882 turns and said "I don't know" on 923
of 1,540 questions. The Benchmarks thread proposes one change: **ep-382 episodic memory**. Every heard turn is kept
word for word (the nb-323 turn log already stores {turn_id, text, t}; t is wall-clock time, so a conversation's own
date needs its own field). When the notebook has no answer, the MiniLM retriever pulls the most relevant raw turns
and the chat model answers from them, notebook facts first, citing the turns it used. The notebook write rule does
not change (raw turns are not notebook facts).
- Its own pass (Benchmarks thread): LoCoMo practice ≥ 25.06, no loss on MMLU-Redux/GSM8K, labelled "after using
  LoCoMo for development"; LoCoMo text never trained on.
- Joining (this thread): 0.1 + ep-382 on bank C vs 0.1 and twin b, 336 marks. It should move M3/M4 (answers) but
  can add wrong answers (M2), so M2 stays the guard.
- Second lever (general-knowledge and math questions go straight to the chat model) is a separate change after it.
- Order if Ben says yes: ep-382 is 0.2's first join; gram-360 second; old sleep stays until the new sleep passes.

## Rebalance 2026-09-25 ~19:30 UTC (Ben, 19:22 UTC, Fix sleep thread: relations are "genuinely 1% of the work")
Ben is right about this line. 7 of the 11 marks in 336 (M1-M6, M9) and every 331 bank are about facts on people.
From now on the six rows are judged by what each row is about, using tests other threads already own. Relation
facts become one floor check inside memory and safety.
| Row | Measured on the joined agent by | Shared with |
|---|---|---|
| Conversation | open chat panel (338 spec), blind judges; grammar of the 1B's own replies | grammar thread |
| Creative | creative panel (333 spec) and 24-style puzzle hits, with creative called as a tool | creative thread |
| Reasoning | GSM8K and MMLU-Redux (Benchmarks harness) and fresh reasoner puzzles; math and general questions go to the chat model or reasoner, not "not sure" | Benchmarks, sleep research |
| Learning over time | Fix sleep's multi-night scorecard (366) run on the joined agent: better at tasks after nights, not only more facts | Fix sleep |
| Memory | LoCoMo (Benchmarks) with ep-382 episodic memory; bank C once as the people-facts floor | Benchmarks, reading thread |
| Safety | wrong things stated as true, counted across all of the above | every thread |
Stopped: more work on the relation-only confirm harness (381/381b stay registered FAILs). Banks C and D stay sealed
for a one-time floor check. Every 0.x candidate is one build that all six tests run on, so each thread's part is
tested inside the whole agent and not only alone.

## Update 2026-09-25 ~20:50 UTC: join order for 0.2
0.2 = 0.1 + gram-360 + ep-382 (scripts/claude_e2e382.py; marks PASSMARKS-382.md; fresh sealed chatpanel382 and
creativepanel382). Next single change after its verdict: the lis-319 reader (registered PASS, reads up to 6 earlier
turns; Reader319 in scripts/claude_lis319_read.py), as 0.2b on bank D. Then rd-378 notes into the 382 store and
rd-371 as the checker, each after its own PASS. The new sleep (Fix sleep: night(model, day_groups) -> adapter)
joins after dl-1 decides the learning rule.
