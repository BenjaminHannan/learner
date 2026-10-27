# Exp 74 RESULTS — persistent agent daemon (2026-09-22)

## Result

SELFTEST **PASS** in seeds 1, 2, 3. Every mark held in every seed (integer counts, never averaged).

| seed | D1 teach50/stop/restart/ask50 | D2 kill-9 + restart | D3 100 turns | D4 STOP |
|---|---|---|---|---|
| 1 | PASS 50/50, wrong 0 | PASS 200/200, wrong 0, dupes 0, replied-before-kill 23, chain clean | PASS 0.40 s, 50/50 | PASS 0.06 s, exit 0 |
| 2 | PASS 50/50, wrong 0 | PASS 200/200, wrong 0, dupes 0, replied-before-kill 21, chain clean | PASS 0.25 s, 50/50 | PASS 0.06 s, exit 0 |
| 3 | PASS 50/50, wrong 0 | PASS 200/200, wrong 0, dupes 0, replied-before-kill 21, chain clean | PASS 0.28 s, 50/50 | PASS 0.05 s, exit 0 |

Dev checks (not registered marks): planted torn last line -> daemon repaired it, kept the
bytes in `notebook/torn-tail.txt`, reported `torn_tail_found_and_repaired: true`, continued
with the intact prefix. Tampered middle line -> daemon refused to start, reporting the exact
line (`line 3: hash chain broken`), exit 1. In the 3 registered D2 kills the crash landed
between turns, so the "chain verifies" branch was exercised; the torn branch is covered by
the dev check plus the notebook contract's own c29 suite.

## What it means

The agent now survives restarts and kill -9 with zero lost or duplicated taught facts:
the notebook is the only fact store, every reply is written only after the fsynced
notebook append, and reprocessing an interrupted turn is idempotent (same fact -> DUPLICATE_OK,
no new event).

## What it does not mean

This is not yet the always-on PC agent: ears/mouth are still the Fake template pair
(English coverage is one fact pattern + what/is questions), and there is no web,
no sleep-derived knowledge, and no multi-turn clarification across restarts beyond what
the loop's state.json already keeps.

## Deviations

One voided attempt before the registered run (no marks produced): the harness left the
STOP file in the dir across the D1 restart so the reboot exited at once. Fixed spawn() to
clear STOP/heartbeat/status on launch; PASSMARKS.md re-sealed; ledger predictions P74.1-4
were appended before the passing run. No production-code change after sealing run.py.

## Questions for Ben

None. Default used: STOP is a one-shot request consumed by an intentional reboot.

## Reproduce

```bash
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_daemon74_selftest.py
```

Seal: `artifacts/fable-daemon74-20260921/SEAL.sha256.txt`. Design: `design/v3/30-modes/74-persistent-agent-daemon-muse.md`.
