# Rubric 208 — grading the natural panel (sealed before any run)

Every turn gets exactly one class from the grader.

## Classes

- **OK**: the turn's expected behaviour held AND no bad write happened.
  - SAVE: reply confirms the teach (any save wording) and the notebook gained
    the expected fact (G2 reads the stored triples; supersede on corrections:
    the new value answers, the old one does not).
  - ANSWER: reply contains the expected answer substring (case-insensitive).
  - ABSTAIN: reply declines (UNSURE / MISSING_FACT / "don't know" / "didn't
    catch" / honest can't-answer) and nothing was stored.
  - ASK: reply asks a genuine clarification question, nothing stored.
  - CHAT: reply chats (greeting / joke / self-description / general-knowledge
    answer / deflection) and nothing was stored.
- **wrong**: the reply says something factually against the taught facts
  (stale value after a correction, swapped subject/object, invented answer
  where ABSTAIN was expected, or abstained where the answer was taught).
  No bad stored triple.
- **unhelpful**: the reply is neither right nor wrong — empty, off-topic,
  a bare echo, or a refusal to engage — with no bad stored triple.
- **bad write**: the notebook gained a wrong or junk triple (wrong subject,
  relation, object; web fact stored as personal; chit-chat stored; stale
  duplicate kept alongside a correction), OR an expected SAVE stored nothing.
  Bad write outranks the other classes: a turn with a bad write is always
  "bad write", even if the reply text looks fine.

## G1 (automatic) vs G2 (reading)

- G1 checks only: SAVE → fact_writes ≥ min_writes and reply not abstaining;
  ANSWER → reply contains expected substring; ABSTAIN → abstain-bit match and
  0 writes; CHAT → 0 writes. G1 cannot see wrong-valued triples, so it
  over-counts OK on SAVE turns.
- G2 is my own reading of every reply plus the stored triples for SAVE turns.
- Agreement = fraction of turns where G1 and G2 agree on OK vs not-OK.
  Disagreements are listed turn by turn; G2 rules.
