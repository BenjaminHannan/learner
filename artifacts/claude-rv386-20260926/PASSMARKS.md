# rv-386 pass marks (thought-memory thread, written 2026-09-26 ~02:30 UTC, before any rv-386 test grid was made)

Question: when code already bans a failed move, does ALSO telling the model why that branch failed help it?
Proposed by Ben's reviewer (pasted 02:11 UTC, section 5): ban-only vs ban + note, same bans, 80 fresh grids per seed,
at least 6 more grids in both seeds. Kept, with two corrections from our code (below).
Code: scripts/claude_rv386.py (imports rv-385's sealed search, grids and model wrapper). Sealed below.

## One change
Both arms are rv-385's revert_ban (same grids, same step budget, same visible-rule check, same bans, and the same random
numbers per grid). ban_note adds, before the question, the abandoned paths from that exact grid with their reasons:
"row 2, column 3 = 4: row 2 already has a 4"; "row 2, column 1 = 5: after it, row 2, column 4 had no number that fit".
If the model ignored the prompt, both arms would make identical choices (selftest checks this).

## Corrections to the reviewer's version
1. rv-385's note ("..., it broke the rule") would be fully redundant once the number is banned, so a gain would be
   impossible by construction. The note here carries the reason, including what the current grid no longer shows
   (which later cell got stuck).
2. A proposer near chance cannot use a reason (the reviewer makes the same point for latent restoration). So a gate:
   the model may be used only if its first choices on rv-385's 12 practice grids (seed 9001, ban arm, 60 choices)
   match the solution at least 50% of the time (blind guessing: 20%). `claude_rv386.py gate` measures it and records
   the weights' sha256. The plain MiniCPM5-1B was measured below; the test runs only on a model that passes.

## Test set
Seeds 386101 and 386202, 80 fresh 5x5 grids each, 60 model choices per grid (rv-385's budget).

## Marks (unit = grid; the counts re-check every solved grid as in rv-385)
- PASS: ban_note solves at least 6 more grids than ban in BOTH seeds.
- PROVED WRONG (the reason adds nothing): ban_note solves no more grids than ban in BOTH seeds, OR its share of choices
  that break the rule is higher than ban's in both seeds.
- Anything else: no clear result.
- Compute: the budget is model choices (equal by construction). Prompt tokens are reported for both arms; if ban_note
  uses more than 1.5 times ban's tokens, the report says the note arm used more compute per choice.
- Validity: identical grids in both arms; no grid over 60 choices; the gate result and weights hash are in the log.

## Predictions
- P386.1 For a model that passes the gate, ban_note solves more grids than ban in at least one seed. (Untested guess.)
- P386.2 The plain 1B does not pass the gate (it scored 22-29% first-choice accuracy in rv-385).

The plain 1B's gate measurement is written to GATE-plain-1B.json next to this file (practice grids, not the test).
