# 167e — one surface rule for every relation-key reply (Muse)

## Problem

Loop167c fixed only the `Saved:` confirmation. The director probe
09:10 showed the same raw-key leak in four more templates: `Forgotten:
Ada's place_of_birth.`, `I don't know Ada's place_of_birth.`, and by
the same code path the CONFLICT change-prompt and BROKEN_CHAIN lines.
167c's G2 FAIL was exactly this: q4 improved 7 -> 4 through Saved
lines, while the other templates kept leaking.

## Design

One change, mouth-side only: `Label167eMouth`
(scripts/fable_fix167e_label.py) wraps loop167c's mouth and applies
the answer path's own rule (`key.replace("_", " ")`, the exact
expression at scripts/fable_agent_loop.py:166-167) to the relation
slot of Saved, CONFLICT, MISSING_FACT, BROKEN_CHAIN, and Forgotten
replies, for keys with underscores, tolerating Listening's
dropped-question prefix. Ears, reasoner, notebook, matching, stored
keys, and reply choice are loop167c's literally, so non-key behaviour
is byte-identical by construction. Templates with no relation slot
(clarifies, AMBIGUOUS listing, UNKNOWN_ENTITY, answers) and internal
Saved texts that never reach the mouth pass through untouched; the
full enumeration with file:line is sealed in PASSMARKS.md.

## Evidence

T1 (34 turns, every key template x 3 underscore relations):
34/34 OK, zero underscore tokens, scrubbed events identical to
loop167c. T3: 25/25 loop167c probe rows byte-identical. G1: 600
bench items, only the 37 predicted MISSING replies moved. G2:
marks123 per-case identical except F6/L6/S2 rt110 replies; q4 0
leaks (predicted FAIL -> PASS). G3: 449 turns, zero moves. Zero new
wrong anywhere; seal 10/10 clean; max run 223 s.

## Limits

Stored keys keep underscores (only the surface changes); reply
choice never changes, so a wrong-but-spaced reply is still wrong;
q4 scans only p2/p4/rt110/q1 reply fields. Possible follow-up (not
proposed now): nothing -- the surface is uniform.
