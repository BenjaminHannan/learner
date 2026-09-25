# 336b: the one follow-up to 336 (month-end line). Marks fixed 2026-09-25 ~01:20 UTC, before any run on bank B

Ben 00:56 UTC 2026-09-25 (answering the plan in the month-end thread): "just run the thing".

## The one change
Arm **G** = 330c + the gram-360 slot finisher (scripts/claude_e2e360.py:build_360; scripts/claude_gram360.py). It
rewrites only the rule agent's fill-in lines (capital names, no raw relation keys or underscores, "a"/"an", "?").
Why this change: 336 M7 grammar was 87.0% / 55.9% vs a 99% bar, and the graders split mostly on those lines
(VERIFY-336.md). The grammar thread owns gram-360 and tests it on its own bank G (artifacts/claude-gram360-20260925);
336b is the end-to-end check. G counts for the Sept 30 conversation row only if gram-360 also passes its own marks.

## Environment fix (both P and G; not a change to the agent)
Sleep's learning needs artifacts/fable-reasoner44-20260921/runs/base-seed4102.pt, which is not in git; in 336 it was
most likely missing, so sleep learned nothing (VERIFY-336.md addendum). On the rental it is rebuilt with the sealed
script (`fable_reasoner44.py --stage base --seed 4102`, ~30 s CPU) and every arm runs under
scripts/claude_sleepcheck_wrap.py with SLEEPCHECK_STOP=1, which stops the arm if the file is missing at any sleep
and logs every sleep (run/sleep_<arm>.jsonl). Local check (2026-09-25): the rebuild takes 33 s; final loss
0.00012316 vs the original run's 0.00012317.

## Arms (bank B, artifacts/claude-e2e331-bankB-20260925, 40 lives, once)
- **G** = 330c + gram-360 (the registered arm; marks below apply to G).
- **P** = 330c as sealed for 336 (control, report only): the same agent as 336 but with sleep able to learn.
- **T** = twin b (plain MiniCPM5-1B, thinking off, whole chat). Needed for M6.
- **B** = 292t (old base). Needed for M8c.

## Marks
M1-M11 exactly as artifacts/claude-e2e336-20260924/PASSMARKS.md (same bars, same judging protocol, same scorer
scripts/claude_e2e336_score.py, same judge packet builder artifacts/claude-e2e336-20260924/judges/judge_prep336.py
with new seeds 3361/3362 for the grammar packets and 3363 for the pair order), applied to arm G. M11 is measured on
the rented GPU, as in 336.

Extra marks (G vs P; each grammar packet holds the union of G's and P's distinct replies plus the 80 planted lines, and graders are never told which arm a line came from):
| Mark | What | Bar |
|---|---|---|
| B1 | M7 share for G minus the same share for P, each valid grader | >= +5 points on both |
| B2 | sleep learned in P and G: every sleep log row has checkpoint_exists true, and the rows with attempted true | 0 missing; attempted >= 1 row per arm |

Report only: every scorer count for G and P side by side, since the finisher should change no memory result (the
1B samples, so small differences can be noise; any difference is listed, with the turns' kinds);
every scorer count for all four arms; G vs P and P vs 336's P on each mark (the effect of sleep
actually learning, not a registered claim since bank A and B differ); the sleep log counts (attempted, installs).

## Proved wrong
If B1 fails (G's grammar not at least 5 points above P with both graders), rendering the fill-in lines is not what
holds whole-reply grammar down, and the next grammar change should target the 1B's replies or the reader's frames.

## Addendum 2026-09-25 ~02:35 UTC, before any run: moved to BensPC
Ben asked for tonight's GPU work on his own PC (no rentals tonight). The run moves from a rented 5090
(handoff/held/rent-336b.md, never run) to BensPC's RTX 5070 Ti (handoff/held/benspc-336b.md, slotted by the
director), with a one-life DEV smoke first (Windows has never run the joined agent end to end). M11's speed marks are
measured on BensPC, the machine the plan named. scripts/claude_sleepcheck_wrap.py now also loads the Windows
`resource` stand-in (scripts/winshim), as claude_twinb_wrap.py does; SEAL-code updated for that one file. No mark,
bar, arm or bank changes.

## Correction 2026-09-25 ~02:35 UTC
The move above did not happen: the watcher had already launched rent-336b at 01:42 UTC (before the move commit), so
336b runs on the rental under the task and seal as they stood at launch. benspc-336b stays held and runs only if the
rental fails without writing run/ (director, 02:22 UTC). M11 is therefore measured on the rented GPU, as in 336.
