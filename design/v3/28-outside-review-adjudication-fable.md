# Outside review of the 44 problems — coordinator adjudication (Fable, 21 Sep 2026)

Source: `28-outside-review-answer-verbatim.txt` (19-page PDF relayed by Ben; text extracted unchanged).
The review was written before experiments 26, 27 and 29 finished, so some items are already settled.

## Already settled by our own results (review's forecast → what happened)

| # | Review said | Outcome |
|---|---|---|
| 5 | Finish the no-training probe; 0.80 it changes the story | Exp 26 done: STOP healthy, operation pointer "counts calls". Matches the review's #2 diagnosis. |
| 10 | Run 27 unchanged; 0.30 all seeds pass every cell | 27: 2/3 (review right). 29 (10,000 updates): 3/3 PASS. |
| 11 | Pointer output should beat frozen-scale decoding | Not needed for 16-candidate worlds (29 passed). Still the right fix for the open-set pick (0.57–0.60). |
| M1 | Candidate set ambiguous (4,096 vs chance 1/16) | Loss and scoring use the 16 names in the world; the 4,096-code pick is a separate descriptive read-out. |
| M2 | Reserved codes may be training negatives | No: they never enter a training world, and the softmax is over the world's names only. |
| M3 | Sampling with replacement → collisions | No: `rng.sample` (without replacement), fable_newnames21.py:389. |

## Accepted (changes what we do)

- **#1, #3, #44 stop-rule: hard-code the hop loop for the assistant.** The learned dispatcher becomes an
  ablation, off the demo path. 25b step 3 stays held. If ever reopened: supervised traces, not RL (#3), and a
  relative-position operation head (#2).
- **#13, #17, #18, M16–M21: write the notebook contract as plain software first** — stable IDs + aliases,
  append-only event log with supersede, discrete failure statuses (MISSING_FACT, BROKEN_CHAIN, AMBIGUOUS,
  CONFLICT), deterministic "I don't know" templates, idempotent events. Tests before any model touches it.
- **#7, #21: Ben writes his sentences before more talker tuning.** 30 natural teach/correct/ask turns now
  (scope written first), the sealed 100 later. This is the cheapest test in the whole review.
- **#20, #26: gist has no factual authority; old values come from the notebook as references**, not from a
  wider thought vector.
- **#24: capitalisation name-masking is not an identity authority**; keep raw spans recoverable.
- **#30: no 6-hour Windows run until save–kill–resume is shown to give the same next batches.**
- **#32: cut the 90M and 209M milestones for now. Keep the $27.**
- **#38: lighter manifests for cheap diagnostics; full freeze + audit only for confirmations.** (Experiment 29
  cost more procedure than compute — the review is right.)
- **#41: concept toy parked. #34, #35, #36: dreamer, web, tools stay parked.**
- **#43: adopt the review's honest description**, updated for 29: "binds never-seen names in 16-candidate
  worlds, 3/3 seeds, fixed scale" replaces "new entity codes not demonstrated".

## Not accepted, or Ben's call

- **#42 "deterministic replies first, 33M talker is not the cheapest experiment."** Technically right, but Ben
  explicitly asked for a model that talks (talker route B). Proposal: do both in order — deterministic
  renderer is the reference path and the debugging control (#25); the learned talker is trained against the
  same structured interface and must match it. Ben decides whether the learned talker waits.
- **#33 bAbI / Memory Network replication, #6 assistance ledger, #28 LM-with-facts baseline:** worth doing
  before any outside claim; not this month's critical path.
- **#44 R4 "zero trap" as the possible research result:** agreed it is the best novelty candidate; a minimal
  causal reproduction is cheap (finite-difference gradient check + collapse/rescue on a tiny model). Queue
  after the notebook contract.

## Proposed order (short)

1. Ben: 30 natural turns (30 min of his time). Me: scope note first, so the set is fair.
2. Notebook contract + deterministic executor + status templates, with the 30-sequence lifecycle suite (#17).
3. Represent Ben's 30 turns in the schema by hand → fix the schema gaps (#7 pass mark 27/30).
4. Smallest supervised parser into that schema; deterministic replies; end-to-end on Ben's turns.
5. Learned talker (route B) against the same interface, only after 4 works.
