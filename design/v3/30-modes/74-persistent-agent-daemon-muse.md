# 74 — Persistent agent daemon (design)

Status: built and registered-tested 2026-09-22. Artefacts: `artifacts/fable-daemon74-20260921/`
(RESULTS.md, PASSMARKS.md, SEAL.sha256.txt). Code: `scripts/fable_daemon74_run.py` (daemon),
`scripts/fable_daemon74_selftest.py` (marks D1–D4, seeds 1–3). Wraps `scripts/fable_agent_loop.py`
and `scripts/fable_notebook_contract.py` without editing them.

## 1. Goal

The agent as a PERSISTENT PROCESS that survives restarts — the stepping stone to an always-on
agent on Ben's Windows PC (Python 3.10, stdlib + torch + numpy only). This file is portable by
construction: pathlib everywhere, `os.replace` for atomic writes (atomic on Windows and POSIX),
a polling loop only — no fork, no signals, no Unix-only modules. This file imports stdlib plus
the two existing fable modules only, and runs on 3.10+ (no 3.11/3.12-only syntax).

## 2. State lives where (all under one `<dir>`)

- `notebook/events.jsonl` — the ONLY fact store: append-only JSONL with the hash chain, owned
  by the notebook contract. Verified line-by-line on every boot.
- `state.json` — the loop's own state (inbox, experience log, counters, pending question),
  written temp-then-`os.replace` after every tick by `AgentLoop` itself.
- `inbox/*.txt` — one English turn per file; taken in name order. Producers must write
  temp-then-rename so the daemon never reads a half-written turn.
- `outbox/<same name>.txt` — the English reply, written atomically (temp + fsync + replace)
  BEFORE the input is moved. A reply on disk always means its fact is already fsynced.
- `done/` — processed inputs moved here (`os.replace`, so a re-boot never re-reads them as new).
- `heartbeat.json` — pid, boot time, turn count, notebook length, last verified chain hash,
  rewritten every 5 s.
- `daemon_status.json` — the boot verdict: verified chain hash, or `boot_ok: false` with the
  exact broken line. Never silently accepted.
- `daemon.log.jsonl` — every turn, every idle tick, boot/stop/corruption lines.
- `STOP` — drop this file in; the daemon finishes nothing new and exits 0.

## 3. Crash safety (why kill -9 loses nothing replied)

Order per turn: (1) `loop.turn()` appends to the notebook (flush + fsync + read-back inside
the contract); (2) reply written atomically to outbox; (3) input moved to done. A kill between
(1) and (2) leaves the input in inbox, so the reboot reprocesses it — and the notebook answers
DUPLICATE_OK (same taught value appends no new event), so no duplication. A kill inside (1)
leaves a torn last line: the contract flags `torn_tail` on the next boot, the loop repairs it
(torn bytes kept in `notebook/torn-tail.txt`), the daemon reports
`torn_tail_found_and_repaired: true`, and the interrupted turn is reprocessed from inbox.
A kill inside (2) leaves a `*.tmp*` file the next boot deletes. Middle-of-log tampering is not
repairable: the daemon reports the exact line and refuses to start (exit 1).

## 4. Idle behaviour

When no mailbox file is waiting and `idle_seconds` (default 30) have passed since the last
activity, the daemon takes exactly one `AgentLoop.step()` — i.e. the loop's own hooks: the
SLEEP tick when the experience log is full (`Sleeper.sleep`), otherwise the THINKING tick
(`Thinker.think`, or the stub counter when none is plugged in) — and logs it as `idle-tick`.
Stubs change nothing; real hooks drop in through `build_loop()`.

## 5. Where real ears/mouth plug in

`build_ears()` / `build_mouth()` assert the objects satisfy the `G.Ears` / `G.Mouth`
runtime-checked Protocols from `fable_agent_loop.py` (`hear(turn) -> actions`,
`say(record) -> sentence`), then hand them to `AgentLoop`, which already routes every write
through LISTENING and every question through the reasoner. Swapping FakeEars/FakeMouth for the
real pair (agent 1/6's work) touches only these two constructors. Reasoner/Sleeper/Thinker take
the same path through `build_loop()`.

## 6. Launch on Windows (exact command)

```bat
py -3.10 -B scripts\fable_daemon74_run.py --dir C:\Users\Ben\fable-daemon
```

Talk to it with plain files (PowerShell): one turn per file, e.g.
`Set-Content C:\Users\Ben\fable-daemon\inbox\0001.txt "Mira's city is Lisbon."`,
then read `outbox\0001.txt`. Watch `heartbeat.json` for liveness; stop with
`New-Item C:\Users\Ben\fable-daemon\STOP`. No torch/GPU needed for the daemon itself.

## 7. Non-goals / limits

Fake template English only (one fact pattern + what/is questions); no web path, no
sleep-derived knowledge yet; no file locking (single daemon per dir); inbox filenames must
be unique per turn. Registered: D1 50/50 restart recall, D2 200/200 after kill -9 with 0
dupes, D3 100 turns < 1 s (bar was 60 s), D4 STOP in ~0.06 s — 3/3 seeds each.
