# rd-378 = REGISTERED FAIL (verified by the "Fix: reading facts from chat" thread, 2026-09-26 ~01:30 UTC)

Builder result: origin/builder-outbox:artifacts/claude-rd378-20260925/RESULTS-benspc.md (BensPC, $0).

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| N1 multi found@10 | B >= A + 10 points | 30/30 vs 30/30 | FAIL |
| N2 time found@10 | B >= A + 5 points | 30/30 vs 30/30 | FAIL |
| N3 all found@10 | B >= A + 5, no type > 3 below | 149/150 vs 150/150 | FAIL |
| N4 blind judge "unsupported" | <= 5% of B's notes | 113/360 (31%) | FAIL |
| N5 unparsed turns | <= 2% | 0/324 | PASS |

Proved-wrong clause (all found@10 B <= A + 1) is TRUE as registered.

## What I checked
- score.json counts read from the pushed file (n@10 = 150 = 5 types x 30; "none" skipped).
- N4: a blind judge agent (the training judge's brief, data/JUDGE_NOTES.md) read the 30 panel dialogs with the 360 notes
  and gave one verdict per note: ok 230, unsupported 113, bad_when 8, bad_cite 5, bad_form 4; 90 of 324 turns miss a
  memorable item (91 items). Unsupported by kind: chat 42/173, overheard 71/187. Counts: judge_panel_counts.json.
  The thread built the judge input and read counts only.

## Diagnosis
1. The finding test could not show a gain (my design flaw). Retrieval runs inside one dialog of 12-16 turns
   (claude_rd378_eval.py: items per dialog), so top 10 is most of the dialog: heard-only already found 150/150.
   Report-only found@5 (144 vs 138) and allfound@5 (132 vs 122) lean toward notes, but k=5 is still most of a short dialog.
2. The 1B note writer is not faithful: about 1 note in 3 says something its turns don't state (overheard worse: 38%).
   The Opus notes it learned from were judged ok 93-98% of the time, so it did not learn the "nothing guessed" part.

## What follows
- Notes are search aids at most; nothing may answer from a note without checking its cited turns (382 store rule).
- The one follow-up targets faithfulness, not finding: the 1B's own dev notes (277) graded by the blind judge give real
  "unsupported" examples (graded own drafts, not Claude text). They feed the sentence checker (rd-371's one follow-up),
  which filters notes before they are stored. Any finding test must search across many dialogs, not inside one.
