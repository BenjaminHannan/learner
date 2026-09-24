COMMON RULES (the notebook thread, Claude, wrote this task on 2026-09-24). Same COMMON RULES block as handoff/queue/talk-f0-base.md: read its first 14 lines and follow them in full (additive only, fictional names, never the repo-root notebook/, uv run python, report format, getting files with git show origin/main:<path> and git show origin/builder-outbox:<path>).
GPU: no (Mac CPU only).
TIME CAP: 150 minutes in total. Test dirs live under /tmp/nb323/ (never inside the repo). Delete them at the end.

EXP nb-323: a durable, hash-chained turn log. CPU only. ONE change, on the verified 274 base: scripts/claude_loop274_agent.py on origin/builder-outbox (build_agent274, Loop274Daemon), read-only. It is needed for the month-end 3-day restart test (design/v3/30-modes/330-month-end-plan.md, 330c).

PROBLEM (the notebook thread checked this in the code):
- Premonition has two turn logs today, and neither survives a crash or a sleep intact.
- (a) The daemon's daemon.log.jsonl (scripts/fable_daemon74_run.py:93-96 _append_log; record built at scripts/fable_loop102_agent.py:411-424):
  - flush only, no fsync;
  - no hash chain;
  - the turn text is cut at 200 characters and the reply at 500;
  - it is written only in daemon mode, not when a harness calls loop.turn().
- (b) The loop's experience list in state.json (scripts/fable_agent_loop.py:262-275, 331):
  - it is emptied by every accepted sleep (:387);
  - it has no replies.

THE CHANGE: a NEW file scripts/claude_nb323_turnlog.py, built on log (a): the same record fields as daemon.log.jsonl, made durable.
- class TurnLog323(path).
  - Appends one JSON line per record: fsync, then read-back before returning (the same pattern as scripts/fable_notebook_contract.py:164-178).
  - Hash chain: each line carries prev = sha256 of the previous line, starting from the contract's GENESIS.
  - Opening verifies the whole chain. A torn final line is reported and set aside with repair_torn_tail(), as in the contract. Any other broken link raises an error.
  - Nothing ever rewrites or deletes a line, and sleep never touches the file.
  - Reader: read_turns(path) returns the records in order, plus a list of interrupted turns (a BEGIN with no END).
- Records:
  - BEGIN, written before the inner turn runs: n, prev, kind, turn_id, t (UTC ISO), full text.
  - END, written after the reply exists: the same turn_id, the full reply lines, and the daemon.log fields (records, ears_stage, ears_score, new_fact_ids, new_entities, turn_count, notebook_events before and after), mode, and deaf_s from 274's deaf_log274 when present.
  - No truncation anywhere.
- install_turnlog323(loop, path): wraps loop.turn as it is at install time, so the month-end joiner installs it LAST and it captures the final reply. Replies are returned unchanged. daemon.log.jsonl keeps being written exactly as before.
- build_agent323(cfg) = build_agent274(cfg) plus install_turnlog323 with the log at <state_dir>/turns323.jsonl. Loop323Daemon = Loop274Daemon with the same install.
- Short design note: design/v3/30-modes/323-turnlog-muse.md.

SEAL FIRST: artifacts/claude-nb323-20260924/PASSMARKS.md (the marks below, verbatim) and SEAL.sha256.txt (the new .py files plus PASSMARKS.md), before any registered run.

MARKS:
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

OUTPUT: artifacts/claude-nb323-20260924/RESULTS.md and results.json. Verdict first, then integer counts, every miss, every deviation, and the plain-English meaning.

PUSH: scripts/claude_nb323_turnlog.py scripts/claude_nb323_test.py design/v3/30-modes/323-turnlog-muse.md artifacts/claude-nb323-20260924/PASSMARKS.md artifacts/claude-nb323-20260924/SEAL.sha256.txt artifacts/claude-nb323-20260924/RESULTS.md artifacts/claude-nb323-20260924/results.json
