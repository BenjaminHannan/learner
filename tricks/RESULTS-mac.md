# Tricks Mac test (2026-10-24, Ben's M1 Pro, mlx-lm 0.32, 4-bit)

Plan and pass marks: `mac/README.md`. Run by the backbone thread's Mac session. Raw files: `/mnt/project-files/results/tricks-mac/`.
Lookup is harness-enforced: Wikipedia intros come from searching PopQA's subject name, fetched once, so both models read the
same evidence. The answer appears in the evidence for 176/400 rows.
Boss = LFM2.5-24B-A2B-MLX-4bit (Ben's pick). Its thinking is closed by a template ending `<think>\n</think>\n`. Worker = Qwen3.5-4B-4bit.

## Scoring fix found here
The boss writes narrow no-break spaces and non-breaking hyphens ("Gregg Hurwitz", "Anderson‑Lopez"). Whole-word matching
then failed on correct answers. `popqa_match` now applies NFKC, maps all dashes to "-" and collapses spaces (tricks1.py and
mac/run_mac.py, test added). All numbers below use the fixed scorer. Before the fix the boss with lookup read 29.5%, and the
partial "4B beats boss 48 vs 42" reported earlier was this artifact. The fix does not change the Vast/GPU numbers (s_wiki 36.5, b_plain 27.25).

## Lookup (400 questions, half rare)
| arm | accuracy | rare | popular | wall time | peak memory |
|---|---|---|---|---|---|
| 4B closed-book | 12.25 | 13.0 | 11.5 | 93 s | 4.6 GB |
| 4B + lookup | **40.0** | 42.0 | 38.0 | 657 s | 6.0 GB |
| LFM2.5 boss closed-book | 13.75 | 12.5 | 15.0 | 227 s | 13.9 GB |
| LFM2.5 boss + lookup | **39.25** | 39.0 | 39.5 | 565 s | 15.2 GB |

- Paired boss + lookup minus 4B + lookup: **-0.75 points (95% CI -3.0 to +1.5): a tie.** The pass mark was "send fact
  questions to the boss only if boss + lookup ≥ 4B + lookup + 5". **Result: the 4B handles fact lookups as well as the boss,
  in about 40% of the memory.**
- Lookup is the trick for both models: +27.75 points for the 4B, +25.5 for the boss. Closed-book, the two are about equal (12-14%).
- 4B + lookup minus boss closed-book: +26.25 (CI +21.5 to +31.0). So the small model with the trick beats the big model without it.

## Timing (300 new tokens; seconds)
| model | prompt | 1 answer | 8 in one batch | 8 one after another | batch / single | decode tok/s (1 answer) |
|---|---|---|---|---|---|---|
| 4B | 1k | 9.2 | 58.9 | 75.7 | 6.4x | 48 |
| 4B | 8k | 30.0 | 231.9 | 242.0 | 7.7x | 45 |
| LFM2.5 boss | 1k | 7.1 | 39.6 | 58.2 | 5.6x | 62 |
| LFM2.5 boss | 8k | 21.7 | 154.0 | 170.8 | 7.1x | 54 |

- The LFM2.5 boss (2B active) is **faster** than the 4B worker on this Mac, at both prompt lengths.
- Pass mark "voting is out if batched 8 > 6x one answer": out for the 4B (6.4x); borderline for the boss at 1k (5.6x), out at 8k.
- Each of the 8 batched answers re-reads the whole prompt (no shared prefill): 22.5 of 58.9 s for the 4B at 1k, 190 of 232 s at 8k.
