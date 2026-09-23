# Canonical-operator variant `balance` — relation-balanced one-hop canonical records

Written 2026-09-20 EDT, before any `balance` run. Drafted by the build agent from Ben's
brief. **Review and amend before running `freeze`: `freeze` hashes this file and
`check_manifest` re-verifies the hash before every worker and every wave.**

## The problem this addresses

In v1/v2/v3r the six canonical records per visit are 2 one-hop questions taken from the
generator (relation uniform over r8, r9, r10), 2 LINK records, and 2 terminal records.
The terminal records are derived from the two practised two-hop questions, whose relation
is drawn from `two_rel = [0, 1]` in training, so they only ever ask about relations 8 and
9. Per visit the expected canonical attribute-record counts are therefore

    r8: 2/3 + 1 = 5/3      r9: 2/3 + 1 = 5/3      r10: 2/3

— relation 10 (the held-out relation, the one cells c3 and p12-3 depend on) gets about
2.5x fewer canonical attribute examples than r8 or r9. The v3r diagnosis already showed
seed 0 at 191-196/203 on relation 10 while relations 8 and 9 were saturated.

## The ONE change versus v3r

Each visit's two one-hop canonical records are rebuilt as fresh one-hop questions over
that visit's own visible facts:

* entity: uniform over the world's six people;
* relation: (r8, r9, r10) = (1/6, 1/6, 2/3), drawn as a single `randrange(6)`;
* answer and supporting line: read off the visible attribute row `[world] ENT REL VAL` —
  the same information the generator's own one-hop questions carry;
* `where` (causal eligibility) is the question-line index of the one-hop question the
  record replaces, so the eligible-fact mask is byte-identical to v3r's.

Expected canonical attribute-record counts become 4/3 per relation per visit, equal
across r8, r9, r10. Still exactly 6 canonical + 2 monolithic records per visit. Relation
10 is still never the terminal of a two-hop-derived record.

## Everything else is identical to v3r

Model `CanonicalOperator`, init `A.new_model(seed)`, AdamW(lr 1e-3, betas .9/.99, eps
1e-8, weight decay .1), grad clipping 1.0, the v3r lr-decay schedule (warmup to 1e-3 over
100 steps, flat to update 4,000, linear to 1e-4 at 6,000), 6,000 updates, 16 visits per
update, `random.Random(1101)` consumed identically for world generation (the extra draws
come from a separate `random.Random("fable-variant-balance:<seed>")`), the semantic
overlap `forbidden` check, answer CE + 0.5 x supporting-line attention loss at .75/.25,
the two monolithic records unchanged, zero three-hop / 12-person / held-out-composition
training, final-checkpoint-only scoring of R and M on the same ten panels with the same
cutoffs, training cap 1,500 s, work/terminate deadlines 1,740/1,770 s, incomplete =
failed.

## Predictions (score as written)

1. Relation 10 improves: c3 (own held-out two-hop) and p12-3 meet their cutoffs in more
   seeds than v3r did.
2. c1 (own one-hop) does not regress below its 487 cutoff in any seed.
3. Relations 8 and 9 are unaffected: c2 and p12-2 stay at or near their v3r values.
4. M stays below 128/512 on c3-c6 and s3 in every seed.

Success = R meets all ten cutoffs in every seed of wave 1 (seeds 0, 1, 2). Wave 2
(seeds 3, 4, 5) is reported the same way and never averaged with wave 1.

If it fails: report, keep, and diagnose before any further change.

## Fable's amendments before freeze (2026-09-20 ~09:20 EDT, before any run)
Roster: seeds 0,1,2 (wave 1). If wave 1 shows no harm, seeds 3,4,5 follow as wave 2 under the same frozen manifest. Pass marks: Astra's ten cutoffs for the recursive arm R, every seed separately, plus Ben's criterion: relation-10 one-hop accuracy (c1 and p12-1, split by relation) must rise for seed 0 versus v3r (150/163 and 126/174) WITHOUT relations 8 or 9 dropping below their v3r counts by more than 2 questions in any seed. Context (shown): v3r gave 5 of 6 seeds perfect; seed 0 missed c4, c5, p12-1, p12-3, all through relation 10 with every LINK correct.
Predictions: seed 0's relation 10 improves on both panels; seeds 1,2 stay at 512-level; seed 0 passes the six-person cells but I give only ~50% that it clears p12-3 (461/512). If relation 10 does not improve, under-representation is insufficient to explain seed 0 and the balance idea is dropped.
