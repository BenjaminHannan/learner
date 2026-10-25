# Bonsai-2 LoRA smoke results (Oct 25, 2026)

Script: `bonsai/lora_smoke.py` (rank 8, alpha 16, all 400 packed linears, lr 2e-4, 6 steps,
one new fact "Ben's robot dog is named Pixelbark", `--chunked` GDN).

| Run | Where | Step time | Peak mem | Loss | Fact learned | Controls kept |
|---|---|---|---|---|---|---|
| 2B, no replay, 10 steps | cloud CPU | 48 s | - | 2.48 -> 0.0003 | yes | yes |
| 27B, no replay | cloud CPU | 740 s | - | 2.55 -> 0.0005 | (probe cut by time limit) | - |
| 27B, no replay | M1 Pro Mac | 2.9 s | 12.98 GB | 2.55 -> 0.0004 | yes | no: "capital of France is named Pixelbark" |
| 27B, + 3 replay answers (one graph) | M1 Pro Mac | 13.6 s | swapped, killed | - | - | - |
| 27B, + 3 replay, grads per sequence | M1 Pro Mac | 8.7 s | 13.02 GB | 2.55 -> 0.0008 | yes | yes (one-word Paris/42/Mercury) |

Grad check (packed vs dense layer): rel err 2e-6 on Mac. Mac env: mlx 0.32.3, mlx-vlm 0.7.8.
Lesson: cramming one fact without replay leaks it into nearby answers; the sleep recipe's replay is needed.
