# 154f — plain negation removes a taught value (Muse)

Base: loop154e. The director probe (10:12) showed `Rana's language is
not Hindi.` answered `I can take one fact at a time — could you split
that?` and changed nothing: only the `No, X's R is Y, not Z.` form
could remove. 154f adds the missing plain form.

## The one change

`scripts/fable_fix154f_negate.py`: `parse_negate154f` matches ONLY
single-hop `X's R is not Y.` / `X's R isn't Y.` — one-word name
anchored at turn start, no trailing `?`, no possessive inside R or Y.
`scripts/fable_loop154f_agent.py` subclasses loop154e read-only
(`Loop154fEars` adds the pre-scan, `Loop154fAgentLoop` adds the
`negate_one154f` action, `Loop154fDaemon` with `idle_seconds=30.0`).
The pre-scan cannot divert sealed 154e turns: correct-not, forget-one,
teach, ask, yes/no and `Say`/`Pretend` shapes have disjoint anchors.

Behaviour: Y current → retract exactly the rows showing Y via
`nb.retract()` (appends the notebook's RETRACT event kind — the same
kind 154b's `_act_correct_multi154b` uses at
`fable_loop154b_agent.py:165`, which is the path 154c's correct-not
takes) and reply one fixed sentence naming remainers (`OK, Rana's
language is not Hindi. I still have Urdu and Bengali.`) or, when none
remain, `OK, Kim's boss is not Lee. I don't have another boss for
Kim.` Single-valued relations take the same path: taught facts are
only ever changed by the user's hand, so the teacher may retract a
single value directly. Y not current → 0 writes,
`I don't have Tamil as Rana's language.` Unknown X → falls through to
the base reply. Questions (`Is X's R not Y?`), multi-hop negations
(`The city of Kim's boss is not Oslo.`, `Kim's boss's city is not
Oslo.`), possessive values and directive prefixes never match, so the
base reply is byte-identical. Never an inference: asks still write
nothing (verified: 0 new events on every ask in the seal file).

## Evidence

N1 102/102 (90 turns: 8 multi removals, 6 single removals, 8 misses
with 0 events, 4 unknown, 19 traps). N2: bench 800 items 0 moves/0 new
wrong; marks123 per-case verdict+reply identical (only predicted
volatile metadata); G3 0 moves/0 new wrong/write. Pre-seal trigger
scan: 0 possessive-negation turns in any frozen input except redteam136
C072, which runs on a fresh notebook (Mira unknown → falls through).
Seal 10/10 OK post-run; no post-seal edits.

## What it means

Plain "is not" deletes exactly the fact named — the smallest step from
"split that" to a teachable removal on every relation.

## What it does not mean

It does not retract by guessing (exact display match only), does not
touch multi-hop or question handling, and does not let inferences
overwrite taught facts.
