# Finding: the creative side of the bridge is only half attached (2026-10-21; labels: shown / suggested / untested)

**Shown (code):** `custom_io.models.ledger.Ledger.run` (used by `model.loss`, `generate`, `state`) adds the bridge vector P_dc(ctx_d) to the controller tokens. `creative/sampler.py::sample_run` (used by the C2b search that writes the sleep records, by `greedy_tries`, and therefore by `creative_sleep.dev_report` / W2 scoring) re-implements the run loop and has no bridge term. So in V1: sleep training passes see the bridge; record search and creative scoring do not.

**Shown (numbers):** in both arms creative first-try is identical with the bridge on and off (FULL 3.9% / 3.9%, FLOOR 8.6% / 8.6%), as expected if the scorer never sees the bridge. D, whose forward does take the bridge, changes a lot with it off (FULL 78.1% -> 22.8%, FLOOR 27.6% -> 18.5%).

**Shown (contrast):** the Gate S sleep+G1 trial on a 1/8 pool with a ZERO bridge (so no mismatch possible) reached creative dev 26.2%; the arms (trained P_dc, norm ~3.9, mismatch present) reached 3.9% (FULL) and 8.6% (FLOOR).

**Suggested (untested):** the train/inference mismatch (trained with a shift of Z that the sampler never applies) is a main cause of the low W2 numbers in the arms. Not tested: (a) re-scoring W2.pt through `Ledger.generate` (bridge on, the training-time path) vs the sampler path; (b) a run with the creative bridge removed or applied in the sampler too.

**Not done, per coordinator ruling:** no fix, no relaunch, no change to marks. The seal stays shut (`results/decision/DECISION.json`: chosen FULL, W1 pass, W2 fail on dev). Choosing the one change is the coordinator's.
