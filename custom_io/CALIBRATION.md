# Calibration runs (exploratory, no verdict)

Written 2026-10-05 03:20 UTC (11:20 PM ET Oct 4), before the runs. Job `queue/01-calib.sh`, one seed each.
Purpose: set the update budget and see how hard the skills benchmark is for plain char-level transformers trained from
scratch, before any design is tested. These rows are NOT reused as baselines for any verdict; every comparison with
marks uses fresh paired seeds.

- `tf3m`: plain causal char transformer, d256 x 4 layers (3.2M params).
- `tf10m`: d384 x 6 layers (about 10.7M).
- `tf2x4`: d256 x 2 layers looped 4 times (1.6M params, compute like 8 layers).
All: 8,000 updates, batch 256, AdamW, bf16, shuffled order, full eval on the 6 dev splits.

## Result of 01-calib (03:38 UTC, 11:38 PM ET; one seed, exploratory)
| run | params | in_dist | answer | frame | vocab | variant | family | multi-step in_dist | min |
|---|---|---|---|---|---|---|---|---|---|
| tf3m | 3.2M | 65.7 | 38.2 | 62.2 | 53.1 | 16.3 | 0.6 | 47.3 | 7.6 |
| tf10m | 10.8M | 65.6 | 31.1 | 60.4 | 54.5 | 17.1 | 3.1 | 50.8 | 12.0 |
| tf2x4 | 1.7M (looped x4) | 59.3 | 25.7 | 53.8 | 48.6 | 14.4 | 2.5 | 44.6 | 11.1 |

Weakest families for all three: chain_ops 2-8%, state_update 8-10%, var_chain 12-20%, table_lookup 22-28%,
chain_story2 18-28%. Held-out families: 0-3%. Reference: the 1.2B sandwich (main2) is 74.6% on in_dist.

## 02-calib-long (queued 03:42 UTC): the same 3.2M and 10.8M at 24,000 updates.
