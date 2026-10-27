# lis-320 ADDENDUM-8: pilot 5 verdict and the one change (narrow the group-speaker "me and" words); pilot 6
# (written before pilot 6 exists; no lis-320 training row or reader read exists)

Written 2026-09-27 00:04 UTC by the reading thread.

## Pilot 5 verdict: FAIL on PILOT-THRESHOLDS item 1 (one family under 40%); everything else passed
Pilot 5 (builder-outbox artifacts/claude-lis320-20260926/pilot5/, seed 325, 60 dialogs, --variant low, 5 workers,
23:50-23:58 UTC 09-26, check_we):
- Route: 60 of 60 called, 55 parsed (mark 54), 0 failed calls (mark 6), rawcheck OK (60 rows).
- Item 1: 327 of 428 turns kept (76%), but someone_else kept 3 of 8 (38%, mark 40%). Every other family is at 60% or
  more (plan 6 of 10, yes_after_ask 11 of 18). The five lost someone_else turns: 2 in unparsed dialogs, 1 no_cue
  ("someone was telling me"), 1 must_missing (the person named only by "hes"), and 1 false drop by ADDENDUM-7's own
  check: bare "me and" matched "someone told me and im just repeating it".
- Items 2-4: lowercase 0.994, missing-apostrophe 0.434, over 20 words 0.398, shapes 100 per 100, write facts in long
  turns 0.529.
- Item 5 (fresh agent, sample rng "lis320-pilot5-read"): 1 of 20 kept labels wrong (K05: "its her favorite food and mine
  too", the user's share is unlabelled). Passes (mark: more than 2). correct_ref: 1 of 9 wrong, a casing error only (owner
  "Mitavia" where the history typed "mitavia"; role word and value right). I read both and agree.
- Report only: 14 of 20 dropped rows were judged over-drops, 6 of the 9 group_speaker drops among them ("we dont see her
  much", "we found out the hard way"). Over-drops cost rows, not labels.

## The one change: bare "me and" / "and me" no longer count as group words
New file scripts/claude_lis320_check_we2.py is check_we with one edit: "me and" and "and me" count only when joined to a
person ("me and my roommate", "Nuroa and me", "my wife and me"), the same rule check_we already used for "and i".
we / our / us / ours / ourselves / we're / we've / we'd / we'll / "both of us" are unchanged, as is every other check.
Check of the check (not evidence; built after seeing these rows): on pilot 5's raw rows it keeps 329 of 428 and
someone_else 4 of 8; on pilot 4's, 345 of 419. The fair test is pilot 6 on fresh seed 326.

## Known, not changed now (one change at a time)
- correct_ref owner casing: the label types the seeder's name ("Mitavia") even when the chat typed it lowercase. It goes
  into DATA.md before training with its count, and is fixed there by a counts-only recasing step only if the Thread
  manager agrees it is a label fix and not a second change.
- Shared-fact gap (ADDENDUM-7 note) and "mine too" shares stay step 2 items.

## Pilot 6 (fixed now, before it runs)
handoff/queue/lis320-pilot6-mac.md: pilot 5's job with seed 326 and claude_lis320_check_we2.py in place of check_we.
Pass marks are ADDENDUM-7's, unchanged. If it passes, the full run (seed 324, glm_oclow, check_we2) is queued in chunks.
If it fails, one thing changes, it is named, and the pilot re-runs on seed 327.
