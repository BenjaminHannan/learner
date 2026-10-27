# RESULTS — Exp 150d: hedge words are case-sensitive (Muse, 2026-09-22)

Result first: 6/6 marks PASS. bench132-4hop-152 flips wrong→correct
(exact); the 44-case probe goes 44/44 with 0 wrong writes; every regression
suite is per-case identical to loop138b's frozen rows except the one
predicted flip. One file subclasses loop138b; no existing file edited; no
post-seal code edits (`shasum -c SEAL.sha256.txt` passes); ledger P150d.1–6
pre-run, outcomes appended post-run.

The bug (Step 1): `scripts/fable_fix150_subjectguard.py:144-145`
(`_is_hedged` via ci `_starts_with_phrase` at `:121-124`) refused the
Title-Case song subject "I Believe I Can Fly" as hedge "i believe", so the
152 chain lost its country-of-origin teach and answered short (WRONG).

The one change: a hedge counts only when its content word is lowercase as
typed, or the whole span is all-caps
(`scripts/fable_fix150d_subjectguard.py`, `_hedge_counts`). "I believe Kip"
still refuses; "I Believe I Can Fly" stores. Phone-form single-word hedges
with a fuller phrase behind them ("Maybe Kip Dune", "Maybe, Kip Dune",
"Maybe the capital of Peru") still refuse; only a lone Title-Case token
("Maybe Tomorrow", "Perhaps Love") stores. Reporting openers, fillers, rule
(c), and both replies are untouched. Possessive owners keep the 150
case-insensitive veto in the 137-upgrade path (`_upgrade137` override):
"Maybe Tom's boss" (sealed C081 nowrite) is indistinguishable from "Maybe
Tomorrow's author" there, so both refuse exactly as on loop138b.

## Marks (every seed/case reported)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 probe (44) | title 16/16, hedge 16/16, other 12/12, 0 wrong writes | 16/16 (12 singles save exact triples, 4 chains answer gold; loop138b refuses subject-side titles), 16/16 reply+store identical to loop138b with 0 writes either arm, 12/12 identical (3 neutral twins answer gold; O11 title-possessive refused both) | PASS (20.6 s) |
| T2 bench152 | flips to correct | correct, exact ("...continent is Antarctica") | PASS |
| G1 bench | 0 new wrong vs 138b rows; only predicted move | new_121/old/edit200 per-item identical; bench132 exactly 1 move: 152 wrong→correct; 0 new wrong | PASS (65 s) |
| G2 marks123 | per-case identical to marks138b | 0 moves: p2 64/64, p3 levels equal (l5z1 fail inherited), p4 30/30, rt110 62/62, q1 F5+M5, bench 200+200, rt81 60/0/14 (fail label inherited), sleep SKIP, soak 2000 0/0/0, q4 clean | PASS (307 s) |
| G3 junk/143/sessions | 0 moves, 0 new WRONG/WW | rt136 135/7/3, cases150 57/57, f1 45+t14-only, cases139b 101/101, 143 106 OK/11 WRONG, sessions 129 OK/2 WRONG — all 0 moves | PASS (10+14+18 s) |
| G4 time | each run < 25 min | slowest 307 s; daemons take idle_seconds | PASS |

## Deviations

None. No code edit after the seal (agent, guard, all five drivers,
PASSMARKS, cases, config all verify); no open re-runs; no soak/rt110
flakes observed. Pre-seal case retunes only (T10 value-side "Maybe
Tomorrow" hits the separate 139b value guard on both arms, so T10 uses an
"I Believe…" value; T14/T15 asks reshaped after both arms declined the
possessive-of-of question). The 150d rule itself never changed after
first verification.

## What it means

Title-Case works named like hedges ("I Believe I Can Fly", "I Think We're
Alone Now", "Maybe Tomorrow", "Perhaps Love", "Maybe Baby") now teach and
answer chains exactly like neutral names, while every real hedge shape —
lowercase, phone-form, comma, filler-led, all-caps — refuses exactly as
before, with zero movement on any sealed suite.

## What it does not mean

Not a general title fix: possessive-of-title ("Maybe Tomorrow's author")
still refuses (loop138b-identical, indistinguishable from hedged "Maybe
Tom's boss"); Maybe/Perhaps-led VALUES still hit the separate 139b value
guard on both arms; confident false single facts still store.

Reproduce (Mac CPU, offline, OMP/MKL=1, after seal):
`python -B scripts/fable_fix150d_probe.py`,
`python -B scripts/fable_loop150d_bench.py`,
`python -B scripts/fable_loop150d_junk.py`,
`python -B scripts/fable_loop150d_redteam143.py`,
`python -B scripts/fable_loop150d_sessions.py`,
`python -B scripts/fable_marks123_all.py --agent scripts/fable_loop150d_agent.py --config artifacts/fable-hedgecase150d-20260922/loop150d-config.json --out artifacts/fable-hedgecase150d-20260922/marks150d --workers 4`
(+ `scripts/fable_fix150d_markscompare.py`). Questions for Ben: none.
