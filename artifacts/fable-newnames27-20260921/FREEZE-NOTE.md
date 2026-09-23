# Experiment 27 / M1-F new names (name scale fixed at 1.2) — pre-registration freeze note

Fable (coordinator) · written 2026-09-21T01:59:46Z, after AUDIT-27 (NO: 1 major) → builder fixes → AUDIT-27-delta (FREEZE-READY: YES) and run_data.sh (DATA_DONE, 79 s), BEFORE any registered update is trained. No cloud spending.

Source fingerprint for every run: 6bb75f53575a0b776072fce5a28083d4408bf430d2892f490ca0d190b0e8878e (enforced by run_integrity).

sha256 of every bound file:

```
63d2bb51c412336fd54bdcc5d012a7da9ac01ae4d01ff2b52497a95052c5d990  design/v3/27-new-names-followup-design-fable-review.md
69d54c04fdb54172ea737a4ecf0c316d7e3b5056dac4c20e3494b075f14f1530  scripts/fable_newnames27.py
f300b38f4a5328cadc1b95350f7e7b68316389b52ca61c58fdc37e60f2f9ecfb  tests/test_fable_newnames27.py
14336a4971e2976a60e8af31b29b2393e13aba6ee6bf0b190b759a9d85dac500  scripts/fable_newnames21.py
c1d26dd2ce415d2c1490282b54739d6984a017556159c68f3a235982ee7414c6  scripts/fable_confirmation_panels.py
62b13de0950f94c62713312e41003900972680d4b4270c2a24801541d1917798  artifacts/fable-newnames27-20260921/run_data.sh
2729e4af9e374a00b9b3653c9089f7ca092bc4fa51a7142105fa1912040cf39f  artifacts/fable-newnames27-20260921/run_train.sh
21e47fae8cc75a0d1b8e72dba0e3dcddd79ef7900e958ea6e95da06547ba371a  artifacts/fable-newnames27-20260921/run_score.sh
da91661cc1ac740661089a4e4db8af0814f2b6f34a6fc4880702b7321ec065f4  artifacts/fable-newnames27-20260921/BUILD-NOTES.md
5c68e8064629cdb077ae839ba2cf6c3aab96aac5691ad9ba536e9d56c38ad035  artifacts/fable-newnames27-20260921/FABLE-PREDICTIONS.md
abfe12bf2c35d5080085d3d48b158933fa60c6d84b5c8c988c5b75345f800c99  artifacts/fable-newnames27-20260921/AUDIT-27.md
5326f91368e78710651746a40129480c1d9dece78ebe72a3a3e70630cade2cb1  artifacts/fable-newnames27-20260921/AUDIT-27-delta.md
f05637f92aebf40b6be6d6c24d3a864ea0b5d7aef2aa8e4a3919fd75c501665b  artifacts/fable-newnames27-20260921/control-equivalence.json
38077832015a09bac1e752c8133da30f31ce2505b1f5e942de35507e53255686  artifacts/fable-newnames27-20260921/treatment-equivalence.json
9523fca2c3f0aee7c06615c16142d42d42582cc9d4b297b7855b8eccb2d94a47  artifacts/fable-newnames27-20260921/inertness.json
222143ecb39369ec970d4aeb19a061920843e095f96d75ec078c1188e8474365  artifacts/fable-newnames27-20260921/pool/pool-ref.json
d107c3bec5ce00816fb6769a672986976760418dcf6f5b84bce10af34257758d  artifacts/fable-newnames27-20260921/panels/audit.json
79ad9e9d0083e4ae77f04e52822516af862466c8494a5b2355e9bc3134d8683e  artifacts/fable-newnames27-20260921/panels/c1.pt
9be64bf5969f735d898af16525f8cf7dd1f074d359d16a439ba18388e4178a26  artifacts/fable-newnames27-20260921/panels/c2.pt
8d0f9448781572eed168befe4552b6a661d6ec6d7ff20458b7e87d25ade95796  artifacts/fable-newnames27-20260921/panels/c3.pt
eabe1d03fd0a6a0cc1b595dcc02857cd82bfb57a794c6fe0d6cb6b772963872e  artifacts/fable-newnames27-20260921/panels/c4.pt
63332857ed054e0670d92e1a96fd75908c2b76fc4738a0be4d31f3e934d4f9a9  artifacts/fable-newnames27-20260921/panels/c5.pt
4df66f9433cb879d3eddd7d44288610cf915ad0550a1abaf9e3de2f41b49e0ab  artifacts/fable-newnames27-20260921/panels/c6.pt
024464f1d2b2e4b075a8d1a4f59413c9cea638819b843afc479edecf584537fb  artifacts/fable-newnames27-20260921/panels/forbidden-semantics.json
263a9f47c2c0f9911b47c5eea1cf2024afa0e2e39f1221eee2173e94c098fc76  artifacts/fable-newnames27-20260921/panels/manifest.json
5b907e651db6dc7fa4995f90c6b08ecf4b532d1edea3bb519e94dabde247be81  artifacts/fable-newnames27-20260921/panels/newnames27-panels.json
27aaf2c014e5adb60e3984fafc8c8b39d5559467356ab3270932d0cfaaf9f7e6  artifacts/fable-newnames27-20260921/panels/p12-1.pt
2ebb66db82fb78d2889bbc9b31ccc6b6528df4a8a2283412f070993b206915c8  artifacts/fable-newnames27-20260921/panels/p12-2.pt
0133161c7d5dfcb6274e09f2e8699cf98a8118fc07fa5255857c9c2ddc7467d4  artifacts/fable-newnames27-20260921/panels/p12-3.pt
c1fc115deba61cd843977fbb8dca980b11d3cabcb1147492d8955a32583f5587  artifacts/fable-newnames27-20260921/panels/s3.pt
```

## Registered procedure

`bash run_train.sh 1` (GATED: control × {2103,2104,2105} + arm F × the same seeds, six single-thread runs, 6,000 updates), then `bash run_score.sh`. Then `bash run_train.sh 2` (DESCRIPTIVE: arm L × the same seeds) and `bash run_score.sh` again; per AUDIT-27-delta MINOR-9 the wave-1 `gates.json` and `report.txt` are first copied to `wave1-verdict/` (hashed) and moved aside so the stale-verdict guard lets the rescore finish. The wave-1 verdict is the registered verdict; wave 2 cannot change it.

Marks: design 27 (sha 63d2bb51…) — the ten cutoffs (487/461 of 512), per seed, never averaged; 3/3 rule; VOID rule for the control; paired reserved-minus-train mark ≥ −13 with the two-sided warning; INVALID if the arm-F scale moves or run_integrity reports a problem. Signatures: scale_collapsed (L only), name_blind (bias_exit / gain_exit), never_started, copy_side_failure (trigger for the pointer head M1c), reserved_gap, unnamed. A wave killed by the time cap may be re-run once, unchanged, only if no score file has been opened. No amendment after launch.

## Predictions (hashed before any code was written)

Reviewer R27-P1..P14: design 27. Coordinator P118–P125: FABLE-PREDICTIONS.md (sha 5c68e806…). Both in the ledger, pending.

## Disclosures

1. Claim wording (audit C5): arm F does not "only change one number". It removes the scale from the parameter set, so gradient clipping runs over 66 tensors, not 67, and every other update differs from a pinned-parameter version. Any pass sentence must say the name loudness was hand-fixed at 1.2 and not learned.
2. Deviation from design 4.3 (MINOR-1): the arm-L equivalence proof ran on fixture seed 9, not seed 2100 (a fresh panel suite changes the exclusion set, so experiment 21's seed-2100 fingerprint cannot be reproduced). Recorded in BUILD-NOTES.
3. Left unfixed, disclosed: MINOR-5, -6, -7 (partial training-stream replay, 100 of 6,000 updates, by design; the run-time forbidden check covers every update), MINOR-9 (above).
4. Coordinator exposure before predicting: the diagnosis probes in design 27 (fixture seeds only: frozen-scale fixture reached LINK 0.5–0.7 by update 1,500). Stated in FABLE-PREDICTIONS.md.
5. Machine state at launch: macOS fileproviderd at about one core (iCloud Desktop sync); no other training job. Training is single-thread deterministic: contention can slow a run, not change its numbers.
6. Q1 limitation carries over from experiment 21: seeds differ in starting weights, blind-curriculum stream and name stream, not in training worlds.

## Claim limits

A pass shows in-context binding of never-trained random name codes on these ten 16-candidate cells, with the name loudness hand-fixed — not open-vocabulary naming, not that a model can find the loudness itself (that is arm L, descriptive), not that the dispatcher works with new identities. A fail does not show new-name binding is impossible; copy_side_failure pre-names the pointer-head follow-up.
