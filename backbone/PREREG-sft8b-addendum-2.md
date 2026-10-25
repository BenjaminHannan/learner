# SFT-8B-1 addendum 2 (2026-10-25 ~01:30Z, before any tau2 on an adapter)

The first training run diverged: val loss went from 1.275 to 1.551 by step 199, and train loss from 1.46 to about 2.1. Cause: mlx_lm's default LoRA scale is 20, which is about 10x the standard alpha/r = 2 at lr 1e-4, and LoRA was also applied to the MoE router gate. The relaunch uses scale 2.0 (alpha 32 / r 16) and leaves the router out of LoRA. Everything else follows the prereg. The aborted run is kept on the Mac in sft8b/*_scale20_aborted and will not be scored.
