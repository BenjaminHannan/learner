# AUDIT: claude-readpanel319-20260925 (counts only, no items)

Second labeller (B): one separate Opus run (`claude -p --model opus`, Read and Write only, no MCP servers, Bash/WebFetch disallowed). B saw only blind_input.jsonl (id, dialog, t, prev_reply, turn) and the labelling rules; the key (panel.jsonl) was moved out of the folder while B ran.

Agreement rule: a fact agrees when owner (case-insensitive, first name ok) and value (case-insensitive) match; relation synonyms allowed. A no-fact row agrees when both give the same nosave_reason.

| | first pass | final |
|---|---|---|
| rows | 240 | 240 |
| rows in full agreement | 236 | 240 |
| rows in disagreement | 4 | 0 |
| key facts | 211 | 211 |
| B facts | 211 | 211 |
| facts matched (owner + value) | 211 / 211 | 211 / 211 |
| fact disagreements (missing / extra / wrong owner or value) | 0 | 0 |
| no-fact rows with a different nosave_reason | 4 | 0 |
| needs_history flag agreement on matched facts (not graded) | 208 / 211 | 209 / 211 |

Resolution of the 4 row disagreements: all 4 were nosave_reason only (key said smalltalk; B said negation x3, sarcasm x1). Fixed the key to B's reason in all 4 (B's reading was the better one). Rows rewritten: 0. Rows replaced: 0. B re-runs needed: 0.

needs_history: 3 first-pass differences. 1 key fixed (owner named in prev_reply, but not in the role the turn uses, so earlier user turns are needed). 2 kept as keyed: 1 where B marked history but the key owner is resolvable from prev_reply alone; 1 where B did not mark history but the owner is named in no earlier assistant reply (only in an earlier user turn).

Mechanical checks (check script): 240 rows, unique ids, 30 dialogs x 8 turns, facts empty iff nosave_reason set, every value in its turn except 3 short answers whose value is in prev_reply, turns 4 to 45 words, no name from the dev name list: ALL PASS.

Scratch copies holding items (blind input, B part files, builder script, held key copy) were deleted after the final comparison.
