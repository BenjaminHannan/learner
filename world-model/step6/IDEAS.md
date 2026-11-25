# Ideas request (advice only). Toy world-model experiment, ~2.5M active params, 16x16 RGB Crafter frames.

Setup: a recurrent "board" (64 rows x 256 dims) reads game frames. A closed-form ridge readout maps a REAL board to
the current frame very well (6% of mean-frame error). We want an "imagine" step: given board_t and action a_t, produce
board_{t+1} so that the same FROZEN readout gives frame t+1. Trained only on real one-step transitions.

History: (step 3) training imagination through the shared trunk with a board-row loss: E/B 31 (B = better of
copy-last-frame and blend), action ignored. (step 4) loss through the frozen readout, shared trunk trained: E/B 321 and
it wrecked reading. (step 5) gated update with a learnable zero-ish scale alpha: alpha learned to go to 0, E/B ~1.3
(copy level), action ignored (shuffling actions changes error by 0%).
Step 6 (about to run): freeze the whole trunk; imagination's new delta = MLP(trunk hidden state per row) x
per-coordinate spread of real boards, last layer zero-init, gated like a normal tick; trainable = that MLP + the action
embedding. Unscored probe of a 1-layer version: img/copy stayed ~1.0 over 600 steps at lr 1e-3.
Real board facts: big shared offset (RMS 1.36) with tiny frame-to-frame spread (~0.02); start board gets 0.2-sd noise.
Pass marks: k=1 error / best baseline <= 0.80, shuffled actions must raise error >= 1.25x in 12/16 held-out worlds.

Questions: (1) Why might a frozen trunk + new head still sit at "copy" level? List the top 3 causes, labelled
shown/suggested/untested. (2) For each, the cheapest no-training or <2-min check that tells them apart. (3) One change
for the NEXT step if step 6 fails, with a pass mark fixed in advance and the result that would prove it wrong.
Be short (<= 400 words).
