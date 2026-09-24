# 323: a durable, hash-chained turn log (nb-323)

Short design note for the month-end join (330c). CPU only.

## Problem (checked in the code)

Premonition keeps two turn logs and neither survives a crash or a sleep:

- (a) The daemon's `daemon.log.jsonl` (`scripts/fable_daemon74_run.py`
  `_append_log`, record built in `scripts/fable_loop102_agent.py`
  `process_file`): flush only, no fsync; no hash chain; turn text cut at
  200 chars, reply at 500; written only in daemon mode, never when a
  harness calls `loop.turn()`.
- (b) The loop's experience list in `state.json`
  (`scripts/fable_agent_loop.py`): emptied by every accepted sleep, and
  it holds no replies.

## Change (one new file, verified 274 base untouched)

New file `scripts/claude_nb323_turnlog.py`, built on log (a)'s record
shape, made durable:

- `TurnLog323(path)`: one JSON line per record, flush + fsync +
  read-back before returning (same pattern as
  `scripts/fable_notebook_contract.py` `_append`). Each line carries
  `prev` = sha256 of the previous line, from the contract's `GENESIS`.
  Opening verifies the whole chain. A torn final line is reported and
  set aside with `repair_torn_tail()` (contract pattern); any other
  broken link raises. Nothing rewrites or deletes a line; sleep never
  touches the file. `read_turns(path)` returns records in order plus
  interrupted turns (BEGIN with no END).
- Records: `BEGIN` before the inner turn runs (n, prev, kind, turn_id,
  t UTC ISO, full text); `END` after the reply exists (same turn_id,
  full reply lines, the daemon.log fields, mode, `deaf_s` from 274's
  `deaf_log274` when present). No truncation anywhere.
- `install_turnlog323(loop, path)` wraps `loop.turn` as it is at install
  time, so the 330 joiner installs it LAST and it captures the final
  reply. Replies pass through unchanged; `daemon.log.jsonl` is written
  exactly as before.
- `build_agent323(cfg)` = `build_agent274(cfg)` + the install, log at
  `<state_dir>/turns323.jsonl`. `Loop323Daemon` = `Loop274Daemon` + the
  install.

## Crash argument

BEGIN is fsynced before the turn runs; END is fsynced before the reply
is returned to the caller. So any reply the caller saw has its END on
disk; any turn killed mid-flight shows up as BEGIN-without-END
(interrupted), never as a half line (torn tails are set aside on open).
Each turn writes exactly one BEGIN and one END, so ENDs cannot
duplicate; restarts only append, so the chain stays dense per file.

## What it does not do

It does not replace the experience list, change any reply, touch the
notebook, or write `daemon.log.jsonl` differently. Cost is two
fsync+read-back appends per turn (measured in M5).
