# Exp 206 RESULTS — sleep smoke mark for merges: PASS (3/3)

Live sleep now has a one-line check, and both merges pass it: loop138i and
loop138h each install `maternal_grandmother` from 20 episodes and answer 5/5
new-people probes, exactly 145's numbers. **MARKS S1–S3 PASS, 3/3. Ledger
P206sleep.1–P206sleep.4 all TRUE.** Seal 7/7 OK after the runs; no post-seal
edits. New files only: `scripts/fable_sleepsmoke206.py`, this folder,
`design/v3/30-modes/206-sleepsmoke-muse.md`.

## Why this exists

The all-marks runner forces `sleep_threshold = 100000` and its SLEEP suite
always reports SKIP/PASS, so no merge ever ran live sleep. This harness
drives the frozen exp-104 world (seed 1: 50 teaches, 20 episode asks,
5 fillers, 5 new-people probes, +1 broken-chain probe) through a fresh
daemon of any agent+config with `sleep_threshold` = 75, in an isolated
scratch dir (repo-root notebook/ never touched).

## Marks (every seed/case reported, never averaged)

| mark | result |
|---|---|
| S1 loop138i seed 1 | PASS: sleeps 1, installed (episodes 20, `sleep145-words.json`), probes 5/5 right 0 wrong 0 abstain, broken-chain (Q99) abstains, taught 50/50 dupes 0, overwrote 0, 98.9 s |
| S2 loop138h seed 1 | PASS: identical numbers (sleeps 1, installed ep 20, 5/5 right, Q99 abstains, taught 50/50, ow 0), 208.4 s |
| S3 budget | PASS: max run 208.4 s < 300 s, Mac CPU, OMP=1/MKL=1, idle_seconds 30 |

Probes answered from sleep-derived rows (report_rows_sleep_derived 1 each).
Gate evidence (OOF/agreement) lives in the daemon sleep log, not the 145
word file, so the driver reports those fields as None — install quality is
proven by the 5/5 probes instead. Pilots (pre-seal, deleted) matched the
registered runs.

## Reproduce (the one-line command future merges run)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_sleepsmoke206.py --agent <agent-script> --config <config-json> --root <scratch-dir> --report <out.json> --label <name> [--idle-seconds 30]

Seal check: `shasum -c artifacts/fable-sleepsmoke206-20260922/SEAL.sha256.txt`
(7/7 OK). Ledger `P206sleep.*` (suffix: bare `P206` was taken by ears).

## Deviations

- D1 (naming): ledger predictions use `P206sleep.*` because bare `P206`
  already exists; PASSMARKS notes this.
- D2 (driver detail): word-file OOF/agreement fields reported None (145
  format stores episodes/logits/report_fid only); marks do not depend on them.

## What it means

Both merges carry a working live-sleep path: sleep fires, the 145 recipe
installs, new people are answered right, unknown people get an honest
"don't know", and no taught fact is overwritten.

## What it does not mean

One clean seed only — noise/crash cases (Z4/Z5) and grown-slot words are
not covered; this smoke test does not replace the full 104/145 suites.
