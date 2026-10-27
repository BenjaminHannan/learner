# Exp 206 PASSMARKS — sleep smoke mark for merges (sealed before any registered run)

Harness addition only. New files: `scripts/fable_sleepsmoke206.py`,
`artifacts/fable-sleepsmoke206-20260922/`, `design/v3/30-modes/206-sleepsmoke-muse.md`.
No agent script, config, or sealed file is edited. Agent code sealed by hash
alongside the marks (loop138h/loop138i agent scripts + both configs).

## World (frozen in cases206-seed1.json)

The exp-104 world verbatim via `fable_sleep104_drive.build_turns` (seed 1,
noise 0): 50 mother teaches, 20 `maternal_grandmother` episode asks on train
kids, 5 fillers, 5 new-people probes on test kids (T01–T05, never asked
pre-sleep), plus one broken-chain probe `Who is Q99's maternal grandmother?`
(Q99 never taught). Fresh daemon per run in an isolated scratch dir
(state_dir = run dir; repo-root notebook/ never touched). Scratch config =
base config with `state_dir` + `sleep_threshold` = 75 (log full exactly at
the last filler, as in exp 104) + all `sleep*_seed` = 1. Daemon launched with
`--idle-seconds 30`. `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`, Mac CPU, offline.

## Expected numbers (copied exactly from exp 145's sealed wave-report-104.json)

Seed 1/2/3 on 145: installed True, episodes_at_install 20, probes 5/5 right,
0 wrong, 0 abstain, taught 50/50, dupes 0, sleep_overwrote_taught 0,
wrong_install False, sleeps_logged 1, report_rows_sleep_derived 1.

## S1 — loop138i + loop138i-config.json, seed 1

S1 PASS iff: sleeps_logged >= 1; installed True with episodes_at_install 20;
new-people probes 5/5 right, 0 wrong; broken-chain probe verdict abstain
(honest: no invented grandmother); taught 50/50 with dupes 0;
sleep_overwrote_taught 0; run < 300 s. If 138i does NOT reproduce 145's
numbers, that is the finding: record a registered FAIL with one diagnosis
note, never patch the agent.

## S2 — loop138h + loop138h-config.json, seed 1 (parity)

Same bars as S1.

## S3 — budget

S3 PASS iff each registered run (S1, S2) < 300 s wall-clock Mac CPU.

## Fail protocol

Any missed bar is recorded FAIL with one diagnosis note, never re-run into
a pass. Ledger predictions `P206sleep.1–P206sleep.4` appended before the run
(`P206` bare already taken by the ears wave; suffix keeps it unambiguous);
outcomes appended after in a new line. Claims never exceed evidence. Every
seed/case reported, never averaged.
