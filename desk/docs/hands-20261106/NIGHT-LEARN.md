# Night learning: current handoff

This is not a working nightly pipeline yet. No real night run or improvement is claimed.

`src/night-learn/score.js` calculates the fixed P2 marks from paired predictions on the same later-in-time examples. It checks both controls, demands click and key examples, and hashes the held labels. It does not establish that data or predictions are real, load a model, change weights, or promote anything. The caller must save and check the actual model and full evaluation-set hashes and prove that the no-intent arm zeroed the intent input.

The current compiler explicitly refuses native training labels. Its accepted receipt says timing and geometry between real events and video are not established. The current pixel policy was built for toy tasks: its intent is one of five task IDs, its key list has eight entries, and its trainer consumes successful sandbox attempts. It does not yet accept Glim's step text or ordinary recorded actions. The attempt-log document is a proposal, pending agreement with HANDS-ACT.

To finish: REC-LIVE must provide usable real recordings and the agreed timing/coordinate contract; connect Glim with its eyes under the model lock; build the real example and sleep-only training path; connect the three-arm evaluation and atomic promotion/rollback; wire the existing sleep scheduler; and run the fixed marks on the actual day. Never mark recordings trained or delete them just because this scorer ran. Record real hashes, five actual explanations, and the measured P1–P3 results after that run.
