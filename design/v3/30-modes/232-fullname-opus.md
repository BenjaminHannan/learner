# 232 — multi-word names in verb sentences (Opus)

Base: 138i (`scripts/fable_loop138i_agent.py`, `artifacts/fable-agent138i-20260922/loop138i-config.json`).
New agent: `scripts/claude_loop232_agent.py`. Artifacts: `artifacts/claude-fullname232-20260922/`.

## The gap (reproduced, `repro-138i.txt`)
138i handles "Orrin lives in Quellmoor." / "Where does Orrin live?".
With "Orrin Vask", "Tessaly Marrow-Fen", "Juno de Carvel" or "Pell Oskin Dray",
the verb turn gets "I didn't understand…" and 0 facts are saved. The verb
question gets the generic abstain/clarify.

## Cause
The verb path (fix167 `Verb167Mixin` / 167d) rewrites verb turns into a
possessive twin ("X's city is Y.") and passes that to the possessive path.
Its subject pattern `V167._NAME = [A-Z][A-Za-z'’\-]*` plus `_subject_ok`
accept exactly one token. A multi-word subject never matches, so the turn
falls through to the clarify reply. The possessive path already accepts
multi-word subjects (137 `parse_possessive137`, 150 subject guard). Only the
verb gate was one-word.

## The one change
`Verb232Mixin` sits just outside 167b's value screen, in the same place in
the ears stack. It claims a verb statement or question only when the subject
has **2–4 tokens** and passes `subject_ok232`:
- every token is a 137 name token (capitalised, hyphens allowed, initials such
  as "K." allowed), or it is a middle token from a closed particle list
  (de da di do dos das del della der den des du van von la le ter ten bin ibn al);
- no token is possessive, a 150 hedge/filler/reporting opener, a pronoun,
  determiner, conjunction, time word or question word (closed lists);
- no multi-word 150 opener phrase appears, and it is not a 150c closed-class
  subject;
- `screen_subject_150` returns ("store", subject unchanged).

A claimed statement goes through 167b's `screen_value` (so it gets the same
refusal text), then becomes the same possessive twin 167 would build, and
that twin goes to the unchanged 138i stack. A claimed question becomes the
possessive question twin. One-word subjects are never claimed, so they take
the exact 138i code path.

## Parity steps
These make a multi-word name behave exactly like a one-word name. Each was
found by `scripts/claude_fullname232_parity.py`.
1. **Particle surrogate.** The 137 upgrade refuses lower-case particles.
   For the twin of a claimed turn only, the upgrade is re-run on a surrogate
   twin with the particles title-cased, and the real name is put back on the
   resulting action.
2. **Refusal mirror.** When the upgrade still refuses a claimed twin, the
   same G91 / 139b / 150 guard messages a one-word name would get are
   returned (for example the SPLIT message for "speaks Norric and Veltish"),
   instead of the generic clarify.
3. **Doubt record.** Doubt146 records refused teaches through a one-word
   FakeEars. For a claimed statement, the relation is found on a stand-in
   one-word twin ("Qzvrenn") and the doubt is recorded under the real name.
4. **Pending drop.** Structured multi-word teaches go straight to `_teach`,
   which skips Listening's "(I dropped my earlier question.)" step. The v232
   tag plus `Loop232AgentLoop._act` clear the pending yes/no question and add
   the same note, so a later "yes" can't apply a stale change.

## 228 guard
Installed as the rules require: `install_srcguard228()` runs at import and in
the builder, and `SrcGuardMixin228` is first in the daemon bases. The
comparison base is plain 138i, as the brief says.

## Known out-of-scope gaps (inherited from 138i's possessive path, not verb turns)
- Possessive yes/no questions with multi-word names ("Is Orrin Vask's city Quellmoor?", 154d).
- Of-chains through a multi-word name ("What is the city of Orrin Vask's boss?", 174).
- Typed possessive teaches with particle names ("Juno de Carvel's city is X.").
- Typed multi-word possessive teaches don't drop a pending question.
- A declined ";" turn with a hyphenated multi-word name replies "I cannot predict." This is base 138i behaviour, confirmed on 138i.

## Pilot results (before the seal)
- Dev (54 own items): 232 54/54; 138i 37/54 (multi-word right 3/20).
- Parity: 207/210 (misses: t27 × 2 particle possessive teach; t31 × 1 hyphen ";").
- Suite diff: GATE clean. The one move is rt143 K5, reply-only.
- Sleep smoke: pass.
