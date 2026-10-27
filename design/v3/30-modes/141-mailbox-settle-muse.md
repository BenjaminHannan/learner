# 141 — Mailbox settle gate (Muse, 2026-09-22)

## Problem

Exp 135's regression soak showed one wrong reply in 2000 turns
(`artifacts/fable-fix135-20260922/marks135/soak-report.json`, turn 238:
"What is SoakP038's city?" → "I didn't catch anything."), unreproduced on
re-run: intermittent under load. Diagnosis: `Daemon.run`
(`scripts/fable_daemon74_run.py`) serves every inbox `*.txt` the moment it
appears, but writers use non-atomic `write_text` (create file, then write
bytes). A poll landing in the gap serves a 0-byte file, and the empty turn
is answered "I didn't catch anything." — a wrong reply on a non-empty
message that can also poison the notebook (a served prefix like "FixV0"
gets stored and breaks later asks, as the R1a runs show).

## The one change

`scripts/fable_daemon141_settle.py` (new; nothing existing edited): serve a
mailbox file only when settled — (A) non-zero size with identical (size,
mtime_ns) across two consecutive polls, or (B) first observed ≥ 2.0 s ago.
(B) gives truly-empty messages the existing "I didn't catch anything."
reply exactly once, after the grace. `SettleGate141` is pure observation
(stat only, per-name first-seen + last-key, pruned each poll); the daemon
subclass keeps `process_file`, the outbox/done protocol, heartbeats, idle
ticks and STOP byte-identical (its `run()` mirrors D74's with only the
file-selection line changed). In-process callers (`process_file` direct)
bypass the gate, so p2/p4-style suites are unaffected by construction.

## Composition with exp 108

`CombinedSettleExactlyOnce141Daemon` layers 108's receipts +
`boot_reconcile` (read-only import) over the settle daemon: reconcile drops
the loop.inbox crash artefact and finishes interrupted moves for
already-durable replies without re-execution; receipts audit each durable
reply. R4 shows 12 aimed kill-9s → 12/12 replies, one turn event each,
0/0/0, with reconcile + receipt lines in the logs.

## Evidence and limits

R1a reproduces the race on demand (2–4 empty-serves + truncated-value
serves per 300 msgs unpatched). R1b (3000 msgs, patched): 0 empty-serves,
but 82 wrong / 93 dupes from two-chunk writes whose inter-chunk pause
exceeds two polls — the specified rule serves the stable-looking prefix,
and the writer's next chunk recreates the moved file. Any poll heuristic
has this hole; multi-stage writers must write atomically. R3: all 128
suite verdicts and 64/64 p2 reply texts identical to sealed loop134; added
p50 latency measured +59 ms vs the ≤ 50 ms bar (confounded: patched
notebook held 3000 turns vs 300, plus run jitter) — recorded as FAIL on
its face. Cost by construction is ~one poll per turn; nothing else
changes.

## Plug points

Drop-in `--agent scripts/fable_daemon141_settle.py` anywhere loop134's
agent is used (`--combined` for kill-9-prone deployments); `--grace` tunes
the empty-message wait; `--daemon --dir --config` CLI mirrors loop134.
