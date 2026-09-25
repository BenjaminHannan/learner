# slp-364 results: REGISTERED FAIL (proved wrong)

Run 2026-09-25 ~01:35-02:40 UTC, CPU, $0, sealed code (SEAL.sha256.txt checks OK), 40 bench cases, 0 errors.
Raw rows: results.json (`rows`); marks recounted by hand from the rows and agree with the script.

| Mark | Bar | Result | |
|---|---|---|---|
| P364.1 faulty nights rejected | ≥ 18/20 | 13/20 | FAIL |
| P364.2 clean nights rejected | ≤ 1/20 | 0/20 | pass |
| P364.3 gate catches minus twin catches | ≥ +6 | 13 − 0 = +13 | pass |
| P364.4 every rejected night leaves main unchanged | all 13 | 11/13 | FAIL |

Proved-wrong clause (fewer than 14/20 faults caught): TRIGGERED (13).
Twin (the sleeper's own `accepted` flag) caught 0/20: today's rule accepts every faulty night.

## Per category (faults caught)
| Category | Caught |
|---|---|
| wrong-route | 3/3 |
| taught-fact-changed | 3/3 |
| forgets-earlier-word | 2/2 |
| one-of-many | 2/2 |
| some-people-corrupted | 1/1 |
| made-up-answer | 2/3 |
| silent-noop | 0/3 |
| new-names-only | 0/3 |

## Why each miss happened (checked in the code after the run; these are the reasons, not fixes)
1. **silent-noop 0/3** (slp364-01, -29, -32). The sleeper said it learned a word but nothing changed. The gate only
   looks for replies that got worse; a night that changes nothing looks clean. Missing check: "the sleeper says it
   installed word X, so X's questions must now be answered right."
2. **new-names-only 0/3** (slp364-05, -14, -37). The fault only hits people taught after the sleep. The gate only
   asks about people who already exist, so it cannot see it. Missing check: teach a few invented people inside the
   sandbox after the night and ask about them.
3. **made-up-answer 1 miss** (slp364-30, word "father of mother"). A budget bug: broken-chain lures are capped at
   60 (MAX_L364) and filled word by word in a fixed order, so the cap ran out before this word's broken chains.
4. **P364.4, 2 cases** (slp364-10 sleep_rewrites_taught, slp364-19 sleep_writes_guess). The gate rejected both
   nights, but those faults wrote rows with source "taught" straight through `loop.nb.assert_fact` during the
   sleep. slp-360 only moves guessed sources (sleep-derived, inferred) to the scrap layer, and slp-361 never copies
   the main notebook back, so the rows stayed. Real gap: during a sleep nothing should be able to write "taught".

Clean nights: all 20 kept, 0 reasons. Wall time ~67 CPU-minutes total (4 workers).

## What it means
The gate is much better than today's rule (13 vs 0 bad nights caught, 0 good nights thrown away), but it is not
good enough to rely on, and it can't yet stop a sleep from writing "taught" rows. 364 stays FAIL.
Next (each a new sealed test on a NEW blind bench, since this bench has now been seen): 368 = block every
main-notebook write during sleep; 364b = gate with the claim check, sandbox new-people probes, and lures spread
across words.
