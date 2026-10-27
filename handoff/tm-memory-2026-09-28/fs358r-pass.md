---
name: fs358r-pass
description: 2026-09-27 22:35 UTC: fs-358r PASS, doubling phase-C replay (150+150 vs 75+75) keeps dense loop's grids through mazes; also dl-12 PROVED WRONG
metadata:
  type: project
  modified: 2026-09-27T22:35:04.965Z
---
**fs-358r PASS** (Fix-sleep thread, sealed 370eb499a, results a00d985f8; blind recount agrees). This was the Thread manager's ask at 19:13 UTC 09-27.
- **Setup:** 358e4 dense-replayall vs the same net with phase C replaying 150 grids + 150 sums (358e4: 75 + 75), still 1,500 C steps. Seeds 9-12, paired, cloud CPU, $0.
- **grids5 after C:** candidate mean 159.25 vs baseline 112.50 (after B 166.25). Paired gain +46.75, won 4/4 seeds.
- **maze7 after C:** -1.00 mean; worst seed -27.
- **Reading:** a low replay share in C is the main cause of the grids loss (dev set seed 48000, reused).

**dl-12 PROVED WRONG** (VERIFY 292d01c0f). A label-free router on the plain MiniCPM5-1B's last-layer state:
- sends quiz-panel "bigger" items to the sum skill: 0-6 of 119 to base;
- sends only 178/185 of 300 panel items to base at 750 per kind;
- passes every other bar.

This is report-only input to the experts card.

**Why:** these are the last two Fix-sleep results before Ben stopped all threads at 19:57 UTC 09-27 ("I'm going to run individual chats in the cloud").
**How to apply:** use 150+150 C replay as the dense baseline in later sleep/replay tests. Related: [[fix-sleep-0926]], [[sleep-trains-reasoner-only]].
