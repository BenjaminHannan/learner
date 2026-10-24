# Mac reduced run 1 (2026-10-24, CPU, seed 0, `--reduced`: school 8,000, nightly 300, drawn <= 4 steps)

dev + labelled (768 questions), greedy first try.

| Arm | affine | sq_plus | double_add | Hard | square | last_digit | Easy | skills harm (pts) | school loss |
|---|---|---|---|---|---|---|---|---|---|
| base | 0.6 | 16.3 | 18.3 | **11.8** | 96.8 | 79.1 | 87.9 | 2.0 | - |
| occam_deep | 0.6 | 0.7 | 5.9 | **2.4** | 88.3 | 96.7 | 92.5 | 1.0 | 4.03 (1,000 updates) |
| occam5_strict | 0.6 | 0.7 | 14.4 | **5.2** | 87.7 | 94.8 | 91.2 | 1.5 | (cached school, resumed at W1 sleep after a disk-full crash) |

Round-3 marks: occam_deep Hard 2.4 <= base + 3 -> **PROVED WRONG** (one seed: "suggested"). Mechanism line: school loss 4.03 > 2.0, so the arm
did not learn its dreams. occam_deep's school: 2,000 dreams per found length 1-4 (found-4 needed 10.4M draws); no dream equals a held-out form
(any_held_out_same_function 0.0); 7.7% equal an add form, 1.3% a mult form (practised kinds).
Round-2 marks: occam5_strict Hard 5.2 <= base + 3 -> **PROVED WRONG** (one seed). Both Occam schools wipe out sq_plus (16.3 -> 0.7)
and raise the easy kinds (+3 to +5 points).
Aggregator bug noted: results.json lists `failed_arms: []` although occam5_strict had no arm_result.json (it is simply absent).
