BensPC run 2026-10-04 (UTC-4 local), spec PC-JOB.md @ 99b883729, skills_pretrain_v1.py sha256 EA077199... Smoke: lm-lora 92 linears, A_with_grad 92 == A_total 92.
S (shuffle-pool, 1360 in_dist): 1014 correct = 74.6% (intact main2 68.5%).
A1-A3 (--lm-lora 8, 6000 updates): train fit 13.4 / 11.2 / 11.2 (start 37.8 / 38.1 / 33.1; baseline at 6000 50.6 / 52.5 / 46.3) = -37.2 / -41.2 / -35.0, mean -37.8. Held-out in_dist 27.8 -> 10.0 / 9.4 / 9.1.
Registered rule: HURTS. Caveat: LoRA ran at the harness lr 1e-3 (not tuned for adapters); the collapse may be an lr/instability effect, not proof that an LM adapter cannot help (untested).
