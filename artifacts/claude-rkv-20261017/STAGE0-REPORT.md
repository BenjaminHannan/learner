# Stage 0 report: decoder_reader_kv on the far-fact toy

Run 2026-10-20 on CPU in this container, $0, no rental. The runner and card are at `7de83cf5f`
(coordinator review of that change: CLEAN, so these runs count).
- **Seals:** `SEAL.sha256.txt` is **superseded** by `SEAL-v2.sha256.txt`.
- **Card:** RUN-CARD §12 is **amended by Addendum A** (exact step matching).
- **Raw outputs:** `stage0/` (META.json, one JSON per run, STAGE0.json, stage0.log, RUN-NOTE.md).

## Verdict against the sealed marks: **FAIL. No GPU spend; stages 1+2 do not book.**

| Mark | Rule | Result | |
|---|---|---|---|
| **V1** (validity) | identical step count and per-step phase schedule in every pair | 1672/1672, 1672/1672, 1671/1671; phases identical | **holds** |
| **G2** | an arm's held-out accuracy > chance + 0.05 = **0.1125** in ≥ 2 of 3 seeds | control 0 of 3; treated **1 of 3** (s1 only) | **fails** |
| G1 | control's pooled cards/q > 0 | 3.96 | passes, **but carries no evidence**: an untrained model already fetches about 4 cards/q (§12) |

FAIL comes from G2 alone. By the card's own wording, the premise of the GPU A/B is shown wrong on this
evidence: neither arm leaves chance in 2 of 3 seeds, so the village A/B could not produce a gain that counts.

## Per-seed rows (chance = 0.0625; 256 held-out questions per run)

| arm | seed | steps | acc | gold-card acc | cards/q | asks/q | null/q | loops | halt rate | gold recall@4 | L_ans | L_ask | true cost ÷ counted | wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| control | 0 | 1672 | 0.055 | 0.055 | 3.99 | 1.00 | 0.01 | 8.00 | 0.00 | 1.000 | 1.251 | 0.031 | 1.000 | 509 |
| treated | 0 | 1672 | 0.074 | 0.074 | 3.93 | 1.00 | 0.07 | 8.00 | 0.00 | 1.000 | 1.253 | 0.007 | **1.019** | 589 |
| control | 1 | 1672 | 0.043 | 0.043 | 3.94 | 1.00 | 0.06 | 8.00 | 0.00 | 1.000 | 1.252 | 0.020 | 1.000 | 516 |
| treated | 1 | 1672 | **0.160** | 0.137 | **7.91** | **1.98** | 0.00 | 8.00 | 0.00 | **0.332** | **0.681** | **2.387** | **1.019** | 622 |
| control | 2 | 1671 | 0.066 | 0.066 | 3.96 | 1.00 | 0.04 | 8.00 | 0.00 | 1.000 | 1.252 | 0.165 | 1.000 | 516 |
| treated | 2 | 1671 | 0.066 | 0.066 | 3.93 | 1.00 | 0.07 | 8.00 | 0.00 | 1.000 | 1.250 | 0.004 | **1.019** | 607 |

- **Paired accuracy differences** (treated − control): +0.020, +0.117 and 0.000.
- **FLOPs:** treated rows use the control's FLOP accounting (Addendum A). Their true cost is 1.9% higher per step (`own_cost_vs_counted`).
- **Guard on the toy** (evidence only, not the verdict guard): the pooled cards/q drop is −32.5%, meaning treated fetched more. Reading: "guard holds".

## What this shows, and what it doesn't

- **Shown:** control D is at chance on the toy in all three seeds (0.043–0.066). Gold-card accuracy is no better, and retrieval recall@4 is 1.00. This reproduces the 09-18 trainer handoff exactly ("retrieval reaches 100% recall@4, answers at chance, even when the gold card is loaded").
- **Shown:** the flag alone does not lift D off chance in 2 of 3 seeds at the toy gate's settings.
- **Suggested, one seed only (treated s1):** the new path *can* make D learn something (L_ans 0.68 vs ~1.25 everywhere else; accuracy 0.160). But in that seed retrieval got **worse** (gold recall@4 1.00 → 0.33, L_ask 0.03 → 2.39) while the card count **rose** (7.9 vs 3.9 per question). That fits the decoder answering from the reader states while the thinker's retrieval degrades: the bypass the guard exists to catch. **The card's count-based guard would not have caught it.** A guard for any later stage should also read gold recall@4 or a retrieval-quality measure, not only the card count. That would be a card change, so it is for the coordinator and Ben.
- **Untested:** whether more steps, other learning rates or more seeds change G2. The marks forbid tuning after the fact; any of these would be a new card.
- **Not shown:** RNG parity at 1,500 steps. The runner doesn't record the trainer generator's state, so parity is shown only at 30 steps (test).

## Open, before any GPU stage (from the coordinator's reviews)

- V1 should assert `matched_to_control`.
- Remove the hard-coded `need` rule.
- Drop the duplicate held-out pass.
- Add resume logic.
- `train_d` step matching (finding 1 of round 2).
- Reader-KV memory growth per loop.
- The FLOP-fit attention term.
- The 2.15M parameter-band disclosure.
- W-store building the memory twice.
- The empty-batch crash.
- CPU-only `fork_rng`.
- The softread mixin failing late.
