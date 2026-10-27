# 231 -- Possessive chains inside table questions (Opus build)

**Status:** built 2026-09-22 on top of loop221. The registered verdict is FAIL.
- M1a, M1c and M1d fail. 58 of 72 panel items were blocked by the base's two-word-name verb-teach
  gap, which 232 is fixing.
- M2, M3, M4 and M5 pass, and M1b and M1e pass.
- Results: artifacts/claude-chain231-20260922/RESULTS.md.

## Why
After "Kim's boss is Lee." and "Lee lives in Oslo.", the question "Where does Kim's boss live?"
got the long glued refusal on both 138i and 221, even though both facts are stored.
- 138i answers chains only in its own wordings: "What city does Kim's boss live in?" (158c whcity)
  and "What is the city of Kim's boss?" (174 of-chain, reasoner multi-key ask).
- 221 reads many more wordings through the relation table. But its slot gate (`_slot_ok`) refuses
  any subject with "'s" or "of the", so chains never reach it.

## The one change
`Chain231Mixin` (scripts/claude_loop231_agent.py) sits outermost on the loop221 ears.
- **When it acts.** Only on a turn ending in "?", and only when one of these holds:
  - the whole 221 stack did not understand the turn (`base_missed221`), or
  - 221 produced one ask on one relation key that no notebook fact has ever used
    (e.g. "Who is Kim's boss married to?" -> key `boss_married_to`).

  On every other turn, the 221 actions pass through untouched. That covers every single-hop
  question and every chain wording the base already answers.
- **Reading.** It uses the same table templates as 221 (the ask rows plus the table's yes/no rows),
  with one difference: `{X}` may hold a chain. Chain forms:
  - possessive: "Kim's boss", "Kim's boss's sister"
  - of-form: "the boss of Kim", "the sister of Kim's boss", "the sister of the boss of Kim"
  - user: "my boss", "my boss's sister"

  Of-form splits try every " of ". A split whose relation is a table key wins, longest first, so
  "the country of citizenship of X" reads correctly. An of-form root must be capitalised.
  Exactly one distinct reading over all templates is required, with at least one hop.
- **Resolving.** It walks the chain hop by hop through the notebook and is read-only.
  - It uses only rows where `source == "taught"` and `active`, so it never touches forgotten,
    superseded, inferred or sleep rows.
  - Each hop needs exactly one distinct value. A key with no rows may fall back to its table group,
    but only if every key in the group agrees (the 221 rule).
  - The value must resolve to exactly one entity.
  - If any of these fails, the reply is an honest abstain that says how far the chain got:
    - "Kim's boss is Lee, but I don't know Lee's city."
    - "I don't know which one you mean: my notes have more than one friend for Kim."
    - "I don't know anyone called Zed."
- **Reply.** A clarify action carrying text, e.g. "Kim's boss is Lee, and Lee lives in Oslo."
  - The last clause uses the relation's live teach template ("{X} lives in {Y}.") when there is one.
    Otherwise it uses "X's R is V".
  - Yes/no answers start with "Yes." or "No.". "No." is only possible for single-valued relations
    that allow a no. Anything else starts "I don't know.".
  - The stage never emits teach, correct or forget, so it cannot write.

## Declared differences
1. **Chain-only input tidy.** A leading filler ("so", "ok", "hey", ...) and a trailing
   " again" / " now" / ", then" are stripped, but only for the chain reading.
2. **Yes/no templates are read, for chain subjects only.** 221 skipped yes/no.
3. **Table v1 gaps are inherited.**
   - The "What language(s) does X speak?" template compiles to require the "s", so "What language
     does Kim's boss speak?" is still not read.
   - "wife" and "spouse" are separate groups, so a "wife" hop over a stored `spouse` abstains.

## What it is not
- It does not infer, store or sleep on anything.
- It does not change how chains that 138i already answers are worded.
