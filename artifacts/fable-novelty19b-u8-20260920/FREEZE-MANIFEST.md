# Experiment 19b (D-only, U5 vs U8) — freeze manifest

Fable (coordinator) · 20 September 2026 · written after the independent auditor's operative
`FREEZE-READY: YES` and before any 19b training or scoring. Experiment 19 remains a registered FAIL; this is
a new development experiment conditional on experiment 19's three D awake checkpoints (not three new seed
replications). No cloud spending.

## Bound documents and code (sha256)

| File | sha256 |
|---|---|
| design/v3/19-development-readout-and-next-step.md (Astra; governing design and marks) | 6d95f596d0a40911336d106f35d1d2e7387b82b225f07f93b654633e03714abf |
| FABLE-PREDICTIONS.md (P83–P93, hashed before any build output) | 2298881d27ed1fe4455a986066256995afbbf65f1e540f4806828127f0552659 |
| AUDIT-19b.md (ends `FREEZE-READY: YES`) | d0261f9607ed0e458af50fc90c55daf53a8c26c9f5099206306e96c1a410d0fb |
| scripts/fable_novelty19b_data.py | 1467112295e4df51351152d438e137076fd83e8fbdf21deb9ff01af723947a88 |
| scripts/fable_novelty19b_train.py | 2c4602a4e39fd74a11c299ec6aa09dc3d6388b52999cbf324b4c6955c37e14dd |
| tests/test_fable_novelty19b_data.py (35) | 955cc2d92e5439350af2150eb3ee0e81980d4f921212c3aa12cfdff924bec3f2 |
| tests/test_fable_novelty19b_train.py (23) | 654e0641ac4789120a423d88527c8c3c39c3e4f24eeee2e3a806a539e332ecf9 |
| scripts/fable_novelty19_data.py (frozen exp 19) | ef1df0e149aa4741a22f7185fadb9eaeb054b072d50c09a1ad2a196a998ae9de |
| scripts/fable_novelty19_train.py (frozen exp 19) | 77644a1f15e6e683b2260261b04411a6ee30c8bb74f80121a8ef7318749cd5a8 |
| run_data.sh | f7d4d1bc72e80583887ebcf5206295164f0255bfe9524201362db01a2656a3b3 |
| run_offline.sh | 97a351b189f0d93f0dabd4455bb9ccaaca00d3cb86be8575ae8a274fd7b46ac3 |
| run_score.sh | d5a2612ebacb16537c5998898342d86b900b494173a2a0545505e9882252514b |
| experiment 19 FREEZE-MANIFEST.md (source of the awake checkpoints) | 95f06d6829b9c3ee4a9374714c131f94c1d50b190be02fd6b00170fc5e81cc7f |

## Bound data (sha256)

| File | 1900 | 1901 | 1902 |
|---|---|---|---|
| buffers-<seed>/manifest.json | 182d7831…daeadb27 | 30b9e37e…fa288a61b | bbb2cf93…3225360e |
| buffer-U5.pt | 4a909b69…c19ec4f3 | d8dd1069…e72bfb57 | 16e4ceaa…fb84de48 |
| buffer-U8.pt | 658c208f…f82c0e9f | 30ee4ce5…76fd391f | ac1b4333…f062c8fd |
| offline-order.json | 2f89f11a…1bb59c57 | c5716464…e98a6e51c20 | d098f62b…e091bdea |

dev-panels/manifest.json: 5aebf97f782a034e58dcebc35e8ba50c42b48baee12603c2532557fec473472d (38 cells × 64 units).
Stream mapping sha 685264df… . Full shas are in the per-folder manifests and the audit.

## Registered procedure

`bash run_offline.sh` (six runs concurrently: seeds 1900/1901/1902 × arms U5/U8; 2,000 updates each from the
byte-identical final D awake checkpoint; optimizer reset; experiment-19 schedules; 16 worlds × 4 questions,
K=16, call cost 0.01; training cap 8, evaluation cap 16; final checkpoint only) then `bash run_score.sh`
(awake anchor + U5 + U8 per seed on the 38 cells, then gates and report). Marks are Astra's five conditions,
per seed, no averaging. Confirmation panels stay locked unless `DEV-PASSED.json` is written by a true full pass.

## Disclosures

1. PROCESS DEVIATION. The trainer builder ran `run_data.sh` before this freeze (22:48–22:49Z). No model,
   checkpoint, run or score existed. The auditor rebuilt all buffers and all 38 panels from the bound script
   bytes into scratch: every `.pt`, exclusion file, `offline-order.json` and cell JSON is byte-identical
   (only wall-clock sidecars and absolute paths differ). `run_data.sh`'s mtime post-dates the artifacts it
   built; the content rebuild neutralises this.
2. Builder judgement calls recorded here as part of the registration: the H-cell "no loss ≥ 7" guard is applied
   to BOTH answers and strict (stricter than Astra's text; cannot manufacture a pass); a missing endpoint
   reads "undetermined", which never passes or unlocks; condition 2 uses per-unit flags added to the score
   JSON; "U5 also competent" and "only practised endings succeed" are printed as readings, never as gates.
3. Auditor MINOR findings left unfixed to keep audited bytes stable: `gates` can exit 0 with missing
   endpoints (the rule still cannot pass — the coordinator will check completeness by hand); NaN counts crash
   `report` (fail-safe); per-unit flags and cell totals are not cross-checked by the code — the coordinator
   will cross-check them after scoring and report any disagreement as invalidating condition 2; launchers
   are mode 644, so invocation is `bash run_*.sh`; one hard-coded audit line (`dev_panel_hashes`) is backed
   by a real check that aborts first (proved by tampering).
4. U5 is item-identical, not byte-identical, to experiment 19's U buffer.
5. Six-person training worlds can cycle and c=7/8 necessarily revisit people; evaluation at c=6..8 uses
   sixteen-person worlds with all visited people distinct.

## Claim limits

A pass would establish trained-length execution and held-out-ending transfer through eight calls on
development panels — NOT length extrapolation (c=6..8 are practised) and not seed generalisation. A fail
means this mixture did not solve the problem in 2,000 updates; it does not show more time or a new mechanism
is necessary.
