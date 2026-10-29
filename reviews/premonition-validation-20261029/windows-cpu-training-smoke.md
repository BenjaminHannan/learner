# Windows CPU training smoke — 2026-10-29

An isolated synthetic two-step LFM3 training smoke ran on BENSPC, not Jacob’s laptop. It verifies backend and checkpoint plumbing, not learning quality or 8 GiB laptop feasibility. No GPU or installed app, service, user data, or accepted adapter was touched.

The first run used frozen sleepmlx source 32944833 and failed at adapter save because Windows `os.fsync` rejected a read-only descriptor in checkpoint.py. Both updates before the failure had finite CE and KL. The original failed result is retained in the accompanying JSON.

With checkpoint fix 71893fad, the same real CPU model completed two updates, saved the synthetic adapter, cleared and reloaded it, and produced exactly equal logits. Losses were CE 9.00555 and 8.34648; KL 0 and 0.002598. LoRA B had 663,552 nonzero elements after the updates, versus zero initially. The run completed in 9.58 seconds; the job reported peak process commit 3,996,897,280 bytes and minimum sampled system free memory 18,940,297,216 bytes. Windows targeted checkpoint tests passed 2/2; the local full checkpoint suite passed 13/13. All owned task Python processes had exited after completion.

Python 3.12.12, Torch 2.15.0+cpu, two Torch threads, bf16 base, below-normal priority, CPU-only environment, 8 GiB job process commit limit, at least 8 GiB system-free watchdog and 300-second deadline were used. The full model and nine supporting files were hash-verified; the source model SHA-256 is 135922caef64e81e52af88ede8b7c3ddaa9d6da220a9737fb3065275dbfb4330. The isolated task directory remains `C:/Users/benja/learner-ops/premonition-wincpu-learning-20261029`. Direct HF transfers stalled; an existing public model copy with matching HF blob SHA-256 was copied into the task directory.

Separately, two native Windows tests with a fake backend passed: external stop handling and wake during training after seven completed steps, with those steps preserved in the checkpoint. This is cancellation logic coverage rather than a cancellation run of the real model.
