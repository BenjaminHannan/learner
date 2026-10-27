# PASSMARKS — Experiment 141: mailbox settle gate (2026-09-22)

Registered single-change robustness fix for a mailbox race seen in exp 135's
regression run (`artifacts/fable-fix135-20260922/marks135/soak-report.json`:
turn 238 "What is SoakP038's city?" got "I didn't catch anything."; the
director's re-run of the same soak got 0 wrong, so it is intermittent under
load). Diagnosis: `scripts/fable_daemon74_run.py` `Daemon.run` serves every
inbox `*.txt` it sees, while writers use non-atomic `write_text`
(create-then-write); a poll landing in between serves a 0-byte file.

THE ONE CHANGE (`scripts/fable_daemon141_settle.py`, new, prefix-owned; no
existing file edited): a file is served only when settled — non-zero size
with unchanged (size, mtime_ns) across two consecutive polls, OR first
observed ≥ 2.0 s ago (grace; truly-empty messages still get the existing
"I didn't catch anything." exactly once). `process_file`, outbox/done
protocol, heartbeats, idle ticks, STOP path unchanged. `run()` mirrors
D74's with only the file-selection line changed. Composition with exp 108
(`scripts/fable_daemon108_run.py`, read-only import):
`CombinedSettleExactlyOnce141Daemon` = settle gate + 108 receipts +
108 `boot_reconcile`.

Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B ...`; loop134 config
`artifacts/fable-loop134-20260922/loop134-config.json` throughout):

  R1: `scripts/fable_daemon141_stress.py stress` (every inbox message
      written non-atomically on purpose: create, sleep uniform 0–300 ms,
      write, ~30% in two chunks; 6 writer threads; seed 141):
      (a) unpatched agent `scripts/fable_loop134_agent.py`, n=300:
          ≥ 1 "didn't catch anything." on a non-empty message (if 0 in the
          time box, report honestly; the mark is then only R2–R4).
      (b) patched agent `scripts/fable_daemon141_settle.py`, n=3000:
          0 such replies, 0 lost / 0 wrong / 0 dupes.
  R2: `... stress.py empty` with the patched agent, n=24 genuinely-empty
      0-byte files: each gets exactly one "I didn't catch anything." reply
      (0 lost / 0 wrong-content / 0 dupes).
  R3: `scripts/fable_marks123_all.py --agent
      scripts/fable_daemon141_settle.py --config <loop134-config>
      --out artifacts/fable-daemon141-20260922/marks141
      --suites soak,p2,p4,rt110 --workers 4`: per-suite and per-case
      verdicts identical to sealed
      `artifacts/fable-loop134-20260922/marks134/` (soak 0/0/0;
      p2 ok_to_bug [B7,D8], still_bug [B7,C2,C5,D8], bug_to_ok 14 listed;
      p4 PASS; rt110 PASS with still_bug [R4,N6,S3,S6], bug_to_ok [F5,M5]);
      p50 turn latency added by the gate ≤ one poll interval (0.05 s),
      measured in R1 (patched p50 − unpatched p50 on correct replies).
  R4: `... stress.py killburst --kills 12` with the patched agent
      `--combined` (CombinedSettleExactlyOnce141Daemon): aimed kill-9 per
      turn around a non-atomic write window, reboot, no resend:
      0 dup / 0 lost / 0 wrong.
  R5: whole registered wave (R1a+R1b+R2+R3+R4) < 1500 s wall-clock Mac CPU.

A registered FAIL is recorded as FAIL, never re-run into a pass. Every
seed/case is reported, never averaged. Claims never exceed evidence.
