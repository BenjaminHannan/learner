# 212 — Selfgate: the self-router only fires on question-shaped turns (Muse)

## Problem
Loop138i answers plain statements about the user or third parties as if
they were questions about itself, dropping the user's fact. Director-
verified: `My favourite colour is teal.` -> `I do not have favourites.`
(D1) and `Tired is my cat's name.` -> `You never told me your name, so I
do not know it.` (D8). Root cause: on any notebook miss the turn is fed to
the self-question router (route127 over live state), whose keyword-overlap
scoring happily routes statements (`favourite`+`colour`, `name`) to
decline-intents whose answer bodies talk about the assistant.

## Change (one)
`scripts/fable_loop212_agent.py`: `Loop212AgentLoop` subclasses
`Loop138iAgentLoop` and wraps `turn()` only. When
`should_skip_self_router212(text)` fires — statement-shaped (normalised
turn does not end with `?`; first `[A-Za-z]+` word via the base's own
`_FIRST_WORD188` not in `_QWORDS188`/`_AUX188`, reused by import from
`fable_loop188_agent`) AND no whole-token second-person word (closed set:
you, your, yours, yourself, u, ur) — the exact function object the call
site reads (`L138._route127`, called at `fable_loop138g_agent.py:324`,
reached via MRO 138i -> 138h.turn -> 138g.turn) is swapped for a DECLINE
stub for that turn only (restored in `finally`). The turn is then served
the base's normal decline, byte-for-byte the router-declined path. Nothing
else changes: ears, `_act`, reasoner, notebook, sleep, daemon are 138i's.
`Tell me about yourself.`, `Describe yourself.`, `You are clever.` keep
today's route (they carry `yourself`/`You`); questions are untouched
(`Where am I from?` keeps its separate bug by design).

## Why this shape
The router only runs after the notebook already missed, so skipping it can
never lose a save — the only possible outcome is the honest decline. The
swap-stub (rather than a copied turn body) guarantees every non-gated turn
executes the sealed 138i path untouched, which is why M2/M3 can be 0-move.
The statement test is deliberately wider than 188's (command openers
count as statements); the second-person rule is what protects imperatives
addressed at the assistant.

## Evidence
32/32 G-cases fixed (intents D1/D2/D3/D7/D8/D10/C1/C14/C25/C27, 0 facts);
49/49 S-cases byte-identical; frozen suites, marks123 (except predicted
rt81 `I_edges-03` UNCLEAR->OK), bench v3 4x200, and the self105 scorer all
match the sealed 138i rows. Full counts in `RESULTS.md`.

## Limits
Gated statements decline rather than save (no new teach shapes learned);
bare single words (`Mira`) now decline instead of guessing; a predicted
rt81 row flips UNCLEAR->OK because the decline carries the judge's wanted
marker. Question-shaped self bugs are out of scope.
