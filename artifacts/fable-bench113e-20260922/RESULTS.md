# Exp 113e RESULTS — gate inverse cues (Muse, 2026-09-22)

Result first: registered FAIL with the targeted repair demonstrated. The
one change (each relation's cue set = every surface the repo's own tables
canonicalise to R or inverse(R)) restores every 113d over-abstain it was
built for — Fable-Edit reversal 35/50 -> 50/50, P4 29/30 -> 30/30, L5-Z1
52/60 -> 58/60, L5-Z2 MISS 17 -> 2 — with 0 wrong anywhere and every 113d
protection intact (bench121 7 wrongs stay abstained, fresh 056/103/196 stay
abstained, B5/B3 fixed, 0 new wrong writes, 23/23 redteam OK stay OK). It
fails its bars where the leftover word belongs to a *different* relation,
not an inverse surface: Edit-200 088 (`position`) and 096 (`origin`) stay
abstained (198/200), and the two `in 2019` qualifier items stay abstained
(L5-Z1 58/60). Fable-Edit, L5 and P4 items were seen by 113d, so this
measures repair, not generalisation.

## Marks table (integer counts, scorer v2 where noted)

| Mark | loop113c (before) | loop113e (after) | Bar | Verdict |
|---|---|---|---|---|
| E1 redteam124 62 cases | 23 OK / 39 BUG | 23 OK / 39 BUG; OK->BUG 0; new wrong writes 0; B3+B5 BUG->OK; Q2/U1/V4 finals abstain (no prefix answer); prefix_after = C08, U3 (identical to 113d, composer path, out of scope) | fixes hold, 0 OK->BUG, 0 new wrongs | PASS |
| E2 Fable-Edit-200 (v2) | 200/200, 0 wrong | 198 right-behaviour, 0 wrong (reversal 50/50; twohop 98/100: only 088, 096 abstain) | 200/200, 0 wrong | FAIL |
| E3 fresh-4hop (v2) | 145/52/3 | 145/55/0 (exactly 056/103/196 wrong->abstain; 0 other moves) | >=145, 0 wrong | PASS |
| E3 bench121 new (v2) | 119/73/8 | 119/80/1 (same 7 wrong->abstain as 113d; same single remaining wrong 069; full movement in fable_bench113e_121_summary.json) | >=119, <=1 wrong | PASS |
| E4 P2 (marks123, 64) | 64/64 (113c-era) | 64/64 OK, 0 OK->BUG, 0 still-BUG | 64/64 | PASS |
| E4 P3 L1/L2/L3/L4 | — | all PASS | pass | PASS |
| E4 P3 L5-Z1 (60) | 60/60 (113c) | 58/60, 0 wrong (only t42/t43 `in 2019` qualifier abstains) | 60/60 | FAIL |
| E4 P3 L5-Z2 | — | 148 correct / 50 abstain-ok / 0 WRONG / 2 MISS (113d: 133/50/0/17) | as 113c | FAIL |
| E4 P3 L6 (200 x 3 seeds) | — | 200/200 x3, 0 wrong | 200/200 x3 | PASS |
| E4 P4 (30 innocent) | — | 30/30, 0 false refusals (P4-24 birth-year repaired) | 30/30 | FAIL-free PASS |
| E5 wave wall-clock | — | ~161 s subprocess total (E1 8 + bench 70 + 121 36 + p2 7 + p4 3 + p3 38) | <1500 s | PASS |

113c->113e per-item movement: Edit exactly 2 (088, 096 correct->abstain,
both already abstained under 113d); fresh exactly 3 (056/103/196
wrong->abstain); bench121 exactly 7 (wrong->abstain, same ids as 113d). No
other item moved on any bench; no new wrong on any bench or mark.

## Why the remainders stay (all correct->abstain or already-abstain)

088's remainder `position` is position_played's cue and 096's `origin` is
country_of_origin's cue: genuine other-relation words, not inverse surfaces
of the walked frames, so no inverse-cue change may consume them without
also consuming genuine prefixes. The `in 2019` trailers hit the unchanged
trailing-qualifier rule. Toy words no table knows stay quiet by design.

## Deviations

1. E1 first invocation HARNESS-ERRORed on all 62 after-arm cases (the 113d
factory looks up `Loop113dDaemon` on the swapped module). Fixed in my own
wrapper (verbatim 113d factory body with the after-arm class/config); the
rerun is the only registered E1 outcome. No registered result was kept
from the error run.
2. Pre-run refinement in my own file (before any registered run, bars
unchanged): REV_BY_VERBS verb-membership edges dropped — a shared verb
(`founded` in location_of_formation cues) is not an inverse declaration;
edges come only from declared pairs (REV_OF_NOUNS, wikidata, closed maps).
3. `fable_loop113e_marks.py` documents that the 113d harness's kill-9 burst
spawns from an inline hardcoded 113d path; E4 was measured via
fable_marks123_all.py as registered, so that wrapper was not run for bars.
No existing file edited; no other agent's files touched.

## Reproduce (Mac CPU, offline, after seal)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop113e_agent.py --selftest
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench113e_redteam124.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench113e_run.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_bench113e_121.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop113e_agent.py --config artifacts/fable-bench113e-20260922/loop113e-config.json --out artifacts/fable-bench113e-20260922/marks123 --suite p2
(same --suite p4, p3)

Daemon launch:
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop113e_agent.py --daemon --dir DIR --config artifacts/fable-bench113e-20260922/loop113e-config.json

Added words per relation: artifacts/fable-bench113e-20260922/fable_bench113e_added_cues.json (474 added cues, each with its source table).

## What it means

A consumption gate must speak every direction its own parser speaks: giving
each relation the table-declared inverse surfaces repairs reversal,
family-word and own-spelling abstains (reversal 50/50, P4 30/30) while
genuine-prefix protection transfers byte-identically.

## What it does not mean

It does not mean broader understanding: leftovers naming a different
relation (088, 096) or trailing qualifiers still abstain, and the repaired
items were all seen by 113d — the next step is qualifier/descriptive
semantics on the fallback, not a threshold tweak.
