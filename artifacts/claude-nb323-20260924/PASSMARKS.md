# Exp nb-323 — PASSMARKS (sealed 2026-09-24, before any run)

A durable, hash-chained turn log. CPU only (GPU: no; Mac CPU). ONE
change, on the verified 274 base (scripts/claude_loop274_agent.py on
origin/builder-outbox: build_agent274, Loop274Daemon; read-only): a NEW
file scripts/claude_nb323_turnlog.py (TurnLog323, read_turns,
install_turnlog323, build_agent323, Loop323Daemon). Needed for the
month-end 3-day restart test (design/v3/30-modes/330-month-end-plan.md,
330c).

Problem (checked in the code): Premonition has two turn logs and neither
survives a crash or a sleep. (a) daemon.log.jsonl: flush only, no
fsync, no hash chain, turn text cut at 200 chars and reply at 500,
daemon-mode only. (b) The experience list in state.json: emptied by
every accepted sleep, no replies.

The change: BEGIN before each turn runs + END after the reply exists,
same record fields as daemon.log.jsonl, full text and reply, fsync +
read-back, GENESIS hash chain, torn-tail repair; installed LAST around
loop.turn so it captures the final reply. Replies unchanged;
daemon.log.jsonl written exactly as before.

Test dirs live under /tmp/nb323/ (never inside the repo). All names and
turn texts in the test are invented. The sealed panel is run once for M1
only (same runner, scorer and gold as 274), never read item by item.

## Marks (verbatim)

- M1 no behaviour change: run the 292t/273 panel exactly as 274 ran it (same runner, scorer and gold; see artifacts/claude-loop274-20260924/ and handoff/queue/274-build.md) on build_agent323. Scores must be identical to 274 (90/90, 0 overlaps, 0 wrong). Replies and notebook stores must be byte-identical to 274 on every turn. Any change is a FAIL.
- M2 complete across restarts and sleeps:
  - Use 20 seeded dev dialogs you write yourself: fictional names, 30 turns each, teaches, questions and small talk.
  - Each dialog has 2 kill-free restarts (rebuild the agent on the same state_dir) and 2 sleeps. Force the sleeps with a sleep_threshold small enough that sleep runs, and report that threshold.
  - The log must hold exactly one BEGIN and one END per turn, in order, with the full text and reply matching what turn() returned: 600/600.
  - 0 records lost to sleep or restart.
- M3 crash: 30 SIGKILLs at random moments while turns run (loop mode). On reopen:
  - 0 turns whose reply was returned are missing an END;
  - 0 duplicate ENDs;
  - 0 failed opens;
  - every interrupted turn is listed by read_turns (report the count).
- M4 tamper: 20 copies of a finished log, one byte changed at a random offset in each, outside the final line. 20/20 are caught on open.
- M5 cost, report only: per-turn overhead (median and max ms), and the time to open a 10,000-turn log.
- Proved wrong by any M1 change, any lost END, or a missed tamper.

## Verdict rule

PASS only if M1–M4 all hold (M5 reports only).
