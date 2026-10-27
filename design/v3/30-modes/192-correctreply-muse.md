# 192 — Correct-reply: corrections say what they replaced (Muse)

## Problem
Director probe 09:49 on loop167e: after "Kim's boss is Sam.", both "No,
Kim's boss is Lee." and "Actually, Kim's boss is Lee." reply "Saved:
Kim's boss is Lee." The user is never told Sam was replaced. The plain
re-teach "Kim's boss is Lee." asks "I have Kim's boss as Sam. Do you
want me to change it to Lee?" — that question stays.

## Fix (reply text only, outermost)
One new mixin, `CorrectReply192Mixin`
(scripts/fable_fix192_correctreply.py), stacked outermost on the loop
class in scripts/fable_loop192_agent.py. After the loop's own
_listening_tick (writes, records, said, experience, counters all
byte-identical to loop167e by construction), it rewrites the outgoing
English of exactly those write records whose turn appended one FACT
event with `supersedes` set AND whose turn the user marked as a
correction — explicit forms (No, / Actually, / Correction: / Sorry-I-
meant, verb twins, which all arrive as act=correct) or a yes to the
change question (line "yes"). The Saved confirmation becomes one fixed
sealed template naming both values:

    Updated: Kim's boss is Lee (it was Sam).

with the 167e relation surface (underscores spaced, the answer path's
own `replace("_", " ")` rule).

## Scope decisions (sealed)
- First-time teaches keep "Saved: ..."; repeats keep "I already have
  that."; declined changes keep "Okay, I left it as it was."; the
  change question itself is untouched (no FACT is written on those
  turns, so the rule cannot fire).
- Multi-valued additions never set `supersedes` (the contract
  accumulates them), so they keep loop167e's reply. In loop167e every
  English-taught relation is functional, so this path is vacuous
  there — stated for completeness.
- Silent bench73-stage auto-corrects (a plain re-teach the template
  ears upgrade to act=correct with no user correction marking) keep
  "Saved:". Reason: sealed harnesses judge those teach replies
  literally — redteam143's `teach_accepted()` takes only "Saved:"/"I
  already have that.", so moving them flips 7 Q-cases to
  HARNESS-ERROR. The brief's parenthetical ("explicit correction
  forms, or a yes") covers user-marked turns; silent upgrades are
  neither. The structured-vs-silent discriminator is the turn text:
  explicit ⟺ it carries the sealed F3 correction prefix
  (`fable_loop102_agent.strip_correction_prefix`).
- Consequence, predicted in PASSMARKS: redteam143 Q1–Q7 (whose teaches
  use "Actually,"/"No,"/"Correction:" explicitly) move their teach
  reply to Updated and their verdict to HARNESS-ERROR by harness
  design; stored triples identical, no new WRONG-ANSWER.

## Why this shape
The old value is read from the superseded FACT (`nb.facts[supersedes]`)
and the new value from the fresh FACT, so both names are correct by
construction. A consistency gate requires the record's Saved text to
equal exactly the confirmation that FACT would have produced (raw
relation key, pre-mouth); any mismatch keeps the base reply. `said` is
rebuilt through the loop's own mouth, so the 167e label render still
applies downstream (verified byte-identical on "Updated:" shapes).
Any exception keeps the base reply (fail-safe, never breaks the loop).

## Events
Untouched: the rewrite runs after the write; C2 checks scrubbed event
identity on every case turn.

## What it does not do
No ears/reasoner/sleeper/notebook change; no new relations; no
change-question wording change; no multi-value semantics change.
