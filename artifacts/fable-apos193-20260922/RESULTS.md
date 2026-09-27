# Exp 193 — missing-apostrophe possessives on loop138h — RESULTS (PASS)

Base: loop138h. One change, ears only, outermost: a token that equals a
notebook name plus a trailing "s" (`kofis`, `Kofis`, `toms`, `Juans`;
also "s'" forms), immediately followed by a known relation, is read as
that name's possessive (`Kofi's city`), silently, then parsed by the
unchanged base. Unknown stems, real plurals, known stems before
non-relations, opinion questions, and already-parsing turns are
untouched. The director probe (`What is kofis city?` -> `I have no
opinions.`) now answers `Kofi's city is Lagos.`

## Marks table (integer counts, every seed/case reported, never averaged)

| mark | bar | number | status |
|---|---|---|---|
| A1 case193 (40 turns) | 40/40 | cap 6/6, ask 14/14 reply==twin 0 writes, teach 6/6 reply+delta==twin, trap 14/14 reply+delta identical | PASS |
| rt136 (145) | 0 moves | counter 136/6/3, moves_vs_138h 0, new_wrong 0 | PASS |
| rt143 (124) | 0 moves | counter 107/7/10, moves_vs_138h 0, new_wrong 0 | PASS |
| sessions152 (180 turns) | 0 moves | moves 0, new_wrong 0, new_writes 0 | PASS |
| bench121 (4x200) | 0 moves | all splits 200 items, moves 0, new_wrong 0 | PASS |
| marks123 (10 reports) | per-case identical except predicted | p2/p3/p4/q1/bench/rt81/soak/q4 SAME; sleep SAME after filename rename; summary SAME after rename+timing; rt110 SAME-semantic (3 statuses-only metadata diffs) | PASS |
| G4 time | each run < 1500 s | A1 11.8 s; suites ~60-400 s each; marks123 395.6 s | PASS |
| seal | 8/8 clean post-runs | `shasum -c SEAL.sha256.txt` 8/8 OK, no post-seal edits | PASS |

Ledger: P193.1 TRUE (40/40) | P193.2 TRUE (0 moves/wrong/writes) |
P193.3 TRUE (0 moves, 0 new wrong) | P193.4 TRUE (identical except
predicted V1+V2) | P193.5 TRUE (0 ask writes; `favourite city`
opinion base-identical) | P193.6 TRUE (max run 395.6 s) | P193.7 TRUE
(seal 8/8, no post-seal edits). 7/7 TRUE. SCORE PASS (A1/A2).

## Deviations (all pre-seal; pilots re-ran on final code)

- D1: first draft dropped `loop.self_forget_log = {}` (copy slip);
  self-routed turns crashed. Fixed pre-seal; A1 re-ran 40/40.
- D2: whole-turn apostrophe veto blocked 2-hop `Kofis boss's city` and
  s'-teaches (inner apostrophe present). Reworked to per-token veto
  pre-seal; A1 re-ran 40/40.
- D3: next-word possessive strip order (`boss'` -> `bos`). Fixed to
  strip lone `'` first pre-seal; 2-hop asks verified OK.
- D4 (registered, predicted V1): rt110 harness `statuses` metadata
  differs on 3 cases (D7/S4/T4; pilot: M1/M3) with identical
  verdict+reply+fact_writes; M1 re-ran 3/3 `["OK"]` on loop193.
  Daemon.log harvest race under parallel load, not behavior.
- Suite-level FAIL bars inherited from 138h unchanged (marks123 p3
  l5z1:F, p4 1 nonpass, rt81 bug-1/unclear-14, sleep SKIP).

## Reproduce (Mac CPU, offline)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix193_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix193_suites.py --only rt136   # rt143|sessions|bench, one at a time
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop193_agent.py --config artifacts/fable-apos193-20260922/loop193-config.json --out artifacts/fable-apos193-20260922/marks193 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix193_comparem.py
shasum -c artifacts/fable-apos193-20260922/SEAL.sha256.txt
```

## Questions for Ben

None.

What it means: dropping the apostrophe on a name the assistant already
knows (`kofis city`, `Toms boss`, `Nadias' mother`) now works exactly as
if typed correctly, including 2-hop asks, with zero change to anything
else.

What it does not mean: the assistant still never guesses unknown names
(`zaras city` still clarifies), and a brand-new relation word never
taught still needs its first teach spelled with the apostrophe.
