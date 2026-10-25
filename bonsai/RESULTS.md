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

## Chunked GDN accuracy on real weights (found by the speed thread, Oct 25 18:00Z)

The series inverse `(I-A)(I+A^2)(I+A^4)...` loses precision with real (correlated, unit-norm)
keys at large chunks; random-key unit tests miss it. Training-mode forward loss, Bonsai-2 2B, CPU:

| T | stock | chunk 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|
| 33 | 6.62634 | 6.62634 | 6.62634 | 6.62105 | 6.61815 |
| 256 | 4.5105 | 4.5105 | 4.5105 | 4.52488 | NaN |

The Mac/CPU 27B runs above used one chunk of ~33 tokens (chunk = min(64, T)), so their training
forward was off by ~0.1%; the probes ran on the stock path, so the pass/fail verdicts stand.
Default chunk is now 8 (exact here) until a forward-substitution inverse lands.

Fixed (19:30Z): the speed thread's blocked forward-substitution inverse (from
claude/project-thread-b0qz6e speed/mlx/) replaces the series. Bonsai-2 2B, T=256 training
forward: stock 4.5105, chunk 64 4.5105, chunk 8 4.5105. Default chunk back to 64.
