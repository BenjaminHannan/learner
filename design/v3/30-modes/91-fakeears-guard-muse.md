# 91 — FakeEars guard (2026-09-22, Muse)

## Problem

Red-team-81 found the M1 doorway core trustworthy but filed two FakeEars
scaffolding limits that write wrong rows silently (doc 81, cases D_q_vs_s-01
and E_double-01). The persistent daemon (`scripts/fable_daemon74_run.py`)
listens through FakeEars by default, so a real person could store a corrupted
value tonight: `"Mira's city is Lisbon?"` saves `"Lisbon?"` (the statement
regex strips `.` but not `?`), and `"Mira's city is Lisbon and Mira's pet is
a cat."` saves city=`"Lisbon and Mira's pet is a cat"` while the pet fact is
lost. The doorway writes its action faithfully; the parser is at fault.

## Design

Add one wrapper, change nothing. `scripts/fable_earsguard91.py` defines
`GuardedEars(inner)` (default inner: `FakeEars`), implementing the glue
loop's `Ears` protocol (`hear(turn) -> list[dict]`). It forwards the turn to
the inner ears, then screens each `teach`/`correct` action's value:

1. contains `?` → clarify "Was that a question?";
2. packs a second fact — matches another possessive relation phrase (`X's
   <word> is`, any case), a second copula (`is`/`are`), ` and <Name>'s`, or
   `;` — → clarify "I can take one fact at a time — could you split that?";
3. longer than 6 whitespace-separated words → same split clarify.

All other actions (questions, yes/no, clarifies, and every clean one-fact
write) are returned exactly as the inner ears produced them. Non-write
actions are never inspected. Because the wrapper only narrows what reaches
the doorway, every doorway guarantee (CONFLICT gating, supersede, no
personal inference, hop limits) is untouched.

Plumbing: `scripts/fable_earsguard91_daemon.py` is a small launcher with the
daemon's CLI that wraps the daemon's own `build_ears` hook
(`scripts/fable_daemon74_run.py` is imported read-only). `scripts/
fable_earsguard91_run.py` is the registered driver: it imports the case list
from `scripts/fable_redteam81_probe.py` and the scorers from `scripts/
fable_turns84_run.py` (both read-only) and runs G1–G4.

## Why clarify instead of split or strip

Stripping `?` would convert a genuine question into a false fact; silently
splitting on "and" would invent facts the user may not have meant (and real
splitting is the ears agent's job). Asking one plain question back is the
conservative default: zero new wrong-write shapes are introduced, and the
user can simply retype the fact(s).

## Evidence

One sealed run: G1 2/2 clarify with 0 writes; G2 74/74 re-run, 5 outcomes
changed (the 2 reproducers plus the 3 follow-on answers that now correctly
report nobody known), 0 new wrong writes; G3 60/60 status match, 0 wrong
writes; G4 daemon selftest exit 0 with D1–D4 PASS in seeds 1, 2, 3. All
P91 predictions TRUE. Full tables in
`artifacts/fable-earsguard91-20260921/`.

## Limits

A legitimate value over 6 words (e.g. a long place name with context) will be
asked to split — safe but annoying; the 6-word bar is documented in
`PASSMARKS.md` so the ears agent can revisit it. Multi-fact turns are not
saved as two facts, only bounced. Genuine `?`-questions already parse as
`ask` and are unaffected.

## What it means / does not mean

Means: the daemon is safe tonight from these two silent corruptions with no
change to any existing module. Does not mean ears is fixed: proper
question-vs-statement parsing and clause splitting still belong to the ears
agent; this guard should be retired once real ears lands.
