# 258: commentary clause after a denial or correction (Opus). Registered FAIL on M1

**What was tried.** On turns that 252/252b already read as a denial or correction, the mixin removes a trailing "that's / that was / which is ..." clause. The shortened turn is handed to 252b unchanged, and nothing is ever taken from the clause.
- Code: `scripts/claude_fix258_comment.py` (one mixin, outermost on the inner ears).
- Agent: `scripts/claude_loop258_agent.py`.

**Result (full table in artifacts/claude-comment258-20260922/RESULTS.md):**
- Blind panel corrtail258, 258 against 252b:

  | Family | 258 | 252b |
  |---|---|---|
  | that_denial | 7/12 | 0 |
  | that_correction | 3/12 | 0 |
  | pure_denial_that | 6/10 | 2 |
  | junk writes | 0 | 2 |
  | false claims | 0 | 4 |
  | wrong values | 18 | 31 |

- Questions, unstored targets, keep items and controls were all perfect, and keep/controls were byte-identical.
- M2–M7 (dev252b, corrpanel252, suites, smoke, restart dialogs, latency +0.23 ms) all passed exactly as predicted.

**Why it failed.**
1. Removing the clause is necessary but not enough. 252b cannot act on many of the shortened turns:
   - lowercase names with "isn't";
   - first-person "My X isn't Y";
   - multi-valued relations, where "X's cat is Fig, not Moss." adds Fig and keeps Moss;
   - contextual corrections of USER facts;
   - a bare "No." after a statement.
2. The whole-turn gate misses "X's R is Z, not Y, that's ..." because 252's ", not W" test needs the turn to end there.

**Next, if pursued (not done here):**
- Gate on the shortened candidates, not the whole turn.
- The bigger gains are in 252b's grammar: lowercase "isn't", first-person negation, and "Z, not Y" as a replace on multi-valued relations.
- These fit the learned ear route (see the learned-reader decision) better than more hand rules.
