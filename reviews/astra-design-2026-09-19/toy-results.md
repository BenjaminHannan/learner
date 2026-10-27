# Toy results regenerated from 30 run JSONs

**Shown.** Validation only; fixed_K4. READS is gold_read_K2_no_fetch/practised. These are old screening gates, not certification.

| Arm | Stuck | READS | Practised | Held-out | All three |
|---|---:|---:|---:|---:|---:|
| baseline | 4/15 | 14/15 | 11/15 | 1/15 | 1/15 |
| shortcut | 7/15 | 14/15 | 8/15 | 8/15 | 7/15 |

| Arm | Seed | One /512 | READS /341 | Practised /341 | Held-out /171 | Updates | All three |
|---|---:|---:|---:|---:|---:|---:|---|
| baseline | 0 | 115 | 341 | 84 | 6 | 12251 | False |
| baseline | 1 | 512 | 341 | 341 | 13 | 12250 | False |
| baseline | 2 | 512 | 337 | 341 | 88 | 12250 | True |
| baseline | 3 | 512 | 341 | 340 | 18 | 12250 | False |
| baseline | 4 | 489 | 332 | 341 | 12 | 12250 | False |
| baseline | 5 | 512 | 336 | 341 | 45 | 12251 | False |
| baseline | 6 | 509 | 262 | 335 | 10 | 12251 | False |
| baseline | 7 | 398 | 341 | 185 | 12 | 12251 | False |
| baseline | 8 | 270 | 341 | 96 | 17 | 12250 | False |
| baseline | 9 | 512 | 341 | 341 | 66 | 12250 | False |
| baseline | 10 | 510 | 339 | 336 | 10 | 12250 | False |
| baseline | 11 | 512 | 341 | 340 | 50 | 12250 | False |
| baseline | 12 | 104 | 341 | 70 | 31 | 12251 | False |
| baseline | 13 | 102 | 341 | 75 | 8 | 12250 | False |
| baseline | 14 | 512 | 328 | 341 | 18 | 12250 | False |
| shortcut | 0 | 506 | 341 | 339 | 171 | 12251 | True |
| shortcut | 1 | 99 | 341 | 69 | 32 | 12250 | False |
| shortcut | 2 | 92 | 341 | 75 | 35 | 12250 | False |
| shortcut | 3 | 512 | 323 | 338 | 170 | 12250 | True |
| shortcut | 4 | 473 | 306 | 257 | 132 | 12251 | False |
| shortcut | 5 | 512 | 341 | 341 | 171 | 12251 | True |
| shortcut | 6 | 112 | 333 | 77 | 38 | 12251 | False |
| shortcut | 7 | 103 | 341 | 82 | 32 | 12251 | False |
| shortcut | 8 | 117 | 341 | 67 | 45 | 12250 | False |
| shortcut | 9 | 101 | 341 | 73 | 39 | 12251 | False |
| shortcut | 10 | 509 | 317 | 339 | 107 | 12250 | True |
| shortcut | 11 | 512 | 341 | 329 | 128 | 12251 | True |
| shortcut | 12 | 511 | 341 | 329 | 158 | 12251 | True |
| shortcut | 13 | 512 | 334 | 339 | 171 | 12250 | True |
| shortcut | 14 | 103 | 341 | 75 | 37 | 12251 | False |

Definitions: stuck one<384; READS>=307; practised>=171; held-out>=86; all_three is the conjunction of READS, practised and held-out. One-hop is a separate gate. Source paths and timings are in toy-runs.csv.
