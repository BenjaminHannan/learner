# RESULTS — Experiment 62: thought v3 groups + no-value rows

Wrapper `scripts/fable_thought62_schema.py` (imports v2, never edits it) implements doc 56's extensions 1–2. Conformance `scripts/fable_thought62_conformance.py --selftest`. **SCORE: PASS 5/5.**

## Marks (integer counts)

| mark | bar | got | verdict |
|---|---|---|---|
| T1 old contract suite through wrapper | 32/32 | 32/32 | PASS |
| T2 new wrapper cases | >= 20/20 | 22/22 | PASS |
| T3 sentences rescued | >= 15/17 | 17/17 (empty 10, link 2, group 5) | PASS |
| T4 answers from empty/link rows | 0 | 0 of 7 probes | PASS |
| T5 to_v1 byte-identical on ungrouped rows | all | 8/8 | PASS |

## The 17 sentences: verdicts

| # | sentence | verdict | extension |
|---|---|---|---|
| W13 | citation fragment ("CRC. (1996)...") | rescued | empty/fragment |
| W19 | Thomas Frank citizenship (not stated) | rescued | empty/absent |
| W20 | USA contains Texas (works-in-Texas text) | rescued | empty/absent |
| W21 | college HQ (title fragment) | rescued | empty/fragment |
| W22 | county border (sales-tax text) | rescued | empty/absent |
| W23 | NYC capital (club text) | rescued | empty/absent |
| W24 | Poland country (holiday quote) | rescued | empty/absent |
| W25 | Cambridge UP HQ (byline only) | rescued | empty/fragment |
| W27 | Kahlur capital (fort location only) | rescued | empty/absent |
| W30 | USA–Canada diplomatic (chart legend) | rescued | empty/fragment |
| W26 | economics tables | rescued | group (2 cells) |
| W28 | survey percentages (66%/71%) | rescued | group (2 cells) |
| W29 | geology text (La Quinta fm.) | rescued | group (2 cells) |
| A17 | SSA sota+adapts+superior | rescued | group (3 rows) |
| A18 | "three key innovations" list | rescued | group (3 rows, list-index qualifiers) |
| A19 | code URL sentence | rescued | link/metadata |
| A20 | kernel URL sentence | rescued | link/metadata |

Nothing is "still not representable": 17/17. Full group answers only after every member is promoted (partial → `partial_group`); plain `ask()` on a member abstains; link/empty rows refuse promotion and never answer; v2-only readers see ungrouped rows natively, grouped rows as ordinary rows, no-value rows not at all; tamper still raises `LogCorrupt`.

## Deviations from the plan

1. Table groups hang off a document entity (e.g. "survey paragraph") with one row per cell, so a group is one claim about one subject.
2. A19/A20 link URLs point at the paper pages — exact code targets were not fetched (offline run); the sentence quote says so.
3. `ask_group` counts answering-source members; a stale proposed original covered by its taught promotion does not block the group.

## Reproduce

`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_thought62_conformance.py --selftest`

## What it means / What it does not mean

It means the notebook can now record *that a sentence says nothing usable* (with why) and *that three rows are one claim*, without weakening any v2 guarantee — the old 32 cases still pass and the adapter output is byte-identical. It does not mean the gold rows are true: they record what each sentence does or does not state, and no group answers until Ben promotes every member.
