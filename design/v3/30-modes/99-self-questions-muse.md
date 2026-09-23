# 99 — Self-questions through the live agent (family demo)

Date: 22 Sep 2026. Prefix `fable_self99_`. Artifact:
`artifacts/fable-self99-20260921/`. Script: `scripts/fable_self99.py` (NEW;
imports `fable_loop90_agent` and `fable_notebook_contract` read-only, edits
nothing). Registered: S1 40/40, S2 0 hallucinations, S3 10/10, 0.9 s.

## Why

For Ben's family demo, "the model answers questions about itself": how many
facts it knows, what was taught last, who told it Mira lives in Paris, what
came from the internet, whether it has slept, what it cannot do, what it has
forgotten, what it is doing right now — plus honest declines (favourite
colour, feelings, yesterday). Like demo 54's Q9 self-report, every claim
must be read from state, never generated.

## Design

`Self99Agent` wraps the loop90 build (`build_agent`, sleep threshold huge so
sleep never fires). It adds four live-state structures and nothing else: a
turn log (every Ben line with reply, ears stage/score, write flag), a mode
log (tick + mode after each turn), fact origins (`fact_id -> {by: Ben, turn}`
stamped at write time; `{by: web-quarantine}` for the filed row), and a
forget log (`fact_id -> turn` Ben retired it, from active-set diffs).

`answer_self()` matches 40 frozen templates (scaffolding, stated openly).
Each branch reads state at answer time: counts from `active()` + source
filters; last/first teachings from FACT events; corrections from the
`superseded` map; forgetting from RETRACT events; web from the quarantine
row's provenance; mode from `loop.mode`; turns/answers/writes from the turn
log and loop counters; sleep from `counters["sleeps"]` (0, answered
honestly as "not slept yet"). The ONLY fixed text is the capability sheet
(`CAPABILITY_CAN` / `CAPABILITY_CANNOT`, written once): everything the agent
can/cannot do as plain software.

Session: 20 teaches ("Mira's mother is Ana." …), 2 corrections
("Actually, …"), 3 asks (two answerable, "What is Leo's mother?"
MISSING — evidence for the unsure-list), 1 quarantined web row filed as
actor `thinking` with url + quoted span (mirrors the Z3 doctrinal call), and
1 forget. The forget line cannot be parsed by the template ears, so the
wrapper sends it through the SAME M1 doorway (`listening.hear`) with the
same rights and logs it as a turn — same behaviour, honest log.

Checking (script, never eye): per question, the checker re-derives each
value from the notebook/loop and asserts equality; S2 scans every answer
for integers and capitalised names and requires each to occur in the live
state snapshot; S3 requires each decline to carry a fixed plain-words
marker ("I do not have…", "You never told me…", …).

## Evidence

S1 40/40, S2 0 invented numbers/names, S3 10/10 declines. Session counts
exact: 19 active taught, 6 people, 1 quarantine, 2 corrections, 1 forgotten,
0 proposed, 0 inferred, 0 sleep-derived, 26 turns, 3 answers, 22 writes,
0 clarifications, 0 sleeps.

## What it means

Self-report generalises from Q9's single report to 40 checkable questions
with zero hallucination on this run — the demo beat Ben asked for.

## What it does not mean

Forty templates, not open English; no confidence claims; the capability
sheet is authored, not learned; sleep unexercised (history reads 0).

## Deviations

Forget-line doorway-direct routing (above); scaffolding iterated in the
scratchpad while the 40 questions stayed frozen; one registered run.
