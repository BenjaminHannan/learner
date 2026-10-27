# bm-398c RESULTS: the 1B translates, a calendar computes (benchmarks thread, written 2026-09-26 17:30 UTC)

**Verdict: FAIL, and proved wrong.** With the calendar, the 1B was right on 4 of 58 date questions. Answering by
itself from the same lines, it was right on 9. This is registered as sealed (PLAN.md, c318673f6) and does not change.
The independent recount (its own script, key and labels only) agrees on every number. Every LoCoMo number is "after
using LoCoMo for development". Counts only.

## Blind labels (58 date questions, judges see the evidence lines)

| Arm | A right | C partly | D wrong | E don't know |
|---|---|---|---|---|
| G: 1B answers from the right lines (bm-398d's replies) | 9 | 13 | 35 | 1 |
| GC: 1B copies date and time words, calendar answers | 4 | 5 | 17 | 32 |
| Q2: Qwen3.5-2B, whole chat (report only) | 11 | 6 | 41 | 0 |

- **C1 (GC ≥ G + 8 right, p < 0.05): FAIL.** GC minus G is −5. GC gained 3 questions and lost 8 (McNemar p 0.23).
- **C2 (GC wrong ≤ G wrong + 3): holds.** GC's D is 17 against G's 35. But that is only because GC said "I don't know"
  on 32, so it is not a win.
- **Proved wrong: yes** (GC's A of 4 is not above G's 9).
- Relabel agreement is 20 of 20. The G-by-GC table: A→A 1, A→D 2, A→E 6, C→D 4, C→E 9, D→A 3, D→C 5, D→D 11,
  D→E 16, E→E 1.
- Report only:
  - GC against Q2: −7 (gained 3, lost 10, p 0.09).
  - Official F1 (bm-390 scorer, category 2): G 43.86, GC 18.53, Q2 35.10.
  - The first-run judges gave G 9 here and 10 in bm-398d, and Q2 11 here and 10 there, on the same replies.
  - One main judge (group L1) marked a right month and year with a wrong day as C, where the others mostly used D.
    Each group holds every arm on a third of its questions, so this moves C against D equally for all arms. It
    doesn't change any A count.

## Predictions
| Prediction | Held? |
|---|---|
| P1 (50%): C1 passes. Point guess GC 20 | no (GC 4) |
| P2 (75%): C2 holds | yes (for the wrong reason: "don't know" on 32) |
| P3 (45%): PASS | no |
| P4 (85%): not proved wrong | no |
| P5 (60%): GC ≥ Q2 | no (4 vs 11) |

## Where it broke (post-hoc counts, report only; scripts in diag/, written after the verdict)
Both breaks are in the 1B's copying step (translation), not in the calendar's arithmetic.
1. **Format.** On 32 of 58, the 1B never wrote a line starting "DATE:". 31 of those 32 still had a date in a form
   the calendar reads, somewhere in the reply. The label on the line was just different, so the calendar said
   "I don't know". On the 26 where it did write "DATE:", the date was the right session date on all 26.
2. **Time words missed.** On 21 of those 26, the 1B wrote "same day" as the time words. The calendar then gave the
   session date, which was right on 1 of 21. By a rough word-list check, 16 of those 21 evidence lines do hold time
   words such as "last week" or "two days ago".
   - When the 1B did copy real time words (5 questions), the calendar was right on 3 of 3 week, month or year
     spans and 0 of 2 exact days.

So the calendar isn't the weak link. The 1B, prompted to copy, can't reliably find and copy the time words, and it
doesn't follow the two-line format. This is the same finding as bm-398d from another side: the loss is in reading,
not arithmetic.

Brain first (a textbook-level guess, not checked): people don't answer "when did that happen?" by re-reading a
transcript and computing. The time is tied to the memory when it is stored ("that was the week before the trip"),
and it is recalled with the memory. The matching design is for the reader to resolve and store the time when it
saves a note. Silicon can do better than biology here, with an exact calendar date plus a pointer to the raw words.
Then a date question is answered by recalling that stored date, not by the talker reading the chat at question
time.

## What it leads to
- Per the PLAN, "proved wrong": a clock fed by copied words doesn't help at 1B. Dates wait for the learned
  reasoner, or for a learned reader that stores the time with each note. That second option is Reading facts'
  reader, not this thread's; offered to them as a suggestion.
- No re-parse or re-prompt of these 58 is run. Loosening the "DATE:" parser after seeing these counts would be
  tuning on the test, and a prompt or parser change is hand-written rule work that the Redirect stops.
- The disclosed scaffolding (category 2 sends a question to the calendar) is not carried anywhere. The learned
  router or reasoner that would choose the clock is still owed.

## Files
- score.json (F1 and tool counts), jscore.json (blind verdict), judge/key.json (item → question id and arm only),
  judge/labels/*.jsonl (item and label only), diag/*.py (the post-hoc counts above; they print counts only).
- GC run: 58 rows, sha256 15291243…4390, CPU fp32, 405 s, kept in the scratchpad (holds benchmark text).
- Cost $0 (CPU in this container, plus 5 Opus agents: 4 judges and 1 recount).

## Scope and corrections (added 2026-09-26 17:33 UTC, after the Thread manager's check; this header first said 17:37 by mistake)
- **The split, stated plainly.** Of GC's 54 misses (58 − 4):
  - 32 are a format failure: no line starting "DATE:". 31 of those 32 replies still held a date the calendar can
    read. Where the 1B did write the line, it copied the right session date on 26 of 26. So on dates alone, the
    1B's copying was fine. The strict parser plus the 1B's loose format lost these 32.
  - The only support for "the 1B misses the time words" is the other part: "same day" on 21 of 26, of which 16
    have time words by a rough, hand-written word-list check (not blind, not verified). There were 5 real copies
    of time words, and the calendar was right on 3 of them.
  - So "the loss is in reading" above is too strong. The evidence shows a format failure on 32 and a likely
    time-word miss on about 16.
- **What was proved wrong** is prompted copying at 1B, read by a strict parser. It is not "a learned part
  translates and a tool computes", which is Ben's design. A reader trained to emit the time as a field was not
  tested. This mirrors how 358x's verdict was limited to crippled loops.
- **The warning the seal missed.** The only try-out before sealing was a 3-question smoke on the first 3 of these
  58 test questions, not on development items. Its text was not read, and it counted 1 of 3 with no readable
  date. I did not look into why before sealing. A format check on development chats (the code-made chats, for
  example) would likely have caught the missing "DATE:" labels. Lesson: before sealing a prompted format, count
  format compliance on development items, and keep the smoke off the test items.
