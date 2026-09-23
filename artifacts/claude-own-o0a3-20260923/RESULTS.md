# own-O0a3 PERMISSION AUDIT — RESULTS (registered run, once, 2026-09-23)

## Verdict first

**Pown0a3.1 10/10 predictions HIT. Pown0a3.2 PASS (0 crashes). Pown0a3.3 PASS
(table complete: every kind x rule).** This is a measurement, no pass bar on
the counts — and the measurement is stark: of wrong readings built on top of
*savable* truths (clean subset), v0 lets 68.1% through, v1 lets 68.1%
through, and learned-licensed lets 96.7% through. Only three things in the
whole exercise ever stopped a wrong reading: a missing relation cue (m5 under
v0/v1), a WE owner (m6-me2we, Ben's ruling), and a no-save mode / empty value
/ OTHER relation (m8 structural). Every other kind of wrongness — wrong
person, wrong value, reversed fact, wrong-but-cued relation, ME-claimed
fact, off-by-one-word value, or a question dressed up as a statement — sails
through every rule, because the compiler trusts the reader's choice of span,
relation and mode.

## Marks table (integer counts)

| Mark | Bar | Got | Result |
|---|---|---|---|
| Pown0a3.1 predictions stated pre-run, hits/misses honest | report | 10/10 HIT (P1,P2,P3,P4,P5,P6a,P6b,P6c,P7,P8) | report |
| Pown0a3.2 crashes in registered run | 0 | 0 | **PASS** |
| Pown0a3.3 table complete, every kind x rule | complete | 11 rows x 3 rules, all filled | **PASS** |

Fixed denominators (deterministic generator, sealed): 553 gold ACD facts ->
5696 mutants (m1 813, m2 1639, m3 353, m4 137, m5 1659, m6 553, m7 542);
190 gold no-save facts -> 190 m8 mutants. Total 5886 wrong readings.

## Raw table: wrong readings made / blocked / let through, per kind x rule

(clean = subset whose gold fact is itself writable under that rule)

| Kind | Rule | Made | Blocked | Through | Clean made | Clean blocked | Clean through |
|---|---|---|---|---|---|---|---|
| m1 owner->other name | v0 | 813 | 433 | 380 | 363 | 0 | 363 |
| m1 | v1 | 813 | 49 | 764 | 737 | 0 | 737 |
| m1 | licensed | 813 | 21 | 792 | 764 | 0 | 764 |
| m2 value->other word | v0 | 1639 | 763 | 876 | 844 | 0 | 844 |
| m2 | v1 | 1639 | 159 | 1480 | 1442 | 0 | 1442 |
| m2 | licensed | 1639 | 94 | 1545 | 1507 | 0 | 1507 |
| m3 owner/value reversed | v0 | 353 | 168 | 185 | 185 | 0 | 185 |
| m3 | v1 | 353 | 45 | 308 | 308 | 0 | 308 |
| m3 | licensed | 353 | 25 | 328 | 328 | 0 | 328 |
| m4 relation->cued other | v0 | 137 | 4 | 133 | 109 | 0 | 109 |
| m4 | v1 | 137 | 4 | 133 | 129 | 0 | 129 |
| m4 | licensed | 137 | 4 | 133 | 132 | 0 | 132 |
| m5 relation->uncued | v0 | 1659 | 1659 | 0 | 828 | 828 | 0 |
| m5 | v1 | 1659 | 1659 | 0 | 1428 | 1428 | 0 |
| m5 | licensed | 1659 | 105 | 1554 | 1503 | 0 | 1503 |
| m6 ME->WE | v0/v1/lic | 180 | 180 | 0 | 91/168/173 | 91/168/173 | 0/0/0 |
| m6 name->ME | v0 | 353 | 167 | 186 | 185 | 0 | 185 |
| m6 name->ME | v1 | 353 | 42 | 311 | 308 | 0 | 308 |
| m6 name->ME | licensed | 353 | 22 | 331 | 328 | 0 | 328 |
| m6 WE->ME (clean n=0) | v0 | 20 | 5 | 15 | 0 | 0 | 0 |
| m6 WE->ME | v1 | 20 | 1 | 19 | 0 | 0 | 0 |
| m6 WE->ME | licensed | 20 | 0 | 20 | 0 | 0 | 0 |
| m7 trim | v0/v1/lic | 40 | 18/7/6 | 22/33/34 | 21/32/33 | 0/0/0 | 21/32/33 |
| m7 extend-next | v0/v1/lic | 232 | 128/21/6 | 104/211/226 | 104/211/226 | 0/0/0 | 104/211/226 |
| m7 extend-prev | v0/v1/lic | 270 | 119/37/28 | 151/233/242 | 151/233/242 | 0/0/0 | 151/233/242 |
| m8 mode->ASSERT | v0 | 190 | 125 | 65 | (n/a) | (n/a) | (n/a) |
| m8 | v1 | 190 | 81 | 109 | (n/a) | (n/a) | (n/a) |
| m8 | licensed | 190 | 65 | 125 | (n/a) | (n/a) | (n/a) |

m8 partition (hierarchical: empty value 55, incl. 7 also-OTHER; OTHER-valued
1; WE-owned valued 9; rest 125): the 65 structural mutants are blocked 100%
under all three rules; rest through-rates are v0 65/125 = 52.0%, v1 109/125
= 87.2%, licensed 125/125 = 100% (rest blocks under v0/v1 are all
no-relation-cue: cue-less questions and checks).

Rollups: raw through-share v0 2117/5886 = 36.0%, v1 3601/5886 = 61.2%,
licensed 5330/5886 = 90.6%. Clean through-share (wrong readings on savable
truths — the safety-relevant number) v0 1962/2881 = 68.1%, v1 3400/4996 =
68.1%, licensed 5063/5236 = 96.7%.

## Prediction score (Pown0a3.1): 10/10 HIT

P1 m1 clean-through >=95% all rules: got 100/100/100% HIT. P2 m2: 100% HIT.
P3 m3: 100% HIT. P4 m4 >=90%: got 100% (n=109/129/132) HIT. P5 m5: blocked
100% v0 (828/828), 100% v1 (1428/1428), through 100% licensed (1503/1503)
HIT. P6a me2we blocked 100% all (91/91, 168/168, 173/173) HIT. P6b name2me
>=95%: got 100% HIT. P6c we2me raw >=70% each: got 75/95/100% HIT (clean base
empty as predicted — no WE gold is writable while WE is never saved). P7 m7
>=90%: got 100% in all 9 sub-cells HIT. P8 m8: structural 65/65 blocked
everywhere HIT; rest licensed 100% HIT, v1 87.2% in 75-95% HIT, v0 52.0% in
40-65% HIT, ordering lic>=v1>=v0 HIT.

## Every move, every miss, deviations

- Moves: the run executed the sealed script once on the sealed inputs; 5886
  mutants judged under 3 rules (17658 verdicts); per-cell made =
  blocked + through asserted in code (0 assertion failures, 0 crashes).
- Misses: none against the sealed predictions (10/10). One refinement is
  disclosed, not hidden: the brief's design guess said "m8 mostly get
  THROUGH every rule", but the pilot (dev data, sanctioned by the
  registration protocol) showed rest-v0 at ~52%, so the sealed P8 band for
  v0 was written as 40-65% before the seal — the seal, not the guess, is
  what is scored, and it HIT. No TEST-ONLY panel, no
  artifacts/claude-*panel* folder, and no artifacts/claude-own-bench-20260923
  was opened at any point; CPU only; fictional names only; additive only
  (1 new script + 1 new artifacts dir + ledger lines appended).
- Determinism check: registered summary.json is byte-identical to the pilot
  summary (diff empty). Seals re-verified after the run: shasum -c OK on
  both sealed files. No sealed file changed.
- Overlap note: 7 m8 mutants are both empty-valued and OTHER-related;
  counted once under empty-value in the hierarchical partition.

## What it means (plain high-school English)

Think of the write rules as a bouncer checking IDs. We handed him 5886 fake
IDs — each wrong in exactly one way — built from real guests. He caught only
three kinds of fakes: ones naming a relation nobody mentioned (but only
while the strict list is in force — the loose backup rule waves those
through too), ones saying "we" (because Ben ruled "we" always gets a
question, not a save), and ones that were questions pretending to be
statements but had nothing to point at. Every other fake — wrong person,
wrong value, backwards fact, wrong-but-mentioned relation, "mine" claimed
for someone else's fact, value off by one word, or a normal question
rewritten as a statement ("Is Mira's dog Pip?" -> "Mira's dog is Pip") —
walks straight in under EVERY rule, including the strict one. Loosening the
rules bought coverage (O0a2: 68% -> 90%) and the price is printed here:
licensed lets through 96.7% of wrong readings built on savable truths.

## What it doesn't mean

It does NOT mean the system saves wrong facts 97% of the time — these fakes
were fed straight to the bouncer, skipping the reader; a real ear has to
*make* these misreadings first, and measuring how often it does is a
separate experiment. It does NOT mean v1 is less safe than v0 in any way
that matters here: on the clean measure both let through exactly the same
kinds (68.1% each; v1's extra saves are true facts per O0a2). It does NOT
mean the rules are useless — the mode gate, the span requirement, the cue
requirement and the WE ruling each demonstrably block a real class of
wrongness. It means only this: the rules check the *shape* of a reading
(spans present? cue present? mode right?), never its *truth*, so any wrong
reading with the right shape gets saved — and only the reader (or an
independent checker that re-reads the turn) can stop those.
