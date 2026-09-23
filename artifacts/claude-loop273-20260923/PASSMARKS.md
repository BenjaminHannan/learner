# Exp 273 — PASSMARKS (sealed 2026-09-23, before any run)

Listen-before-sleep on the 292t base. ONE change only: the loop's step()
order becomes inbox -> sleep_due -> work_queue -> thinking (292t inherits
sleep_due -> inbox -> work_queue -> thinking from
scripts/fable_agent_loop.py, which delays a waiting user turn by a whole
sleep tick). New files only (scripts/claude_loop273_agent.py provides
build_agent273 + Loop273Daemon, built exactly like 292t with the order
installed as a wrapper on the built loop object); no existing file is
edited; reader/ear stages untouched. CPU only (GPU: no).

## M1 — order test (scripts/claude_loop273_test.py)

Fresh loop with sleep_due() forced True AND one user message in the inbox;
the first step() must be a listening tick. 20 seeded cases.

- Bar: 273 20/20 listening first. 292t comparison arm: report its number
  (expected 0/20: sleep first).

## M2 — no starvation (scripts/claude_loop273_test.py)

Sleep due + a stream of 1 user message per tick for 10 ticks, then an
empty inbox; sleep must run within 3 ticks of the inbox emptying.
20 seeded cases.

- Bar: 273 20/20. 292t numbers reported for comparison.

## M3 — no behaviour change on the verified 292t panel

Rerun the 292t blind join panel with 273: same panel file, same runner
(scripts/claude_join292t_run.py) and same scorer
(scripts/claude_join292t_score.py) the talking line used
(artifacts/claude-joinpanel292t-20260923, seal checked read-only), 273 in
the 292t slot, the other four arms byte-identical reruns, scored once.

- Bar: every score identical to 292t's recorded one: agreement 90/90,
  0 overlaps, 0 wrong (0 moved turns, 0 old-sheet hits), same per-category
  agreement, same mechanical owners, verdict PASS. Any change = FAIL.

## M4 — 0 new wrong saves anywhere in M3

- Bar: 0 question-turn writes and 0 smalltalk-turn writes on 273, 0 store
  diffs 273 vs 292 (same as recorded: all empty).

## What would prove it wrong

Any M3 score change, or M2 starvation (sleep later than 3 ticks after the
inbox empties, any case).

## Verdict rule

PASS only if M1–M4 all hold.
