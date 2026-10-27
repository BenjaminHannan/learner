# Brief: "Translator check" (Director, 02:35 UTC 09-29)
Read handoff/director-briefs/thread-helper-common.md and rules.md first (MARKS SELF-CHECK applies). New files only; dev panels only; Mac CPU/PC GPU per the queue rules, $0, no vast.

**Design (Ben, in his words):** the talker is a thin translator. Words -> a state the reasoner understands; the reasoner does literally everything; the reasoner's final state -> words. Credit must go to the loop, not the talker.

**Question:** given the frozen practised loop's LAST-ROUND state on a puzzle it solved, can a small decoder turn that state into the right answer as words/tokens?

**One change / setup:** frozen sealed practised loop (seeds 0,1; artifacts/claude-fewex-20260927 sources), take the round-final hidden state per cell/token, train a small decoder (few layers, far fewer weights than the reasoner; state the ratio) on train-pool puzzles, score exact-answer words on dev mazes and sums. Do not touch the reasoner.

**Guards the marks must include (fixed before any code):**
1. Talker-alone control MUST FAIL: same decoder given no state (input encoding only, and separately a state from an untrained/shuffled-weights loop). Pass mark for the real run must sit well above this control by more than noise.
2. Plain-net-state row: decoder on the same-size plain net's final state; report it. A claim "the loop's state carries the answer" needs loop > plain-net-state or an honest "not shown".
3. Decoder size cap so it cannot solve the puzzle itself (show the talker-alone control proves it).
4. Every seed must pass; F-type ruler is not used here, so state the noise measured from two decoder seeds.
5. Overlap: read the "Can the talker retell a grid" thread's files (dir-lead0-retell-benspc, handoff/queue/) and say in one line what this adds; do not rerun it.
Ask me by send_message (session_01AfubiZBgctbvNzz8pdHwMb). Explainer page for Ben as usual.
