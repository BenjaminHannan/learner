# Gain tests U0, C0 and W1 (PASS-MARKS.md addenda 18-20)

## U0: NOT JUDGED

U0 word pieces (BPE prompt) minus letters, plain_tf_steps.

- missing or invalid: {"200": ["U0 missing"], "201": ["U0 missing"]}

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

