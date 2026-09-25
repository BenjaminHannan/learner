# VERIFY gram-362 (grammar thread, 2026-09-25 ~08:45 UTC)

**Verdict: registered FAIL** on P362.2 (both graders) and P362.5; the proved-wrong clause is triggered by grader A.
PASSMARKS.md registered and sealed at main 0b8d95092 before the run. Component test on CPU in the cloud container,
chatpanel362 (sealed, 2/2 OK, first use), 112 turns per arm, MiniCPM5-1B 87179e5c, enable_thinking=False.
Graders: two blind Opus agents (planted errors caught 39/40 and 39/40, clean kept 40/40 and 40/40: both valid).
Judge: one blind Opus agent, sides shuffled. Scores: grades/score.json (scripts/claude_gram362_score.py).

| Mark | Bar | Result | Verdict |
|---|---|---|---|
| P362.1 critic replies clean, each grader | >= 90% | A 102/112 (91.1%), B 107/112 (95.5%) | PASS |
| P362.2 gain over base, each grader | >= +5 | A 100 -> 102 (+1.8), B 102 -> 107 (+4.4) | FAIL |
| P362.3 helpfulness, critic preferred or tied | >= 50% | 63/112 (critic 29, tie 34, base 49) | PASS |
| P362.4 all-samples-failed turns | critic <= base + 3 | 0 vs 0 | PASS |
| P362.5 most common sampled critic reply | <= 5% (5.6) | 8/112 ("I'm not sure.") | FAIL |

Proved wrong (gain < +2 on a valid grader): triggered by grader A (+1.8). As registered: the 1B's own word
probabilities cannot tell its clean drafts from its broken ones well enough to help.

## What happened (report only)
- The critic prefers short drafts. Replies went from 40.4 to 28.1 words on average. Among the 1B's 4 drafts there
  is sometimes a bare cop-out ("I'm not sure.", "I don't know."); the critic picked those 8 and 4 times. They are
  grammatical, so the graders pass them, but they are not answers, and the judge preferred today's replies 49 to 29.
  Part of the small grammar gain is bought with emptier replies. That is not a real improvement.
- Training showed the same lean (length alone has AUC 0.37 against clean; the critic's largest weight is on
  length, -0.33 on standardised log tokens, just ahead of average word probability at +0.32), and PASSMARKS listed it as report-only. The marks caught it; the design did not guard against it.
- By kind (A): explain 17/20 -> 20/20 and smalltalk 24/27 -> 26/27 improved; advice 23 -> 22, feelings 17 -> 16,
  followup 19 -> 18 slipped. B: explain 18 -> 20, smalltalk 24 -> 27, others equal.
- 19 of 112 turns got the identical reply in both arms.
- The base arm here is cleaner (89.3% / 91.1%) than gram-361's t07 arm (82.7% / 81.8%) on a different panel and
  different graders, so the room for a picker was smaller than the training data suggested (75% of drafts clean by
  both graders there).

## What it means
Choosing among 4 drafts with the 1B's own confidence does not get the chat replies near 99%: the useful signal is
weak (cross-validated AUC 0.71) and mostly says "shorter is safer". The critic is not joined anywhere.
Two honest options remain for the 1B's own sentences, both larger steps than a picker:
1. A picker that must also keep the answer (for example a length or content floor, or a helpfulness term), tested
   again as its own change. Expected gain is small (+2 to +4 points), still far from 99%.
2. A bigger chat model (the card's alternative), which needs Ben's yes for a new download.
