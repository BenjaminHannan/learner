# 113d — The fallback path gets the same half-understanding rule (Muse, 2026-09-22)

For Ben in plain language: last time (exp 113c) the assistant learned that
a half-understood question counts as not understood — but that rule only
watched the NEW part of the brain (the N-hop composer). The OLD part (the
loop102 fallback it hands confusing questions to) still had the same bug:
asked a 3- or 4-hop question, it answered a 2-hop PREFIX, e.g. "CM Punk's
spouse's country of citizenship is Spain" when the question asked for the
language, the continent, or something with a year on it. This experiment
applies the exact same rule to the fallback: if the answer the old path
found leaves relation words or qualifiers of the question unconsumed, the
assistant stays quiet instead of answering the shorter question.

## The one change

`scripts/fable_loop113d_agent.py` (new, prefix-owned; nothing else edited).
`Loop113dEars` subclasses `Loop113cEars` and keeps 113c routing exactly,
except every delegation to the loop102 chain goes through
`_fallback_guarded()`: the exact loop102 chain runs, then any returned
`ask` whose relations fail 113c's `frame_consumes_question()` (reused
byte-for-byte: trailing year qualifier, then every walked relation's cues
deleted longest-first by substring, entity names deleted, then any OTHER
relation's cue still matching means prefix) is replaced with the honest
abstain (`L113.CHAIN_MISS_TEXT`, the loop's own "I didn't understand"
clarify, which every abstain scorer counts). Asks that consume the
question, and all non-ask actions (teach / correct / forget2 / clarify),
pass through byte-identical. Sitting on the fallback's returned actions
(rather than inside one stage) covers Bench73Stage and any other 2-hop
question path reached through the fallback.

Pre-seal probes (pure functions, no daemon): `B73.compose_question`
returns exactly the reported 2-hop prefix frames on B5 / Q2 / U1 / V4 and
`frame_consumes_question` is False on all four; an exact 2-hop question
consumes True; a 1-hop FakeEars ask ("Who is C00's capital?") consumes
True — so legitimate short answers survive the gate.

## Evidence (sealed P113d.1–P113d.4 before any run; outcomes appended after)

Registered runs (all Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B ...`):
`scripts/fable_bench113d_redteam124.py --run` (D1),
`scripts/fable_loop113d_marks.py --mark all` (D2),
`scripts/fable_bench113d_run.py --run` + `scripts/fable_bench113d_121.py
--run` (D3).

## Limits

Question-side routing only; teach patterns, qualifier storage, and the 3
remaining 113b teach-gap fresh wrongs (056/103/196) are untouched. A
prefix the gate cannot see (leftover words all scaffolding or entity
names) keeps 113c behaviour — the gate only reroutes toward abstain, never
toward a new answer, so it cannot invent a wrong the fallback did not
already produce.

## What it means

The half-understanding rule now covers the whole question path: composer
and fallback both answer only what consumes the full question.

## What it does not mean

It does not mean the notebook knows more: where no evidence was ever
taught, the loop stays quiet rather than guessing — answers there need
teaching coverage, not routing.
