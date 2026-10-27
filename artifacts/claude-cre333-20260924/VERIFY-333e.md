# 333e verified (creative research thread, 2026-09-25 ~00:50 UTC): registered FAIL on P333.3; routing PASS; E.2 proved wrong

Run: rent-333e-creative (origin/builder-outbox: RESULTS-333e.md, run-e1, run-e2; $0.10; precheck matched the CPU
DEV counts exactly; 0 think text). Judges: design/v3/30-modes/333-judge-prompt.md verbatim, one fresh blind Opus
agent per run on run-eX/judge_creative.jsonl (P vs twin b, shuffled seed 333); keys applied afterwards by script.
Verdict files: judge-333e/verdicts-e1.jsonl, verdicts-e2.jsonl. This thread did not open the judge packets or replies.

| Mark | Bar | e1 (tool-call router) | e2 (+ writer sees the chat) |
|---|---|---|---|
| P333.1 notebook events on creative turns | 0 | 0 PASS | 0 PASS |
| P333.2 controls equal to B | ≥ 29/30 | 30/30 PASS | 30/30 PASS |
| P333.3 creative items useful (P) | ≥ 32/40 | 7/40 FAIL | 6/40 FAIL |
| P333.4 invented person-facts (P) | ≤ 2/40 | 0 PASS | 2 PASS |
| P333.5 P preferred or tied vs twin b | ≥ 20/40 | 25/40 PASS (P 17, tie 8, T 15) | 21/40 PASS (P 9, tie 12, T 19) |
| E.1 creative items routed (e1) | ≥ 34/40 | 40/40 PASS | (40/40) |
| E.1b controls routed (e1) | ≤ 2/30 | 0/30 PASS | (0/30) |
| E.2 useful(e2) − useful(e1) | ≥ +4 | | −1 FAIL, proved wrong (≤ 0) |
| E.2b invented (e2) | ≤ 2/40 | | 2 PASS |

Report only: twin b useful 10/40 and invented 3/40 in both judgings (judge noise on T: 0). Items useful for both
P and T: 1 (e1) and 1 (e2); P only 6 / 5; T only 9 / 9. Fallbacks e1 3, e2 0.
Headline: useful(e2) 6 is not ≥ useful(T) + 3 = 13, so no "beats the plain 1B" claim.

What it means: the wiring is fixed. The 1B's own tool call routes every creative request and no look-alike, and
memory answers on the controls are untouched (30/30, first time in the 333 series). But once every request reaches
the writer, the writer is the limit: 7/40 useful vs twin b's 10/40. Giving it the chat did not help (6/40). DEV
replies (artifacts/claude-cre333e-dev-20260924, e1/e2 rehearsal on 28 items, CPU) show why: the base 1B's ideas are
often incoherent or off-target, and with the chat in the prompt it copies earlier replies ("Got it.") or answers
a different turn. Next single change: train the writer (333f).
