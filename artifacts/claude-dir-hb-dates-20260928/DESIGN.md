# Design: can the learned reasoner combine recalled facts? (dates and multi-part questions)

Helper HB, 2026-09-28. Serves Ben's item B on the menu page (Premonition Next Problems). Marks: `PASSMARKS.md`. Labels: **shown** (a file says it), **suggested**, **untested**.

## Why this test (plain words)
- **Shown** (bm-398d RESULTS.md lines 75-76): when the plain 1B is handed exactly the right chat lines, it answers single facts 65.9% of the time, dates 17.2%, multi-part questions 22.6%. The loss is in *combining* the lines, not in finding them.
- Ben's design (goals page): reader -> **learned reasoner** -> talker. Combining recalled facts is the reasoner's job, and it is the shortest road to beating same-size models.
- So the test asks one thing: **hand the reasoner the recalled facts and see if the learned reasoner (not a rule) combines them.** The loop reasoner is the race baseline (2 shared layers, width 512, learned stop, cap 48); its twin is the plain 8-layer net of the same size.

## What one item is
A store of 8-20 recalled facts ("<person> <did something> on <date>", fictional people and activities as anonymous labels, relabelled every item) plus one to three questions. The net writes the answers into blank cells. Grid rows, no absolute positions in the net; every item is re-derived from its tokens by the checker. Details and op list: the docstring of `scripts/claude_dir_hb_kinds.py`.
- **Date questions:** days between two events (before/after), the date N days after an event, days from an event to a given date, which of two came first. Real month lengths, years 2025-2027 (all non-leap).
- **Multi-part questions:** join (who did both A and B), set (what happened in a month), count (per person, per month), and **two or three questions in one item** (right only if every part is right).
- **Bigger stores** (16-20 facts against practice at 6-12) test whether the skill scales.
- **Control:** one plain recall question. If the nets cannot do that, nothing else is read.

## The stand-in and what it means (disclosed)
A code stand-in plays the reader: the facts arrive already split into person, activity and date tokens. That is test scaffolding that isolates the learned part (goals page: allowed). Whether a learned reader can produce those tokens from real chat text is **untested** here. `claude_dir_hb_kinds.py panels` also writes each item as plain English lines with canonical answers so plain 1B/2B models can read the same stores in a later step (a fairer contrast with bm-398d than the numbers quoted above).

## Practice data
Code-made, endless, never repeated, nothing from LoCoMo, MMLU-Redux, GSM8K or LongMemEval, nothing Claude-written or Claude-judged (the text rendering is test-only and the nets never see it). Panel items are dropped from the stream by canonical key (relabelled copies collide). GLM or Luna are not needed for this test; a Luna-worded chat version is a later step (untested).

## The one change and what is held fixed
One comparison: loop vs plain, same practice, same size. Two seeds each. Nothing else varies. The alternatives a failure would point at (a calculator for the arithmetic, another reasoner design) are **not** run here; each would be its own single-change test after a REFUTED verdict.

## Brain check (goals page asks for this on any failure)
People do date arithmetic by anchoring to landmarks ("about three weeks after the wedding") and counting in chunks, and they count on paper when it matters. Suggested reading, not checked: if the loop learns filtering and counting but not calendar arithmetic, the sensible next test is to give it a calculator step (silicon may improve on biology, Ben 16:08 UTC 09-26), still learned in *when* to use it.

## Files
`scripts/claude_dir_hb_kinds.py` (items, checker, baselines, text rendering, selftest, panel writer), `scripts/claude_dir_hb_run.py` (nets, practice, eval; needs torch, not run here), `scripts/claude_dir_hb_marks.py` (dev gate and score), `handoff/queue/hb-dates-a.md` (HELD job), `SEAL-hb.sha256.txt` (hashes of the four sealed files).
