# 0.2d gates, ADDENDUM-28: 0.2d runs on BensPC. Written 2026-09-26 18:50 UTC, before any code or run

Ben 18:42 UTC (relayed by the Thread manager 18:48): no new money; rentals only from the remaining vast balance, everything
else on BensPC (RTX 5070 Ti 16 GB, torch 2.11, one job at a time). No mark, bar, panel or arm changes here; compute only.

1. **Where 0.2d runs.** Every 0.2d job (D0, rows, rival arms) is queued on BensPC through the Director. 0.2d asks for
   no vast money: the leftover balance goes to the gates first (358b3, dl-7b, lis-320, mu-405), as the Thread manager set.
   torch 2.11 on BensPC also keeps the 358b3 loop net clear of the autocast bug.
2. **Order, one job at a time:** D0 (DEV chats + one night) -> memory row (bank E, build arm J, which also gives H1, S1/H3,
   Y1) -> row A (build, loop-net-off) -> row B (sleep on vs off) -> no-harm rows (C1, K1, GSM8K/MMLU-Redux) -> rival arms
   that Benchmarks cannot reuse from earlier sealed runs. D0 must pass before any row is queued (ADDENDUM-26).
3. **Estimate (a guess, not measured on BensPC):** 0.2d-r's 40 lives took ~14 min on a rental 5090; the 5070 Ti is taken
   as about half that speed.
   | job | GPU hours |
   |---|---|
   | D0 health gate, plus one allowed rerun after a fix | ~1 |
   | build arms: memory row, row A (2 arms), row B (2 arms), C1, K1, GSM8K/MMLU | ~4 |
   | rival arms (3 models; row A raw + grid-given at --max-new 8192, cap hits cost ~2-3 min each) | ~3 to ~8 |
   | **total** | **~8 to ~13** |
   The range is mostly row A's rival cap hits and how many earlier rival outputs Benchmarks can reuse (same model, recipe,
   panel sha). Blind judges are agents, no GPU.
4. **Waits outside compute:** 0.2d's sleep frame is one GLM-written line (ADDENDUM-19); it waits on Ben's OpenRouter
   decision like every new GLM job. If the H-B recipe that passes already carries a GLM frame, that one is reused.
