# Probe-6: an "ask first?" judge to fix picking on trick jobs

Fixed 2026-10-28 ~03:50Z, before any judge is run on any pool. Small card experiments and the village model are not
involved. Labels: shown / suggested / untested.

## Why (shown)
Probe-4 (K2) and Probe-5 (LFM3) pick well on normal jobs but badly on trick jobs (LFM3: 21.1% of a possible 57.9%).
On Probe-4's trap pools, winning tries end with a question 122/137 times; on non-trap pools, tries that ask lose
112/122. No test writer (K2, LFM3-tuned, Haiku with state, Haiku with checklist) captures "should have asked".

## One change
Pick rule ASK-GATE: a judge reads the request and start state (never the tries) and gives P(ask first).
If P(ask) >= t: among the 12 tries whose final reply contains "?", pick by TEST-T score (ties by SELF); if none ask,
fall back to TEST-T. Else: TEST-T as in Probe-5. Everything else (tries, TEST-T, SELF) is reused unchanged.

## Data
- Dev (choose judge and t): Guess-1's 48 target tasks (K2 pools, IND/MENU x seeds 1-2), trap = scenario in
  {confirm_irreversible, clarify}; plus judge-only accuracy on 200 of the 372 non-target sandbox tasks (seeded).
- Test (once, after the choice is committed): the frozen Probe-5 LFM3 pools (96 tasks, 38 traps), with Probe-5's
  TEST-T and SELF scores. No new tries.

## Judge arms (all scored on dev; one is chosen on dev AUROC for trap vs non-trap, ties to the cheaper one)
- J-LFM3: LFM3-1.7B (BF16 GGUF, llama.cpp), prompt "Should the assistant ask the user before acting? yes/no",
  P(yes) from logprobs, thinking off.
- J-D1: Liquid AI's d1-3B decision model (Ben's idea, 00:16Z Oct 28), same question as a typed yes/no decision.
- J-HAIKU: Claude Haiku via the Batches API, same question, P(yes) from 5 samples. Reference only: cannot be chosen
  (the assistant must run locally); it bounds what a judge could reach.
t is chosen on dev as the value maximising dev end-to-end pick rate (grid 0.1..0.9 step 0.1).

## Pass marks on the Probe-5 test pools (fixed now)
- A1: ASK-GATE all-task pick >= TEST-T (57.3) + 5 = 62.3%.
- A2: non-trap pick >= 81.0 - 3.5 = 77.5% (at most 2 normal jobs lost).
PASS = A1 and A2. PROVED WRONG: all-task pick <= 58.3% (TEST-T + 1). Otherwise INCONCLUSIVE.
Reported: traps / non-traps; the judge's test AUROC; ORACLE-GATE (true trap labels) as the rule's ceiling; J-HAIKU
on test as a reference line.

## Cost
Haiku batch < $0.50. LFM3 and d1-3B judging: 96 + ~250 single-pass prompts, free (M3 or cloud CPU).
