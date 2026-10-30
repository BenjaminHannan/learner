# Practice-1M results (Mac M3, Oct 26 2026)

Setup (PREREG addenda 4-7): K2-Horizon-3.7B q4 on mlx_lm.server, live web, think-then-call prompt. Arms P (checker: SFT on wins + DPO) and C (checker removed, same steps) run side by side; 60 practice puzzles x 2 tries/day, 2 days, 2 nights; test100 (sha256 312375da...) scored at 2 tries per puzzle.

| Arm | Test score |
|---|---|
| A0_P (before) | 18.5% |
| A0_C (before) | 19.5% |
| A0 mean | 19.0% |
| P after night 2 | 16.5% |
| C after night 2 | 15.0% |

Verdicts (shown):
- Noise A0_P vs A0_C: -1.0 pt, p=0.89.
- T1 (P >= A0+8, p<0.05): FAIL, -2.5 pt, p=0.42. The pre-registered "wrong if P <= A0+2" line is triggered.
- T2 (P >= C+5, p<0.05): FAIL, +1.5 pt, p=0.78.
- C vs A0: -4.0 pt, p=0.22.
- T4 (no tool collapse): PASS, 2.01 vs 1.90 calls per try.

By kind: grid 0/30 in every arm. Number A0P 10/30, A0C 9/30, P2 11/30, C2 5/30. Word 10, 10, 7, 9 of 28.
Practice-day wins (of 120 tries): P 14 then 24; C 18 then 11.
Nights: P1 14 unique wins, 7 pair candidates, loss to 0.027; P2 31 unique wins, 18 candidates, loss 0.178. C1 25% of SFT tries correct (loss 0.45); C2 18.8% (loss 1.30).

Likely causes (suggested, not tested):
1. Too few unique wins per night (14, 31), so P mostly memorised them.
2. Native tool calls with arg_key "bash" started with a bare `python3` line, giving NameError in 10-15% of tries. Fixed in tools.strip_shell_line (test_native_bash_python3_line_stripped).
3. Grid puzzles at 0/30: a text-only 3.7B model.
4. Web search almost unused (0-1 tries per arm).

Deviations: the Kaggle replication finished day 1 only (night 1 OOM at 4k tokens; lessons now capped at 2048; no quota left this week). Mac-side fixes (k2_horizon MLX model file, mlx_server.py memory caps, supervise.sh, LoRA scale 2.0 + cosine + clip) live as a patch on the M3 at ~/learner-ops/practice1m/fixes_since_8a1e21e.patch and are not in this repo yet.

Next: rerun with the format fix and many more wins per night (more tries per puzzle, or Sonnet critiques of failed tries via Batches), 3 nights, on Kaggle after the quota reset or on the 4090s.
