# Existing TRAIN receipt analysis

Shown: standard-library analysis of existing TRAIN-RAW, DIAGNOSTIC-RAW, INPUT-FRAMES, pinned TRAIN tokenizer audit and independently verified TRAIN target packet only. No evaluation items were accessed, no model/tokenizer was rerun, and no optimizer was called.

| Arm | First update CE | Last update CE | First visit mean CE | Visit 20 mean CE | Updates clipped (preclip norm >1) |
| --- | --- | --- | --- | --- | --- |
| loop seed 0 | 8.224053 | 0.002134 | 3.566407 | 0.595171 | 4874/5120 |
| plain seed 0 | 8.224053 | 0.000153 | 3.548421 | 0.563919 | 4892/5120 |
| loop seed 1 | 7.336820 | 0.832088 | 3.301482 | 1.283073 | 5006/5120 |
| plain seed 1 | 7.336820 | 0.730345 | 3.321140 | 0.884043 | 4959/5120 |

First/last update losses refer to different individual scheduled rows; visit means and fixed whole-TRAIN diagnostics are better trend evidence.

| Arm | Visit 3: diagnostic mean CE; strict TRAIN | Visit 10 | Visit 20 |
| --- | --- | --- | --- |
| loop seed 0 | 2.556257; 12/256 | 1.530478; 69/256 | 0.462230; 194/256 |
| plain seed 0 | 2.633807; 12/256 | 1.658413; 63/256 | 0.342684; 214/256 |
| loop seed 1 | 2.713884; 9/256 | 2.003380; 33/256 | 1.303000; 98/256 |
| plain seed 1 | 2.918941; 14/256 | 1.629733; 62/256 | 0.584647; 185/256 |

Loss decreases and strict TRAIN accuracy increases in every arm across the preregistered visits 3/10/20 (updates 768/2560/5120). All four arms still miss the predeclared final TRAIN 244/256 threshold. Teacher-forced whole-sequence exact totals equal strict native generation totals at every diagnostic boundary; this equality is an aggregate comparison, not a claim about every intermediate token. Every final TRAIN diagnostic emits EOS. Seed 1 plain had four missing-EOS/max-token-limit outputs at visit 3, but none at visits 10 or 20. Final unfamiliar-question outputs all emitted EOS as well.

Across all 20,480 saved optimizer-update records: zero nonfinite loss/norm records and zero zero-norm records. Clipping is frequent (95.2–97.8% of updates), consistent with active gradients under the fixed clip norm of 1. It does not establish exploding gradients or identify an optimization fix. The sealed numeric_optimizer_step checks finite CE, runs backward, clips with error_if_nonfinite=True, and executes AdamW once per record. Parameter-level Adam/gradient participation is enforced by the unchanged runner and durable closure; this analysis does not load checkpoint tensors to re-audit it.

All input/target checks pass for 256 frames and 5,120 updates per arm: question token IDs with EOS match the pinned TRAIN tokenizer audit; question hashes match the audit and independently verified TRAIN target packet; canonical numeric targets agree; notebook is empty; no truncation; canonical frame hashes are valid; every update's frame hash, question hash, labels and mask match its intended saved frame. All three diagnostic snapshots bind to those same labels and targets. This verifies saved bindings. The sealed source shows that these question IDs feed the frozen LM embedding lookup, then reader and fixed4 core, and that canonical target IDs plus EOS are the CE labels. No new tokenizer call was made to independently regenerate label token IDs. Sources: unchanged scripts/sol_cloud_capability256_v1.py, token preparation/input frames/latent function and numeric_optimizer_step; source SHA256 dfeef09f14fdcd0a1987c38d6a89a560f4ef02159b732cd1665cf51e9fa39b01.

Suggested interpretation: demonstrated learning with incomplete optimization/fit under the declared recipe. The seed-1 loop arm fits considerably less well; two fixed seeds show outcome variation but cannot identify stochastic variance, warm-start quality, schedule ordering, architecture capacity, or optimizer dynamics as the cause. End-stage missing EOS is ruled out by saved receipts. The matching teacher-forced/native totals give no evidence for a generation-only decoding failure, while an internal reader/prefix/readout representation limitation remains unlocalized. No causal diagnosis is supported and no test-driven tuning is proposed.

Proposed next test — requires Ben's separate approval, not executed: a new TRAIN-only continuation experiment in a separate namespace, with exactly 20 additional visits (5,120 updates) under the same recipe for both seeds and both arms, fixed diagnostics, no unfamiliar-question reruns and no adaptive extension. Preserve the completed sealed capability evaluation as-is. Predeclare the fit test: both recurrent seeds must reach at least 244/256 strict TRAIN correctness. Falsifier: if either recurrent seed still misses 244/256, another fixed 20 visits alone did not solve TRAIN fit under this recipe. If both pass, that supports a duration-limited fit explanation but establishes no unfamiliar-question capability or recurrent advantage. New budget/protocol approval is needed before any execution.
