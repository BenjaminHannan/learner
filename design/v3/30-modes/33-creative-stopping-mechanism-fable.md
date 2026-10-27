# 33 — How CREATIVE ends: FOUND, ASK-BEN, or BUDGET-OUT (Fable design, 21 Sep 2026)

Status: **designed**, not built, not tested. Additive to 31/32. CREATIVE is a sub-routine (ruling 32) called by
WORK or by idle THINKING/LEARNING. It runs 31-B3's lead engine: dreamer → dedupe → filter → checker. This file
adds only the ending. All numbers are **defaults, to be tuned on a development suite and frozen before any test**.

## 1. Step 0 and the three exits

**Step 0 — freeze and classify.** Before round 1 the *caller* (never the dreamer) freezes the goal and, if one
exists, an acceptance check: a test, experiment, notebook derivation or tool run with a pass mark.
- **CHECKABLE**: such a check exists (e.g. "new context-compaction method" + frozen benchmark, baseline, margin).
- **UNCHECKABLE / opinion**: the filter is only a judge.

| Exit | Exact definition | What goes back |
|---|---|---|
| **FOUND** (checkable only) | The **checker** (not the filter) returns PASS on the lead's structured claim + dependency IDs against the frozen check, score = 1.0 (or ≥ the frozen margin). If the check is noisy, it must pass again on a fresh seed / held-out instance. | Lead `SURVIVED` + evidence IDs → appended to WORK's checklist (T5). Text says "passed check X", never "true". |
| **PROPOSALS** (uncheckable form of exit 1) | Stopping rule fired; nothing can be verified. | Top 3 ideas from 3 different clusters, filter-ranked, each with its strongest objection, stamped `judge_only, verified=none`. **Never called FOUND.** No side-effect actions on them without Ben. |
| **GIVE-UP → ASK-BEN** | Stopping rule (§2) says continuing is not worth it, budget remains, refine loop used up. | Job `PARKED`, one question (template below), drop to THINKING. |
| **BUDGET-OUT** | A harness-metered hard cap hit first: "attempt exhausted", not "impossible". | Job `PARKED`, question kind `BUDGET`: same template + trend ("best score 0.4 → 0.8") + exact extra budget requested. |

**Question template (≤ 8 lines, answerable in one line):**
1. Goal, as frozen. 2. Tried: N ideas, M distinct clusters, K checked, compute spent. 3. Best 3 rejected ideas
(distinct clusters): score + the exact check condition each failed. 4. **The unblocker**: the single failed
condition or `BLOCKED` fact shared by the most near-misses. 5. Options: (a) give the fact/hint, (b) relax
condition X, (c) grant budget B, (d) drop the job.

If the caller is THINKING, no immediate question: the record goes to the gap list and at most one digest line.

## 2. The stopping rule

One **round** = dream G candidates → signature dedupe → filter → check the top C survivors.

**Defaults:** G = 8, C = 2. Hard caps: 6 rounds, 48 candidates, 12 checks, job-class wall-clock; metered by the
gateway (31-B2), never self-reported. Check score s ∈ [0,1] = share of frozen conditions passed.
**Near-miss**: 0.7 ≤ s < pass. Minimum 2 rounds before any give-up.

After each round, in this order:
1. **Any PASS → FOUND.**
2. **Hard cap hit → BUDGET-OUT.**
3. **Stall test (diminishing returns).** A round is a *stall* if (new distinct clusters < 2 of 8) AND (best s
   improved < 0.05). A *dry* round (filter kept nothing) is a stall. **k = 2 stalls in a row → stop.**
4. **Expected-value test.** Per-check pass chance from a Beta(1,3) prior:
   `p = (1 + 0.5·near_misses) / (4 + failed_checks)`; `P_round = 1 − (1−p)^C`. Continue only if
   `P_round × V ≥ round_cost`. Default V = 5 × round_cost, so **stop when P_round < 0.20**. Worked out: no
   near-misses → stops after 6 failed checks (round 3); one near-miss → after 11; two → the hard cap decides.
   The caller may raise V, never the hard caps.
5. **If 3 or 4 fired:** an unrefined near-miss exists → **refine loop**; otherwise → GIVE-UP.

**Refine loop.** For the best near-miss (at most 2 leads): up to 3 steps; each step = 4 small mutations, check
the best one. A step must raise s by ≥ 0.05 or the loop ends. Refine checks count inside the 12-check cap.
PASS → FOUND; otherwise GIVE-UP with the near-miss leading line 3 of the question.

**"How high" schedule.** Temperature levels {0.7, 1.0, 1.3, 1.6}, start 1.0, one move per round:
- a near-miss appeared → **down one**, and half of the next round is mutations of it (narrow);
- all rejected and > 50% duplicates or boring-but-wrong (s < 0.3, near an old cluster) → **up one** (widen);
- > 50% rejected as incoherent → **down one**;
In v1 (enumeration proposer, no neural dreamer) "temperature" = search radius in the hypothesis space.

**Uncheckable questions:** no s exists, so only the caps (halved: 3 rounds, 24 candidates) and the novelty half
of the stall test apply (no new cluster enters the top 3 for 2 rounds). Exit is PROPOSALS.

## 3. Guards

| Failure | Guard |
|---|---|
| Dreamer learns to please a weak filter | The filter never grants FOUND and its score is never a training reward; later dreamer training uses checker PASS/FAIL only. Planted attractive-but-false decoys: count reaching FOUND must be 0. Filter precision (accepted → check-pass) falling below half its dev value is a digest fault. |
| Shared blind spots | Filter ≠ dreamer: different weights where possible; it sees only the structured claim, never the dreamer's wording. Final authority is the non-neural checker. **Rescue audit:** every 8th check goes to a random filter-rejected lead, measuring what the filter wrongly kills. |
| Same idea, new words | Signature = normalised (required facts, actions, predicted outcome); with a learned dreamer, also embedding cosine > 0.9 = same cluster. Rejected clusters persist per job; an equivalent retry is forbidden unless `notebook_version` changed. |
| Endless refinement | ≤ 2 leads × 3 steps, must-improve-by-0.05, inside the hard cap. |
| Asking too often | One question per parked job; ≤ 2 CREATIVE asks/day from WORK; THINKING never asks immediately (one batched digest line); jobs sharing an unblocker merge into one question; no re-ask of an unanswered unblocker within 7 days; 31's max of 3 blocking questions stands. |
| Asking too rarely (false FOUND) | Checker-only FOUND; re-pass for noisy checks; margins frozen at Step 0; uncheckable never FOUND. A FOUND route that later fails WORK's acceptance check is logged `FALSE_FOUND`: digest fault, target 0. |

**Notebook labels (31/32).** A FOUND *route* is not a fact: it lives in the lead log (`SURVIVED` + evidence).
A FOUND *fact candidate* is written `proposed` with `deps` and `check_id`. It becomes `inferred` only when it is
an exact application of a Ben-approved rule, committed by the checker alone. PROPOSALS are `proposed` +
`judge_only`. Nothing from CREATIVE is ever `taught`; answers keep using `taught` + `inferred` only.

## 4. A learned "stop thinking" token, later

A small controller could emit `CONTINUE / REFINE / STOP-ASK` each round, replacing only the **soft** parts:
stall test, EV estimate, temperature move. **Never learned:** hard caps, checker-only FOUND, the PROPOSALS
label, ask rate limits. Training signal: runs pushed to the cap, labelled in hindsight with the best stopping
round. It first runs in **shadow** (logged, not obeyed). Evidence to switch it on: a frozen held-out suite,
≥ 200 items × 3 seeds, where it gives **≥ 10% more solved per unit compute** than the plain rule with
**0 false FOUNDs**, correct give-ups on unsolvable items within 2 points of the rule, no higher ask rate, plus
31's bar of ≥ 50 logged episodes where the plain rule was demonstrably wrong.

## 5. Smallest test (CPU, < 30 min, no neural training)

**Toy: hidden rule in a notebook world.** 12 entities, 6 random base relations. Hypothesis space H = one
relation or a 2-step chain, each step optionally inverted: 12 + 144 = 156 rules. Each item hides a target
relation. Check = exact comparison over all 144 entity pairs; s = overlap (Jaccard) of predicted and true pair
sets, so sparse relations cannot score high by predicting nothing.
- **120 solvable** items (target in H); **60 unsolvable** (3-step chain or random relation, confirmed unsolvable
  by exhaustively checking all 156).
- Dreamer = random sampler over H; temperature sets chain depth and mutation distance from near-misses.
  Filter = strict cheap judge seeing only 6 example pairs (so it errs). Checker = exact.
- Separate 60-item dev suite for tuning; then freeze numbers, suite and 3 seeds.

**Arms** (same dreamer, filter, checker, caps, seeds): (A) this rule; (B) fixed-N rounds, N tuned on dev;
(C) never-stop-until-budget; (D) negative control: FOUND granted by filter score.

**Pass marks, fixed now:**
1. False FOUNDs = 0 in A, B, C; **> 0 in D** (shows the metric can catch them).
2. A solves ≥ 95% of what C solves.
3. A uses ≤ 70% of C's total compute.
4. A vs B: ≥ 5 more solved at equal-or-less compute, or equal solved at ≥ 15% less compute.
5. Unsolvable items: A exits GIVE-UP (not BUDGET-OUT) on ≥ 48/60, using ≤ 60% of the cap on average.
6. 100% of give-up records contain all template fields; the unblocker names a real failed condition.
Any miss → keep plain fixed-N and say so. A pass supports only "the stopping controller is sensible on a toy";
it says nothing about creativity or a neural dreamer.

## 6. Summary for Ben (8 lines)

1. Before brainstorming, the caller freezes the goal and says whether an idea can be *checked* or only *judged*.
2. Checkable: FOUND means the strict checker passed it — never the filter's opinion, never the dreamer's.
3. Only judgeable: it returns its top 3 as ranked "proposals", clearly stamped unverified, never "found".
4. Each round: dream 8, remove repeats, filter, check the best 2; hard cap 6 rounds / 12 checks, enforced from outside.
5. It stops early when two rounds bring nothing new and no better score, or when the odds of a hit fall below 1 in 5.
6. Near-misses make it calm down and polish (max 3 polish steps); all-boring rounds make it go "higher".
7. Giving up means one short question: what I tried, the 3 best failures and why, the one thing that would unblock me.
8. First test is a CPU toy with some provably unsolvable puzzles: it must beat fixed-N and never-stop, with zero false FOUNDs.
