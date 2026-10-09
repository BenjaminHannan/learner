# Looped-LM ideas for B2: a no-training probe first (written 2026-10-06 about 17:55 UTC, 1:55 PM ET, before the probe ran)

Source: ALoDLM (Amazon AGI with UIC and Korea University, arXiv 2610.04198), summarised at `/mnt/project-files/papers/amazon-looped-llm.md`,
plus the Dense Supervision paper (2606.24898). The coordinator relayed four candidates: a per-token halting gate, a loss at every loop
round, a hidden-state size probe, and checking whether B2 already needs more rounds on arithmetic.

## Why a probe before any training (suggested)
B2's loop is not ALoDLM's loop. ALoDLM repeats a block of transformer layers and lets each token stop when it is confident. B2's
controller writes one program step per iteration (iterations t = 1..7 each write one result slot through the exact calculator), and a
program that is done writes no-ops. So B2 already spends loops unevenly: a 1-step question uses 1 write, a 5-step chain uses 5. The
no-op is its halting signal. The candidates only help B2 if B2 is short of loops, wastes them by changing a right answer later
("overthinking"), or lets its hidden state blow up across loops. All three can be measured on the two saved B2 screen checkpoints
(seeds 100 and 101, `/mnt/project-files/custom-io/checkpoints/29-b2-screen/`) on CPU, with no training and no GPU.

## What the probe measures (`custom_io/probe_loops.py`, big dev build, 200 rows per cell)
- **M1** in_dist exact at loops K = 1..16 (K = 8 is the trained setting), per family and per gold program length L (0-7 steps).
- **M2** settle round of each row right at K = 8: the smallest K from which it stays right up to 8; compared with L + 1.
- **M3** late gain: per family exact(K = 16) - exact(K = 8); rows wrong at 8 that are right at some K in 9..16.
- **M4** overthinking: rows right at some K < 8 but wrong at 8.
- **M5** size of the hidden state: root-mean-square of the controller tokens (8 control, 9 register) after each iteration, 1..16,
  on 512 in_dist rows.
- Read only: M2 split into number families and string families (ALoDLM: number tokens took more loops on their own).

## Gates (fixed now; a gate must open on BOTH checkpoints)
- **G1, more loops (test-time loop scaling):** some family with at least 50 in_dist rows gains >= 3.0 points at K = 16 over K = 8, OR
  rows wrong at 8 but right at some K in 9..16 are >= 5% of the rows wrong at 8. Opens a training test of "train at 8, answer at 16 with
  a per-round readout loss".
- **G2, halting (stop early per row):** overthinking rows (M4) are >= 2% of in_dist rows. Opens a training test of a per-row halting
  gate on the readout.
- **G3, hidden-state growth:** the control tokens' RMS after iteration 8 is >= 10 times its value after iteration 1. Opens a training
  test of the Dense Supervision fix (normalise the controller state inside the loop).
- **No gate opens:** no training run. B2 already covers what ALoDLM adds (shown by the probe numbers), and its loop budget goes back
  on the shelf next to the used-number mark. M2 then says only whether a no-op stop rule would save compute (read only).

A gate opening is not a pass: any training test it opens gets its own marks, written before it runs, 2 seeds against plain B2 on
the same machine, then 6 seeds before anything is adopted (noise rule).

## Result (2026-10-06, 2:35 PM ET; `custom_io/results/40-loops-probe/PROBE.json`, 6,800 in_dist rows per checkpoint, CPU)
| | B2_s100 | B2_s101 |
|---|---|---|
| in_dist at K = 1 / 4 / 8 / 16 | 30.6 / 82.4 / 89.4 / 88.2 | 30.2 / 78.8 / 90.5 / 89.7 |
| program rows (1-7 steps) at K = 8 / 16 | 92.7-100 / within 0.7 | 96.2-100 / unchanged |
| no-program rows (L = 0, 4,007 rows) at K = 8 / 16 | 84.0 / 82.1 | 85.0 / 83.6 |
| best family gain at K = 16 (>= 50 rows) | +2.0 (table_lookup) | +2.0 (word_filter, order_chain) |
| worst family at K = 16 | cipher_map -13.0 | seq_next -14.5 |
| wrong at 8 but right at some K in 9..16 | 53 of 724 (7.3%) | 54 of 644 (8.4%) |
| overthinking (right before 8, wrong at 8) | 130 rows, 1.91% | 113 rows, 1.66% |
| control-token size, iteration 8 / iteration 1 | 3.9x | 3.4x |
| mean settle round, number / string families | 3.09 / 1.69 (L + 1 = 2.51 / 1.15) | 3.33 / 1.74 (2.49 / 1.15) |

Gates: **G1 opens** on both checkpoints, but only on its second clause (7.3% and 8.4% of the rows wrong at 8 are right at some later
round); no family gains 3 points, and answering at 16 is net worse (-1.1 and -0.8). **G2 stays shut** (1.91% and 1.66%, mark 2%).
**G3 stays shut** (3.9x and 3.4x, mark 10x; the size grows by a steady amount per round, no blow-up).

What it means (suggested): every program question is already right by round 8 and extra rounds do nothing for it. B2 already spends
more rounds on arithmetic (number families settle about 1.6 rounds later than string families), exactly because their programs are
longer: the no-op is a working halting signal. The loss sits in the no-program families (rules and lookups), where the answer is not
stable across rounds: rows flip right and wrong as rounds go on. So the one ALoDLM idea that fits is its supervision at every depth,
to make the answer stable once the program is written, not a halting gate and not more loops. The test G1 opens is Test LR
(PASS-MARKS.md addendum 5). Its upside is small: the late-right rows are 0.8% of in_dist and the overthinking rows 1.7-1.9%.
