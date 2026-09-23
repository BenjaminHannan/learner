# RESULTS — Experiment 113c: partial/prefix composer frames treated like None (2026-09-22)

Registered single-change follow-up to exp-113b M1 FAIL. THE ONE CHANGE:
loop113c = loop113b + a composer frame counts as usable only if it
consumes every relation phrase / qualifier in the question (no leftover
content words after the frame is matched); a partial or prefix frame is
treated exactly like None → delegate to the unchanged loop102 chain (as
113b does for double-None). Applied to the B92 N-hop branch and the B73
explicit-2-hop branch; compound-guard, non-explicit clarify, hearsay
screen, and teach path identical to loop113b. Scorer v2 identical to exps
113/113b.

Overall: M1 PASS, M2 PASS, M3 PASS, M4 PASS. The 113b M1 FAIL is fixed
with zero movement anywhere else — and two fresh teach-gap wrongs fixed
as a bonus.

## Marks table (sealed `PASSMARKS.md`, sha `678d26b8…`)

| Mark | Result |
|---|---|
| M1 loop102 marks P2+P3(L1-L6)+P4 vs loop113c identical to loop102 | **PASS**: P2 0 OK->BUG, 0 still-BUG (B7/C2/C5/D8 all OK); P3 L1-L6 all pass (L5-Z1 60/60, L6 200/200 × 3 seeds, L5-Z2, L1-L4); P4 30/30, 0 false refusals |
| M2 loop113c Fable-Edit-200 right behaviour 200/200, 0 wrong | **PASS**: 200/200, wrong 0, 0 teach rejects |
| M3 loop113c fresh-4hop correct ≥ 140, wrong ≤ 5 | **PASS**: 145 correct, 52 abstain, 3 wrong (056/103/196); exactly 125+200 moved vs 113b (wrong→abstain) |
| M4 whole wave < 25 min Mac CPU | **PASS**: 52.7 s bench + 40.2 s marks = 92.9 s |

Ledger P113c.1–P113c.4: TRUE × 4 (4/4).

## Before/after tables (scorer v2, per type: correct / abstain / wrong)

Fable-Edit-200, loop113b (before): mquake-twohop 100/0/0; reversal 50/0/0;
abstain-absent 0/25/0; abstain-broken 0/25/0. Right behaviour 200/200.
Fable-Edit-200, loop113c (after): IDENTICAL, 200/200, 0 wrong, 0 teach
rejects.

Fresh-200, loop113b (before): 145 / 50 / 5, contains_gold 146, teach
rejects 22 (12 items). Fresh-200, loop113c (after): 145 / 52 / 3,
contains_gold 147, teach rejects 22 (same 12 items). Wrong ids
056/103/196 (the mid-chain "and"-guard rejects, out of scope as
registered); 125 and 200 (child-hop teach-gap partials) move
wrong→abstain — their B92 frames were 1-hop prefixes naming fewer hops
than asked, now delegated to the loop102 chain, which clarifies.

## Mechanism

1. **The 4 P2 cases are fixed.** B7/C2: "…official language of the country
of citizenship of Roberto Merhi?" → B92 walks only `[country_of_citizenship]`;
after deleting the walked cues, "official language" still matches → partial
→ loop102 chain → clarify (abstain). C5: "Where was the author of Fasti
born?" → frame `[author]`; "born" survives → partial → clarify. D8: "Who
is Poland's capital in 2019?" → trailing year qualifier → partial →
loop102 → "I don't know…" (abstain).
2. **No full frame is disturbed.** The gate is deliberately asymmetric:
consumption over-eats (substring match, longest cue first, so stems like
"creat" eat "created"), entity names are deleted before the leftover scan
("death" in "Death Eater" is not a relation), and scaffolding cues
("where", "city where/​located where", "located", "home to", "played",
"spoken", "work") never count as leftovers. Single-word cues otherwise
match on word boundaries ("office" never fires on "officer"). Result: all
145 full-4-hop frames still ask through the composer; per-item verdicts on
split-A are byte-identical to 113b.
3. **M3's remaining 3 wrongs are untouched, as predicted** (056/103/196,
mid-chain teach-gap partials with no notebook evidence — out of scope).

## 5 most instructive turns (verbatim)

1. FIXED (B7): `What is the official language of the country of
citizenship of Roberto Merhi?` → `I didn't understand that. Could you say
it another way?` (was: answered Spain's language over a broken chain.)
2. FIXED (D8): `Who is Poland's capital in 2019?` → `I don't know
Poland's capital_in_2019.` (was: leaked `Poland's capital is Warsaw.`)
3. FIXED (C5): `Where was the author of Fasti born?` (birthplace
forgotten) → clarify (was: `Fasti's author is Ovid.`, a 1-hop prefix).
4. BONUS (fresh-125): child-hop partial now abstains instead of answering
wrong; stage `none` via the loop102 chain.
5. Unchanged good (fresh-001): full 4-hop chain still walks end to end,
exact gold, stage `loop113c-nhop`.

## What it means

Composer-covered questions are now safe against short-prefix frames: the
loop answers a frame only when the frame accounts for the whole question,
and anything less falls back to the loop102 chain that already knew how
to stay quiet.

## What it does not mean

It does not mean every confident wrong is gone: 3 fresh teach-gap wrongs
(056/103/196) remain, where the notebook holds no evidence of any
continuation — a teaching-coverage problem, not a routing problem, and a
different one change.

## Deviations / reproduce

Deviations: (a) pre-seal gate prototyping ran pure-function probes plus
two full scratchpad bench comparisons under `scratchpad/fable_loop113c/`
(no artifact writes; first version regressed 32 fresh items via the
loop102 2-hop truncation, fixed by substring consumption + entity-span
deletion + the scaffolding denylist before sealing); (b) the scratchpad
probe dirs were removed after the registered run. No other agent's files
touched; nothing committed. Reproduce: `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B scripts/fable_bench113c_run.py --run`
(52.7 s) then `python -B scripts/fable_loop113c_marks.py --mark all`
(40.2 s). Rows:
`artifacts/fable-bench113c-20260922/fable_bench113c_*_rows.jsonl`.
Daemon launch: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run
--offline --no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_loop113c_agent.py --daemon --dir DIR --config
artifacts/fable-bench113c-20260922/loop113c-config.json`.
Questions for Ben: none.
