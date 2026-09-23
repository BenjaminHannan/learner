# Experiment 21 / M1 new-names — pre-registration freeze note

Fable (coordinator) · written 2026-09-21T00:02:56Z, after AUDIT-21.md (FREEZE-READY: YES) and run_data.sh (DATA_DONE), BEFORE run_train.sh. No cloud spending.

All 15 data files match AUDIT-21 §5.1's independently built hashes. sha256 of every bound file:

```
11dc2f73c01cec378b4dd6785059a059a807a44eb019dd49a7182da67f9f59d0  design/v3/21-teachable-assistant-roadmap-fable-review.md
7142b9c34419014098221203b46f4b10a609b608f24b4e61b98acbd9e94fd153  design/v3/21b-new-names-rulings-fable-review.md
14336a4971e2976a60e8af31b29b2393e13aba6ee6bf0b190b759a9d85dac500  scripts/fable_newnames21.py
f62ada7108d6a0aa7934b6ea8bfa4ba70033877e7d436345367c603bc09eb68d  tests/test_fable_newnames21.py
c1d26dd2ce415d2c1490282b54739d6984a017556159c68f3a235982ee7414c6  scripts/fable_confirmation_panels.py
8fa4674d1b1dbcad5ae4fe51f4bfe74fe3fb6be3361569b825a4183be3aa8d53  scripts/fable_dispatcher_v3.py
2081a94cae4f3d152230e86d58772d4c5aeabdb03dac46be5efff85fefa91545  scripts/fable_dispatcher.py
7b837fdd20660cb690de6b3e5cf29c465eb060f1134aa6c069b823e8f19f9819  artifacts/fable-newnames21-20260920/run_data.sh
2351d4e6122b5a0477b209e197ff5032fc0ff58b705387782f82cfb471b98ff6  artifacts/fable-newnames21-20260920/run_train.sh
95087be9441bd2068c7582b1de8fc4f71c753a8ea4527141ba0f5470e569552f  artifacts/fable-newnames21-20260920/run_score.sh
d28db9b945d87758c1589d93b89a89001fdd959f6ff37dbea9c11112170222db  artifacts/fable-newnames21-20260920/BUILD-NOTES.md
7cbf39a70493df819c9d1ba50a914fed09408a10e21f9b2839442ba59dae7526  artifacts/fable-newnames21-20260920/FABLE-PREDICTIONS.md
3d440751b94e4c7ee6cab7c93faafade079e76a90edf12ea683fdd87bce19da7  artifacts/fable-newnames21-20260920/AUDIT-21.md
9a4b25d1f8894c714d7aefb1237349a7a38838423640bf1381191602cebdc431  artifacts/fable-newnames21-20260920/pool/pool.json
4e5b5d862b5832e5e410a6bc11409030a77db27be19f1d8dacf6698f4f135c1d  artifacts/fable-newnames21-20260920/pool/pool.pt
57d5893ba8520681687c80c91e474e0750a01f444101f94ae8870a17eaebd6ec  artifacts/fable-newnames21-20260920/panels/audit.json
788e0a7f066ecbd597aafdc42f4b38765b0d274d6a053b87fc5c89b2db97477f  artifacts/fable-newnames21-20260920/panels/forbidden-semantics.json
e9beaf1e4c189c55ad636c3e66aaab381327e4ff617c75f4a4f1ed888d03a461  artifacts/fable-newnames21-20260920/panels/manifest.json
08767ac2d8ee3e12bc47c971232269ddb73347d06946f61cc932a346eafe2fbd  artifacts/fable-newnames21-20260920/panels/newnames21-panels.json
d6247f1d728bdd7f3ad8ecbf3ca182b16cc6a832799824ae76fc94bd25ae7e2f  artifacts/fable-newnames21-20260920/panels/wide64.json
3b836ab6f37864dd6ce3cc508f8c79d12187ae3cefb8efc730dd61f8736f078b  artifacts/fable-newnames21-20260920/panels/c1.pt
a08d86d2afe67658cc5cd3595ce9c438a3032006ac7fa99d2d28fd5b322a2da0  artifacts/fable-newnames21-20260920/panels/c2.pt
e7600c00bc324961cd75412dc2b8d2455d6b9ed9de67bf9c856ab413987eb4f2  artifacts/fable-newnames21-20260920/panels/c3.pt
58f714ae9c722ea2f9f491abae0e062936607e63a96f3cab63e815596a4e7fae  artifacts/fable-newnames21-20260920/panels/c4.pt
ac9edc6ee9c78f957c47d1baf021c46a61b304508f9d9b49fc27454d97f68022  artifacts/fable-newnames21-20260920/panels/c5.pt
aaf61990b2bf030983f0a93b924daf1ba754a7318a4328fc4da0e983cbdd05a9  artifacts/fable-newnames21-20260920/panels/c6.pt
935d8837aaed8608c75da4203ea0b3768b715596da13e5a681001fa0fe8f1e74  artifacts/fable-newnames21-20260920/panels/p12-1.pt
3532d8904aff6fbf52fb06904365e3d298da098821c5da974f584c578c5eee2e  artifacts/fable-newnames21-20260920/panels/p12-2.pt
5cc3ad8a721806e68da2de37cb206c988f263f262bba42a2c2f305356772e4cb  artifacts/fable-newnames21-20260920/panels/p12-3.pt
8189be3e53fc2e6920b3cc62ef4686cdc1ff3e8e0680971b0a444d463ffe68c4  artifacts/fable-newnames21-20260920/panels/s3.pt
34fde7a975c551841be2940aeb49ab74a3b84a12063b126b9656775460a9e976  artifacts/fable-newnames21-20260920/panels/wide64-attr.pt
300b159379acce2665dbcdfe3ad9d2c2199d7f8b7c62b85403fd12447517d52f  artifacts/fable-newnames21-20260920/panels/wide64-link.pt
5408951e2220c3d4a66b41446e01db80fd14730db51d299980b4c72c019d1395  artifacts/fable-newnames21-20260920/panels/wide64-two.pt
3982c24e67d6bfa5667f88cbe75db2eee08bc0ee92c9af701a0a8e5969f0edf5  artifacts/fable-newnames21-20260920/control-equivalence.json
```

## Registered procedure

`bash run_train.sh` (six runs concurrently: arms treatment/control × the three registered seeds, one thread each,
6,000 updates, final checkpoint only; watchdog caps 1,680 / 1,740 s, not raised), then — only after TRAIN_DONE and
all six `completion.json` files exist — `bash run_score.sh`. Marks are the ten cutoffs (487/461 of 512) of
roadmap §5 as confirmed by rulings 21b, per seed, never averaged; VOID rule for the control; one-sided paired
mark with the two-sided warning line added by hand in the report (MINOR: not in code). A wave killed by the time
cap may be re-run once, unchanged, same seeds, only if no score file has been opened. The registration is not
amended after launch, whatever any outside review says (GPT-6 Pro's answer, design/v3/25-…, sha 39a61292…,
arrived before launch, recommends a row-copy output instead and forecasts 0.45 for this design passing 3/3; by
ruling 21b that is a separately registered follow-up with pre-named triggers, not a change to M1).

## Predictions (hashed before any training)

Reviewer P1–P14: in design/v3/21b (sha 7142b9c3…). Coordinator P94–P101: FABLE-PREDICTIONS.md (sha 7cbf39a7…).
Outside forecast recorded for later scoring only: GPT-6 Pro 0.45 (treatment 3/3).

## Disclosures

1. Auditor MINOR findings left unfixed to keep audited bytes stable: the registered pool's max |cos| is 0.6764
   (BUILD-NOTES and ruling quote 0.699; harmless direction); `TERMINATE_SECONDS = 1770` is defined but unused;
   `run_score.sh` would score completed runs before failing on an incomplete one (coordinator will not score until
   all six completion files exist); the two-sided warning line and about half of condition 11's reporting items
   are not in `report.txt` and will be added by hand from `scores/*.json`, `runs/*/training.json`, `gates.json`;
   no training-loss trace is recorded (a failed seed leaves only twelve `code_scale` samples and end-of-run
   panels) — accepted as a known cost.
2. Coordinator exposure before predicting: one builder observation on FIXTURE seed 9 (code_scale fell
   0.1386 → 0.0128 by update 500). Stated in FABLE-PREDICTIONS.md.
3. `run_data.sh` includes a 50-update control-equivalence proof (a registered artefact); it ran after the audit
   and before this note: identical fingerprints and losses, registered anchor reproduced. The audit's dev-source
   sweep came back clear; the training-stream replay covers 100 of 6,000 updates (PARTIAL, as designed).
4. Machine state at launch (8 performance cores): the talker data builder was running short single-core
   tokenizer trials (about one core, intermittent) and macOS `fileproviderd` was using about one core; no other
   training job. Condition 8 ("no other heavy job") is therefore met only in the sense that six cores were free
   for the six runs. Training is single-thread deterministic, so
   contention can slow a run (caps are 2.5× the measured 11 min) but cannot change its numbers.
5. Q1 limitation (verbatim in the report): "The three seeds differ in the model's starting weights, the
   blind-curriculum stream and (treatment only) the name stream. They do not differ in the training worlds. The
   result is therefore conditional on one world stream; it says nothing about other world streams."

## Claim limits

A pass shows in-context binding of never-trained random name codes on these ten 16-candidate cells for this
operator, world stream and seeds — not open-vocabulary naming, not 4,096 simultaneous names, not that the
dispatcher works with the new identities. A fail shows this tied-code design did not learn it in 6,000 updates;
it does not show new-name binding is impossible (the row-copy follow-up is pre-named).
