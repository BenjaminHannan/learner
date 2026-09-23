# Experiment 43F — pass marks (fixed before any run)

Registered bases, seeds 4102 / 4103 / 4104. 3,000 updates. Score = fresh accuracy at the FINAL update.
20% of the episodes are held out (recorded, not used for the score). Every seed reported.

Episodes axis (rank 4 vs plain, same episodes):
- F1 (50 episodes): rank-4 >= plain + 0.10 in >= 2/3 seeds, never lower by more than 0.02.
- F2 (20 episodes): same thresholds.
- F3 (dent in the episode wall): rank-4 at 20 episodes >= 0.50 in >= 2/3 seeds. (Experiment 42 plain: 0.01–0.10.)

Rank axis (100 episodes; rank-4 and plain numbers come from 43E's final update: plain 0.490/0.585/0.435, rank-4 0.710/0.905/0.885):
- F4 (4 is not special): some rank in {1, 2, 8, 16} beats rank 4 by >= 0.05 in >= 2/3 seeds.
- F5 (low rank matters): rank 16 is at least 0.10 BELOW rank 4 in >= 2/3 seeds (if a loose limit works as well, "low rank" is not the point).
- F6 safety: old-skills at the final update >= base - 0.02 in every run.

Reading rule: F1/F2 say how far down the gain survives. F3 fail = the episode wall stands. F4 pass = Sleep-vNext needs a rule
for choosing rank (held-out data), not a fixed 4. Exploration on already-used seeds: anything that passes needs fresh-seed
confirmation before any claim. Toy only; says nothing about length.
