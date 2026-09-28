# Practice launch (2026-09-28)

Started 2026-09-28T19:07:03Z (date -u). Recipe: PASSMARKS-C.md (12,000 batches of 64, guard SOURCE_SEED+300).
- seed 0: pid 18065, 2 threads, log artifacts/claude-relnet-eq-20260928/practice-s0.log, out runs/relnet-s0
- seed 1: pid 18066, 1 thread, log practice-s1.log, out runs/relnet-s1
- hand-over helper: pid 18079 (scripts/claude_relnet_eq_rebalance.py, log rebalance.log). When seed 0 exits it waits for
  seed 1's next checkpoint, stops seed 1 by its exact PID and resumes it on 3 threads (new PID in rebalance.log).
- Expected finish (suggested): seed 0 about +6 h, seed 1 about +8 h (TIMING-ESTIMATE.md).
- Weights (source.pt) stay local and untracked; hashes go in source.json.
