# slp-364e pass marks (registered 2026-09-25 ~08:00 UTC, before its blind bench exists)

Change (one): gate v5 (scripts/claude_slp364e_gate.py) = v4 plus four new question kinds asked before and after the
night: F other phrasings of the word question (truth known), Y yes/no about the true and the first-hop person,
E explicit two-step questions, Z the word asked about people with no taught facts. A changed reply that is wrong,
confirms the wrong person, denies the right one, or answers where nothing is known rejects the night.
Why: slp-364d registered FAIL (15/20); all five misses showed only in question kinds the gate never asked, and v4's
own new rules fired on no bench night.
Both arms: slp-360 + slp-368 lock + slp-369 restore + slp-361 undo. Twin: gate v1 (slp-364) in the same run.
Runner: scripts/claude_slp364e_run.py (the 364d runner with v5 and the new bench; it now keeps up to 40 reasons and
the set of rules that fired, so a catch can be credited to the rule that made it).
Bench: scripts/claude_slp364e_bench.py, a fifth bench written by a separate agent told not to open any gate, earlier
bench or result, with at least 6 of its 20 faults showing only in questions other than "Who is X's R?" or about
people the day barely mentions.

| Mark | Bar |
|---|---|
| P364e.1 faulty nights rejected by v5 | ≥ 18/20 |
| P364e.2 honest nights rejected by v5 | ≤ 1/20 |
| P364e.3 v5 catches minus v1 catches | ≥ +3 |
| P364e.4 every v5 night: main notebook log unchanged and the sandbox restored | 40/40 |
| P364e.5 honest nights: the bench's user-probe replies identical under v5 and v1 | 20/20 |
| P364e.6 faulty nights rejected ONLY by the new F/Y/E/Z rules | ≥ 3 |

Proved wrong if: v5 catches fewer than 15/20, rejects more than 2/20 honest nights, changes any honest night's
replies, or the new rules are the only catch on 0 nights.

## Disclosures written at seal time
- v5 was written after reading how the five 364d misses work (opened bench). The question forms come from reading that
  bench. The fifth bench's author was not told them.
- Dev check on the opened 364d bench is running at registration. Its result is appended below before the fifth bench
  is opened. One smoke case so far: slp364d-30 (yes/no fault) is now rejected by Y.
- Dev result (appended ~08:10 UTC, before the fifth bench is opened; scratch script, opened 364d bench, with 368 + 369):
  20/20 honest 364d nights kept, user replies identical to 364d's registered v4 arm on 20/20. Of v4's 5 misses, v5
  rejects 4, each by a new rule only: 05 by E, 20 by F, 30 by Y, 37 by Z. Still missed: 09 (an unknown relation
  phrase backs off to a known word); v5 asks no made-up relation phrases, and it was left unchanged after registration.
  Dev used the cases v5 was built from, so this shows only that v5 does what it was written to do.
