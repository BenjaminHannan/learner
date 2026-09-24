# 333 verified (month-end thread, 2026-09-24 ~17:40 UTC): registered FAIL on P333.2 and P333.3

Run: rent-333b-creative (origin/builder-outbox:artifacts/claude-cre333-20260924/RESULTS-rent-b.md, run/). Counts below
are from run/summary.json and a mechanical count of arm_P.jsonl rows (reply equal to 333's FALLBACK line or not; no
reply was read). judge_creative.jsonl was not opened and no judge was run.

| Mark | Bar | Result | Verdict |
|---|---|---|---|
| P333.1 notebook events on creative turns | 0 | 0 | PASS |
| P333.2 controls equal to B | ≥ 29/30 | 17/30 (13 look-alike controls routed to creative) | **FAIL** |
| P333.3 creative items judged on topic and useful | ≥ 32/40 | at most 15/40 without judging: all 25 routed creative items got the fallback line, the other 15 were not routed | **FAIL** (mechanical bound) |
| P333.4 invented person-facts | ≤ 2/40 | not judged (no creative text was produced) | not run |
| P333.5 P preferred or tied vs T | ≥ 20/40 | not judged (T is the old twin: 70/70 replies start with a think block) | not run |

Cause: Gen333.sample renders MiniCPM5-1B's chat template with thinking on; each of the 11 candidates is an unfinished
think block inside 120 new tokens, full of capitalised words, so 333's invented-name filter drops all of them and the
fallback line is sent. All 38 routed turns (25 creative, 13 controls) got the fallback. The DEV rehearsal
(rent-330-dev, arm 330a_cre) had the same 10/10 fallbacks; this thread missed it there.
Router: 25/40 creative requests carried a 333 cue; 13/30 look-alike controls did too.

Disclosure (from 11:20 UTC): this thread accidentally saw the text of 2 of the 40 creative items (in a blind writer's
scratch script) after the 333 code was committed and queued. 333's code did not change because of it; 333b and 333c
(below) change generation and routing only, and no panel item informed them.

Follow-ups, one change each, registered in PASSMARKS-333b.md and PASSMARKS-333c.md before they run.
