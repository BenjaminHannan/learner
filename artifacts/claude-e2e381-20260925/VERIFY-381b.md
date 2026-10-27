# 381b verification: registered FAIL on H1 and H2 (month-end line, 2026-09-25 ~02:45 UTC)

Set: 120 items written blind by a separate agent (holdout381b_items.jsonl). Two blind Opus judges agreed on all 120
(56 true claims, 64 not). Harness answers computed by script afterwards.

| Harness | H1 wrong "yes" (bar 0) | H2 true claims kept (bar >= 95%) |
|---|---|---|
| 381b | 1 | 33/56 = 58.9% |
| 381 (report only) | 1 | 19/56 |
| old 336 harness (report only) | 18 | 21/56 |

381b = registered FAIL. Causes (from reading the misses and the one wrong yes):
- The writer's facts store full names ("Rosamund Tewe") and the questions use first names ("your aunt is Rosamund");
  381b only accepts a shorter value when it is the END of the stored value, so most true person claims fail.
- Missing aliases (flatmate/roommate, twin, in-law chains, "your brother's wife").
- The one wrong yes: "your city is Stornby" when Stornby is the hometown and the current city is elsewhere; 381's
  alias group put hometown with city.
Proved wrong (fixed in PASSMARKS-381): H1 > 0, so parsing the claim with rules is not enough; an honest simulated user
needs a judge model that reads the question and the facts, as the blind judges did (they agreed 120/120 and 73/73).
As registered: no third follow-up before Sept 30. Banks C and D use the old sealed harness, and the report lists
381b's answers alongside. The old harness says yes to wrong claims 18 times in 64 here, so the M1 wrong-save count
on any bank should be read with that in mind. After Sept 30: a judge-model user (a registered 381c), if Ben wants it.
