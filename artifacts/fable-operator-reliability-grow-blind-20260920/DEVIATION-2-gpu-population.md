# Deviation 2 — second, separate population on BensPC's GPU; Mac queue stop rule (written 2026-09-20 before any GPU roster seed ran)

State when written: Mac recovery population has seeds 100–105 complete (all ten cutoffs passed, 512/512 everywhere); seeds 106–108 in progress; nothing run on the GPU
except dev seeds ≥ 998000 (timing only).

* The full roster 100–147 is now ALSO run on BensPC (RTX 5070 Ti, torch 2.11.0+cu128, `scripts/fable_operator_reliability_gpu.py --device cuda`, 6 processes, manifest
  28335ce9…, same bundle b3a8c5b0…, same per-seed data streams — batch digests verified byte-identical across Mac/CPU, Windows/CPU and Windows/CUDA). It is a SEPARATE
  population (device-tagged); its results are never merged with the Mac's. Arithmetic differs at float32 round-off (max relative loss divergence 2.6e-7 over 200 dev updates).
* Reason: measured 1.28× the Mac's throughput and, more importantly, it frees three Mac slots for the experiments Astra's audit 18 asks for.
* Stop rule for the Mac queue, fixed now and independent of any outcome: the Mac queue is stopped at the first batch boundary after the GPU wave writes its DONE marker.
  The Mac population is then reported as "n = seeds completed", every seed listed; it is not topped up and no seed is dropped.
* Predictions P6–P9 are scored on the GPU population (the only complete 48-seed population). The Mac partial population is reported alongside.
