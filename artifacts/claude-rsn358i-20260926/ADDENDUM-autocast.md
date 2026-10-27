# rsn-358i addendum: trained under the autocast cache bug (sleep research thread, 2026-09-26 20:02 UTC)

The registered verdict stands and is not rewritten. This note adds what is now known.
- 358i's loop arm trained on a torch 2.8 rental with bf16 autocast and the weight cache on. On torch 2.8 this leaves the loop's block weights without a gradient on every step that has a no-grad round (artifacts/claude-stage0-autocast-20260926/CPU-RESULT.md).
- rsn-358i2 reran the same loop with the cache off on BensPC: SUSPECT CONFIRMED (artifacts/claude-rsn358i2-20260926/VERIFY-recount.md). Dev grids5 at step 10,000 went from 0/1/2/1 to 195/198/197/200, and the grids6 gap to plain went from -83 to +51.75.
- So 358i's loop-vs-plain losses measure the bug, not the design. The plain arm was not affected.
