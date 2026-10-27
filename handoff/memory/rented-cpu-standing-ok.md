---
name: rented-cpu-standing-ok
description: 2026-09-20 Ben's standing OK to use rented CPU when it would significantly speed things up (many-seed waves); limits and how to apply
metadata:
  type: feedback
---

2026-09-20 ~11:15 EDT, Ben: "when it would significantly speed it up you can use rented cpu" (after I said paid compute only helps for many-seed reliability waves and baseline sweeps, ~$1–2).

**Why:** the models are tiny; rentals buy parallelism (48–96 jobs at once), not per-job speed. Sequential design/build time is the real bottleneck most of the time.

**How to apply:** use it only for waves that are genuinely parallel-bound (20+ seeds/arms); quote GPU/CPU type, hourly price and projected total before each rental; stay inside [[gpu-budget-cap]] ($30 lifetime; ~$2.30 spent 2026-09-19) and the <30-min wave rule ([[test-time-limit-30min]]); on-demand only; verified copy-back before teardown; write an active-rentals memory note while anything is billing. The app's classifier still blocks my vast.ai API calls ([[rental-create-blocked-by-classifier]]), so Ben presses Run on rent/destroy/status commands; I do ssh/scp. This is a standing OK for CPU-bound waves, not blanket approval for other spending.
