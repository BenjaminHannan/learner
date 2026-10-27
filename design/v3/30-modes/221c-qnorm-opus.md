# 221c -- Question normalisation before table matching (on top of 221)

**Status:** built 2026-09-22. Results: artifacts/claude-qnorm221c-20260922/RESULTS.md.

## Why
221 (design 217 section 6) reads questions through the relation table, but its templates need
exact wording. It missed "When's X's birthday?", "When is my birthday again?", "Who's my manager?"
and "Who are X's friends?" even when the facts were stored.

## The one change
`QNorm221cMixin` (scripts/claude_loop221c_agent.py) sits outermost on the 221 ears. For a
question-shaped turn it builds a rewritten text:
- extra spaces collapsed; a leading "so," / "um," / "hey," dropped;
- contractions: what's / who's / where's / when's / how's -> "<wh> is"; how'd -> "how did";
  're -> " are";
- trailing fillers dropped (repeatedly): again, now, then, anyway, exactly, please, by the way.
  A capitalised filler with no comma in front is kept, because it is probably part of a title
  ("Who composed Right Now?");
- a missing final "?" is added when the turn starts with a question word and has no final . ! ?;
- plural relation nouns of multi-valued table relations: "Who are X's friends?" -> "Who is X's
  friend?" (also "my" and "the friends of X"). The notebook ask on a multi-valued key already
  lists every stored value;
- case: every rule ignores case. Names keep their case, because notebook names are
  case-sensitive and the table templates already ignore case.

The rewritten text is used only if all three hold:
1. it differs from the turn;
2. it has exactly one table-221 reading;
3. the full 221 stack produces only ask / clarify / answer actions for it (no write action).

Otherwise the original turn goes through 221 exactly as before. Statements (a final "." or "!",
or no question word and no "?") are never rewritten.

## Not covered (deliberately, per the task list)
- "What's my mom's name?": the "X's name" rewrite is not one of the listed rules.
- Yes/no questions: 221 has no yes/no templates.
- New verbs or relation words: those are table coverage, not normalisation. 221b handles them
  separately.
