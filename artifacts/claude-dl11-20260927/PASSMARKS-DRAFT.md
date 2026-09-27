# dl-11 DRAFT (not sealed): can a learned router pick the right skill among look-alike requests?
# (Fix-sleep thread. Drafted 2026-09-27T12:25Z from `date -u`, for the Thread manager's review before sealing.)
# Follows dl-9 (PASS, VERIFY-dl9.md 1cb95fd69). Ben at 11:34: "It should for each request be able to automatically
# decide what." Thread manager 12:21: a $0 BensPC test that joins nothing is the owner's call; build in (a) look-alike
# negatives from night 1, (b) a graded row for keeping helpful spill, (c) only code-made or GLM/Luna wording and no
# kind label as an input.

## Why
dl-9 showed one expert plus an on/off switch stops the spill when the two kinds look nothing alike. Its switch was fit
at 0.0 loss from night 2, and on night 1 it turned on for 86 of the 119 "Which number is bigger" items. It also threw
away always-on S's panel gains (55 and 49, mostly those number items). The open questions are:
- can a switch choose between several skills when the requests look alike?
- can any helpful spill be kept?

## Two skills, both made of numbers, and the look-alikes
- **P (puzzles):** dl-9's day puzzles. "Make the target from these numbers." GLM's frame (sha-pinned), the 1B's own
  code-checked expressions as targets, RuleKeeper scaffolding (disclosed, as in every dl run).
- **Q (expressions):** code-made arithmetic expressions with 3-4 numbers from 2-12, using +, - and * with brackets,
  and an integer value. The instruction frame is written by Luna. Practice keeps the expressions the 1B got right at
  least once (greedy plus 10 samples); the target is the code-made bare value.
- **Look-alike negatives (from night 1):** about 600 short everyday questions that contain numbers (prices, ages,
  dates, sizes, scores), written by Luna in one Mac stage before the GPU run. Code drops the following:
  - anything with arithmetic between digits;
  - anything with "bigger", "larger", "smaller" or "how many" (the panel's two number templates);
  - anything equal to a panel question.

  They are never answered or trained into any adapter.
- **Plain negatives:** dl-9's recipe. These are quiz questions the base 1B writes itself, with digits and panel topics
  dropped, and half carry GLM's "Answer only, no explanation."

## Arms (training is the same for every expert; the arms differ in how the trained model is served)
- **S:** one shared always-on adapter trained each night on the P and Q rows together. This is today's plain practice.
- **X:** a learned router picks P-expert, Q-expert or the frozen base for each request.
- **M:** soft mix. Each expert runs at the router's probability for that request.
- **R:** random routing at X's rates over the same requests.
- **O:** oracle, report-only. The true kind picks the expert. This separates routing error from the cost of
  separate experts.

Router: 3-way logistic regression on the frozen base's last-layer state at the last prompt token. It is dl-9's switch
with three outputs.
- Labels come from where an item came from: P days, Q days, or base (the Luna look-alikes plus the base's own
  questions; 80% fit, 20% held out).
- It is refit each night.
- It takes no kind label as input.

The experts are LoRA r16 on q,k,v,o, one set each for S, P and Q, on one frozen MiniCPM5-1B (87179e5c). Each is
trained with dl-2's recipe: 3 epochs, lr 2e-4, batch 8, growing over nights.

Seeds 18 and 19, 5 nights, 150 P and 150 Q items a day. The tests:
- **P TEST:** 100 fresh puzzles (seed 2990) x 20 guesses at T 1.5 ("lucky").
- **Q TEST:** 200 fresh expressions (seed 2991), greedy right.
- **HARM:** the 300-item panel (lost = right at base, wrong now).

All arms generate live with the same torch seed per pass. Machine: BensPC, $0.

## Marks (night 5 unless stated; score() will compute them)
- **H1 forgetting stopped:** X panel lost <= 5 on each seed, and the X lost sum <= 0.25 x the S lost sum.
- **H2 learning kept:** on each seed, X's P gain >= 0.9 x S's P gain, and X's Q gain >= 0.9 x S's Q gain. Gain is
  over the base, and a negative S gain counts as 0.
- **H3 router picks right on look-alikes:** on night 1 AND night 5, on each seed:
  - P TEST sent to the P-expert for >= 95 of 100;
  - Q TEST sent to the Q-expert for >= 190 of 200;
  - panel sent to the base for >= 285 of 300;
  - the 119 "bigger" items sent to the base for >= 113.
- **H4 choosing beats chance:** X gain >= 2 x R gain on P and on Q (sums), and X lost <= R lost (sums).

**Verdict:** PASS = H1-H4. INCONCLUSIVE if base P lucky < 10, the S lost sum < 20, or S's Q gain sum < 10.

**Proved wrong** (a router learned from where items came from cannot keep both on look-alike requests) if, on either
seed at night 5, any of these holds:
- X lost > 0.5 x S lost;
- X gain < 0.8 x S gain on P or on Q (when S's gain is above 0);
- fewer than 89 of the 119 "bigger" items were sent to the base.

## Graded row for helpful spill (b), not a mark
Kept share = S's gained panel items that the arm also gets right, divided by S's gained items. It is reported for X,
M and O, per seed, with that arm's lost count. The grades:
- none: under 10%;
- some: 10-49%;
- most: 50% or more.

A grade counts as "kept without harm" only when the arm's lost count is <= 5.

## Reported
- The router's choices per night: P TEST, Q TEST, the panel by kind, the held-out Luna look-alikes, and the held-out
  base questions.
- M's mean probabilities on the "bigger" items.
- The reworded rows at night 5: P under GLM's 4 other frames and Q under Luna's other frames. For each, the router's
  choice and greedy right for base, expert and X.
- Minutes.

## Luna stage (Mac, CPU, before the GPU job)
scripts/claude_dl11_luna.py calls scripts/claude_luna_codex.py, one call at a time.
- Its prompts are fixed in the sealed script, and code checks every row.
- It stops the run (no GPU job) if fewer than 400 look-alike questions or fewer than 3 valid Q frames survive the
  filters.
- The outputs are committed with their sha256, and the GPU run logs the hashes it read.

## Limits stated now
- Two skills, both arithmetic, one frozen 1B, and 2 seeds.
- The Q targets are code-made values, not the 1B's own words.
- The look-alikes are Luna's everyday number questions. The panel's own number template is kept out of them, so H3's
  119 "bigger" items test whether the router generalises to a template it never saw.
- Live generation for each arm adds sampling noise to "lucky".
- The asks that make the base write its own questions are dl-7's fixed asks (as in dl-9). They never reach a training
  row or the router's inputs.

## Prediction (fixed now)
H3 on night 1 is the riskiest mark. I expect H1 and H2 to pass if H3 does. I expect M to keep "some" spill at most,
because a router fit on separable kinds gives near 0/1 probabilities.
