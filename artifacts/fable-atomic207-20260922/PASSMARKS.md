# Exp 207 PASSMARKS — ATOMIC INBOX WRITES (driver-only; sealed BEFORE any registered run)

Agent (frozen, no agent change): scripts/fable_loop138i_agent.py
Config: artifacts/fable-agent138i-20260922/loop138i-config.json
Driver (new file): scripts/fable_atomic207.py
Suites: marks123 soak (2000 turns) + rt110, run via the UNCHANGED
scripts/fable_marks123_all.py single-suite path (--workers 2 shape),
idle_seconds=3600. Each suite 3x patched (A1) + 3x control (A2), one at a time.

## Daemon pickup finding (read before building)
- D74.run serves sorted(inbox/*.txt); loop138i's run loop is
  Loop138bDaemon.run (inherited via 138f/138g/138h/138i;
  scripts/fable_loop138b_agent.py settled_files), serving only
  settled files: sorted(inbox/*.txt) MINUS dotfiles MINUS any name
  containing ".tmp", AND non-zero + stable across two polls (rule A)
  OR first-seen >= 2.0 s ago (rule B, D141.SettleGate141).
- TEMP-FILE NAME THE DAEMON IGNORES: `<final-name>.tmp<PID>.<counter>.207`
  (e.g. `s00007.txt.tmp12345.3.207`). Ignored TWO ways: (1) it does not
  end in `.txt` so the `*.txt` pickup glob never matches; (2) it
  contains `.tmp` so settled_files() excludes it explicitly. Same
  convention as D74._atomic_write / Loop138bDaemon.atomic_write_text
  (`<name>.tmp<pid>` + os.replace). Writer fsyncs before os.replace.
- Patched call sites (runtime monkeypatch of Path.write_text/write_bytes
  for targets under a dir named "inbox"): marks123_all.py:159,186,243,413
  + soak send/kill paths; redteam110_runner.py:178,184 + burst200 writes.

## Marks
- A1 (patched, 6 runs): 0 lost / 0 doubled_replies / 0 didnt_catch_nonempty
  (abstain-bit reply on a turn whose case expects a contains-match; soak:
  any abstain-bit reply, all sends non-empty) / 0 empty_serves (daemon log
  turn with empty turn_text for a non-empty send); patched_writes > 0.
- A2 (control, 6 runs): same events counted and reported per run.
  If control shows 0 races in all 3+3 runs, the test is UNDERPOWERED
  (settle gate already masks the race) — reported, not re-run.
- A3: rt110 per-case agent_verdict identical patched vs control (run by
  run); soak wrong-detail classes identical apart from race events.
  No other verdict may differ (driver-only change).
- FALSIFICATION: any lost/doubled/didnt_catch/empty_serve in A1 with
  patched_writes > 0 -> hypothesis WRONG (report + daemon-log evidence).
- Each run < 1500 s wall-clock Mac CPU, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1.
- Ledger P207.1-P207.6 appended before the runs; outcomes in a new line after.
