# Scratchpad implementation checks

SHOWN: the selected learned scratchpad-only code is implemented in new scripts codex_numbers_20260927_cards.py and codex_numbers_20260927_run.py. It adds 12,930 parameters (0.7853%). No bookmark restore is implemented. A shared trace state machine ensures training, own-stop scoring, and the hidden-kind poison test all execute the actual card path.

SHOWN on CPU: the independent cardcheck report verifies identical paired core initialization; exact 48-round raw logits and halts between the per-read-wiped candidate and its identical inherited core on sums/grids/numbers; episode reset; batch independence; delayed answer/halting gradients into all eight card parameter tensors; expected missing/zero card gradients with one round and no preceding card; poison traversal; and checkpoint reload. Saved report: diagnostics/cardcheck-cpu.json. These checks establish wiring, not improved puzzle performance.

SHOWN on CPU: runner regression tests compare new baseline run_train outputs with inherited loop_train and new trace argmax/halts with inherited loop_rounds. They match exactly. The new baseline path preserves the original algorithm.

SHOWN on CPU: four-step width256/batch2 integration runs for both variants confirm identical common configuration, exact shared-core initialization and training-stream hashes, correct weight counts, checkpoint/config/summary serialization, and card gradient count schema. Saved report: diagnostics/integration-s9276213/report.json. This is a software smoke test, not an experimental accuracy result.

SHOWN: independent synthetic recount checks exercise mark boundaries, reconstruct the inherited stop from per-round predictions, call the existing checker, and reject tampered stop/validity claims. Candidate-card zero gradients are retained as possible negative learning evidence; nonfinite gradients invalidate a run. Card-source hashes are recorded in both variants because both import the same module.

Disclosure: an early CPU-only wiring check used the familiar hand [1,2,3,4], which a subsequent partition audit identified as belonging to the previously exposed old300-hand panel. That check used untrained weights, made no optimizer updates and assessed no puzzle accuracy. The final check uses [4,5,7,11], confirmed in the diagnostic training partition. The registered training source, final card benchmark, and four-step integration optimizer smokes use only the practice source. Older throughput probes used a hand-coded example and are not experimental accuracy evidence. This adds no fresh five-number exposure.

PENDING: run the same card checker on MPS after the active diagnostic finishes, and run the bounded practice-only d256/batch128 benchmark. No second GPU job has been started. The benchmark records post-step allocation samples, not a true memory peak. This torch installation lacks a peak MPS allocation API.

PENDING: final 60,000-step diagnostic receipt, immutable pushed PASSMARKS and source seal, four paired training seeds, frozen-checkpoint evaluation with intact/wiped cards, and independent final recount. No claim that cards solve new puzzles is made by these implementation checks.
