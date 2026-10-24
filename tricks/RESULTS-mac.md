# Tricks Mac test, partial (2026-10-24, Ben's M1 Pro, mlx-lm 0.32, 4-bit)

Plan and pass marks: `mac/README.md`. Ran via the backbone thread's Mac session. The Mac's disk filled overnight, so the
boss runs stopped early. Raw files: `/mnt/project-files/results/tricks-mac/`.
Lookup is harness-enforced: the Wikipedia intros come from searching PopQA's subject name (fetched once; the answer is
in the evidence for 176/400 rows). Both models read the same evidence. Whole-word scoring.
Boss = LFM2.5-24B-A2B (Ben's pick, thinking closed by template). Worker = Qwen3.5-4B.

## Lookup
| arm | n | accuracy | rare | popular |
|---|---|---|---|---|
| 4B closed-book | 400 | 12.25 | 13.0 | 11.5 |
| 4B + lookup | 400 | **40.0** | 42.0 | 38.0 |
| LFM2.5 boss + lookup | 100 (first 100 rows, all rare) | 42.0 | 42.0 | - |
| 4B + lookup, same 100 rows | 100 | 48.0 | 48.0 | - |

- Paired, same 100 rare rows: boss minus 4B = **-6.0 points** (bootstrap 95% CI -11 to -2). Pass mark was "send fact
  questions to the boss only if boss + lookup ≥ 4B + lookup + 5". **Result: keep fact lookups on the 4B** (suggested; 100 of 400 rows, rare half only).
- 4B + forced lookup (40.0) beats the earlier Vast run where the 4B wrote its own queries (36.5).
- Speed: the 4B answered 400 lookups in 657 s (~1.6 s each, ~430-token prompts); the boss's smoke run used 15 GB peak vs 6 GB for the 4B.

## Timing (4B; boss timing not run yet)
| prompt | 1 answer | 8 in one batch | 8 one after another | batch / single |
|---|---|---|---|---|
| 1k tokens | 9.2 s | 58.9 s | 75.7 s | 6.4x |
| 8k tokens | 30.0 s | 231.9 s | 242.0 s | 7.7x |

- Pass mark "voting is out if batched 8 takes > 6x one answer": **voting is out** on this Mac with mlx-lm as run.
- Batching 8 raised decode only from 48 to 66 tok/s in total (1.4x). Each of the 8 also re-read the whole prompt, which no prefix
  sharing saved (22.5 of 58.9 s at 1k; 190 of 232 s at 8k). Sharing one prefill would bring batched 8 at 1k to roughly 40 s (~4x), an estimate.

## Still to run (when the Mac has ≥ 8 GB free)
Boss + lookup rows 101-400, boss closed-book, boss timing.
