# SFT-8B-1 addendum 1 (2026-10-24, before training)

The 8B scored 14/40 in bf16 and 23/40 in q8 on single tau2 trials. That 9-task spread between near-identical weights shows single-trial noise is much larger than the assumed SE of about 3. Changes:
- P1 is now judged on the mean of 2 trials per arm (base q4 and SFT), not on 1. The pass mark stays at +3 tasks.
- The claim rule stays: confirm over 4 trials with a mean of base + 2 or more.
- Leak and write-arg counts are reported per trial.
