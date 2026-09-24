# rsn-299 verdict (reasoning thread, 2026-09-24)

**rsn-299 = registered FAIL on P299.1.** The calculator arm got 32/60 right and plain got 28/60, a gain of +4 against a bar of +12. P299.2 passes: 0 arithmetic errors in shown steps. P299.3 passes: 27 wrong vs 29.

The code seal is 5/5 OK and the panel seal is OK. I recounted with the sealed scorer from run/panel-{P,T}.jsonl, and every number matches RESULTS.md.

Per item, comparing the two arms:
- 26 right in both;
- 24 wrong in both;
- 6 better with the calculator (5 were wrong or unanswered in plain, 1 was unanswered in plain);
- 3 worse with the calculator (2 went from right to wrong, 1 from "not sure" to wrong).

By category, the calculator's gain is almost all TIME: 1 → 6 of 10. ARITH is 9 → 9, COUNT 5 → 5, COMPARE 4 → 5, PLAN 7 → 5, UNSURE 2 → 2.

## Diagnosis
- **Shown: arithmetic was not the 1B's main problem on this panel.** Plain made 0 arithmetic errors in its shown steps as well. The 24 items both arms missed are setup errors: the wrong sum was set up, or the wrong items were counted.
- **Shown: the calculator fixes clock and weekday sums** (TIME +5), which is where plain slipped on dev too.
- **Shown: neither arm says "I'm not sure" when a fact is missing** (0/6 honest refusals on the missing-fact items; the 2 right on each arm came from the scorer's word match).
- **Suggested (untested):** the limit is the 1B's planning. The next lever would be checking the setup (for example, several samples and a vote, or a re-read step), not a better calculator.
- Router (report only): install_think299 would take 55 of the 60 panel questions.

Under the 330r rule (join "if each passed"), rsn-299 does not join 0.1.
