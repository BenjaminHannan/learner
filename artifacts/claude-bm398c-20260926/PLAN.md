# bm-398c PLAN: the 1B translates, a calendar computes (benchmarks thread, written 2026-09-26 17:16 UTC)

Registered and sealed before the scored run. A 3-question smoke run (not scored, text not read; it counted 2
translations fully read and 1 with no readable date) and a dry run of score, prep and jscore on made-up labels ran
every step. Every LoCoMo number is "after using LoCoMo for development". Nothing is trained. Counts only.

## Why
- bm-398d (blind) found that the plain 1B, given only the right lines, ties Qwen3.5-2B reading the whole chat
  (137 vs 138). So on most questions the gap is finding the line, not reading it.
- Dates are the exception: both are right on only 10 of the 58 date questions. Many dates in a chat are said
  relative to the day they were said ("last Saturday", "two weeks ago").
- Ben's design has the reader only translate, while the reasoner uses tools such as a clock. This tests that split
  on dates. The Thread manager asked for it at 17:00 UTC.

## The one change
- **GC:** the 1B does not answer. It gets the same right lines, laid out as bm-398d's G arm, and copies two things:
  - DATE, the session date written above the message that says when it happened;
  - WHEN, the time words in that message, or "same day".
  The prompt is fixed in the script (TRANSLATE, 40 new tokens, bm-390's LoCoMo system prompt, greedy, CPU fp32).
- **The calendar tool** turns (DATE, WHEN) into a date. It gives a day where the words name one ("yesterday",
  "last Saturday", "3 days ago"), else a span such as "the week before 9 June 2023", "April 2023" or "2022".
  - Its phrase list was written from ordinary English before any LoCoMo evidence line was read for this test.
  - Words it doesn't know stay as they are, with their day: "<words>, said on <date>". If no date can be read,
    the answer is "I don't know".
- **G:** bm-398d's replies. The 1B answers from the same lines with bm-390's prompt (sha256 593466f6…7a9f,
  reused as they are).
- **Disclosed scaffolding:** these 58 go to the calendar because they are LoCoMo's category 2, not because anything
  learned chose it. The learned router that decides when to use the clock is owed, as the Redirect requires. So is
  the reasoner that would call the tool. Here the category stands in for both.

## Blind check
- Arms: G, GC, and Q2 (Qwen3.5-2B, whole chat, bm-390 run2; report only, because it reads the whole chat, not the
  lines).
- bm-398d's INSTRUCTIONS.md, copied unchanged, so judges see the evidence lines.
- Latin square: 3 groups of 58, each holding every question once, with a question's three arms in different groups.
  random.Random(3996) sets the order.
- 3 main Opus judges (one group each) and 1 relabel judge (X1 = the first 20 questions as L0 holds them).
- Each judge works in a private folder outside the repository. Then an independent recount.

## Marks (fixed now; coded in verdict())
- **C1 (more right):** GC's A-count ≥ G's + 8 of 58, with more gained than lost and a two-sided exact McNemar
  p < 0.05.
- **C2 (no harm: confident wrong answers):** GC's D (wrong) count ≤ G's + 3. E ("don't know") may rise: saying so
  is allowed.
- **PASS** = C1 and C2. Anything else is a registered FAIL.
- **Proved wrong:** GC's A-count ≤ G's. A calendar fed by the 1B's copying would then give no more right dates.
- **Report only:**
  - GC against Q2;
  - F1 with the sealed bm-390 scorer;
  - how often the tool read the date and the words;
  - the G-by-GC label table;
  - relabel agreement.

## Predictions
- P1 (50%): C1 passes. Point guess: GC 20 of 58, against G's 10 in bm-398d.
- P2 (75%): C2 holds.
- P3 (45%): PASS.
- P4 (85%): not proved wrong.
- P5 (60%): GC's A-count ≥ Q2's (report only; Q2 reads the whole chat).

## What it leads to
- **PASS:** splitting translation from calculation beats asking the 1B for the date. Next, the same on the whole
  chat, 1B with and without the calendar against Qwen, as a small GPU run. On this CPU a whole-chat prompt takes
  about 3 minutes, which is why it is not here.
  - The learned part owed: the reasoner, or a learned router, choosing when to call the clock. That goes to Sleep
    research and Month-end as a request, not as a rule.
- **FAIL, not proved wrong:** look at the tool counts. If the 1B's copying is the loss (dates unread, wrong
  session), the translation is the weak link. If the calendar's reading is the loss, the phrase list is.
- **Proved wrong:** a clock fed by copied words does not help at 1B. Dates wait for the learned reasoner.

## Files
- scripts/claude_bm398c_clock.py (selftest 10/10).
- The repository gets counts only: RESULTS.md, score.json, the judge key and labels.
- Translations, replies and judge folders stay in the scratchpad.
