# Probe-3 (MLX, Addendum 1) verdict

**PASS**

MLX-BASE PROBE-S 37.5% is below the P1 mark 39.4%, so the tuned verdict stands.

| arm | PROBE-S pick rate (%) | AUROC | SELF (%) |
|---|---|---|---|
| tuned K2 (MLX) | 48.4 | 0.784 | 34.4 |
| MLX-BASE (untuned, MLX) | 37.5 | 0.663 | 34.4 |

Tuned-arm marks: P1 needs >= 39.4%, P2 AUROC >= 0.75, PROVED WRONG <= 37.5%; tuned-arm verdict before the control: PASS ({'P1': True, 'P2': True}).
Diagnostics (tuned): {"unparsable_samples": 0, "validity_rate": 0.99, "samples_with_no_valid": 0, "reference_agreement": 0.777, "all_tie_rate": 0.073}
Diagnostics (MLX-BASE): {"unparsable_samples": 1, "validity_rate": 0.878, "samples_with_no_valid": 49, "reference_agreement": 0.576, "all_tie_rate": 0.151}
