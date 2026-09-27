# RESULTS — Experiment 113: loop102 + N-hop questions, scorer v2 (2026-09-22)

Registered single-change follow-up to exp-111 FAIL. THE ONE CHANGE:
loop113 = loop102 + exp-103's N-hop composer on the question side, with
the safety rule "never answer a shorter question than was asked"
(N-hop walk first; explicit 1-hop/structural probes keep the old path;
compound-subject guard declines partial walks; else clarify, never guess).
Teach side byte-identical. Scorer v2 registered before the run (answer
value after final " is "/" are ", word-boundary abstain forms).

Overall: N1 FAIL, N2 PASS, N3 PASS, N4 FAIL, N5 PASS. Both FAILs have an
identified mechanism; neither is re-run (FAILs stand).

## Marks table (sealed `PASSMARKS.md`, sha `5cd1bfc9…`)

| Mark | Result |
|---|---|
| N1 loop113 fresh-4hop: confident wrong ≤ 2/200 | **FAIL**: wrong 5/200 (correct 145, abstain 50) |
| N2 loop113 Fable-Edit-200: right behaviour ≥ 195 AND wrong ≤ 2 | **PASS**: 200/200, wrong 0 |
| N3 abstain items 50/50 abstain | **PASS**: wrong 0/50 |
| N4 loop102 marks P2+P3 vs loop113 unchanged | **FAIL**: P2 16 OK→BUG + 19 still-BUG; P3 l5z1 + l6 FAIL |
| N5 whole wave < 25 min Mac CPU | **PASS**: 22.3 s bench + 23.9 s marks |

Ledger P113.1–P113.5: FALSE, TRUE, TRUE, FALSE, TRUE (3/5).

## Before/after tables (scorer v2, per type: correct / abstain / wrong)

Fable-Edit-200, loop102 (before): mquake-twohop 100/0/0; reversal 50/0/0;
abstain-absent 0/25/0; abstain-broken 0/25/0. Right behaviour 200/200.
Fable-Edit-200, loop113 (after): IDENTICAL, 200/200, 0 wrong, 0 teach
rejects. Scorer v2 confirms exp-111 finding #1: all 150 split-A "wrongs"
were mouth framing ("…is Latvia." extracts to Latvia).

Fresh-200, loop102 (before): 0 / 70 / 130, contains_gold 5, teach rejects
22 (12 items). Fresh-200, loop113 (after): 145 / 50 / 5, contains_gold
146, teach rejects 22 (same 12 items — teach path identical, as designed).
Confident wrongs fell 130 → 5 (96% eliminated by the one change).

## Mechanism

1. **The wired composer works.** All 148 fully-taught 4-hop chains now
walk end to end through the mailbox (MAX_HOPS=8 covers 4 hops) and
extract exactly (145 correct; 3 of the 148 lost to teach-gap short walks,
see 2). Split-A frames are untouched: compose_n_hop agrees with the old
2-hop composer on all 100 mquake items, explicit routing covers all 50
reversal + 50 abstain items, guard fires 0 times there.
2. **N1 FAIL: 5 residual wrongs, all teach-gap partials (out-of-scope
class).** Items 056/103/196 (doorway rejects a mid-chain teach, e.g. the
"and"-guard on "…citizen of United Kingdom of Great Britain and
Ireland") answer 2-hop prefixes; items 125/200 ("…child…" sentences no
teach pattern parses) answer 1-hop prefixes. The notebook holds NO
evidence of continuation, so the compound guard cannot fire. Fixing them
needs teach-side patterns — a different experiment (stated as out of
scope in the brief; the 22 rejects are reported, not fixed).
3. **N4 FAIL: over-broad "?" interception.** Loop113Ears reroutes EVERY
"?" turn, including M1-possessive shapes ("Who is Forget's city?") the
FakeStage used to answer. Both composers return None there, so v1 flatly
clarifies: G-group forget flow breaks, L6 (all fake-shape asks) scores
0/200, L5-Z1 drops to 47/60. Reproducer: bound loop113 answers
"I didn't understand…" where loop102 answers "Forget's city is Lisbon."
Diagnosed follow-up (NOT applied — FAILs are never re-run into a pass):
delegate to the exact loop102 chain whenever both composers return None,
keeping flat clarify only for guard hits and non-explicit 2-hop frames.
4. **Scorer v2 behaves as registered:** "notable"-type wrongs now bucket
wrong (word boundaries); loop102-before fresh moves 131→130 wrong vs
exp 111 (one "Please answer with…" reply now abstains instead of wrong).

## Teach rejects (out of scope, reported separately)

22 rejects in 12 fresh items, identical under loop102 and loop113 (18×
"I didn't understand…", 4× one-fact-at-a-time "and"-guard). Split-A: 0
rejects in 800 teaches. Unchanged from exp 111 by design.

## 5 most instructive failures (verbatim)

1. FIXED (001, gold Arabic) — before: `Derek Shepherd's spouse's creator
is Frank Herbert.` → after: `Derek Shepherd's spouse's creator's country
of citizenship's official language is Arabic.`
2. Residual teach-gap (056, gold Stopnica): `Eddard Stark's spouse's
creator is Diana Gabaldon.` (mid-chain teach rejected by "and"-guard).
3. Residual teach-gap (125, gold German): `Winnie the Pooh's creator is
A. A. Milne.` (child-hop sentence has no teach pattern).
4. N4 regression (sealed G1): `Who is Forget's city? → I didn't
understand that. Could you say it another way?` (loop102: `Forget's city
is Lisbon.`).
5. Teach reject, still present (015): `Alberto Zaccheroni works in the
field of association football manager → I didn't understand that. Could
you say it another way?` (needs an occupation pattern; not this exp).

## What it means

The join failure exp 111 diagnosed is fixed from the question side: full
4-hop chains now walk through the real mailbox, split-A is perfect under
an honest scorer, and every remaining fresh wrong traces to a missing
teach (visible in the ledger as a reject), never to truncation.

## What it does not mean

It does not mean the loop is finished: the "?" interception regressed
M1-possessive questions (N4 FAIL, fix scoped for a follow-up), and fresh
phrasings still need teach-side patterns (N1's 5 wrongs + 22 rejects).

## Deviations / reproduce

Deviations: (a) pre-seal offline composer probes + a ~10-turn temp-dir
smoke (no artifact writes) informed P113.1–P113.5; (b) the marks copy
points kill9_burst at the loop113 script and writes under the exp-113
folder (agent class otherwise the only change). No other agent's files
touched; nothing committed. Reproduce: `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B scripts/fable_bench113_run.py --run`
(22.3 s) then `python -B scripts/fable_loop113_marks.py --mark all`.
Rows: `artifacts/fable-bench113-20260922/fable_bench113_*_rows.jsonl`.
Questions for Ben: none.
