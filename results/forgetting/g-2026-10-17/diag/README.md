# Diagnostic D1 (measurement only, 2026-10-17 ~14:40Z): is the residual a coverage gap or a lost tug-of-war?
Recorded L13 step-4000 checkpoint (sha b10f7917, = M0's L13-LBsoft10.pt) vs parent T1SDR_s200, CPU greedy, custom_io evaluate/is_hit.
Sets: the guard's own diary (4,096 rows, sha e21a4703, family mapped back from train.jsonl by prompt) and "fresh": 300 train rows
per family from 10 families, prompts NOT in the diary (Random(7)). No DEV row read.

| family | diary: lost / parent-right | fresh: lost / parent-right |
| fewshot_number_rule | 9 / 100 (9.0%) | 31 / 248 (12.5%) |
| seq_next | 0 / 126 | 6 / 299 (2.0%) |
| order_chain | 0 / 99 | 1 / 300 |
| cipher_map | 0 / 108 | 2 / 298 |
| list_index | 2 / 272 | 3 / 265 |
| rule_apply, verify_claim, copy_word, arith_bare, story_addsub | 0 | 0-1 |
Reading (suggested): fewshot_number_rule is lost EVEN ON THE ROWS BEING REPLAYED -> a tug-of-war the 10x KL loses (the new
sheet task retrains the shared answer readout; fewshot items are zero-call, answer written straight from the GEN registers).
seq_next is a coverage gap (replayed rows held, neighbours drift). Uniform replay gives fewshot ~2.4% of the replay budget.
