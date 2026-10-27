# RUN-NOTE gr-9, addendum 1: stopped by Ben

- **What happened.** Ben asked to stop all threads at 2026-09-27T14:30:29Z, and the coordinator relayed it. The owner
  stopped the gr-9 chain during L9 training, about 2.5 hours in. The chain's PIDs were 4884 (chain.sh) and 4903
  (training).
- **What exists.** No adapter was saved, so gr9_adapter.pt does not exist. No run file and no count exist.
- **Result.** gr-9 has no result. It is not a FAIL and not a PASS.
- **If it is ever re-run.** Its sealed files stay as they are. A re-run needs a new chain file name and a new addendum.

Written 2026-09-27T14:32:19Z (date -u).
