# Concept toy ct20-v1.2 — freeze manifest for the second execution of baseline-only wave 1

Fable (coordinator) · 20 September 2026 · written after the independent auditor's `FREEZE-READY: YES`
(audit/V1.2-AUDIT.md) and before any learner is fitted or scored under v1.2. Authority: Fable reviewer's
rulings 3 (Astra-independent; a note to Astra is prepared for Ben to relay; the launch does not wait on it).
No cloud spending. Launch requires Ben's own explicit "go" (condition 16), recorded at the end of this file's
companion `LAUNCH-LOG-v1.2.md`, not here, so this file's bytes stay fixed.

## What happened and what changes (rulings 3 §2.4 a–e, g, i)

(a) ct20-v1.1 ran once on 20 September 2026 and ended `calibration-invalid/accounting`; tier H was not run.
That verdict is permanent. (b) Cause: a redundant `final_query_panel` evaluation pass was charged to rung 512
without a reservation, putting rung 512 over its 2e8 allowance by exactly one query panel (17,172,576 ops G,
23,224,032 ops T) — wave1/ACCOUNTING-DIAGNOSIS.md. (c) v1.2 changes: that one redundant pass removed (final
predictions = last executed rung's predictions, shown bit-identical); accounting guards added (every ledger row
unused reservation ≥ 0; driver guard runs before any evaluator code, so an invalid run writes no accuracy);
version label. Nothing else; ratified step tables unchanged (L 62/81/81/80/66 and 39/58/57/57/43; H
421/440/439/438/425 and 306/325/324/323/310). Fix 2 not applied. (d) Same worlds, seeds, data bytes, init
bytes, RNG namespaces, gate and predictions: the rerun is a bit-identical replay of the fits. (e) v1.1 outputs
are preserved read-only and unopened until the v1.2 verdict is sealed (wave1/README-QUARANTINE.md). (g) v1.1's
elapsed resources (17.9 s wall, 8.4 s preflight) are reported under wave 1. (h, owed after the verdict) the
v1.1/v1.2 tensor-equality comparison. (i) Wording: "wave 1 was executed twice; the first execution was invalid
for accounting and is reported as such."

Version layers: `ct20-v1` = RNG/contract root (`CONTRACT_VERSION`); `ct20-v1.1` = data and gate contract
(`GATE.VERSION`, calibration-v1.1, fixture-v1.1); `ct20-v1.2` = this registration (`EXPERIMENT_VERSION`, models
file only).

## Bound files (sha256; paths relative to the worktree root)

Changed under v1.2:
- scripts/fable_concepttoy20_models.py cb890374224fec827f419be28a314903834533c10f0c05a9ebb613925726b8b9
- scripts/fable_concepttoy20_wave1.py 09f7ba91f184b4d95ec99a5d480a08694e761f1c2d623e4d49cbf60e2631b546
- tests/test_fable_concepttoy20_models.py (169) 4fd1d38be12bb0a0d93059bce56db6746a145ead33c33594afc2fa2ee26aae81
- tests/test_fable_concepttoy20_wave1.py (64) d296019204793c5502364eba3a0453d1dfed2af2b43f745419856ecc5e95c9a0

Carried over unchanged:
- scripts/fable_concepttoy20_sim.py c56794c52ad0e44022df2af9c161ccf10775eb626bf0ab6052cc81207c96d7a0
- scripts/fable_concepttoy20_public.py 7139c6989f8618dcca9d4ef2e31b5c667424e3fca8a183e8f30b36a1e3b567fe
- tests/test_fable_concepttoy20_sim.py (34) db86bf0fb3a27cafd6f43a8f1336c444d7209b20cb838bb5aa92f5ed9db7d16f
- A/audit/gate_calculator.py 62ec54f10ed2acec9faa97d4abdbda2bb5a43cccb5924016d08a0a4e79738f71
- A/audit/test_gate_calculator.py (174) ce9146abdf76222ee870c74d43ed3daf88d790ff06258b5094314d75f54a82b6
  (A = artifacts/fable-concept-toy20-20260920)

Design and registration:
- design/v3/20-concept-toy-preregistration-draft.md 1bb49e074d70cc7692ce2af40b6624cf626694b8cc5bb8a0b56a816aab258251
- design/v3/20-concept-toy-simulator-spec.md aa80843c5a7a5d51ba675c8c0715ff823a30e15b4b7f15275be506dbd324e8a8
- design/v3/20-concept-toy-build-plan.md ba255726fac5985e305495bba0e6e52ec8139e28624a49c703115a1a2b9fd354
- design/v3/20-concept-toy-rulings-1.md 40f650451b6b1404e352c900fabb9a6f56fa1696aaac31e90fdc4cac2779c6de
- design/v3/20-concept-toy-rulings-2.md 1245e46f567dd1a265d6b05d8482f0267052c735159b8d05864dd6b861a110f2
- A/RULINGS-2-first-version-as-relayed.md fac03f785ca6b0e0a0fb3954ac2308b783629b75afda23863633e1ff3bca1269
- design/v3/20-concept-toy-rulings-3-fable-review.md 77556eb5c79191a0cd577a693e47cb8a9a9df56dba7726fbac3a1b8616da58fa
- A/SCHEMA.md 7e9239c077e4252dc2d44d7cc9b0e932a3c556446aadc5fea1d88a6f96562628
- A/FREEZE-MANIFEST.md (v1.1) 289b631c397d817526d2d875d2886d310f150e886fbbcbde307bc24bc98e1d12
- A/FABLE-PREDICTIONS-pilot.md (P76–P82, untouched) 420f9363c344f8ef7cd6d907c726938fadae5784d95aeb729e2f8e5990da8cc9

Data (459 files re-verified by the auditor, 0 mismatches):
- A/calibration-v1.1/manifest.json de3ccfec81c8847f879c3d886e4a7450085cb4f1bac849cc59acb19644f146d3
- A/fixture-v1.1/manifest.json 97fb94cf450e7aff704ce8601ad3e34ee1faf890cb5ee358eedff1aa3326bbcd

Amendment provenance:
- A/wave1/ACCOUNTING-DIAGNOSIS.md 1de7eb489ea0b2e8cde7d1f59798a9352dbd7678821cfd4d6ff527facc225ea7
- A/wave1/v1.1-quarantine-sha256.txt (444 files) 1ab9656d9ccc27e2769e4854466621abd5a1f2d36b34c1a922e08247f87af9ec
- A/wave1/README-QUARANTINE.md 5129ccc54d1b53072839d0c3be749709ce6decb1e2ae4d600e7d74b98d045b2f
- A/audit/PILOT-AUDIT.md a2b2fa9d5387224220aa977b91e0358e8b90af1657b1ec5d9874b02d22b718df
- A/audit/V1.2-AUDIT.md (ends `FREEZE-READY: YES`) 48581e5549eaa5747b52373555be2fbe2560f2a3f95b6de1c616d2b6c7ec386b
- A/frozen-v1.1-sources/ (9 files): models 0b5711f4…, wave1 2db9889a…, sim c56794c5…, public 7139c698…,
  gate_calculator 62ec54f1…, test models aaae8702…, test wave1 9b5d5a73…, test sim db86bf0f…, test calculator
  ce9146ab… (full digests in V1.2-AUDIT.md §9)

## Environment and launch (condition 14)

Same machine as v1.1 (Apple-silicon Mac, macOS-27.0-arm64), CPython 3.12.14, torch 2.14.0, numpy 2.5.3,
OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1, PYTHONPATH = BASE/runtime.local.json import_roots.

One launch, from the worktree root:
`python3.12 -B scripts/fable_concepttoy20_wave1.py --concurrency 6 --preflight-seconds 6`
Output goes to the driver's default fresh directory `A/wave1/registered-v1.2` (refuses to overwrite; refuses
quarantined paths). No `--resume` unless a genuine infrastructure interruption occurs inside v1.2. After the
run the coordinator checks `n_fits_reused_from_disk = 0` and `n_fits_run_now = 72` for each tier run. The
driver's preflight must pass immediately before fitting, and again before tier H. No other heavy job runs on the
Mac during the wave.

## Pre-commitment (condition 15)

The v1.2 verdict is binding whatever it is. Tier H runs if and only if v1.2's own tier-L verdict requires it
under the unchanged two-tier procedure. No amendment between this freeze and the verdict. If v1.2 ends invalid
for any reason, any further version goes to Astra. A crash on the `resource-infeasible` branch (below) is a
registered stop, not a bug to patch and rerun.

## Exposure statement (condition 4) — who has seen what of v1.1

- Coordinator (Fable, this session): the driver's printed run summary only (version, fit counts, isolation
  PASS, `accounting valid = False`, worst per-rung gap 0.027184, verdict `calibration-invalid/accounting`, the
  procedural explanation) and the accounting numbers quoted in the diagnosis. No E value, median, case count,
  startup label, gate table, predictions or checkpoint. Has not opened any file in the quarantine.
- Diagnosing/fixing builder: the v1.1 ledgers, for ops fields; ledger rows also carry `selection_loss` (a
  learner-side training quantity, not an evaluator score). The diagnosis quotes none of it.
- Reviewer (rulings 3 §0.2): the accounting fields, plus — accidentally — two short non-numeric descriptive
  fields and one truncated key name from the tier-L advance-window block of `verdict.json`. No E value, median,
  case count or startup label. Content deliberately not restated anywhere; Ben may ask after the v1.2 verdict is
  sealed. The chosen fix reproduces v1.1's numbers exactly whatever they are, so the exposure cannot have steered it.
- Auditor: nothing of v1.1 scored content (V1.2-AUDIT.md §0, incorporated here by hash); names, counts and
  digests only. Same agent as the v1.1 pilot audit, so not fresh eyes on the pre-existing design.
- Ben: only the coordinator's chat reports (the invalid-accounting verdict and its cause). No scores.

## Disclosures

v1.1 disclosures 1–6 carry over verbatim (A/FREEZE-MANIFEST.md, bound above): (1) label spelling
`learned_failed_to_transfer` vs `learned_and_failed_to_transfer`, mapped by one named alias; (2) branch
isolation bit-identical under information-bearing perturbations, ≤3.6e-7 under a changed batch shape, which the
registered path never does; (3) shard-scoped checkpoint `work` block / `initial_parameter_hashes`, and the
tier-H feasibility test not subtracting tier L's elapsed time (534 s slack measured); (4) tier-H branch
code-verified but not exercised end to end on a fixture; (5) public/private separation procedural, not
cryptographic; (6) "equal counted operations under the registered estimate", never "equal compute".
New under v1.2:
7. The v1.1 driver wrote full scientific results even when accounting was invalid; v1.2's guard ordering removes
   that (proved by tamper test).
8. Under v1.2 the published fixture stops honestly at `calibration-invalid/accounting` (rung-512 cross-arm gap
   0.0629 > 0.05, because fixture worlds publish far fewer audit keys than reserved); the auditor re-ran the
   evaluator→gate path with only that predicate neutralised and found it byte-identical (modulo version) to the
   frozen-v1.1 fixture run. Calibration gaps in the dry run: L 0.014096, H 0.000557.
9. `checkpoint_hash` changes in every ledger row because the .pt bytes embed the version string; it has no consumer.
10. Pre-existing latent `KeyError` on the `resource-infeasible` branch (frozen v1.1 line 1087): fires before any
    fitting, after a correct `verdict.json`, writes nothing else, exits 1 rather than 3. Left unfixed per
    "nothing else changes"; fail-safe.
11. Tightest rung (tier L, arm T, B=256) clears its allowance by 4,514 ops. Accounting is deterministic and
    data-independent (confirmed over all 36 world × seed combinations), so this is safe, and the reservation
    table is now immovable.
12. The quarantine directory is named `v1.1-INVALID-accounting-QUARANTINED`, not the ruling's suggested spelling.
13. Dry run (720 rows, zero updates, stubbed predictions, private data and evaluator untouched): all rows within
    allowance, unused reservation min 0.0, all 24 registered totals reproduced exactly. The live wave's own guard
    is the first proof on real fits.

## Claim limits

Unchanged from v1.1: a tier-L failure alone does not establish difficulty; a complete valid tier-H too-hard
verdict supports only "not learned by these baselines under either registered budget"; an unresolved control
failure is calibration-invalid; lookup-toy results are not evidence about this toy. v1.1's numbers are never
reported, pooled or preferred.
