# Exp 164 RESULTS — read-only about-stage on loop150 (Muse, 2026-09-22)

One change: a read-only ears stage checked first in `hear()`. "What do you
know about X?", "Tell me about X", "What have I told you about X?",
"Anything about X?", and bare "What do you know?" are answered from the
notebook only (subject-side then value-side active taught facts, max 8,
then "and N more"; unknown X reuses the existing "I don't know anyone
called X."; bare asks report live counts). Clarify actions only: 0 writes.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar | result |
|---|---|---|
| T1 probe (44 dialogues) | 44/44 exact/identical | run-1 FAIL 42/44 (recorded); open re-run 44/44 OK (A 22, B 7, C 4, D 11) |
| T2 must-cases | 33/33 exact, 0 writes on 34/34 about-turns | 33/33, 34/34, 0 wrong writes (open re-run) |
| G1 bench (600 items) | 0 moves, 0 new wrong | 600/600 verdict+reply identical, 0 new wrong (65.3 s) |
| G2 marks123 (10 reports) | 0 per-case moves | 0 mark-moves; 1 diag-only flake R4 (below) |
| G3 sessions (180 turns) | 0 diffs, 0 new WRONG/writes | 0/0/0 (6.4 s) |
| G4 time | every run < 1500 s | probe 5.9 s, bench 65.3 s, marks 276.4 s, sessions 6.4 s, rt110-open 82.7 s |

## FAIL + post-seal edits (all reported, nothing silent)

1. Probe run-1 (sealed code): 42/44 FAIL. A17 — literal values mint no
   entity, so "What do you know about Paris?" missed the value side the
   sealed spec already required ("every stored fact with X as value").
   A22 — sealed case typo (`ask_idx` 1 vs 2). Fix: value side now also
   matches normalised literal values; typo fixed. Files changed
   (SEAL.sha256.txt kept as sealed):
   `scripts/fable_fix164_about.py` 088d48…→c0a2c2…, `cases164.json`
   5a65b6…→6eebf5….
2. G2 attempt stalled twice in p3 with `AttributeError: 'Loop164Daemon'
   has no attribute 'idle_seconds'` — my daemon `__init__` dropped the
   line the base sets; spawned `--daemon` subprocesses crashed on boot
   (probe/bench/sessions use `process_file`, unaffected). Fix: one line
   added (`scripts/fable_loop164_agent.py` 04e58c…→45977b…). G2 full run
   then completed on the final file; probe/bench/sessions re-run on the
   final file in the open (all green above).
3. `scripts/fable_fix164_marksdiff.py` reporting refinements only (exempt
   volatile `seconds`, sleep agent-name strings, diag-only log/reason
   class): no agent change, no mark content change.
4. rt110 R4 registered run: verdicts identical (BUG=BUG) but msg_00 read
   empty ("I didn't catch anything.") shifting the turn log — the known
   mailbox transport race under load ~150. Open re-run: 62/62 per-case
   identical, 0 moves. Both reported per the race clause.

## Deviations

- Near-miss classification (frozen pre-seal in PASSMARKS): unknown-X
  about-shapes (incl. "…about cooking?") return the base's existing
  unknown-entity sentence and score as unknown-X must-cases; near-misses
  are turns the stage provably passes through, machine-checked
  byte-identical loop164 vs loop150.
- G4 bar used: < 25 min (1500 s) per the task brief (brief-48 says 30
  min; task says 25 min; met the tighter one).

## Reproduce (from worktree root; env per PASSMARKS)

`python -B scripts/fable_fix164_probe.py` (5.9 s) ·
`python -B scripts/fable_fix164_bench.py` (65.3 s) ·
`python -B scripts/fable_marks123_all.py --agent
scripts/fable_loop164_agent.py --config
artifacts/fable-about164-20260922/loop164-config.json --out
artifacts/fable-about164-20260922/marks164 --workers 4` (276.4 s) ·
`python -B scripts/fable_fix164_marksdiff.py` ·
`python -B scripts/fable_fix164_session152.py` (6.4 s).
Outputs: `artifacts/fable-about164-20260922/` (probe164-loop164.json,
fable_bench164_*_rows.jsonl, marks164/, marks164-diff.json,
turns164-T-164-*.json, run164-session152-summary.json).

## What it means

Asking "What do you know about Tom?" now lists what was taught, from the
notebook only, with zero writes and zero regressions (600 bench, all
suites, 180 session turns unchanged).

## What it does not mean

No reasoning, no pronouns, no possessive chains ("about Tom's boss"
still delegates), no new sentences for edge cases — unknown shapes keep
exact base behaviour.

## Questions for Ben

None.
