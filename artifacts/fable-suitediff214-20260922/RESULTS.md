# Exp 214 RESULTS — shared suite-diff tool (PASS)

One tool, `scripts/fable_suitediff.py`, replaces the 40+ per-merge copies of
`*_suites.py` / `*_marksdiff.py`. It loads any agent generically
(`DEFAULT_CONFIG*` + `build_agent*` + `*Daemon`), runs the frozen suites
in-process with the existing judges (imported read-only), and diffs each
case against the sealed rows of base 138h or 138i (both JSON-array and
JSONL accepted; base files found by name search, so flat and
g1bench/g2frozen layouts both work).

## Marks table (registered runs, every seed/case reported, never averaged)

| mark | run | result |
|---|---|---|
| V1 reproduce (loop138i vs 138i, all suites) | runs/v1 | 0 moves everywhere: rt136 0/145, rt143 0/124, sessions152 0/180 turns, bench 0/800 (4x200), marks123-subset 0 (p4 30, q1, bench 400, rt81 74). rc=0 |
| V2 second base (loop138h vs 138h) | runs/v2 | 0 moves: rt136 0, rt143 0, sessions152 0, bench 0/800. rc=0 |
| V3 positive control (boss-wrapper vs 138i) | runs/v3 | exactly the 13 predicted ids, all reply-only; rt143 0, sessions152 0 |
| V4 time (rt136+rt143+sessions152+bench) | V1 ~34 s, V2 ~51 s | both < 900 s. marks123-subset 30.9 s (reported, no bar) |
| Verdict | PASS | V1-V4 all pass, no diagnosis note needed |

V3 predicted set (written in PASSMARKS before sealing): C077 C078 C081 C082
C089 C095 C098 C099 C122 C129 C133 C136 C144 — registered run matched exactly.

## What it means
Future merges can rerun the frozen suites and diff per case with one command
(see PASSMARKS.md usage line) instead of copying 200-550 lines of driver.

## What it does not mean
It does not prove the agents are correct — only that reruns reproduce the
sealed bases (V1/V2) and that the differ really detects reply changes (V3).

## Deviations / notes
1. Bench protocol is auto-picked per split from the sealed rows' schema
("confirms" key -> v3 driver `run_item_v3`, else v2 `run_item`); without this
the 138i v3-sealed bench shows ~678 false moves under v2. Same judges either way.
2. One pre-seal pilot bench run showed a single rare flake (1 reply-only move
in old_s2fresh_4hop, item bench103-s2fresh-4hop-117, correct->abstain); 4 of 5
pilots plus the registered V1 run were 0-move. No code changed; noted, not hidden.
3. marks123 in the tool is the fast in-process subset (p4, q1, bench, rt81);
rt110/p2/p3/soak are skipped (subprocess-per-case / kill9 / slow) and reported
as such. The stock CLI's own internal FAIL on rt81 (1 bug, 14 unclear) matches
the sealed base, hence 0 diff moves — the tool diffs against the base, it does
not re-grade old bars.
4. No post-seal edits: `shasum -c SEAL.sha256.txt` all OK after the runs.

## Exact reproduce commands
```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_suitediff.py --agent scripts/fable_loop138i_agent.py --config artifacts/fable-agent138i-20260922/loop138i-config.json --base 138i --out <dir> --only all
```
(V2/V3 same with loop138h/138h and wrap214_boss.py/138i respectively.)

## Questions for Ben
None.
