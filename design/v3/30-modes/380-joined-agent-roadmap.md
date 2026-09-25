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

## What "best in class" means for the joined agent (fixed now)
On a fresh blind bank, judged blind, all at once: (1) beats the same-size plain model on every row; (2) states
0 wrong facts about the user's life and never invents one; (3) grammar 99%+ by two valid graders; (4) keeps 100%
of taught facts across sleeps; (5) gets better after nights of sleep than a copy that never sleeps. Then the same
test against the best open 1-3B chat models (Ben's yes needed for any download). Today only (2)'s "wrong answers"
half is close (3 vs the twin's 187).

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
| 336b | 0.1 + gram-360 fill-in finisher, bank B, BensPC tonight | director slot | M1-M11 as 336; grammar +5 over plain 0.1 |
| 381 | stricter test harness: "is that right?" answered yes only when owner, value AND relation are right | DEV check | on DEV, 0 wrong "yes"; right "yes" kept ≥ 95% |
| 382 | confirm guard: 0.1 never asks "is that right?" about a guess with a vague relation ("other") | 381 | wrong-save turns ≤ 1 on DEV; saved facts not lower by > 2 points |
| 0.2 | 0.1 + every part with a registered PASS by Sept 29 (candidates: gram-360, lis-318 reader, slp-360 scrap + 361 undo, 382) | parts' verdicts | 336 marks on bank C vs 0.1 and twin b |
| 0.2b | one follow-up on bank D | 0.2 | same |
| Sept 30 | report: 6 rows, pass/fail, what 0.2 adds over 0.1 | 0.2 | counts only |
| 0.3 (Oct) | trained reasoner joined (after a PASS), sleep practice school on, creative as a tool call | reasoner + sleep lanes | beats twin on two-step asks by +20 |

## Tonight (Ben asleep; no rentals)
- 336b on BensPC (handoff/held/benspc-336b.md, waiting for the director's slot); verify when it lands.
- Banks C and D being written blind into /mnt/project-files/escrow-331/C and D; blind audit after.
- 381 harness check built and tested on DEV only.

## Honest limits
Memory (57% saved, 22% right) is the biggest gap, and it belongs to the reader, not the joining. Reasoning and
creative will not pass by Sept 30: no learned reasoner has passed yet, and the 1B writes the creative replies.
The Sept 30 report will say so.
