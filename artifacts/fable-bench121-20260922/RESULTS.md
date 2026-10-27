# RESULTS — Experiment 121: teach-side phrasing coverage (2026-09-22)

Registered single-change follow-up to exps 111/113. THE ONE CHANGE (teach side
only; question side byte-identical to loop113b, wrapped not edited): three new
teach patterns (employer / occupation / child, same regexes/keys as exp-92)
tried only when bench73 parses nothing, plus a narrowed "and" guard that lets
"and" pass inside a single Title-Case name span ("United Kingdom of Great
Britain and Ireland") while every other packed-fact screen still refuses.
Base: `scripts/fable_loop113b_agent.py` (existed at build time).

Overall: T1 PASS, T2 PASS, T3 PASS, T4 PASS, T5 FAIL (P2 only; mechanism below).
Ledger P121.1–P121.5: FALSE, FALSE, TRUE, TRUE, FALSE (2/5).

## Marks table (sealed `PASSMARKS.md`, sha `b35fa52c…`)

| Mark | Result |
|---|---|
| T1 new blind split teach rejects ≤ 5 items | **PASS**: 1/200 items (1 reject) |
| T2 new blind split confident wrong ≤ 5 | **PASS**: 1/200 |
| T3 old fresh split rejects 0 of the 22 | **PASS**: 0 rejects (was 22 in 12 items) |
| T4 packed-fact probes still refused, 0 new writes | **PASS**: R110 L1/L2/L4 + literal probe all split-clarify, 0 writes |
| T5 loop102 marks P2/P3/P4 unchanged | **FAIL**: P3 all 7 pass, P4 pass (0 refusals); P2 moves B7/D8 OK→BUG, C2/C5 still-BUG |

## Evidence

Blind split (STEP 1): 200 items, seed 121, 0 case_id overlap with bench103-fresh
+ bench65-200, sealed `data/open/bench121/SEAL.sha256.txt` (`cd05c007…`);
sentences never printed/read — only n=200 and the structured-relation
histogram (30 keys, all covered by bench73+exp-92 patterns, incl. child 10,
employer 8, occupation 6).

Bench (scorer v2, 9.9 s): new split 136 correct / 63 abstain / 1 wrong /
contains_gold 140; old fresh 157 / 43 / 0 (was 145 / 50 / 5 under loop113 —
all 5 old wrongs fixed, correct +12). The 1 new-split wrong and its 1 teach
reject are the same item (`bench121-4hop-069`, full-walk ask on a teach gap —
same residual class as exp-113's 5, unfixable from patterns seen so far).

T5 mechanism (no new writes from this change): loop121's P2 verdicts are
ID-identical to the loop113b base's own sealed P2 (`ok_to_bug` B7/D8,
`still_bug` B7/C2/C5/D8). Those 4 are question-side cases (conflict/
forget/qualifier asks the N-hop composer answers instead of abstaining) —
inherited with the wrapped question side, untouched by the teach change.
P3 L1/L2/L3/L4/L5z1/L5z2/L6 all pass (L5-Z1 60/60; L5-Z2 200/200 with 575
teaches through the new `loop121-teach` path); P4 30/30, 0 false refusals.

## What it means

Fresh teach phrasing is fixed end to end: every rejected shape now teaches,
old-split wrongs went 5 → 0, and packed-fact attacks are still refused.

## What it does not mean

It does not mean the loop matches loop102 on red-team questions — 4 P2 cases
need a conflict/forget/qualifier-aware question rule, a different experiment.

## Deviations / reproduce

Deviations: (a) synthetic-sentence smoke probes + one code fix each before the
registered run, all in new files only: the "and"-name exception had to cover
bench73-parsed teaches too (first smoke refused the citizen sentence), and a
dropped `idle_seconds` line crashed real subprocess daemons (hung P3-L1 once;
fixed, full wave re-run clean); (b) T5 compared against sealed loop102
outcomes as written — the P2 FAIL is inherited from the 113b base verbatim.
No other agent's files touched; nothing committed. Reproduce: `export
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python
3.12 --with torch --with numpy python -B scripts/fable_bench121_run.py --run`
(9.9 s) then `python -B scripts/fable_loop121_marks.py --mark all` (~35 s).
Rows: `artifacts/fable-bench121-20260922/fable_bench121_*_rows.jsonl` +
`regression/`. Questions for Ben: none.
