# 207 — Atomic inbox writes in the test harness (driver-only)

## Problem
Exp 192's registered soak showed 41 wrong vs 40 predicted: a first teach
answered "I didn't catch anything." The suspected cause is the harness
writing inbox files with plain `write_text` while the daemon polls the
same directory — a poll landing between file creation and content write
serves a 0-byte file.

## Daemon pickup (read before building)
- `D74.Daemon.run`: serves `sorted(inbox/*.txt)`.
- loop138i's actual loop is `Loop138bDaemon.run` (inherited through
  138f/138g/138h/138i): serves only *settled* files — `*.txt` minus
  dotfiles minus any name containing `.tmp`, plus the 141 settle gate
  (non-zero + stable across two polls, or first-seen >= 2.0 s ago).
- Temp name the daemon ignores: `<final>.tmp<PID>.<counter>.207` —
  ignored twice (no `.txt` suffix for the glob; contains `.tmp` for the
  filter). Same convention as `D74._atomic_write` and
  `Loop138bDaemon.atomic_write_text`.

## Change (harness only, additive)
`scripts/fable_atomic207.py` monkeypatches `Path.write_text/write_bytes`
at runtime for targets under any dir named `inbox`: write temp, fsync,
`os.replace`. Covers marks123_all.py:159,186,243,413 + soak/kill paths
and redteam110_runner.py:178,184 + burst200. Runners, agent, config, and
cases are untouched (sealed); the daemon subprocess is never patched.
A scorer writes `analysis207.json` per run: lost / doubled /
didnt_catch_nonempty / empty_serves (daemon-log turns with empty
turn_text for non-empty sends — the half-read signature) / patched_writes.

## Evidence
12 registered runs on loop138i: soak-2000 x3 patched + x3 control, rt110
x3 patched + x3 control. All soak: 0 lost/wrong/doubled/empty. All rt110:
0 empty_serves, 0 harness errors; 2 abstain-bit replies (R4 first-name
ask, S6 two-sentence turn) byte-identical across all 6 runs with complete
turn_text in daemon logs — agent behavior, not race. Verdicts identical
patched vs control (A3). Seal 6/6 OK post-runs.

## Conclusion
The patch is correct and inert, but the control never raced: the settle
gate already masks the flake, so this test is underpowered and the
hypothesis stands untested. Recommendation: adopt the wrapper (free,
zero-risk) and, to actually test the hypothesis, re-run against a
no-settle daemon or a fault-injection harness that delays writes
mid-byte. No agent change was made or is proposed.
