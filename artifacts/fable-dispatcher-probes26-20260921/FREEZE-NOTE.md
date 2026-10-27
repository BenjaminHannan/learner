# Experiment 26 (dispatcher fault-localisation probes) — freeze note
Fable (coordinator) · 2026-09-21T01:27:25Z · no training; read-only probes of saved checkpoints.

Bound files (sha256):
- spec design/v3/26-dispatcher-stop-probes-registration-fable-review.md  7d7708e79e7b755bfa47d50bd7aeb8b550d02b20930a313ad1547a7337a09f45
- scripts/fable_dispatcher_probes26.py  f78ca888c7d0c1381cd5c0dbd1e1363b6c2b6699a5f1db728fecc621253af228
- tests/test_fable_dispatcher_probes26.py  22c11a14b7c2d17486705f738093e2e622fa1618af9a6188068dfc55f773de21
- BUILD-NOTES.md  981c8d0f542f11129e0e1d07e660c3b2b427cb44fc07e3afe1fdf2a21a641f60
- AUDIT-26.md  0929d0ebc3119e9f46a8dbdba749589ddb79c4c8550f546d36a991d600606414  (FREEZE-READY: NO, revision 1)
- AUDIT-26-delta.md  b9c9b331e1b5af87dddd377c2b5bb24a580949b37dea1546e8b8d10fb73bdc7a  (FREEZE-READY: YES, revision 2)
- FABLE-PREDICTIONS.md  72c6130d29e8af9e73c3752cc6aec9acc0655465060bb33243895ba07989664b
- ledger at freeze  425315c68649ecc6410e417830aaa4adeffb3f43fd4f8d55c279087c65713f72  (P102–P117 pending)

Procedure: BUILD-NOTES §4 (a) then (b), one pass, this directory, no script edit between. If the positive
control fails, row D0 applies: stop, no registered read-out.
Reading rule imposed by the delta audit: if a registered checkpoint's k8-held reached_step_2 < 48, R6/R6′
failing is attrition, so D4/D4′/D5 are reported not-evaluable for that seed rather than D5 firing.
Disclosures: (1) the auditor's scratch control run already indicates P109 likely TRUE and P110 likely FALSE;
both forecasts predate all code, and only the registered-directory numbers are quoted. (2) An unrelated
audit (experiment 27, fixture seeds, ≤ 3 processes) may run on the Mac at the same time; probes are
deterministic single-thread, so load cannot change numbers. (3) 19-U not probed: weight-identical to 19b-U5.
Claim limits: spec §7. Descriptive fault localisation of nine conditional checkpoints (continuations of
three seeds), one world family; licenses at most one later training experiment via the §6 table.
