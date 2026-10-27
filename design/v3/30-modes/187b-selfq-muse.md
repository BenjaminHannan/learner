# 187b — Self-question paraphrase routing, fresh registration (Muse)

Date: 22 Sep 2026. Prefix `fable_fix187b_` / `187b`. Artifact:
`artifacts/fable-selfq187b-20260922/`. Scripts (NEW, additive-only):
`scripts/fable_fix187b_probe.py`, `scripts/fable_fix187b_suites.py`.
Agent: the CURRENT `scripts/fable_loop187_agent.py`
(`26298ed95eb6c2f7…`) reused read-only — deliberately NOT copied (the
config path is a runtime argument; the module hard-codes no artifact
path, so a copy would add a filename without changing behaviour).
Registered: S1 34/34, S2 as predicted, 7/7 ledger predictions TRUE.
SCORE PASS.

## Why 187b exists

Exp 187 is registered FAIL: its agent file changed after its seal (the
`What's`-contraction guard in `classify_self187`; sealed `3d16d7e2…`
vs current `26298ed9…`). The edit was a genuine fix — without it,
"What's your name?" hits the possessive-`'s` user/third-person guard
and falls through to the D8 user-name reply (the 187 transcript shows
Q09 failing exactly that way, 32/33). Per the rules a post-seal edit
is FAIL whatever the re-run shows, so 187b registers the current code
fresh: same logic, new case file, new seal, predictions before the run.
No agent-logic line was touched by this experiment.

## The one routing step (unchanged from current 187)

On the notebook-missed path only, `classify_self187` (closed stdlib
regexes) routes self-question paraphrases before the frozen route127
router: maker (`who (has|did)? made|built|created|trained you`),
identity (`who|what are you`), name (`what's|is your name`, `what are
you called`, `do|have you (got a|a) name`), cando (`what can you do
(for me)?`, `what do you do`, `capabilities`, `able to do`). The
user/third-person guard drops maker/identity/name when the turn says
`my|me|mine|myself|who am i` or carries a possessive `'s` (skipping a
leading `What's`). Cando reuses the lineage C24 capability sheet
verbatim (text-independent: canonical question per intent); maker /
identity / name serve fixed honest replies (`MAKER187`, `IDENTITY187`,
`NAME187`) because the lineage has no such answers — written only from
the 48 brief + D2, claiming no maker and no name. Everything else runs
the 138g path byte-identically.

## The fresh case (34 turns, zero string overlap with case187.json)

Setup teaches four fresh facts (Nora/Lyon, Eve/Max, Iris, Otto/Ava).
Fourteen self turns cover made/built/created/trained (has/has-ever
auxiliaries + a case variant), who/what-are-you, what-is/what's-your-
name, have-you-got-a-name, and for-me / able-to / do cando. Nine traps
keep the same trap shapes with fresh content (no-`?` user questions,
third-person questions over the new names, one taught-entity
who-made). Seven `you`-statements check the no-write path.

## Evidence

S1 34/34 per-turn checks (10.1 s). Frozen suites vs sealed 138g rows:
redteam136 145 cases 0 moves; redteam143 124 cases 0 moves; bench121
4×200 items 0 moves, 0 new wrong; marks123 9/9 suites per-case
identical after volatile scrub (p3/p4/rt81 FAILs inherited
byte-identical; only nominal diff the predicted sleep SKIP
agent-filename line). sessions152 shows exactly the two predicted
moves: frozen turns with text `who are you` (S2-casual-friends n=10,
S4-pets-identity n=8) move UNHELPFUL → OK, i.e. 138g's D8 user-name
misroute is replaced by the honest identity reply, with 0 new wrong
and 0 new writes. Longest run 887 s < 1500 s. Seal 6/6 OK post-runs.

## Pilot catch (pre-seal, code untouched)

The first draft case contained "Who did make you?" / "Who did
train you?" — grammatical did+base-form turns that fell through to the
generic decline: the closed maker pattern pairs `did` only with
past-tense verbs, so its `did` branch fires solely on ungrammatical
input ("Who did made you?"). That is outside the registered closed
set, so it is recorded as a known boundary for a future experiment,
not a sealed claim and not a code change. The sealed case stays
inside the closed set (has/has-ever forms).

## What it means

Self-questions about the agent now get honest lineage-grounded answers
instead of the user-name misroute or a generic decline, while every
frozen suite stays put except two session turns that get strictly
better (UNHELPFUL → OK) exactly as predicted in writing.

## What it does not mean

The router is still a closed pattern list, not open English (see the
did+base-form boundary above); the maker/identity/name replies are
fixed honest text, not learned facts; nothing about teaching,
reasoning, sleep, or the notebook changed.

## Deviations

None from the 187b plan. One pre-seal case-file correction (the two
did+base-form turns replaced with closed-set has-forms after the
pilot caught them); pilots ran before the seal, one registered run
per suite after. No post-seal edits to any sealed file.
