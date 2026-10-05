# Calibration runs (exploratory, no verdict)

Written 2026-10-05 03:20 UTC (11:20 PM ET Oct 4), before the runs. Job `queue/01-calib.sh`, one seed each.
Purpose: set the update budget and see how hard the skills benchmark is for plain char-level transformers trained from
scratch, before any design is tested. These rows are NOT reused as baselines for any verdict; every comparison with
marks uses fresh paired seeds.

- `tf3m`: plain causal char transformer, d256 x 4 layers (3.2M params).
- `tf10m`: d384 x 6 layers (about 10.7M).
- `tf2x4`: d256 x 2 layers looped 4 times (1.6M params, compute like 8 layers).
All: 8,000 updates, batch 256, AdamW, bf16, shuffled order, full eval on the 6 dev splits.
