# Gain tests U0, C0 and W1 (PASS-MARKS.md addenda 18-20)

## U0: Letters fine: no evidence word pieces help at this size

U0 word pieces (BPE prompt) minus letters, plain_tf_steps.

- pooled-5 U0 - letters: {"200": -3.1291390728476856, "201": -5.364238410596023}
- cipher_map rows of 120: {"200": {"U0": 90, "letters": 95}, "201": {"U0": 57, "letters": 59}}
- prediction proved wrong: True ({"U0": 73.5, "letters": 77.0, "drop": 3.5})
- split changes (2-seed mean): {"in_dist": -1.397058823529413, "answer": -3.0416666666666643, "frame": -10.845588235294116, "vocab": -6.5625, "variant": -0.07575757575757613, "family": 1.25}
- arithmetic families (2-seed mean): {"arith_bare": 3.125, "div_exact": -2.0, "story_addsub": -1.25, "distance_units": 0.25, "chain_ops": 1.5, "chain_story2": 0.25, "story_chain3": -1.25, "var_chain": -5.9375, "state_update": -2.0, "percent_rate": 1.0}
- calculator on: {"d_pooled5": {"200": -3.1788079470198767, "201": -5.413907284768207}, "chain5": {"200": {"U0": 96.6, "letters": 96.4}, "201": {"U0": 96.6, "letters": 96.4}}}

## C0: prediction shown; C0 replaces plain_tf_steps as the yardstick; +6.9 claim stands

C0 plain_tf_steps with no steps cap (107 chars) minus plain_tf_steps (64).

- pooled-5: {"200": {"C0": 66.80463576158941, "tfsteps": 66.82119205298014, "C0_calc": 67.9635761589404, "tfsteps_calc": 67.83112582781457}, "201": {"C0": 67.35099337748345, "tfsteps": 67.08609271523179, "C0_calc": 68.32781456953643, "tfsteps_calc": 68.21192052980132}}
- chain-5: {"200": {"C0": 96.7, "tfsteps": 94.4, "C0_calc": 99.2, "tfsteps_calc": 96.4}, "201": {"C0": 96.7, "tfsteps": 93.9, "C0_calc": 99.1, "tfsteps_calc": 96.4}}
- B2 - C0: {"200": 6.192052980132445, "201": 6.920529801324506}; B2 - plain_tf_steps: {"200": 6.175496688741717, "201": 7.185430463576168}
- split changes C0 - plain_tf_steps (2-seed mean): {"in_dist": 0.44117647058823906, "answer": -0.08333333333333215, "frame": -0.9191176470588189, "vocab": -0.0625, "variant": 1.1742424242424239, "family": 0.625}

## W1: NOT SHOWN

W1 global attention in the reader minus B2.

- pooled-5 W1 - B2 >= +1.0 on both seeds: {"200": 0.8774834437086128, "201": 0.06622516556291203} -> False
- cipher_map in_dist >= 95 (2-seed mean): {"per_seed": {"200": 97.5, "201": 100.0}, "mean": 98.75} -> True
- F1 four lookup families pooled on in_dist, 2-seed mean W1 - B2 not down > 2.0: {"per_seed": {"200": -3.125, "201": -5.0}, "mean": -4.0625, "null_fail_rate": 0.222, "judged": true} -> False
- no dev split down > 2.0 (2-seed mean): {"in_dist": -1.066176470588232, "answer": -0.7916666666666714, "frame": 0.367647058823529, "vocab": 1.75, "variant": 2.5378787878787907} -> True
- chain-5 >= 99.0 on both seeds: {"200": 99.6, "201": 99.9} -> True
- loops:0 in_dist <= B2's + 1.0 and donor in_dist <= 5 on both seeds: {"200": {"loops0": 0.0, "b2_loops0": 0.0, "donor": 3.676470588235294}, "201": {"loops0": 4.1911764705882355, "b2_loops0": 10.808823529411764, "donor": 3.8970588235294117}} -> True
- proved wrong: {"value": {"pooled5_mean": 0.4718543046357624, "cipher_map_in_dist_2seed_change": -1.25}, "wrong": false}
- F2: F1 fails 22.2% of the time with no change -> judged

F3, every other family (rows pooled over the five pooled splits), report only:

| family | W1 - B2 (2-seed mean) | no-change 5th to 95th percentile |
|---|---|---|
| passage_qa | -4.50 | -7.75 to +7.75 |
| seq_next | -3.12 | -4.06 to +4.06 |
| object_track | -3.00 | -5.75 to +5.75 |
| table_calc | -2.00 | -6.75 to +6.75 |
| copy_word | -1.50 | -2.25 to +2.25 |
| prop_eval | -1.25 | -5.83 to +5.83 |
| letter_ops | -1.25 | -1.75 to +1.75 |
| rule_apply | -0.75 | -5.00 to +5.00 |
| backward_solve | -0.62 | -1.25 to +1.25 |
| list_stats | -0.62 | -1.56 to +1.56 |
| div_exact | -0.50 | -1.00 to +1.00 |
| chain_ops | +0.00 | -0.25 to +0.25 |
| distance_units | +0.00 | -0.50 to +0.50 |
| story_addsub | +0.00 | +0.00 to +0.00 |
| story_chain3 | +0.00 | -0.25 to +0.25 |
| var_chain | +0.00 | +0.00 to +0.00 |
| word_filter | +0.25 | -1.75 to +1.75 |
| compare_numbers | +0.62 | -3.44 to +3.44 |
| syllogism | +0.62 | -0.62 to +0.62 |
| state_update | +0.75 | -1.50 to +1.50 |
| table_lookup | +0.75 | -2.75 to +2.75 |
| odd_one_out | +0.94 | -3.75 to +3.75 |
| chain_story2 | +1.25 | -5.50 to +5.50 |
| list_index | +2.00 | -7.75 to +7.75 |
| digits_parity | +2.19 | -3.12 to +3.12 |
| percent_rate | +5.00 | -9.50 to +9.50 |
| kin_chain | +5.25 | -3.75 to +3.75 |
| verify_claim | +5.42 | -10.42 to +10.42 |
| arith_bare | +5.62 | -11.56 to +11.56 |
| order_chain | +6.00 | -6.75 to +6.75 |

W1 null check (no change, q33 B2 vs B2, 360 draws): failure rates {"F1": 0.222, "split": 0.222, "cipher_map_down": 0.067, "old_family_line": 1.0}

