# Concept toy ct20-v1.1 — freeze manifest for baseline-only wave 1

Fable (coordinator) · 20 September 2026 · written after the independent auditor's operative
`FREEZE-READY: YES` and before any learner was fitted or scored on the registered calibration worlds.

Scope authorised by Astra's rulings 2: G/T baselines only, tier L, plus the single conditional tier H
if and only if the tier-L verdict is `awaiting-tier-H`. No pool models, no task B, no M-family work.
Seeds 20001/20002/20003; no replacements or selective restarts. No cloud spending.

## Bound documents (sha256)

| Document | sha256 |
|---|---|
| design/v3/20-concept-toy-preregistration-draft.md | 1bb49e074d70cc7692ce2af40b6624cf626694b8cc5bb8a0b56a816aab258251 |
| design/v3/20-concept-toy-simulator-spec.md | aa80843c5a7a5d51ba675c8c0715ff823a30e15b4b7f15275be506dbd324e8a8 |
| design/v3/20-concept-toy-build-plan.md | ba255726fac5985e305495bba0e6e52ec8139e28624a49c703115a1a2b9fd354 |
| design/v3/20-concept-toy-rulings-1.md | 40f650451b6b1404e352c900fabb9a6f56fa1696aaac31e90fdc4cac2779c6de |
| design/v3/20-concept-toy-rulings-2.md (on disk; second Astra chat) | 1245e46f567dd1a265d6b05d8482f0267052c735159b8d05864dd6b861a110f2 |
| RULINGS-2-first-version-as-relayed.md (first Astra chat, preserved from Ben's relay; original on-disk sha 8a62ef05… is not reproducible) | fac03f785ca6b0e0a0fb3954ac2308b783629b75afda23863633e1ff3bca1269 |
| FABLE-PREDICTIONS-pilot.md (P76–P82) | 420f9363c344f8ef7cd6d907c726938fadae5784d95aeb729e2f8e5990da8cc9 |
| SCHEMA.md | 7e9239c077e4252dc2d44d7cc9b0e932a3c556446aadc5fea1d88a6f96562628 |
| audit/PILOT-AUDIT.md (ends `FREEZE-READY: YES`) | a2b2fa9d5387224220aa977b91e0358e8b90af1657b1ec5d9874b02d22b718df |

Both rulings-2 versions are bound. The auditor and the coordinator each read both and found no
conflict; where one is silent the other governs (first version: three cost constants, per-rung
scoring, per-rung step table, launch preflight, secret-salt recommendation; on-disk version:
complete-wave train + validation integrity).

## Bound code and data (sha256)

| File | sha256 |
|---|---|
| scripts/fable_concepttoy20_sim.py | c56794c52ad0e44022df2af9c161ccf10775eb626bf0ab6052cc81207c96d7a0 |
| scripts/fable_concepttoy20_public.py | 7139c6989f8618dcca9d4ef2e31b5c667424e3fca8a183e8f30b36a1e3b567fe |
| scripts/fable_concepttoy20_models.py | 0b5711f4ef8c378284e784032c6d8560fe169f686c4a76a8af5b4abc918d34ff |
| scripts/fable_concepttoy20_wave1.py | 2db9889a49ad8d88edf58a8921efb19dbf0c179e3c093cd6cd60d83cc0b46c69 |
| tests/test_fable_concepttoy20_sim.py | db86bf0fb3a27cafd6f43a8f1336c444d7209b20cb838bb5aa92f5ed9db7d16f |
| tests/test_fable_concepttoy20_models.py | aaae8702ac8280e9be20bafb491be28a5533b6cc3abc2abe831de83a0ea60e49 |
| tests/test_fable_concepttoy20_wave1.py | 9b5d5a73bcd270601add5d9f4b663c017c110024aa82f0a927b93581a6d6a812 |
| audit/gate_calculator.py | 62ec54f10ed2acec9faa97d4abdbda2bb5a43cccb5924016d08a0a4e79738f71 |
| audit/test_gate_calculator.py (174 tests) | ce9146abdf76222ee870c74d43ed3daf88d790ff06258b5094314d75f54a82b6 |
| calibration-v1.1/manifest.json | de3ccfec81c8847f879c3d886e4a7450085cb4f1bac849cc59acb19644f146d3 |
| fixture-v1.1/manifest.json | 97fb94cf450e7aff704ce8601ad3e34ee1faf890cb5ee358eedff1aa3326bbcd |

The auditor verified 459 data files against these manifests with 0 mismatches.

## Registered procedure

One launch of `scripts/fable_concepttoy20_wave1.py --concurrency 6 --preflight-seconds 6`, output
`wave1/registered`, which refuses to overwrite. 72 fits per tier (12 worlds × 3 seeds × 2 arms);
tier L 370/254 updates (G/T), tier H 2,163/1,588. The driver repeats the bounded synthetic preflight
immediately before fitting, and again before H for the remaining schedule. Verdict precedence,
E_primary, median, cost-gap rule, tie rule, advance window, branch isolation and padding are as in
rulings 2 and are implemented in the bound calculator and driver.

## Disclosures

1. The simulator emits the label `learned_failed_to_transfer`; the prereg and calculator spell it
   `learned_and_failed_to_transfer`. No gate predicate reads the string; the driver maps it by a single
   named alias. Auditor ruling: acceptable as is; correct in the next versioned amendment together
   with the stale SCHEMA §3.1 prose.
2. Branch isolation: predictions are bit-identical under every information-bearing perturbation; a
   changed batch *shape* moves outputs by ≤3.6e-7 (1–3 ulp float32). The registered path never changes
   batch shape.
3. Non-blocking defects left unfixed to keep bound bytes stable: (a) the checkpoint `work` block and
   `initial_parameter_hashes` are shard-scoped — audit costs from `tier*/ledgers/*.jsonl` only;
   (b) the tier-H feasibility test does not subtract tier L's elapsed fitting time — honest arithmetic
   leaves 534 s of slack and `timing_ok` still catches a real overrun.
4. The tier-H branch was code-verified and covered by calculator tests but not exercised end to end on
   a fixture (the fixture cannot produce `awaiting-tier-H`).
5. Public/private separation is procedural, not cryptographic. An evaluator-held secret salt is
   recommended as a separately versioned amendment before wave 3.
6. Comparisons are "equal counted operations under the registered estimate" (≤5% per-rung spread),
   never "equal compute".

## Claim limits

A tier-L failure alone does not establish difficulty. A complete valid tier-H too-hard verdict supports
only "not learned by these baselines under either registered budget". An unresolved control failure is
calibration-invalid. Lookup-toy results are not evidence about this toy.
