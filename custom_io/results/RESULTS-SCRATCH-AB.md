# Scratch A/B screen (Oct 16): register_loop (base) vs register_scratch (arm), seeds 100-102

Box: Vast 56298437 (RTX 5090), branch claude/project-thread-2zeaoc, queue custom_io/queue/scratch, MAXPAR=1 (one run at a
time). Both data builds regenerated on the box and hash-checked by box.sh. Training flags exactly as the run card. No run
came near the 130-minute rule (training 16.9-20.0 min each). Readouts: custom_io/scratch_readout.py (readout.json per run).
Spend: $1.46 of Vast credit (34.25 -> 32.79), incl. $0.06 storage on a first box (56292549) that never started.

| run | in_dist | chain-5 | staircase final | intact / scratch_zero / scratch_shuffle (in_dist) | scramble cost |
|---|---|---|---|---|---|
| base_s100 | 84.85 | 67.5 | 66.5 | 84.85 / 82.13 / 83.38 | 1.47 |
| base_s101 | 82.43 | 62.2 | 60.8 | 82.43 / 81.32 / 81.84 | 0.59 |
| base_s102 | 85.29 | 60.4 | 58.9 | 85.29 / 85.15 / 84.63 | 0.66 |
| arm_s100 | 82.06 | 51.9 | 50.3 | 82.06 / 82.35 / 81.91 | 0.15 |
| arm_s101 | 81.76 | 47.1 | 45.0 | 81.76 / 82.06 / 81.69 | 0.07 |
| arm_s102 | 82.79 | 53.2 | 51.6 | 82.79 / 83.01 / 82.65 | 0.15 |

Swap check: every base checkpoint loaded into RegisterLoopScratch gives the same answer as RegisterLoop on all 7200 eval
questions (six dev splits + chain-5), and the reloaded base reproduces its RESULT.json exactly. Base lesions are valid.

Arm scratch next-value accuracy (staircase rows, 962; rounds 1-6): s100 59.7 49.3 49.8 51.1 49.9 49.2; s101 55.2 45.0 45.9
46.0 44.5 44.6; s102 58.2 50.0 51.6 52.1 51.9 51.8; 0 excluded. On all in_dist rows (1358 scored): ~80-83% per round;
2 rows per round excluded (value > 7 chars). Untaught base scratch read the same way: 0-7%.

Verdict (pre-registered rules): in_dist base mean 84.19 (SD 1.54), arm mean 82.21, diff -1.99 against a threshold of
+3.09; worst arm 81.76 < base mean. No answer improvement. Scramble cost arm 0.12 mean vs base 0.91 mean: the arm's
scratch is not load-bearing; the base's untaught scratch is more so. => The idea fails at this size.

Full readout table: scratch-ab-verdict.txt in this folder.
