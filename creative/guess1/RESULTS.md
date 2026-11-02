# Guess-1 results (Oct 26)

Verdict (prereg, both seeds summed, marks doubled): **PROVED WRONG** - LIST and MENU both <= IND + 2.
Full tables: results/report_seeds12.md. Raw: /mnt/project-files/creative/guess1/out-seed2/guess1-seed2/run/ (both seeds).
Scoring re-checked independently from results.jsonl (cracked per arm matches the report).

| arm | cracked s1 | cracked s2 | sum | per-try success s1/s2 | top-share s1/s2 |
|---|---|---|---|---|---|
| IND (plain) | 31 | 33 | 64 | .179/.192 | .13/.14 |
| HOT | 32 | 33 | 65 | .193/.233 | .13/.12 |
| LIST | 21 | 25 | 46 | .229/.273 | .22/.25 |
| MENU | 34 | 32 | 66 | .219/.194 | .11/.14 |

Shown:
- K2-3.7B (thinking off, T 0.7) is not collapsed at the plan level on this sandbox: ~540 distinct plan signatures per 576 tries.
- LIST (sees its own earlier tries, told to differ) has the HIGHEST per-try success but cracks the FEWEST tasks, in both
  seeds, and repeats its favourite plan most (top-share .22-.25 vs .13). Showing past attempts anchors the model.
- Across all ~4,600 Stage-2 tries, 9 of 48 tasks were never solved (seed 1), 7 of them confirm_irreversible.
- Doubt Forks Step 0: NO-GO (5/48 tasks with >= 8 surviving forks vs 70% needed); shelved.
Suggested: the gap is first-try (~18-27% per try) vs found-in-12 (~65-70% of T), not guess variety.
