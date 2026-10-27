# Exp 154 RESULTS — yes/no questions (Muse)

Loop154 = loop150 + one yes/no stage (scripts/fable_fix154_yesno.py,
scripts/fable_loop154_agent.py). Registered runs after seal
(SEAL.sha256.txt) except one reported post-seal edit below.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar | number | status | secs |
|---|---|---|---|---|
| Y1 | 49 probe dialogues, 0 wrong yes/no | 21 yes OK, 12 single-no OK, 8 multi only-know OK, 8 unknown non-No OK; wrong 0; question writes 0 | PASS | 5.1 |
| Y2 | 0 writes from any yes/no Q | 0 writes over all 54 cases incl. "Is Bob a doctor?" | PASS | (in probe) |
| G1 | bench per-item identical to loop150 | 600/600 verdicts identical, 0 reply moves (150/50/0, 157/43/0, 136/63/1) | PASS | 92.0 |
| G2 | marks123 per-case identical to marks150 | p2 64/64, p4 30/30, rt110 62/62, q1 identical, bench identical, q4 identical leaks, soak PASS, sleep SKIP identical; 3 moves: rt81 D_q_vs_s-04 OK->UNCLEAR, p3 l5z1 60/60->58/60 (turns 49, 58) | FAIL (letter) | 181.1 |
| G3 | sessions reply-identical to T-T | 0 reply moves, 0 new WRONG, 0 new writes over 6 sessions | PASS | 6.7 |
| G4 | each run < 1500 s Mac CPU | 5.1 / 92.0 / 181.1 / 6.7, daemon idle_seconds OK | PASS | — |

Predictions: P154.1 TRUE (49/49) | P154.2 TRUE (0 writes) | P154.3 TRUE
(600/600) | P154.4 FALSE (3 moves, bar was 0) | P154.5 TRUE (0 reply
moves) | P154.6 TRUE (all < 1500 s). Brier: 0.04, 0.01, 0.0625, 0.5625,
0.04, 0.01.

## G2 diagnosis (one note)

All 3 moves are one mechanism: a yes/no-shaped turn whose answer is
unknown ("Is Mira's city Lisbon?" with no Mira taught; L5-Z1 "Is Mira's
city Cedar Hollow[ lol]?" on fresh daemons). The stage relays the
brief-mandated honest forward reply ("I don't know anyone called Mira.")
instead of the pre-yes/no clarify the sealed expectations still assert.
Zero writes, zero new BUG/WRONG on every move; the zero-move forecast
missed that the sealed suites contain 3 Is-turns. No silent re-runs.

## Deviations

D1 (post-seal code edit, reported): Loop154Daemon.__init__ dropped the
`self.idle_seconds` line when copied from loop150, so daemon-subprocess
boots crashed (in-process runs were unaffected: Y1/G1/G3 passed
pre-fix identically). One line restored; Y1, G1, G3 and G2 all re-ran in
the open after the fix. D2: G3 S5 turn 16 shows verdict OK(sealed) vs
UNHELPFUL(fresh mechanical judge) with byte-identical reply and writes —
the sealed OK was hand-review; feeding the sealed turn through the
current judge reproduces UNHELPFUL, so no behavior move.

## What it means

"Is ...?" turns the loop never understood now answer Yes / No (single-
valued only) / "I only know that ..." / the honest abstain, with zero
writes and zero movement on benches, sessions, and all non-yes/no suites.

## What it does not mean

It does not teach the loop new facts or relations: single-chain cued
Is-questions are still answered directly by the old N-hop composer, and
ambiguous shapes still clarify.

## Reproduce (worktree root, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1)

uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154_probe.py --agent loop154 --out artifacts/fable-yesno154-20260922/probe154-loop154.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop154_agent.py --config artifacts/fable-yesno154-20260922/loop154-config.json --out artifacts/fable-yesno154-20260922/marks154 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154_session152.py
