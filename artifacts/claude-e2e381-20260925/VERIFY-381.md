# 381 verification: registered FAIL on H2 (month-end line, 2026-09-25 ~03:35 UTC)

Two blind Opus judges answered all 73 held-out DEV confirm questions as the user; they agreed on 73/73 (0 splits):
43 yes, 30 no. Key applied by script afterwards (holdout_key.json; verdicts in judges/).

| Mark | Bar | 381 | Old 336 harness (report only) | Verdict |
|---|---|---|---|---|
| H1 wrong "yes" | 0 | 0 | 10 | PASS |
| H2 right "yes" kept | >= 95% | 38/43 = 88.4% | 40/43 = 93.0% | FAIL |

The old harness said yes to 10 wrong claims out of 73; 381 to none. But 381 said no to 5 true claims:
- alias gap: "boss" vs a stored "manager";
- the claim names a relation-word owner ("nan's dog" where nan is the user's grandmother);
- a two-step relation ("your nephew" = the sibling's son);
- a shorter value ("illustrator" for "freelance illustrator");
- one parse error (the owner was read from an earlier line).
Proved-wrong clause (H1 > 0) did not fire: parsing the claim is enough to stop wrong "yes" answers.
Next (381b, one follow-up): fix those five causes as general rules, built on these 73 (now dev), tested on a fresh
blind-written set of confirm questions with fresh blind judges, same marks. 381 is not used on any bank until then.
