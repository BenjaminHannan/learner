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
