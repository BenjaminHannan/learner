# 221 -- Questions read through the relation table (first build of design 217 section 6)

**Status:** built and measured, 2026-09-22. Registered verdict **FAIL**. Coverage misses the
bar (P1 64.8 % vs 90 %), and one suite flag fires (rt143 S5). On safety, nothing failed:
0 wrong values, 0 question writes, G3 and the sleep smoke unchanged.
Results: artifacts/claude-tableask221-20260922/RESULTS.md.

## What it is
`TableAsk221Mixin` (scripts/fable_fix221_tableask.py) sits outermost on the loop138i ears
(scripts/fable_loop221_agent.py). It only looks at turns ending in "?", and it never writes.
1. **(a) Read.** When 138i's reply is the not-understood clarify, the question is matched
   against the table's ask/inverse templates (relation_table_v1.json, 1486 patterns).
   - A forward reading becomes an ordinary ask.
   - An inverse reading is answered from the notebook, labelled "(worked out backwards)",
     and never stored.
2. **(b) Rekey.** A one-hop ask on a key with no rows is re-pointed to a key in the same
   table group that does have rows. Conflicting values produce a "which is right?" clarify
   instead of a pick.
3. **(c) Label.** 138i's own reverse answers (153) get the same label.

## Why it failed the bar
It failed on coverage, not on a mistake. The 25 blind-panel misses, all of which abstain:
- 12 are wordings with no template: speak, own, coach, "When's", "was ... birthday",
  "Who's my", "my mom's name", "name of X's pet", "Which books did X write".
- 9 are stored relation words outside every group: founding_date/year,
  wedding_anniversary, opening_date, graduation_date, physician, supervisor, residence,
  native_language.
- 3 are "the R of X" where R is not in the table (landlord, dentist, mayor).
- 1 is a deliberate choice: hometown is not treated as a synonym of birthplace.

## Next options (not built)
- Table v1.1 with the missing verb and "when" templates and the synonym groups above.
  Every difference would be listed.
- A generic "Who/What is the R of X?" read for ANY key, even one outside the table. It would
  reuse the possessive ask and add no new meaning.
- A decision on whether a "2-cycle -> abstain" test (rt143 S5) should stay gold, now that a
  one-hop reader can answer the taught fact directly.
