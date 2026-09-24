# 298: a middle hop with several values follows every branch

Reasoning line, 2026-09-24. Assigned by the month-end plan (330-month-end-plan.md, reasoning row).

## The bug
nb-320 found it at scale: 118 of 2,000 two-hop probes were answered with the list of names at the
first hop (artifacts/claude-nb320-20260923/RESULTS.md §3). The store does what its contract says: a
multi-valued hop answers at once and never continues down the chain. On 292 the same thing reaches
the user. "Where does Ana's friend live?" (Ana has two friends, Bo in Oslo and Cy in Rome) gets
"Ana's friend is Bo and Cy. Which one do you mean?". The ear cannot read the answer to that
question ("Bo." and "I mean Bo." are both refused), so the user never gets the city.

## The one change
scripts/claude_fix298_branches.py wraps the agent's reasoner (install298; build_agent298 =
build_agent292 + install298). When a chain question stops at a multi-valued hop that is not the last
hop, it asks the rest of the chain for each value, oldest fact first, up to 4 values:
- every branch gives the same answer: that answer ("Oslo");
- the branches differ: "Oslo for Bo and Rome for Cy";
- some branches are unknown: "Oslo for Bo (I don't know it for Cy)";
- every branch is unknown: "I don't know Bo or Cy's city" (MISSING_FACT);
- more than 4 values: unchanged, 292 still asks "Which one do you mean?".
Everything else passes through untouched: single-hop questions, single-valued chains, a
multi-valued LAST hop, and every other kind of question. It only reads the notebook; it never
writes.

This is the "follow every branch" option from the plan. Asking "Which friend?" needs the ear to
read the reply, which is ear work, not reasoning. The >4 case still asks, and that stays broken
until the ear can read "Bo." as an answer.

## Tests
- **branchpanel298** (new, blind, sealed before any run). 90 dialogs written by a fresh Opus agent
  that never saw the fix, its hand checks, or this note's examples. 6 categories of 15: SAME,
  DIFFER, PARTIAL, NONE, OVER4, CONTROL. It uses the fact and question shapes the 292 ear reads,
  because 298 tests the reasoner and not the ear.
- **Regression** on the old panels, 292 vs 298: nhoppanel268, nhoppanel268b, yesnopanel293,
  corrpanel291, mixpanel292, and the hand sets hx292 and hp293.

Pass marks: artifacts/claude-rsn298-20260924/PASSMARKS.md. Scorer:
scripts/claude_rsn298_score.py. Both are sealed before the panel is run.

## Known and out of scope
On 292, "Mira's neighbour is Tobin." followed by "Mira's neighbour is Quill." then answers
"Mira's neighbour's boss" with Tobin's boss only (a hand check on 2026-09-24; not investigated).
That happens before 298 and 298 does not change it.
