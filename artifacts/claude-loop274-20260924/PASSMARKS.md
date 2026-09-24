# Exp 274 — PASSMARKS (sealed 2026-09-24, before any run)

Never-deaf step A on the 273 base (scripts/claude_loop273_agent.py on
origin/builder-outbox, verified PASS; worktree copy byte-identical, diff
empty). CPU only (GPU: no).

Problem (director checked): scripts/fable_agent_loop.py:313-319 turn() =
submit() + run_until_idle(), and busy() includes sleep_due() (line ~290),
so when sleep is due the reply to a turn is only returned after the whole
sleep runs. 273 fixed tick order but not this.

ONE change only, in a NEW file scripts/claude_loop274_agent.py
(build_agent274, Loop274Daemon), built exactly like 273 (same frozen
bases, same listen-first step order inbox -> sleep_due -> work_queue ->
thinking installed as a wrapper on the built loop object; WORK vs SLEEP
order NOT changed — pending ruling for Ben): turn() runs ticks only while
the inbox is non-empty (the listening ticks), returns/writes the reply,
and leaves any due sleep for the next idle tick (the daemon's idle loop /
next run_until_idle). run_until_idle() itself is unchanged outside a turn.
Plus a deaf-seconds meter: for every turn, seconds between the message
arriving and its reply being written; logged per turn on the loop object
(loop.deaf_log274) and summarised (median, max).

No existing file is edited. Reader/ear stages untouched. All names and
turn texts in the test are invented. No sealed panel is read item by item.

## M1 — reply before sleep (scripts/claude_loop274_test.py)

20 seeded cases with sleep forced due (sleep_threshold 5 + 5 prefilled
experience entries, sleep_due() verified True before the turn) and one
waiting message. Both arms carry the same slow stub sleeper (0.5 s per
sleep tick, never accepts, writes nothing) to stand in for a heavy
consolidation sleep. Criterion per case: turn() returns the reply with
zero sleep ticks run (loop counters["sleeps"] still 0, inbox drained).

- Bar: 274 20/20. 273 comparison arm: report its number (expect 0/20:
  273's turn() drains the sleep inside run_until_idle before returning).

## M2 — sleep still happens (scripts/claude_loop274_test.py)

In the same 20 cases, right after the M1 turn() returns, step the loop
(up to 30 ticks) with the inbox empty; the due sleep must run within the
next 3 idle ticks.

- Bar: 274 20/20. Proved wrong if sleep never runs.

## M3 — no behaviour change on the verified panel

Rerun the 292t/273 blind join panel with 274 in the 273 slot: same sealed
panel file (artifacts/claude-joinpanel292t-20260923/panel.jsonl, seal
checked read-only), same runner (scripts/claude_join292t_run.py), same
config (artifacts/claude-join292t-20260923/loop292t-config.json), the
other four arms byte-identical reruns, scored once with the same scorer
(scripts/claude_join292t_score.py) against gold 273 (recorded
artifacts/claude-loop273-20260923/run273/panel-273.json and
panel-score273.json).

- Bar: every score identical to 273's recorded one: agreement 90/90,
  0 overlaps, 0 wrong (0 moved turns, 0 old-sheet hits), same per-category
  agreement, same mechanical owners, per-turn 274 vs recorded 273 90/90
  identical, verdict PASS. Any change = FAIL.

## M4 — deaf meter on the 20 M1 cases

Agent meter (loop.deaf_log274) on the 274 arm vs wall clock around
turn() on the 273 arm, same 20 cases.

- Bar: 274 max deaf seconds < 273 max deaf seconds, and 274 median <= 2 s.
  Report both arms (meter rows + wall rows, median and max).

## What would prove it wrong

Any M3 score change, or sleep never running (M2 finds no SLEEP tick).

## Verdict rule

PASS only if M1–M4 all hold.
