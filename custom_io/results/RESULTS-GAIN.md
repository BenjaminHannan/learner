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

## W1: NOT JUDGED

W1 global attention in the reader minus B2.

- missing or invalid: {"200": ["W1 missing"], "201": ["W1 missing"]}

W1 null check (no change, q33 B2 vs B2, 360 draws): failure rates {"F1": 0.222, "split": 0.222, "cipher_map_down": 0.067, "old_family_line": 1.0}

