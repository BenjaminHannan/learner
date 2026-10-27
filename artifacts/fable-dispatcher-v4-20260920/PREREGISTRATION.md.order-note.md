Order note (2026-09-20, before any registered v4 run): at Ben's request the waves run `reg+ctx` first, then `v3-repro`, `reg`, `ctx` (`run_v4_regctx_first.sh`, identical to
`run_v4.sh` except for that order). Wave order does not affect any run: each job has its own seed and output folder. The v3-repro faithfulness evidence (bit-identical
computation on a batch) already exists from the test suite; its 6,000-update run is a same-stream control, read together with the other arms.
