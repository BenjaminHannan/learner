# 252 — corrections and denials (Opus build on 138k)

## The gap, reproduced on 138k (pilot dialogs, before the fix)

- "X doesn't work at Y." / "Y isn't X's boss." / "That's not true, X doesn't ..."
  are not understood: nothing is removed ("I couldn't save that as a fact").
  Only the form "X's R is not Y." worked (154f).
- "That's wrong." after an answer: not understood, nothing removed.
- "No, it's Z." after an answer: not understood.
- "Actually, X lives in Z, not Y." on a one-value relation (city, employer):
  "I can take one fact at a time". It works on multi-value relations (154b).
- "X doesn't work at Y, X works at Z.": not understood.
- "Correction: Tomas's city is Aldgate." writes a junk subject "Correction: Tomas".
- "No, Tomas speaks Veldish." (language allows many values) adds instead of replacing.
- The reverse lookup "Whose employer is Y?" works; "Who works at Y?" is not
  answered at all on 138k (not changed here).
- Already right on 138k and kept: "No, X lives in Z." / "Actually, X's city is Z."
  (Updated), a one-value re-teach asks "Do you want me to change it?", and
  "Actually, my name is Z." asks to confirm.

## The fix (scripts/claude_fix252_correct.py)

One ears mixin and one loop mixin, added by an instance class swap, like 251.
No new storage and no direct notebook writes:

- **Removal** goes through the 154f action `negate_one154f`. That path resolves
  the name, matches the exact stored value and calls `nb.retract`. Only the reply
  text is rewritten: "OK, I removed Y as X's R."
- **Replacement** hands the canonical sentence "No, X's R is Z." to the base ears.
  It is used only if the base returns exactly `correct` / `correct_single154g`
  for the same name, relation and value, so every base teach check still applies.
  The base act then writes "Updated: ...".
- **"Which fact"** comes from the previous turn's reply. An answer made from two or
  more facts, or not from taught facts, counts as inferred: the model says what it
  worked the answer out from and asks which fact is wrong. Otherwise it counts the
  taught active facts whose subject and value both appear in the reply. A previous
  turn that wrote anything counts as "none".
- **Safety first:**
  - A question never writes: a trailing "?", or an opening auxiliary or wh-word.
  - A pending question from the base is left alone.
  - "my / I / me" turns stay with the base (the own-name confirm flow).
  - Several stated facts, or none, means ask.
  - A bare name after "No," ("No, Kira.") asks.
  - "It's Z." with no correction word is left to the base.
  - "no X's R is Z" without a comma is left to the base (sessions152 K146).
