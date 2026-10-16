# M0 pre-registration (written 2026-10-16 before any scoring)
Measurement only, no training. CPU, greedy, domain/harm.py path (in_dist_hits) + the same evaluate() on frame/variant/answer.
DEV rebuilt from skills_curriculum (branch claude/project-thread-y0sxwe) --seed 1 --dev-per-cell 40; all 7 manifest hashes MATCH.
Checkpoints: parent T1SDR_s200 (far-transfer-inputs, 13,290,166 B); children step_4000 of L12-LA64, L12-LB, L13-LBsoft10, L14-LBnk30 (yha868).
Predictions:
 P1 parent in_dist = 1227/1360 = 90.22 on this path (cio train-time RESULT says 1228 = 90.29; expect 1-item path difference).
 P2 L13 = 89.78 and L14 = 89.93 exactly (reproduces recorded harm rows).
 P3 (open, the real unknown) unguarded L12-LB drop: prior 1-4 pts; L12-LA64 (base frozen add-on) drop <= 1.
 Decision use: if L12-LB drop <= ~0.5 with item-level 95% CI covering 0, staged forgetting at this size is not a measurable cost on in_dist and the guards buy nothing on it while costing ~30 HO points (single seed, data confounded: L12 rows != L5 rows).
 Wrong-framing signal: if parent != 1227 or L13/L14 don't reproduce, the scoring path is not stable and every recorded slip is suspect.
