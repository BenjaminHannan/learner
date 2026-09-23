# RESULTS — Exp 161: grounded self card (Muse, 2026-09-22)

Loop161 swaps loop138's L2 (frozen router + baked self table) for SelfCard161
(`scripts/fable_selfcard161.py`), which computes every reply from live state:
names/relations/values parsed from the asked text against notebook vocab,
counts/turns/origins read from logs, content served only when groundable
(provenance needs a live fact; trail needs a walk ending in a plain value).
Serving rule unchanged (notebook wins; card only on miss; decline text on
DECLINE). PASSMARKS + cases sealed pre-run (`SEAL.sha256.txt`); ledger
P161.1–6 appended pre-run. Mac CPU, offline, OMP/MKL=1.

## Marks (every case reported; full per-case rows in JSONs)

| mark | bar | got | verdict |
|---|---|---|---|
| S1 name-leak grep | 0 unlisted intersections | 11 hits, all allow-listed generic words, 0 panel names | PASS |
| S2 fresh 69 (3 states) | ≤2 wrong, 0 hallucinations | 14 wrong, 7 hall flags | FAIL |
| S3 127-panel turn path | ≤6 wrong | 15 wrong | FAIL |
| S4 bench121-new 200 | 0 card content | 0 content, 62 declines | PASS |
| S5a bench 600 vs 138 | identical exc. predicted | 165 wrong→abstain; 599 identical; 0 new wrong | PASS |
| S5b marks123 vs 138 | identical exc. predicted | 6/7 moves exact; 1 unpredicted (favorable) | FAIL |
| S6 time | each run <25 min | 3.3 s / 136.6 s / 253.9 s | PASS |

S5b moves (all self-path, evidenced): rt110 P1/P3/S1 reply-only, S4 OK→BUG
(packed ask+teach counted, not declined — no novelty guard); p2 predicted
reply moves invisible in report schema (final-reply only); rt81 M_hops/O_user
reply-only, I_edges UNCLEAR→OK (decline text contains "another way", which
the judge wanted). q1/q4/p3/p4/bench/soak/sleep identical (soak 2000 turns
3 kills 0/0/0).

## Why each FAIL happened (one diagnosis note each)

- S2: the matcher overfit dev phrasing families — "who exactly are you"
  missed identity (exact-substring) and fell to speakers via "tell me";
  "recently" ≠ "recent"; "ever tell" hit first before speakers; 7 "hall"
  flags are scorer allow-list omissions of generic template words
  (All/Web/What) — no answer mentioned anything outside the notebook.
- S3: 4 structural turn-path issues (C17 quotes fail the name scan, C18
  hardcodes 26, Q059 notebook-guard wins — all shared with loop138's
  design) + 10 blind-rephrasing gaps (treat-as-true, taught/learned-cues,
  arrived-through, boundaries, origin, letters/words, policy/delete,
  other-day, packed-turn "cannot") + Q078 words-count answered as turns.
- S5b: I_edges verdict moved favorably on a predicted reply turn.

## Deviations (all open; no re-runs into a pass)

- D1: sealed case file was truncated by one closing brace; repaired (one
  char, content identical) and re-sealed before any completed run
  (PASSMARKS/config hashes unchanged).
- D2: brief's "I can't predict" shipped as "I cannot predict" (the scorer's
  decline marker), and identity drops "in plain English" (else the word
  "English" fails the state-membership scan).
- D3: marks-diff p3 compared seconds as well as pass flags; fixed to
  pass-only (analysis code; registered data untouched).

## What it means

The card answers fresh names correctly from state, never serves a baked
panel string, routes 0 bench questions to content, and replaces five of
loop138's hardcoded lies ("Oslo and Paris are only values you taught me"
on redteam misses) with honest declines — with every collateral move counted.

## What it does not mean

Not a drop-in upgrade: blind rephrasings outside dev families still defeat
the template matcher (S2/S3 FAIL), and one packed turn lost its abstain
(S4 in marks123). Template matching has the same disease class as the
router it replaces, only milder (0 wrong on 320 dev questions).

## Reproduce

Seal: `shasum -c artifacts/fable-selfcard161-20260922/SEAL.sha256.txt`.
S1–S4: `… python -B scripts/fable_selfcard161_marks.py`. S5a: `… python -B
scripts/fable_loop161_bench.py`. S5b: `… python -B
scripts/fable_marks123_all.py --agent scripts/fable_loop161_agent.py
--config artifacts/fable-selfcard161-20260922/loop161-config.json --out
artifacts/fable-selfcard161-20260922/marks161 --workers 4`, then `… python
-B scripts/fable_loop161_marksdiff.py`. Questions for Ben: none.
