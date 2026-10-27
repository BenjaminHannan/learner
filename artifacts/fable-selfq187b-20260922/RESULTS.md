# Exp 187b RESULTS (fresh registration of current loop187; Muse)

Agent: `scripts/fable_loop187_agent.py` (`26298ed9…`) reused read-only
(no copy; config path is a runtime arg). Exp 187 stays FAIL (post-seal
`What's`-guard edit). Case: `case187b.json`, 34 fresh turns, zero
string overlap with `case187.json`. Seal `418c9ecb…` (6 files) before
the runs; ledger P187b.1–7 before the runs. Mac CPU, OMP/MKL=1,
offline, one suite at a time.

## Marks table (integer counts, every seed/case reported)

| mark | setting | result |
|---|---|---|
| S1 | 34 turns (setup 4, self 14, trap 9, stmt 7) | 34/34 PASS (10.1 s) |
| S2 rt136 | 145 cases vs sealed 138g rows | 0 moves, 0 new wrong (OK 136, WRONG-WRITE 6, MISSED 3 — all inherited) |
| S2 rt143 | 124 cases vs sealed 138g rows | 0 moves (OK 107, MISSED 7, WRONG-ANSWER 10 — all inherited) |
| S2 sessions | 152 sessions / 180 turns | exactly the 2 predicted `who are you` moves (UNHELPFUL→OK), 0 new wrong, 0 new writes |
| S2 bench | 121 4 splits × 200 items | 0 moves, 0 new wrong |
| S2 marks123 | 9 suites vs sealed marks138g (scrubbed) | 9/9 identical; only nominal diff the predicted sleep filename line (p3/p4/rt81 FAILs inherited byte-identical; 887.0 s) |
| G4 | time/etiquette | all runs < 1500 s; idle_seconds on daemons; fictional names; 1.3M outputs |

Ledger: 7/7 TRUE (P187b.1 0.01, P187b.2 0.0225, P187b.3 0.01, P187b.4
0.04, P187b.5 0.01, P187b.6 0.0025, P187b.7 0.0025). SCORE PASS.

Reproduce (post-seal, registered):
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_fix187b_probe.py` then `.../fable_fix187b_suites.py
--only rt136|rt143|sessions|bench|marks` (one at a time).

## What it means

Self-questions get honest answers (never the user-name reply, never a
generic decline) and nothing else moves except two session turns that
improve exactly as predicted.

## What it does not mean

Closed patterns, not open English: grammatical "Who did make you?"
(base form) still falls through — known boundary, future work, code
untouched.

## Deviations

Pre-seal only: two draft self turns outside the closed set replaced
with has-forms after the pilot caught them. No post-seal edits (seal
6/6 OK after all runs). The suites driver exits 1 on sessions because
any move flags — the 2 moves are the predicted PASSMARKS ones.

## Questions for Ben

None. Conservative default taken: did+base-form left unhandled
(pattern stays closed) rather than widening the router mid-registration.
