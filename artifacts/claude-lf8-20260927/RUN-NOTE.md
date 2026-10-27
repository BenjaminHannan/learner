# lf-8 run note

- 2026-09-27 19:41:15 UTC: the CPU fallback was started in the "Making things up about you" thread's container (4 cores,
  torch 2.14.0+cpu). It ran two lanes of 2 threads, loop8 seeds 9 and 10 first.
- 2026-09-27 19:55:13 UTC: Sleep research started the same sealed plan (72cb903bc) on vast: all 4 runs, one RTX 5090,
  instance 53022539, with SEAL 16/16 (its message at 20:00 UTC).
- 2026-09-27 20:00:53 UTC: the CPU fallback was stopped by exact PID, as the Thread manager asked (19:41 UTC): the lane shells
  1093-1095, then loop8 s9 (1100) and loop8 s10 (1101). Both had reached step 500 of phase A (about 19 min) and
  produced no score. The vast run is the registered one. If it fails, the CPU runs start again from scratch.
