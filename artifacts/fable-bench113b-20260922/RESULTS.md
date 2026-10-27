# RESULTS — Experiment 113b: loop113 + fallback to the exact loop102 chain (2026-09-22)

Registered single-change follow-up to exp-113 N4 FAIL. THE ONE CHANGE:
loop113b = loop113 + delegation to the exact loop102 chain
(`Loop102Ears.hear` on the same instance) whenever BOTH composers return
None on a "?" turn; flat clarify kept only for compound-guard hits and
non-explicit 2-hop frames. Teach path identical. Scorer v2 identical to
exp 113.

Overall: M1 FAIL, M2 PASS, M3 PASS, M4 PASS. The FAIL has an identified
mechanism (below); it stands, never re-run.

## Marks table (sealed `PASSMARKS.md`, sha `edbf8592…`)

| Mark | Result |
|---|---|
| M1 loop102 marks P2+P3(L1-L6)+P4 vs loop113b identical to loop102 | **FAIL**: P2 2 OK->BUG (B7, D8) + 2 still-BUG (C2, C5); P3 all pass; P4 pass |
| M2 loop113b Fable-Edit-200 right behaviour 200/200, 0 wrong | **PASS**: 200/200, wrong 0 |
| M3 loop113b fresh-4hop correct ≥ 145, wrong ≤ 5, same 5 ids | **PASS**: 145 correct, 50 abstain, 5 wrong (056/103/196/125/200) |
| M4 whole wave < 25 min Mac CPU | **PASS**: 22.0 s bench + 24.0 s marks |

Ledger P113b.1–P113b.4: FALSE, TRUE, TRUE, TRUE (3/4).

## Before/after tables (scorer v2, per type: correct / abstain / wrong)

Fable-Edit-200, loop113 (before): mquake-twohop 100/0/0; reversal 50/0/0;
abstain-absent 0/25/0; abstain-broken 0/25/0. Right behaviour 200/200.
Fable-Edit-200, loop113b (after): IDENTICAL, 200/200, 0 wrong, 0 teach
rejects. (Before arm reproduces sealed exp-113 split-A exactly.)

Fresh-200, loop113 (before): 145 / 50 / 5, contains_gold 146, teach
rejects 22 (12 items). Fresh-200, loop113b (after): IDENTICAL 145 / 50 /
5, same 5 wrong ids (056/103/196 mid-chain "and"-guard rejects, 125/200
child-hop teach gaps), teach rejects 22 (same 12 items).

## Mechanism

1. **The fallback works where diagnosed.** G1–G7 + 12 more v1 OK->BUGs
are fixed (P2 OK->BUG 16 -> 2); L6 returns to 200/200 on all 3 seeds
(v1: 0/200); L5-Z1 returns to 60/60 (v1: 47/60); L1–L4, L5-Z2, P4
(30/30, 0 false refusals) all pass. Smoke reproducer: loop113b answers
"Forget's city is Lisbon." via the FakeStage (`fake` stage) where loop113
clarified. Split-A and fresh-4hop are byte-identical to loop113 — the one
change fires only on double-None questions, as designed.
2. **M1 FAIL: 4 P2 cases where B92 returns a SHORT frame, not None.**
Post-hoc probe (hand-built triples, not a re-run): B92.compose_n_hop
returns a 1-hop prefix frame on B7 ("…citizenship of Roberto Merhi?" ->
`[country_of_citizenship]`), C2 (same shape after a forget), C5
("Where was the author of Fasti born?" after forgetting the birthplace ->
`[author]`), and D8 ("Who is Poland's capital in 2019?" -> `[capital]`,
qualifier ignored). So the fallback never fires; the inherited v1
ask-path answers the prefix: B7/D8 answer where loop102 abstained
(OK->BUG), C2/C5 re-answer where loop102 abstained (still-BUG vs
loop102's BUG->OK). B92's coverage gate checks parse coverage and the
compound guard only catches notebook-holds-MORE; neither catches
notebook-holds-LESS (broken chain, qualifier), while loop102's ChainEars
coverage check clarified these. Scoped follow-up (NOT applied): treat
partial frames (fewer hops than the question names) like double-None.
3. **M3's 5 wrongs are untouched, as predicted**, all teach-gap partials
with no notebook evidence of continuation — out of scope, reported by id.

## 5 most instructive turns (verbatim)

1. FIXED (G1): `Who is Forget's city?` -> `Forget's city is Lisbon.`
(v1 clarified; stage `fake` via fallback.)
2. STILL BROKEN (D8): `Who is Poland's capital in 2019?` -> `Poland's
capital is Warsaw.` (should abstain; qualifier swallowed by the composer.)
3. STILL BROKEN (C5): `Where was the author of Fasti born?` (birthplace
forgotten) -> `Fasti's author is Ovid.` (1-hop prefix of a 2-hop ask.)
4. Residual teach-gap (125): `…child…` -> `Winnie the Pooh's creator is
A. A. Milne.` (no teach pattern for child-hops; same as v1.)
5. Unchanged good (fresh-001): full 4-hop chain still walks end to end,
exact gold, stage `loop113b-nhop`.

## What it means

The exp-113 N4 regression is fixed for every question neither composer
parses (everyday possessives, FakeStage shapes): L6/L5-Z1/P4 fully
restored with zero movement on split-A or fresh-4hop.

## What it does not mean

It does not mean v1 routing is safe wherever a composer returns a
frame: short-prefix frames on broken chains and qualifier questions are
still answered confidently (4 P2 cases) — that needs the follow-up
partial-frame rule, a different one change.

## Deviations / reproduce

Deviations: (a) a 3-turn shared-notebook smoke (reproducer only, no
artifact writes; stray root `notebook/`+`state.json` removed) informed
nothing beyond the sealed prediction; (b) post-hoc composer probes with
hand-built triples diagnosed M1 (analysis only, no registered re-run).
No other agent's files touched; nothing committed. Reproduce: `export
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_bench113b_run.py --run` (22.0 s) then `python -B
scripts/fable_loop113b_marks.py --mark all` (24.0 s). Rows:
`artifacts/fable-bench113b-20260922/fable_bench113b_*_rows.jsonl`.
Daemon launch: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run
--offline --no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_loop113b_agent.py --daemon --dir DIR --config
artifacts/fable-bench113b-20260922/loop113b-config.json`.
Questions for Ben: none.
