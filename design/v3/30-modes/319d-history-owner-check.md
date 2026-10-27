# 319d (follow-up, NOT registered, not run tonight): let the structural check see the reader's history

Why: on readpanel319c the lis-319 reader finds 37 of 57 history-dependent facts but saves only 2 (0.995) or 3 (0.98).
Cause (code, claude_lis300_compiler.check_fact): the owner must appear in the current turn or the assistant's last reply,
so "she's a teacher" about someone named three turns back is rejected as owner_not_span, whatever the reader's confidence.
The reader was given history (lis-319); the check was not. (Second outside review, item 8: "integrate the history reader
completely".)

Dev preview (report only; 133 lis-319 dev history rows, dev_pred of the lis-319 reader, claude_lis300_score.match):
owner may also be a whole-word span of one of the last 6 USER turns (never an assistant reply; value rules unchanged).
| bar | right saves now -> with history | wrong rows now -> with history |
|---|---|---|
| 0.995 | 55 -> 71 | 0 -> 1 |
| 0.98 | 65 -> 93 | 0 -> 3 |
Back-reference family at 0.98: 5 -> 32 of 52. All 3 new wrong rows are role confusion: "she" with two women in the window
(e.g. a stepmother and a girlfriend), the reader picked a name the key would not save.

So the plain change buys ~28 facts per 133 history rows and costs ~3 wrong rows: too many for the <= A+1 safety bar.
Candidate single changes, in order (each needs a fresh sealed panel with role-confusion rows, marks fixed first):
1. History-resolved owners are ASKED BACK ("Is Angharad the primary teacher?") instead of saved; local owners unchanged.
   Marks: back-ref facts saved-or-confirmed >= A + 20 of ~60; wrong saves <= A + 0 (asks are not saves); questions per
   100 turns reported; role-confusion rows: 0 new wrong saves. Proved wrong: wrong saves >= A + 2.
2. Only if 1 passes: save silently when the window holds exactly one earlier-named person the pronoun could mean.
The reviewer's ">= 90% on supported back-references" is kept as the target for correctness of what is saved, not coverage.
