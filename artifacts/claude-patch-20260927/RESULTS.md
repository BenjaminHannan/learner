# Registered practice result: source gate failed

Updated 2026-09-28T05:56:22Z from `date -u`. **Shown:** all eight registered arms completed; the practice gate failed in both seeds. No maze race ran.

## Construction and qualification

The rank-eight feedback-written patch reasoner passed all eight fp32 construction checks on the local MPS GPU, including 48-round bounded-patch stability, zero-patch equivalence, query isolation, frozen ordinary weights during writes, and finite nonzero gradients for 20 of 20 matrices. The patch has 1,652,767 total coefficients including 4,096 persistent A/B coefficients; the own loop has 1,645,726 and the plain model 1,646,693. The patch is 0.428% larger than its own loop, within the sealed 2% budget. Both trained patch checkpoints also passed the eight checks. See `CHECKS.md`, `checks.json`, and the two `trained-checks.json` files.

The separate plain-loop qualification pilot passed all six sealed kinds: sums 300 of 300, grids 287 of 300, sorting 300 of 300, reversing 296 of 300, counting 300 of 300, and brackets 300 of 300. Its checkpoint was not reused by any race arm. The kind list and generators were sealed before the pilot and the independent two-seed practice. `QUALIFIED-SEAL.json` and `QUALIFICATION-RECOUNT.json` carry the raw provenance.

## Two-seed practice (selected learned stop)

The fixed marks were 285 of 300 for sums and grids, 270 of 300 for each extra kind, and no more than nine answers behind either own loop control on each kind. All arms received 18,000 supervised batches of 64 and 2,000 episodes on the same six kinds. `loop_meta` is the episodically trained primary loop; `loop` is the additional ordinary-practice reference.

| Seed | Arm | Sums | Grids | Sorting | Reversing | Counting | Brackets | Grids fixed 48 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 927401 | patch | 300 of 300 | 278 of 300 | 297 of 300 | 289 of 300 | 298 of 300 | 300 of 300 | 288 of 300 |
| 927401 | loop | 300 of 300 | 274 of 300 | 293 of 300 | 295 of 300 | 298 of 300 | 300 of 300 | 281 of 300 |
| 927401 | loop_meta | 300 of 300 | 282 of 300 | 297 of 300 | 292 of 300 | 298 of 300 | 300 of 300 | 288 of 300 |
| 927401 | plain | 295 of 300 | 164 of 300 | 297 of 300 | 299 of 300 | 299 of 300 | 300 of 300 | 164 of 300 |
| 927402 | patch | 300 of 300 | 272 of 300 | 296 of 300 | 293 of 300 | 298 of 300 | 300 of 300 | 280 of 300 |
| 927402 | loop | 298 of 300 | 272 of 300 | 298 of 300 | 292 of 300 | 299 of 300 | 300 of 300 | 283 of 300 |
| 927402 | loop_meta | 300 of 300 | 260 of 300 | 298 of 300 | 291 of 300 | 297 of 300 | 300 of 300 | 272 of 300 |
| 927402 | plain | 292 of 300 | 160 of 300 | 300 of 300 | 297 of 300 | 299 of 300 | 300 of 300 | 160 of 300 |

**Shown:** every arm in both seeds passes the other five kinds but misses grids. The patch meets the nine-answer comparison with both loop controls on every kind in both seeds. The full registered gate is therefore **failed**. Fixed-48 scores are diagnostics; they cannot replace the learned-stop eligibility score. Seed 927401's patch recovers ten grid answers at fixed 48 (288 of 300 versus 278 of 300 selected); seed 927402 still scores only 280 of 300 at fixed 48. Early stopping contributes to some errors, but does not explain the complete failure. `PRACTICE-GATES.json`, `BLIND-RECOUNT.json`, and `FINAL-GATE-AUDIT.json` record the decision and raw recount.

## Compute and limits of the result

The patch performs 8,000 support writes per seed; the episodic loop and plain controls each perform 8,000 inner gradient steps. All eight arms have 18,000 supervised and 2,000 episode optimizer steps. Batch-one fp32 MPS inference timing on 180 sealed inputs per arm varies across runs: patch mean 29.1 ms versus episodic loop 35.7 ms on seed 927401, and patch 55.8 ms versus episodic loop 13.9 ms on seed 927402. Those observed timings do not support a stable speed advantage or overhead claim across the sequential runs. `result.json` and `inference-timing.json` preserve operations, rounds, and per-input timings.

**Shown:** `STATUS.json` records `completed_all` and `race_run: false`. The gated race driver returns `wider-practice gate failed; no design race`, and no race output exists. The test harness marks were sealed, but source eligibility was not met.

**Untested:** few-example maze advantage over the loop or plain net, old-kind retention after maze supports, sleep absorption with the patch removed, whether wider practice helps the loop on mazes, and the Test A `F_all` bars. No contender is promoted.

**Suggested:** the separate Astra review recommends a fresh 18,000-versus-36,000-batch source-only study across all four arms and both seeds to test whether more supervised practice restores eligibility. Its code, protocol, and fresh 300-item panels are sealed in `budget-v2/`; no budget-v2 model has been trained or scored. It is a separate, post-failure study, not a reinterpretation of these failed gates. A full maze race would require a new source-eligible registration and the ruler's V1–V3 validity.

## Audit status

The lead's raw recount regraded 17 panels (pilot plus eight development and eight verification panels) and matched all selected counts and the gate flags; `FINAL-GATE-AUDIT.json` agrees with `PRACTICE-GATES.json`. A separate Sol subagent then regraded all 17 raw files against sealed panel identities and the original marks without reading the lead's verdict. `FINAL-SOL-BLIND-RECOUNT.json` and `.md` report the same failed gate, all six counts per arm/seed, and no recount discrepancies. Candidate source hashes still match the original seal. No checkpoint, budget, stop rule, threshold, or panel was changed in response to an observed score.
