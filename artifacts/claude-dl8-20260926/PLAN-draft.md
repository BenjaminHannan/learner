# dl-8 draft (NOT sealed; Fix-sleep thread, written 2026-09-26 17:20 UTC)
Question: does a night that practises only what the model does NOT yet do right keep the learning and cut the
forgetting?
Evidence: dl-5 learned the grid day in one night (48.8 -> 93.8 points on fresh grids), then stayed flat while losses
kept climbing (seed 8: 8, 21, 38, 46, 98 of 200). dl-2..dl-4: losses grow with the amount trained, and the wrong-answer
placebo lost about as much as real practice (suggested, not shown).
Brain first: sleep strengthens what is new or still weak; what is already consolidated is not re-trained each night
(prediction error drives learning). Silicon version: before training, the night checks each practice row with the
current model; a row the model already gets right (its greedy answer equals the target) is dropped.
ONE change from the parent night: error-gated rows. Everything else identical.
Testbed options (pick after dl-6b's verdict):
- Grid nights (dl-5 shape) with the bare code-checked number as target and GLM-written grid wording; the gate bites
  hard after night 1. Needs the thought-memory thread's grid code reworded by GLM.
- Number-puzzle copy nights (dl-6 shape, GLM puzzle frame from frames.json); the gate bites less (the day is mostly
  unsolved greedily), so a weaker test.
Draft marks (to be fixed before sealing): gated arm keeps >= 80% of the parent's skill gain AND its final lost is
<= half the parent's on each seed. Proved wrong if the gated arm loses as much as the parent on both seeds.
Money: none left in Fix sleep's $2; needs Ben's yes (reasoning first).
