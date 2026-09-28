# rsn-358e7 RESULTS: FAIL (not proved wrong) (written 2026-09-28T20:34:20Z)

Sealed marks: PASSMARKS.md (e7007ec7c). CPU in this container, 1 thread per run, 18:49-about 21:31 UTC 09-27. Raw files: runs/. A blind recount by a fresh worker from result.json and PASSMARKS.md only agrees.

| seed | arm | grids5 after A | grids5 after B | sums4 after B | sums6 after B | maze7 after C | grids5 after C | minutes |
|---|---|---|---|---|---|---|---|---|
| 1 | **moe-grow-lat-replay** | 187 | 192 | **93** | 59 | 0 | 182 | 101.5 |
| 2 | **moe-grow-lat-replay** | 188 | 192 | **98** | 48 | 0 | 0 | 104.6 |
| 1 | dense-big-replay (report only) | 198 | 171 | 200 | 190 | 124 | 0 | 160.5 |
| 2 | dense-big-replay (report only) | 199 | 152 | 200 | 196 | 137 | 0 | 161.9 |

- **V:** met (187 / 188). replayed_batches = 250 in every run.
- **PASS** needs sums4 after B >= 150 on both seeds: 93 / 98. **Not met.** grids5 after B was kept (192 / 192).
- **Proved wrong** needs sums4 <= 146 (s1) AND <= 77 (s2): s1 met, s2 not (98). **Not fired.** So FAIL, not proved wrong.
- **Size claim:** none (the lateral net is below dense-big on sums4 on both seeds).
- Against 358e3's moe-grow-replay (136 / 67), lateral connections moved sums4 to 93 / 98: lower on seed 1, higher on seed 2. The frozen grown net still learns the new kind badly and learned no mazes (0 / 0); the same-size dense net with replay learned sums fully and mazes (124 / 137).
