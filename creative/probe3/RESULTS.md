# Probe-3 results: PASS

Prereg: `PREREG.md` (sealed 5820fbe0b0) + Addendum 1 (e6ae41068e, MLX on the M3). Code 8b6c3eccd4. Run on Ben's M3
Pro, 11:08-13:44Z Oct 27: 58 LoRA steps at ~134 s/step, peak 12.0 GB. Replay gate 100%. Raw: `results/m3/`.
Re-analysed independently in the cloud from the pushed probes: same numbers.

| test writer (sees the start state) | pick rate, all pools (%) | solvable (%) | AUROC | tests holding on the reference |
|---|---|---|---|---|
| RAND | 19.7 | 29.1 | | |
| K2 self-judge (Pick-1) | 34.4 | 50.8 | 0.692 | |
| K2 untuned, vLLM (Probe-2) | 36.5 | 53.8 | 0.661 | 60.2% |
| K2 untuned, MLX (backend control) | 37.5 | | 0.663 | 57.6% |
| Haiku, teacher prompt (Probe-2) | 44.3 | 65.4 | 0.759 | 74.5% |
| **K2 + LoRA trained on Haiku's tests** | **48.4** | **71.5** | **0.784** | 77.7% |

P1 (>= 39.4) ok, P2 (AUROC >= .75) ok; MLX-BASE 37.5 < 39.4 so the pass is credited to training (Addendum 1). PASS.

## What it means
- shown: a 3.7B model can learn to write good end-state tests from 449 examples of a bigger model's tests on other
  tasks, and then picks its own winning try 48% of the time (random 20%, its own judgement 34%). It even edges past
  its teacher's 44% (one run; ties broken by SELF; effective sample ~48 tasks).
- shown: tests are well formed (99% valid, 0 empty samples) and mostly right (78% hold on the reference).
- caveat (prereg): training and test tasks come from one generator and share scenario families; this shows transfer
  inside the sandbox, not to new kinds of jobs.
- next (prereg): end to end on fresh tasks (12 tries + tuned tests vs one try and vs self-judge); and a better teacher
  exists (Haiku with the Brain-1 checklist: 49.5%).
