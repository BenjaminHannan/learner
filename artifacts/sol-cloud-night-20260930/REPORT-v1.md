# Additive cloud fixture night implementation

Recorded 2026-09-30T07:50:41Z. Requested worker model: gpt-6.1-sol, xhigh. Actual model/effort introspection is unavailable. Local execution is Linux x86_64, Python 3.12.14, without torch.

The new driver consumes the independently pinned TRAIN packet and a captured SQLite fixture batch. It requires the watcher JOB and exact TREE before loading a model. The fixture batch must be in its durable running claim and retain the captured activity revision. Original human question, context, answer, accepted answers and source hashes must match the released TRAIN rows.

The authorized operation remains exactly 25 optimizer calls, with two physical rows per call: one captured fixture row and one replay row. Only the ordered core enters the optimizer; halt, input translator, output prefix and language model are frozen. Fixed four rounds are engineering runtime, not qualified learned stopping. Targets are literal official human answer spans plus EOS, often short phrases. Context evidence is retained as provenance, not used as the new target. This does not qualify grammatical conversation, semantics or generalization.

Each update records actual nonzero core gradient norms and a changed-core fingerprint chain. Per-parameter gradient participation counts bind to the saved Adam step. Sparse or unused parameters are reported honestly: absent Adam state requires the tensor to remain unchanged. The saved source, candidate, resume, populated moments, frozen prefix, halt and position/role buffers are checked without another model score. Before/repeat/after guards use only open HUMAN TRAIN rows; their tokens, labels and masks are reconstructed from the packet and local tokenizer. Recounted repeat noise sets the unchanged engineering tolerance.

The driver writes durable candidate-parent, rebound frozen prefix, resume/optimizer, raw rows and guard records. Atomic saves account for both retained output and the temporary file, under a maximum 256 MiB aggregate output cap and 1 GiB free-space reserve. Files are fsynced; POSIX directories are also fsynced. Power-loss behavior has not been tested. Interrupted raw rows beyond the last durable watermark are retained as noncommitted evidence, and existing output directories cannot silently restart.

Every complete cycle validates the saved candidate and records explicit rollback: reject the inactive candidate and retain the previous reference bundle. It never temporarily activates a model. Existing pointer databases are read without constructor writes, including database/WAL byte hashes and logical revision/history. An absent pointer remains absent. The previous reference bundle hash must remain unchanged before and after the durable rejection receipt. No predecessor pointer entry is required.

Shown locally: 16 of 16 stdlib contract checks pass, including queue rejection before torch import, unsafe source paths, fixture field changes, saved mask/input/target tampering, loss/answer guard failures, long-question token parity, absent/existing pointer preservation and mocked explicit rejection. Source compilation passes. Actual optimizer execution, saved tensor/Adam validation and rollback completion remain pending the integrator's new watcher job. No model inference, optimizer updates, queues, git operations, pushes, rentals or activations were launched by this worker.

Files:

- `scripts/sol_cloud_night_v1.py`: watcher-gated driver and actual-update instrumentation.
- `scripts/sol_cloud_candidate_v1.py`: saved-evidence validator and explicit rejection.
- `artifacts/sol-cloud-night-20260930/test_cloud_night.py`: negative stdlib contract checks.
- `artifacts/sol-cloud-night-20260930/TEST-RECEIPT-v1.json`: source hashes and exact local test scope.
- `artifacts/sol-cloud-night-20260930/STDLIB-TEST-RAW-v1.txt`: saved test output.
- `artifacts/sol-cloud-night-20260930/RECOVERY-FAILURE-v1.json`: preserved filename-listing policy breach; no protected contents read or used.

Independent source review is pending; integrator owns final source sealing, packaging, publication and queue execution. No static25 or V12 experiment was restarted. The existing unrelated vision page and old evidence remain untouched.
