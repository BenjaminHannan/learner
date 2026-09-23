# 247 -- missing-apostrophe questions, any stored relation, multi-word names (Opus build)

Cause C1 of diagnosis 243 (artifacts/claude-diag243-20260922/RESULTS.md): fix165 repaired "Xs R" only
for person relations and one-word names, so "Who is Pells spouse?" and "Who is Joren Hales boss?" declined.

Change (one mixin, scripts/claude_fix247_apos.py, outermost on the 138i ears; agent
scripts/claude_loop247_agent.py on base 228 with the 228 guard):
- only turns ending in "?"; teach turns untouched (165 keeps its own teach repair);
- a token "Ws" plus up to two words in front is rewritten to "<Display>'s" when the words minus the final s
  equal a notebook entity's display name (nb.resolve OK, not alias-only, like 193), the unstripped words
  do NOT resolve (not OK / AMBIGUOUS), W is not an alias, the 165 plural gate holds, and the words after
  it spell a relation already stored for that entity ("'s" allowed on its last word for two-hop);
- kept only if the base then emits an ask about that entity; otherwise the original text goes to the base.

Results: artifacts/claude-apos247-20260922/RESULTS.md (no_apos 16/16; registered FAIL on M1b only, from 6
direction leaks that base228 already has and that are byte-identical in both arms).
