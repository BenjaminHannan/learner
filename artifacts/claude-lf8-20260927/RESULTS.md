# lf-8 RESULTS: PASS (sleep research thread ran it on vast; written 2026-09-28T20:34:20Z)

Sealed plan: PASSMARKS.md (Making things up thread, 72cb903bc). Run: one RTX 5090 on vast (instance 53022539), torch 2.11.0+cu128, bf16 autocast with the weight cache off, all 4 runs at once, 19:55-20:02 UTC 09-27, $0.13, destroyed after a manifest-verified copy (run-vast/COLLECT.txt, END DONE). Raw files: runs-vast/. A blind recount by a fresh worker from the result.json files and PASSMARKS.md only agrees on every number below.

| seed | arm | grids5 after A | sums4 after B | grids5 after C | sums4 after C | maze7 after C | **T** | minutes |
|---|---|---|---|---|---|---|---|---|
| 9 | loop2 | 193 | 200 | 120 | 193 | 155 | **468** | 3.8 |
| 9 | loop8 | 200 | 200 | 181 | 196 | 182 | **559** | 6.6 |
| 10 | loop2 | 192 | 200 | 61 | 198 | 115 | **374** | 3.8 |
| 10 | loop8 | 200 | 200 | 177 | 196 | 188 | **561** | 6.7 |

- **V:** met (grids5 after A >= 120 and sums4 after B >= 120, both seeds, both arms).
- **PASS:** mean T8 560.0 vs mean T2 421.0, +139.0 (needs >= +40), and T8 > T2 on both seeds (+91, +187). **Met.**
- Proved wrong (T8 <= T2 + 10 on both seeds): not fired.

What it shows (per the sealed reading): the 8-layer loop kept the first skill much better through mazes (grids5 after C 181 / 177 vs 120 / 61) and learned mazes better (182 / 188 vs 155 / 115). loop8 has 3.9x the weights, so this is depth and size together, not depth alone. As PASSMARKS says, a PASS here means "worth a bigger test", not "shown"; the next test it names is a same-size check (8 layers at a width matching 1.65M weights).
Report only: loop2 on this GPU gave T 468 / 374; 358e4's six CPU seeds gave 393-525.
