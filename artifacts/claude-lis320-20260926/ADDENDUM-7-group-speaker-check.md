# lis-320 ADDENDUM-7: pilot 4 verdict and the one change (a group-speaker drop check); pilot 5
# (written before pilot 5 exists; no lis-320 training row or reader read exists)

Written 2026-09-26 22:56 UTC by the reading thread.

## Pilot 4 verdict: FAIL on PILOT-THRESHOLDS item 5 (everything else passed)
Pilot 4 (builder-outbox artifacts/claude-lis320-20260926/pilot4/, seed 323, 60 dialogs, --variant low, 6 workers):
- Route: 60 of 60 called, 58 parsed, 0 failed calls, 3.1 minutes; rawcheck OK (60 rows). Marks: >= 54 parsed, <= 6 failed.
- Item 1: 362 of 419 turns kept (86%); lowest family former 20 of 29 (69%); correct_ref 22 of 26 (85%).
- Items 2-4: lowercase 0.994, missing-apostrophe 0.461, over 20 words 0.406, shapes 100 per 100, write facts in long turns 0.53.
- Item 5 (fresh agent, no pilot rows seen before; 20 random kept rows from other families, 20 correct_ref, 20 dropped;
  sample file built with rng "lis320-pilot4-read"): 3 of 20 kept labels wrong (mark: more than 2 trips it); correct_ref 0 of
  20 wrong. I read the three myself and agree. All three are one flaw: GLM worded a one-owner plan fact as shared, so the
  text states a second owner's fact the label leaves out: "Nuroa is a chef and we live in Lotirmoor" (label: Nuroa's city
  only), "Nuroa and me actually live in Junzocombe not Lotirmoor" (label: Nuroa's city only), "our cat is named gani and we
  live in nufimere" (label: leek's cat, the user's city).
- Report only: 13 of the 20 dropped rows were judged over-drops (must_missing firing when a pronoun resolves the person,
  hedge cues in side clauses). Over-drops cost rows, not labels, so they are not changed here (one change at a time).

## The one change: drop turns where the user speaks for a group
New file scripts/claude_lis320_check_we.py runs claude_lis320_check_cr.py's checks unchanged and then drops any turn whose
user text has we / our / ours / us / ourselves / we're / we've / we'd / we'll / "both of us" / "me and" / "and me", or
"and i" / "i and" joined to a person of the dialog or to "my <word>", with reason "group_speaker". Re-run on pilot 4's raw
rows (a check of the check, not a pilot): 344 of 419 kept (82%), 19 turns dropped for group_speaker, lowest family former
69%, and all three wrong rows are dropped. This is the "tighten the checks" branch PILOT-THRESHOLDS item 5 names.
The GLM prompt, the seeds script, the route and every other check are unchanged.

## Pilot 5 (fixed now, before it runs)
handoff/queue/lis320-pilot5-mac.md: pilot 4's job with seed 325 and claude_lis320_check_we.py in place of check_cr.
Pass (all of), as ADDENDUM-6: PILOT-THRESHOLDS items 1-5 (every family including correct_ref at 40% or more of its turns
kept; item 5's hand read by a fresh agent that has seen no pilot rows, 20 random kept rows outside correct_ref, 20 kept
correct_ref rows, 20 dropped; more than 2 of the 20 kept rows wrong fails, and correct_ref is reported on its own with the
same bar); at least 54 of 60 dialogs parsed; at most 6 of 60 dialogs failed or timed out; rawcheck OK.
If it passes, the full run (seed 324, glm_oclow, check_we) is queued in chunks. If it fails, one thing changes, it is named,
and the pilot re-runs on seed 326.
