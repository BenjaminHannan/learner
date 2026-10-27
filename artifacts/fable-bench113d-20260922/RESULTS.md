# Exp 113d RESULTS — fallback partial-frame gate (Muse, 2026-09-22)

Result first: registered FAIL. The gate fixes every fallback 2-hop prefix
it was built for (B5, B3, Q2/U1/V4 finals, fresh wrongs 056/103/196, 7
bench121 wrongs — all become honest abstains, 0 new wrong writes anywhere)
but applied verbatim it also abstains on legitimate fallback answers, so
the no-movement bars fail: Edit-200 183/200, L5-Z1 52/60, P4 29/30.

## Marks table (integer counts, scorer v2 where noted)

| Mark | Before (loop113c) | After (loop113d) | Bar | Verdict |
|---|---|---|---|---|
| D1 redteam124 (62, check_case/loop113b exp.) | 23 OK / 39 BUG | 25 OK / 37 BUG; OK->BUG 0; new wrong writes 0; prefix finals fixed: B5, B3, Q2, U1, V4 | 0 prefixes, 0 new wrongs, all OK stay OK | FAIL (U3 composer-prefix remainder, see below) |
| D2-P2 (64 redteam98) | — | 64/64 OK, 0 OK->BUG, 0 still-BUG (only change: D8 reply wording) | 64/64 | PASS |
| D2-P3 L1/L2/L3/L4 | — | all PASS | pass | PASS |
| D2-P3 L5-Z1 (60) | 60/60 | 52/60, 0 wrong | 60/60 | FAIL |
| D2-P3 L5-Z2 | — | 133 correct / 50 abstain-ok / 0 WRONG / 17 MISS | ident. to 113c | FAIL |
| D2-P3 L6 (200 x 3 seeds) | — | 200/200 x 3, 0 wrong | 200/200 x3 | PASS |
| D2-P4 (30 innocent) | — | 29/30 (1 false refusal P4-24 birth-year) | 30/30 | FAIL |
| D3 Edit-200 (v2) | 200/200, 0 wrong | 183 right-behaviour, 0 wrong (17 correct->abstain) | 200/200, 0 wrong | FAIL |
| D3 fresh-4hop (v2) | 145/52/3 | 145/55/0 (056/103/196 wrong->abstain) | >=145, <=3 | PASS |
| D3 bench121 new (v2) | 119/73/8 | 119/80/1; 7 wrong->abstain, 0 regressions (full id list in fable_bench113d_121_summary.json) | wrong<=8, correct>=115 | PASS |
| D4 wave wall-clock | — | 551 s | <1500 s | PASS |

## Why: three over-fire mechanisms (all correct->abstain, never new wrongs)

1. Reversed relations (15 Edit-200 reversal items): fallback Bench73Stage
frames use `author_of`/`written_by`/`founder_of`, which are not keys in
`REL_CUES92`, so the gate deletes nothing and any leftover cue fires.
2. Toy-family relations (L5-Z1 x6 incl. mother's-husband, husband's-job,
wife's-pet, birth-year; P4-24): `mother/job/pet/city/birth-year` are not
bench vocabulary, so e.g. leftover `husband` matches the spouse cue.
3. Qualifier + descriptive/synonym phrasing (L5-Z1 "in 2019" x2 — the
fallback legitimately answers qualifier questions, the composer premise
does not transfer; Edit-200 088 `position`, 096 `origin`-for-citizenship).

Out-of-scope remainders (composer path, unchanged by design): U3
(`employs` misses word-boundary `employ`, still-BUG); C08 (`whose`
direction, full-chain frame, still-BUG). Q2/U1/V4 verdicts stay BUG only
on turn-2 teach-ack echoes of absent `Spanish` — doc-124's own
expectation-error class, identical before/after.

## Deviations

`Loop113dDaemon.__init__` missed `self.idle_seconds` (transcription bug in
my new file): P3-L1 subprocess boot crashed after P2 had passed. Fixed the
one line (agent behaviour code untouched), kept P2, completed P3/P4.
No other deviation; no existing file edited.

## Reproduce (Mac CPU, offline, after seal)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench113d_redteam124.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop113d_marks.py --mark all
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench113d_run.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench113d_121.py --run

Daemon launch:
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop113d_agent.py --daemon --dir DIR --config artifacts/fable-bench113d-20260922/loop113d-config.json

## What it means

A consumption gate only works in the vocabulary and direction of the path
it was built for: on the fallback it catches every genuine 2-hop prefix
(zero wrongs on all three benches) but abstains on reversed, toy-family,
qualifier, and synonymously-phrased legitimate answers.

## What it does not mean

It does not mean the fallback is worse at knowing: all movement is
correct->abstain, never new wrongs; the next one-change step is a
direction- and vocabulary-aware gate (reversed-relation cue map, qualifier
semantics on the fallback), not a threshold tweak.
