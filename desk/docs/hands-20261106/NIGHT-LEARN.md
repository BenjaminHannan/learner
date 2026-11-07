# Night learning: current handoff

This is not a working nightly pipeline yet. No real night run or improvement is claimed.

`src/night-learn/score.js` calculates the fixed P2 marks from paired predictions on the same later-in-time examples. It checks both controls, demands click and key examples, and hashes the held labels. It does not establish that data or predictions are real, load a model, change weights, or promote anything. The caller must save and check the actual model and full evaluation-set hashes and prove that the no-intent arm zeroed the intent input.

The current compiler explicitly refuses native training labels. Its accepted receipt says timing and geometry between real events and video are not established. The current pixel policy was built for toy tasks: its intent is one of five task IDs, its key list has eight entries, and its trainer consumes successful sandbox attempts. It does not yet accept Glim's step text or ordinary recorded actions. The attempt-log document is a proposal, pending agreement with HANDS-ACT.

To finish: REC-LIVE must provide usable real recordings and the agreed timing/coordinate contract; connect Glim with its eyes under the model lock; build the real example and sleep-only training path; connect the three-arm evaluation and atomic promotion/rollback; wire the existing sleep scheduler; and run the fixed marks on the actual day. Never mark recordings trained or delete them just because this scorer ran. Record real hashes, five actual explanations, and the measured P1–P3 results after that run.

## Additional building blocks (November 7)

`src/night-learn/data.js` splits actions by idle gaps, holds out the last fifth of elapsed time, and identifies possible human or independently verified corrections at weight 3. Those corrections still require verification by the caller. `src/night-learn/pixel_model.py` is an experimental action head using the existing toy policy's image encoder and recurrent memory, with text input and click, drag, key and scroll outputs. It is not a trainer, a live controller, or a release artifact. No weights were changed.

The checked-in recorder source still writes `verified: false` for its screen transform and the v2 encoder proof says `geometryVerified: false`. The fake files predate the proof format. The native compiler therefore continues to reject them as training labels. These pieces do not yet connect recordings to training or run at night. There is no P1–P3 result or schedule from these changes.
