# RESULTS — Exp 209: WRITE SCREEN on loop138i (Muse)

One change on loop138i (subclass; 138i untouched): an outermost ears
screen + `_act` value backstop. (a) strips leading `named`/`called`
from taught values; (b) date relations + `in|on` month/weekday/date
store literals, never entities; (c) clause-word relation keys refuse
with the base one-fact-at-a-time reply, 0 writes. Nothing else changes.

## Marks table (registered runs, sealed code, each < 25 min Mac CPU)

| mark | bar | number | status | secs |
|---|---|---|---|---|
| W1 bad-save (32) | 0 bad saves, exact stored facts | 32/32 pass; all 32 base-differs | PASS | 1.9 |
| W2 near-miss (33) | byte-identical to 138i | 33/33 identical (reply+stored+entities) | PASS | 1.1 |
| rt136 (145) | 0 moves, 0 new wrong | OK136/WRONG-WRITE6/MISSED3, moves 0 | PASS | ~3 |
| rt143 (124) | 0 moves, 0 new wrong | OK107/MISSED7/WRONG-ANSWER10, moves 0 | PASS | ~6 |
| sessions152 | 0 moves, 0 new writes | OK165/UNHELPFUL15, moves 0 | PASS | ~5 |
| bench-v3 4x200 | 0 moves, 0 new wrong | 187/195/149/191 correct, moves 0 | PASS | 30.1 |
| marks123 | per-case identical to marks138i | 0 case-moves all suites (volatiles only) | PASS | 307.0 |

marks123 absolute bars FAIL identically to 138i itself (p2/p3/p4/bench/
rt81 pre-existing fails); per-case vs sealed marks138i rows: p2, p4,
rt81, rt110 (verdict+reply+stored), bench 400/400, p3 l1-l6 case rows,
q1, q4, soak exact — 0 moves. Volatiles only: `seconds`, l6
`replied_before_kill`, sleep SKIP agent filename.

## What it means

The three director-verified bad saves are gone (`dog = Pip`, birthday
`March` as a literal, no `friend_who_lives_in_oslo` relation) while 33
near-misses and every frozen row behave exactly as before.

## What it does not mean

It does not fix date values without `in|on` (`My birthday is March`
still stores an entity) or teach paths outside the ears screen; asks
and sleep/thinking paths are untouched.

## Deviations / notes

None from the brief. Seal `SEAL.sha256.txt` 5/5 OK post-runs; no
post-seal edits. Fictional names only. Isolated scratch notebook dirs
throughout; never wrote to repo-root `notebook/`. Reproduce:
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_writescreen209_probe.py --out <dir>` (W1/W2),
`scripts/fable_writescreen209_suites.py --only <suite> --out <dir>`,
stock `scripts/fable_marks123_all.py --agent
scripts/fable_loop209_agent.py --config
artifacts/fable-writescreen209-20260922/loop209-config.json --out <dir>`.
