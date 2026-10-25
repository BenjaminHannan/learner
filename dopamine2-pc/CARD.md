# Dopamine-2, arms none + value, LR 1e-4 (PC)
Requested by the coordinator at 00:32Z. Code: claude/project-thread-7gkl2b @ 92471e270 (updated 01:04Z to a1ab4ee99, then 01:40Z to 92471e270), in ~/dopa2/src-92471e270 (rlaif/ only). Keyless.
Command: `DTYPE=bf16 LR=1e-4 bash rlaif/run_dopamine1_lane.sh runs/dopa2 none value` (~/rlaifvenv). Queue: ~/dopa2/dopa2q3.sh, gated on "=== WK2 ALL FINISHED" plus an empty GPU-BUSY. Log: ~/dopa2/dopa2.log. GPU-BUSY tag: dopamine2-pc. Estimate: 1.5-2 h.
When done: push eval_*.json/jsonl and log.jsonl (no adapters) to claude/dopamine2-pc-results, then send the branch, commit and held-out success per arm.
The ab_ob Week-2 control (sbwk2c2.sh) now waits for "=== DOPA2 ALL FINISHED" too.

## Result
Finished rc=0: started 02:12:11Z, ended 03:50:15Z (about 98 min for both arms). Held-out n=100, keyless (usd 0).
- d_none: success_rate 0.14, mean_check_frac 0.272
- d_value: success_rate 0.07, mean_check_frac 0.265
(For comparison, Dopamine-1: d_self 0.27, d_batch 0.26.)
Note: the ab_ob Week-2 control mentioned above was cancelled at 02:08:30Z, so nothing was queued behind this run. The GPU was idle afterwards.
