# 224c: honest Q1 decline (design note, Opus, 2026-09-22)

Results: `artifacts/claude-decline224c-20260922/RESULTS.md` (registered PASS).

## Problem

loop224 serves Q1 ("I don't know that yet — you haven't told me.") on any glue turn where the ears emitted an ask. In 224b's registered run, a flake (bench132-4hop-031) went down that path for facts that *had* been taught, so the assistant said something false.

## Change

`scripts/claude_loop224c_agent.py` wraps the built loop224. The sequence on each turn:

1. The loop224 reply comes back.
2. If it is exactly Q1, loop224c reads the ask actions of that turn from loop224's own tap state (its closure cell). It adds no new ears tap and does no extra work on ordinary turns.
3. It runs `q1_confirmed` on snapshot views of the notebook (MappingProxyType / frozenset).
   - The check gets no notebook object and calls no notebook method.
   - An assert confirms that the event count did not change.
4. It keeps Q1 only if every ask is confirmed empty. Otherwise it serves Q2 and updates the self logs to what was actually said.

**Rules for a known subject**, applied along the asked chain (walk the hops):
- Every hop resolves → the answer is stored → Q2.
- A hop's value cannot be followed → Q2.
- At the first empty hop, still Q2 if either:
  - the entity has a stored relation whose word appears in the question but is not in the ask (possible misread); or
  - the asked relation word is used by no fact at all in the notebook (possible synonym such as "manager" for a stored "boss", or an inverse such as "employee").
- Otherwise → Q1.

**Rules for an unknown subject.** Q2 if any of these holds:
- the name appears as a stored value;
- any known entity name, or any 3+-letter word of one, appears in the question;
- the asked name shares such a word with a known name ("Mira" for a stored "Mira Vell"; the misparse "the job of Selwyn Crane").

Otherwise → Q1.

**Other cases:**
- Pronoun subject, malformed ask, or a check error → Q2.
- The rules file requires the exp-228 `_src_of` guard for new 138i-family experiments, so it is installed too. This removes the flake that caused the 224b failure.

## How the Q1 branch was tested

On 138i an ask always yields an answer record, so Q1 is only reachable by the flake. The 228 forced harness does make flakes happen, but those turns carry no ask (they give Q2), and with the guard installed nothing flips.

The case driver's `forced` mode (`scripts/claude_224c_cases.py`) does the following on the probe turn only:
- it turns an ears "ask" into a "didn't understand" clarify record;
- that reproduces the flake's shape (an ask was captured, the notebook reported a miss, the glue was reached);
- under this forcing, loop224 served Q1 on 32/40 taught-fact traps.

## Known limits

1. **Synonyms where both words are in use.** If the notebook uses "manager" for someone else and "boss" for the subject, "Who is X's manager?" still gets Q1 (M2x: 3/3). A word-level check cannot tell synonyms apart. Fixing this needs relation-meaning knowledge, such as a learned relation similarity, not a keyword list.
2. **The new-relation guard costs a little.** "Who is Mira's father?" when "father" is never used anywhere now gets Q2 instead of Q1 in the forced shape (M3x: 0/6 Q1). Q2 is the less informative but not false reply. The cost only shows on the rare flake path.
3. **Outside scope, but the same honesty problem.** 138i's own answer records make similar claims on the natural path, and 224c does not touch them:
   - "I don't know anyone called Mira." when "Mira Vell" is stored;
   - "I don't know anyone called the job of Selwyn Crane.";
   - "I don't know Mira Vell's manager." when her boss is stored.

   In the M2 natural runs, 21 of 40 replies were of this kind.

## Next steps

- Apply the same read-only check to 138i's "I don't know anyone called X." / "I don't know X's R." answer records. That is a separate experiment, because it changes replies where 138i gave a real answer.
- Imperative requests getting S1 (224 lesson 2) is still open.
