# lis-320 ADDENDUM-10: Luna pilot 7 verdict and the two registered responses; pilot 8
# (written before pilot 8 exists; no lis-320 training row or reader read exists)

Written 2026-09-27 06:03 UTC by the reading thread.

## Pilot 7 verdict (Luna, seed 327, 60 dialogs, 3 workers, 05:18-05:36 UTC): FAIL on PILOT-THRESHOLDS items 1 and 2
- Route: 60 of 60 called and parsed, 0 failed calls, rawcheck2 OK (0 error-like, 0 repeated texts), 17.5 minutes.
- Item 1: 404 of 425 turns kept (95%), but plan kept 2 of 11 (18%, mark 40%): 9 dropped for no_cue. Every other family
  90% or more; correct_ref 22 of 23.
- Item 2: apostrophe-less contractions 0.0 (bar 0.12). Lowercase start 0.8 and turns over 20 words 0.213 pass.
- Items 3-4 pass: shapes 94.8 per 100, write facts in long turns 0.328.
- Item 5 (fresh agent, rng "lis320-pilot7-read"): 0 of 20 kept labels wrong, 0 of 20 correct_ref wrong, 0 casing. It
  judged 20 of 20 drops over-drops (9 of them the plan no_cue drops) and found the texting unnatural: tidy punctuation,
  and long turns padded with remarks about the message ("just putting this here", "this might come out rambly") whose
  hedge words trip the hedge checks.

## Two changes, one per tripped item (a stated departure from one change per pilot)
Each tripped item names its own response in PILOT-THRESHOLDS.md, and they touch different counts. Running them one pilot
at a time would re-run a pilot that is known to fail the other item, so pilot 8 carries both, named here:
1. Item 1, the checks: scripts/claude_lis320_check_we3.py adds the "may" half of the seeder's own plan instruction ("the
   user says this will or may happen in the future") to the plan cues: might, may, someday, some day, one day,
   eventually, in the future, later on, at some point, down the line, sometime. Check of the check (not evidence): on
   pilot 7's raw rows plan goes 2 -> 11 of 11 and kept 404 -> 413; on GLM pilot 6's, plan 11 -> 12.
2. Item 2, the instruction's messiness part: scripts/claude_lis320_luna2.py appends one sentence to the prompt's "How the
   user writes" paragraph (text in its STYLE_ADD): skip apostrophes in contractions, start in lowercase, never talk about
   the message itself. The MUST INCLUDE rule is unchanged.
Writer, helper (sha 342a0fb7...), seeds script, other checks, rawcheck2 and every mark are unchanged.

## Pilot 8 (fixed now, before it runs)
handoff/queue/lis320-pilot8-mac.md: pilot 7's job with seed 328, claude_lis320_luna2.py and claude_lis320_check_we3.py.
Pass marks: ADDENDUM-7's, unchanged. If it passes, the Luna full run (seed 324, luna2, check_we3, 70-minute chunks) is
queued. If it fails, one thing changes, it is named, and the pilot re-runs on seed 329.
Known, report only: a group_speaker false drop ("Saia is my wife and I live in Delroby" matches "my wife and I").
