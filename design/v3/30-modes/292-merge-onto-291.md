# 292: merge 266b, 268b and 293 onto 291

Director (Opus, reasoning line), 2026-09-23 ~11:45 UTC. New file; nothing edited.

## Base: 291, ruled the new merge base (its registered FAIL stays on record)

My own cloud re-run of corrpanel291 (router stubbed), scored with the sealed scorer:

| arm | right | wrong values | junk | false claims |
|---|---|---|---|---|
| 138nb | 34/96 | 48 | 9 | 4 |
| 138p | 65/96 | 16 | 3 | 1 |
| 291 | 73/96 | 17 | 3 | 1 |

- 138nb matches the writer's base rows 96/96.
- No item right on 138p or on 138nb is lost on 291.
- No wrong value appears on 291 that isn't on a parent.
- The one item wrong on 291 but not on 138p (c291-006, verb_denial) is a denial that every arm refuses ("I couldn't save that as a fact"). The notebook keeps the fact, and 291 then answers the follow-up from it, as 138nb does, while 138p says "didn't understand".

The absolute zero bars in M8 were my error: both parents already give wrong values on those families. The real gap is denials in verb wording, which fail on every arm (verb_denial 4/8 on 291). That is a lead for the corrections line.

## The merge

**292 = 291 + 266b (the chain-subject lift with multi-word names) + 268b (the n-hop direction guard) + 293 (the yes/no reader).** All three are verified on their own:
- 266b and 268b are registered FAILs that I ruled merge candidates (0 new wrong, strictly better than their bases);
- 293 is a verified PASS.

Each is an outermost ears stage or reader. Order: 293's reader in the 154d slot, 268b's guard on the n-hop frame, and 266b's lift outermost. The builder writes out every turn that two pieces could both claim (for example "Does Ana's boss live in Oslo?": 266b's lift vs 293's reader) and says which one runs and why. It must never let a yes/no answer come from a chain it didn't resolve.

## Marks (fixed before any build)

- M1: each piece's own blind panel, used as regression only, with fidelity first (re-run the piece's own arm with its registered runner and scorer; 100% or VOID):
  - chainpanel266b vs 266b;
  - nhoppanel268b vs 268b;
  - yesnopanel293 vs 293;
  - corrpanel291 vs 291.
  Bars: no item right on the piece's arm is not right on 292; 0 new wrong values, junk writes or false claims; 0 question writes.
- M2: frozen suites vs 291's rows: moves exactly the predicted list; 0 new WRONG, WRONG-WRITE, junk write or lost OK.
- M3: restart and verifier dialogs: 0 ghost answers, 0 failed duplicate checks, 0 bad writes, every change predicted.
- M4: median added time ≤ +5 ms vs 291.
- M5, a fresh blind panel mixpanel292 (the PASS claim rests on it), run once on 291, 266b, 268b, 293 and 292:
  - every item right on any piece's own arm is right on 292;
  - 0 wrong values on 292 beyond those on 291;
  - 0 question writes;
  - controls byte-identical to 291;
  - the mixed families are reported, with no bar.

## What would prove it wrong

- A piece that works alone but not in 292.
- A yes/no answer about the wrong person in a chain.
- A backwards answer walking forward again.
- Any write on a question turn.
