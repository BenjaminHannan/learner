# 358t v3 addendum 2: BensPC, not a rental (2026-09-26 18:48 UTC, before any v3 run)

At 18:42:25 UTC Ben wrote (cmsg_01FuvegZXjMmeUzStiEFVnEW1Fyp2a1czsHakesRWnmhM5): "I lied you're out of money. You can only spend what's left on the vast and rest has to be on benspc". The rental release (fceb57784) was held unlaunched at 18:43 (17da998d3), and its approval was withdrawn.
- v3 now runs on BensPC (handoff/held/claude-sleep-358t3pc.md) after rsn-358i2 frees the GPU.
- The code, seal and marks are unchanged. BensPC runs torch 2.11, where the cache bug does not occur, so Stage 0 is report only. The cache-off line must still read 0/12.
- The run order interleaves the two graded arms, so that a time-cap stop costs both equally. The report-only loop8-trm runs last and is dropped first.
