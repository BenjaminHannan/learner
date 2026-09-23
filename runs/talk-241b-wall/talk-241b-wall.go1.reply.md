Re-measuring the M5 suite wall — verifying the seal and running the timed comparison.
Seal is intact and I found the original measurement protocol — now pinning down the exact suite command for the re-run.
Directory created. Writing the re-measure driver (new file, mirrors the sealed run.sh with the load gate added).
Typo in the workdir — retrying with the correct path.
All six runs completed with gating. Checking results.
**Verdict: WALL RE-MEASURE DONE — 241b median 31.5 s vs 228 median 30.2 s, +4.3%, WITHIN the +5% bar. Sealed checker M5: PASS.**

This re-measure replaces the loaded +8.1% number per ruling item 3, whatever it shows — it shows a pass.

## Marks table (integer counts)

| mark | bar | result | pass |
|---|---|---|---|
| Seal pre-check (SEAL.sha256.txt) | all OK | 19/19 OK | yes |
| Suite runs completed | 6 | 6/6 rc=0, GATE clean 6/6, 1016/1016 event logs captured each | yes |
| 228 walls (s) | — | 27.3, 30.2, 30.5 → median 30.2 | — |
| 241b walls (s) | — | 31.0, 31.5, 32.4 → median 31.5 | — |
| Wall gap | ≤ +5% (limit 31.7 s) | +4.3% (gap 1.3 s) | **yes** |
| Sealed checker m5 --wall241b 31.5 --wall228 30.2 | PASS | M5 PASS (latency part unchanged: median 0.172 ms, p99 1.111 ms) | yes |
| Seal post-check | all OK | 19/19 OK, 0 mismatches | yes |
| Load gate (load1 < 40 before each of 6 runs) | met | 6/6 runs gated, 0 over-gate starts, total wait ~30 min (< 90) | yes |
| Misses | — | 0 misses, 0 deviations from protocol | — |

## Every move (the 6 walls, in run order, with load1 before each)

1. 228 run 1: 27.3 s, load1 26.22 (no wait)
2. 241b run 1: 31.0 s, load1 34.15 (waited 120 s: saw 41.90 first)
3. 228 run 2: 30.2 s, load1 39.21 (waited 120 s: saw 43.18 first)
4. 241b run 2: 31.5 s, load1 30.85 (waited 720 s: saw 53.72, 50.54, 56.35, 51.48, 62.96, 46.32)
5. 228 run 3: 30.5 s, load1 38.30 (waited 720 s: saw 71.51, 57.47, 44.92, 45.23, 45.77, 50.75)
6. 241b run 3: 32.4 s, load1 35.58 (waited 120 s: saw 52.96 first)

Medians: 228 → 30.2 s; 241b → 31.5 s. Difference: (31.5 − 30.2)/30.2 = +4.3%. Limit: 30.2 × 1.05 = 31.7 s. 31.5 ≤ 31.7, so within +5%.

## Misses / deviations
- None on the measurement. 0 failed runs, 0 gate violations, 0 edits to any existing file (26 new files only, all under `artifacts/claude-mouth241b-20260922/wall-remeasure/`).
- One un-actionable instruction: the task said PUSH the wall-remeasure dir, but OPUS-RULES (which the task says applies in full) forbids commits and pushes — and `artifacts/` is git-ignored anyway (`.gitignore:5`). So nothing was committed or pushed; all files (run-wall.sh, uptimes.log, walls.txt, 6 suites-*.log, 3 mouth241b-run*.log, cap*/out* dirs, wall.json, m5-wall.out) are on disk in the worktree for the director to collect.

## What it means (plain English)
- Under calm machines (load under 40, instead of the 160–220 load that poisoned the first try), the extra grammar-polishing step costs about 1.3 seconds on a 30-second test suite — that is +4.3%, inside the allowed +5%. The old +8.1% fail looks like it was mostly machine noise, not real cost.
- The sealed checker agrees: M5 PASS.

## What it doesn't mean
- It doesn't prove the grammar is good — that's the graders' job (M1/M4), untouched by this task.
- It doesn't mean the cost is exactly 4.3% forever: run-to-run spread is still ~3 s, bigger than the 1.3 s gap, so a repeat could land a bit higher or lower. One re-measure was ordered, one was done.
- CPU only, same fiction-only suite set (rt136, rt143, sessions152, bench) — nothing here says anything about other hardware or real names.
