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

## 333b and 333c verified (2026-09-24 ~18:10 UTC): both registered FAIL, and 333b is proved wrong
Run: rent-333bc-creative (RESULTS-333bc.md; run-b, run-c; 0 think text in any arm). Judges: one blind Opus judge per
run on judge_creative.jsonl (P vs twin b, order shuffled with seed 333); keys applied afterwards by this thread's script.

| Mark | Bar | 333b | 333c |
|---|---|---|---|
| P333.1 notebook events on creative turns | 0 | 0 PASS | 0 PASS |
| P333.2 controls equal to B | ≥ 29/30 | 17/30 FAIL | 26/30 FAIL (4 controls routed, was 13) |
| P333.3 creative items useful (P) | ≥ 32/40 | 3/40 FAIL | 2/40 FAIL |
| P333.4 invented person-facts (P) | ≤ 2/40 | 0 PASS | 2 PASS |
| P333.5 P preferred or tied vs twin b | ≥ 20/40 | 22/40 PASS (P 4, tie 18, T 18) | 22/40 PASS (P 5, tie 17, T 18) |

Report only: twin b useful 9/40 and invented 3/40 in both runs; 0 fallbacks in both; routed creative items 25/40 in
both. Proved wrong: in both runs P's useful count is below twin b's (333's clause), and 333b's useful count is below
16/40, so thinking mode was not the main cause of 333's failure. The judges' notes point at the replies P picks:
thin non-answers and refusals. 333's pick rule keeps the most grounded candidate and breaks ties by the SHORTER one,
so when no candidate uses a taught fact the shortest wins, which is usually a refusal or a one-line non-answer.
The 1B is weak at this task either way (twin b: 9/40 useful). Next: 333d generates the creative reply the way 338
does (chat prompt, 4 samples, first that passes 338's guards), keeping 333c's routing; registered separately.
