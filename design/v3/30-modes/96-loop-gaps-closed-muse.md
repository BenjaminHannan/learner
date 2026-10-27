# 96 — Loop gaps closed (Muse, 2026-09-22)

## The two gaps

Exp 90 composed every verified piece into one running agent, but the
director found two holes. First, loop90's ears chain ends in plain FakeEars,
which silently stores two corrupt shapes (red team 81): a `?`-suffixed value
(`Lisbon?`) and a packed double fact (city = `Lisbon and Mira's pet is a
cat`, pet lost). Exp 91 had already built the fix — `GuardedEars` — but the
loop never plugged it in. Second, loop90's Z3 re-ran the old red-team probes
against the old classes, reproducing the sealed 64/3/2 and 53/1/2 tallies;
that proves the probes still run, not that the loop itself resists them.

## Design: one wrap, nothing else

`scripts/fable_loop96_agent.py` adds `Loop96Ears(GuardedEars)`: it forwards
each turn to the loop90 `ChainEars`, screens every `teach`/`correct` value
(`?` → "Was that a question?"; packed second fact or >6 words → split
clarify), and passes everything else through byte-identical. A `bind()`
delegate plus attribute passthrough keeps the chain's notebook binding and
the daemon's stage/score logging working. `build_agent96` = `build_agent`
then one wrap; `Loop96Daemon` = `Loop90Daemon` with the guarded agent
inside; CLI mirrors loop90 (`--daemon --dir --config --once
--write-config`). Notebook, reasoner77, mouth, QuarantinedThinking89,
HardGate46Sleeper, tau-hat gate: same classes, same config, same values.

Why clarify instead of repair is exp 91's ruling, inherited: stripping `?`
would turn questions into false facts, and splitting invents facts. The
guard retires when real ears lands.

## Evidence (sealed L1–L6, all PASS)

L1 replays both reproducers through the loop96 mailbox (fresh daemon each):
2/2 clarify, 0 rows; the same turns through loop90 write the corrupt FACTs.
L2 runs all 74 red-team-81 cases through both agents: 0 wrong writes on
loop96, and exactly the exp-91 G2 five change (the 2 reproducers plus the 3
follow-ons that now correctly know nobody). L3 executes fix77's three F1
reproducers against the loop96 notebook + reasoner: qualifier filtering,
bool spelling/MISSING, and tail-seal detection all hold — including through
the actual `Loop90Notebook` open path. L4 swaps the loop96 thinker class
(`QuarantinedThinking89`, confirmed as the wired module) into the RT79-18,
09, and 53 builders: BUG fixed (kept=0), both site pairs count as 1 site
with web-verified=0, exactly as exp 89 ruled. L5 re-runs Z1/Z2 unchanged
apart from the agent swap: 60/60 with 0 wrong, 200/200 with 0 WRONG. L6
re-runs the kill-9 procedure on the loop96 daemon: 200/200, 0 wrong, 0
dupes in seeds 1, 2, and 3.

## Limits

The guard only narrows: genuine long values get bounced, double facts are
bounced rather than split, and L3/L4 exercise the loop's classes through new
drivers rather than end-to-end English (the bench73 stage never fires on
M1-style turns, so full-English red-teaming of the loop is still open work
for the ears agent). One-word-line limits of the M1 doorway remain.

## What it means / does not mean

Means: the running loop is safe tonight from every attack the red teams
proved, with zero changes to any existing module. Does not mean ears works:
template parsing plus a safety wrapper is still scaffolding, and the neural
rung-2 checkpoint plus mouth53 remain the two documented replacements.
