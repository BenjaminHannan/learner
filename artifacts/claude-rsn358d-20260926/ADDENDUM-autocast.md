# rsn-358d addendum: possibly trained under the autocast cache bug (sleep research thread, 2026-09-26 20:02 UTC)

The registered verdict (INCONCLUSIVE, G0 not met: the loop reached 210/300 on only sums4) stands and is not rewritten.
- 358d's loops trained on a rental with the same bf16 autocast loop code. Its torch version is not recorded; the rent kit used torch 2.8 images, where the weight cache removes the loop's block gradients on steps with no-grad rounds.
- rsn-358i2 showed the loop learns grids normally once the cache is off (artifacts/claude-rsn358i2-20260926/VERIFY-recount.md). 358d's failure to reach G0 fits the bug, but that link is suggested, not shown, for 358d itself.
