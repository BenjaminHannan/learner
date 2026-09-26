# bm-398i AMEND-1: memory fix, rerun (2026-09-26 ~14:00 UTC)

The first scored run (started ~13:22 UTC) was killed by the machine's memory limit during its fourth pass
(mixed), at about 30 minutes. The kernel log shows the python process at 14 GB resident. It wrote no result.json
and no replies; its log has only the pass timings (base 672 s, off 1284 s, on 1814 s). No mark was read.

Cause: `_last_logits` returned `model(...).logits[0, -1].float().cpu()`. On a float32 CPU tensor, `.float()` and
`.cpu()` return the same tensor, so each stored row was a view that kept the whole logits tensor alive (prompt
length × vocabulary × 4 bytes, about 0.8 GB per LoCoMo prompt). 36 stored rows came to roughly 10 GB.

Fix: scripts/claude_bm398i_run2.py runs the sealed script unchanged, except that it replaces that one function
with a version ending in `.clone()`. The compared values are identical; only the memory kept changes. PLAN.md,
the marks, the items, the adapter and the seeds are unchanged. The rerun is launched once, from a fresh process.
