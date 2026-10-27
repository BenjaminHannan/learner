# 293: yes/no questions about the notebook ("Does Ana have a dentist?")

Director (Opus, reasoning line), 2026-09-23 ~09:40 UTC. New file; nothing edited. Diagnosis: artifacts/claude-diag293-20260923/DIAG.md on builder-outbox (Muse, read-only). I checked its key file:lines in the code.

## Result first: the machine never hears these as questions

On 138nb, 61 dev dialogs; 51 yes/no turns:
- **11 answered right**, all from the 154d reader;
- **40 get "I didn't understand that question"**: 16 where the fact is stored (should be "Yes"), 24 where nothing is stored (should be "I don't know");
- 0 question writes.

Why (checked in code):
- The base parser only turns who/what/where into a question (`_QUESTION`, scripts/fable_agent_loop.py:94).
- The only yes/no reader is 154d (scripts/fable_fix154d_yesno.py:67-69, 105-129). It reads only "Is X's R V?" and "Is V X's R?", with one-word capitalised names and exactly one "'s".
- Everything else misses (scripts/fable_loop90_agent.py:291-292) and gets 224's Q2 sentence: "Does/Has" forms, two-word names, of-forms, "live in / work at / come from".

## The one change

**293 = 138nb + one yes/no reader in the 154d slot** (a new wrapper file; 154d's code imported read-only). It parses:
- "Does A have a/an R?", "Has A got a/an R?";
- "Does A live in V?" (key city), "Does A work at/for V?" (key employer), "Does A come from V?" / "Was A born in V?" (key birthplace);
- the existing "Is" shapes, now with multi-word names (resolved against names the notebook holds) and of-forms ("Is V the R of A?").

It answers read-only from the notebook:
- **Yes**: the stored value matches ("Yes, Ana's dentist is Tovi.");
- **No**: only for single-valued relations (SINGLE_VALUED_154), when a different value is stored ("No, Ana's city is Oslo.");
- **"I don't know"**: nothing is stored for that relation, or the relation is multi-valued and V is not among its values (the reply names what is stored);
- never writes; a taken-back value counts as not stored.

Chain subjects ("Does Ana's boss live in Oslo?") stay out: they pass through unchanged (the 266 lift is a separate piece).

Why this option (director decision, logged; clearly better for the model):
- The diagnosis shows 40 honest questions answered with "didn't understand".
- The notebook already has the answer or knows it doesn't.
- One read-only reader covers every shape; it can't write and can't guess.

## Marks (fixed before any build)

M1, a fresh blind panel yesnopanel293 (spec: handoff/kit/briefs/yesnopanel293-spec.txt):
- yes/no families together ≥ 90% right;
- **0 wrong**: never "Yes" when the value is not stored, never "No" when it is;
- taken_back: 0 "Yes";
- 0 question writes;
- is_single_control, wh_control and statement_control byte-identical to 138nb.

M2: invpanel138nb and chainpanel266b (regression only): 0 moves.

M3: frozen suites vs 138nb's rows: moves exactly the predicted list; 0 new WRONG, WRONG-WRITE, junk write or lost OK.

M4: restart and verifier dialogs: 0 ghost answers, 0 write changes, every reply change predicted.

M5: median added time ≤ +5 ms per turn.

## What would prove it wrong

- "Yes" for a fact that was never taught or was taken back.
- "No" on a multi-valued relation.
- Any write on a question turn.
- Any change to a who/what/where answer.
