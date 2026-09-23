# Exp 157 RESULTS — leading-filler strip (Muse, 2026-09-22)

Loop157 = loop150 + one stackable mixin (`Filler157Mixin` in
`scripts/fable_fix157_filler.py`): at ears hear, run unchanged loop150
first; else strip ONE leading filler (closed list of 15, longest-match,
comma-or-lowercase title rule) and accept the remainder only if the
unchanged loop150 parses it as a complete teach/correct or question.
Otherwise byte-identical. No existing file edited.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar | number | verdict |
|---|---|---|---|
| B1 probe (60) | 32 filler==bare, 12 titles 0 wrong, 16 same-as-150 | 60/60 OK (20 teach triples equal, 12 answers equal+want, 12 titles identical+nowrite, 16 identical) | PASS |
| B2 sessions S2 | turns 4,6,12 + 7,13,15,28,29 become OK | 8/8 OK ("Saved: ..." x3, answers x5), other 352 replies byte-identical | PASS |
| G1 bench (600) | per-item identical to loop150 rows, 0 new wrong | 600/600 identical, verdict_moves 0, reply_moves 0, new_wrong 0 | PASS |
| G2 marks123 (10 suites) | per-case verdict identical to marks150 | all 10 suite statuses+numbers identical; p2 64/64 rows, rt81 74/74, rt110 62/62, bench 400/400 verdicts identical | PASS |
| G3 sessions (180) | identical to T-T except 8 predicted S2 turns | moves exactly {4,6,7,12,13,15,28,29}, new WRONG 0, new writes exactly {4,6,12} | PASS |
| G4 time | each run < 1500 s Mac CPU | probe 3.7 s, bench 69.2 s, sessions 4.7 s, marks 391.4 s | PASS |

SCORE: PASS (B1, B2, G1–G4).

## Predictions

P157.1 TRUE (60/60) | 0.0625. P157.2 TRUE (8/8 OK, rest identical) |
0.04. P157.3 TRUE (600/600) | 0.04. P157.4 TRUE (verdicts identical;
see deviation) | 0.09. P157.5 TRUE (8 moves, 0 new WRONG, writes
{4,6,12}) | 0.04. P157.6 TRUE (max 391.4 s) | 0.01. 6/6 TRUE.

## What it means

Phone-style filler prefixes ("btw", "also", "oh and", ...) on teaches
and questions now work exactly as their bare sentences, while titles
("Hey Jude", "Also Sprach ...", "So Far Away"), corrections, and garbage
behave exactly as before; 600 bench items and all 10 regression suites
show zero behavior change otherwise.

## What it does not mean

It does not understand stacked fillers in one turn ("oh, and ..." still
clarifies — one strip only), capitalised fillers without a comma ("Oh
and June's ..." stays refused by title-safety design), small talk,
pronouns, or any other 152 class; those still clarify.

## Deviations

1. Post-seal one-line fix (reported, re-run in the open):
`Loop157Daemon.__init__` missed `self.idle_seconds`, so the first G2
attempt died in suite p3 (daemon booted, crashed on first idle check:
`AttributeError` in daemon.stdout.log). Added the line; ears/loop logic
untouched. B1/G1/G3 use in-process loops/daemons that never execute
`run()`, so their registered results stand; G2 was re-run fully in the
open (391.4 s).
2. G2 metadata note (not a verdict move): 3 rt110 log lines (P5/T5/D2)
record `statuses: []` vs `['clarify']` while reply, writes, and verdict
are identical. Daemon logs prove the records were correct
(`{"kind": "clarify", ...}`); the harness polls outbox (written before
the log append) and scanned the log first — a pre-existing outbox/log
race exposed by today's 10-agent parallel load. No verdict impact.

## Questions for Ben

None.

## Exact reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157_probe.py --out artifacts/fable-filler157-20260922/probe157-loop157.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop157_agent.py --config artifacts/fable-filler157-20260922/loop157-config.json --out artifacts/fable-filler157-20260922/marks157 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157_session152.py
