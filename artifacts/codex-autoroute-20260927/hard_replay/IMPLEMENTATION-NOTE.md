# AR2 implementation and bounded checks

All preparation and tests follow pushed registration `542f61b8c63e505ed02b881eb2216d57001ed1c7`. Scientific training has not started at this note's creation.

The first parent preflight stopped on a test-only shape assertion. It incorrectly expected a grid of logical size s to occupy an s-by-s input tensor. The unchanged sealed `claude_rsn358g_run.py` encoder appends a blank separator and a symbol legend, so the actual tensor is (s+2)-by-s. The preflight assertion was corrected to match that existing format; the sampler, model, generator, marks and planned experiment did not change. Failure occurred inside sampler checks before AutoNet construction, with zero optimizer updates. The failed log is retained as `preflight.log`; the corrected run uses `preflight-2.log`.

The baseline and candidate both use the full-replay schedule. The sole candidate change consumes the normal grid-size RNG draw, then replaces that size with 5 for old-grid replay in B/C. Rejected examples keep that chosen size. Every phase records eight kind/size counters, including zeros; interruption checkpoints preserve them.

The independent grader requires a successful full checkpoint recount as part of M4. Eleven synthetic grader tests and six synthetic raw-recount tests passed before MPS preflight; their logs and validation notes record UTC time, machine and PIDs. Those software tests are not capability results.

The corrected preflight passed on MPS at 2026-09-27 14:56:20–14:56:23 UTC, PID 67716, MacBook-Pro. It verified both exact schedules; the normal RNG draw before the override; unchanged A/non-grid batches; a forced held-out-fingerprint rejection without resampling size; metadata/order/repetition/save-reload invariance; parameter count; and gradients to context and both dense blocks. It made zero optimizer updates. Its recorded source hashes were checked against disk after all Python authors finished and matched exactly.
