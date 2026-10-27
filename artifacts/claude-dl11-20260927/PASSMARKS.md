# dl-11: can a learned router pick the right skill among look-alike requests?
# (Fix-sleep thread. Registered when this file is committed, before any run; written 2026-09-27T12:53:52Z from
# `date -u`. Draft a55d497a3 / b93d3ed6b, reviewed by the Thread manager at 12:29 UTC; all nine points are applied
# below.)

Code:
- scripts/claude_dl11_router.py (its docstring is the method);
- scripts/claude_dl11_luna.py (the Luna stage).

It reuses claude_dl9_experts (the pool recipe, features and GLM texts) and claude_dl1_nights (days, copy rows, panel)
unchanged. This is a $0 BensPC test that joins nothing. A router plus experts joins 0.2d only with Ben's yes (goals:96).

## Why
Ben at 11:34 09-27: "It should for each request be able to automatically decide what."

dl-9 (PASS, VERIFY-dl9.md 1cb95fd69) showed that one expert plus an on/off switch stops the spill when the two kinds
look nothing alike. But its switch fit at 0.0 loss from night 2, and on night 1 it turned on for 86 of the 119
"Which number is bigger" items. It also threw away always-on S's panel gains (55 and 49, mostly those number items).

The open questions:
- Can a switch choose between several skills when the requests look alike?
- Can any helpful spill be kept?

## Two skills made of numbers, and the look-alikes
- **P (puzzles):** dl-9's day puzzles ("make the target from these numbers"), in GLM 5.3 Flash's frame (sha-pinned).
  The targets are the 1B's own code-checked expressions (dl-2's copy rows). RuleKeeper is disclosed scaffolding, as
  in every dl run.
- **Q (arithmetic):** code-made, two numbers with + or - on 2-99, or * on 2-19. The frame is Luna's first valid one,
  which asks for the number only.
  - An expression enters the night's rows if the 1B got it right at least once (greedy plus 10 samples at T 0.7,
    lenient scoring).
  - The row's target is the code-made bare value.
  - The size was set by a CPU probe on dev seeds, using a probe wording of mine that is never used in the run. 3-4
    numbers: 0 of 30 right greedy. 2 numbers: 8 of 45 greedy, and 13 of 45 right at least once.
  - While checking the generator I printed the first 8 Q TEST expressions. They are code-made, and no model saw them.
- **TEST items never practised.** Q TEST (seed 2991) has every Q day expression removed. P TEST (seed 2990) has every
  P day puzzle removed. This follows claude_dl9_experts.py:260-263.
- **Look-alike negatives, from night 1:** short everyday questions containing numbers, written by Luna in the Mac
  stage.
  - Code drops anything with arithmetic between digits.
  - It drops anything with the panel's two number templates or their synonyms. The words are listed as BANNED in
    claude_dl11_luna.py: bigger, larger, smaller, how many, greater, higher, more than, less, fewer, lower, most, least.
  - It drops anything equal to a panel question.
  - The stage stops if fewer than 400 look-alikes or fewer than 3 Q frames survive.
  - The look-alikes are never answered, and never trained into any adapter.
- **Plain negatives:** dl-9's recipe. These are quiz questions the base 1B writes itself (pool seed 2992), with
  digits and panel topics dropped.
- Half of all negatives carry GLM's "Answer only, no explanation." 80% fit the router; 20% are held out.

## Training (the same for every expert)
Each night the P-expert and the Q-expert each gather their own day and train on their own rows. S trains on exactly
the same P and Q rows together. They are LoRA r16 on q,k,v,o, three sets on one frozen MiniCPM5-1B (87179e5c). Each
uses dl-2's recipe (3 epochs, lr 2e-4, batch 8, AdamW) and grows over nights. Seeds 18 and 19, 5 nights, 150 P and
150 Q items a day.

## Router
3-way logistic regression (base / P / Q) on the frozen base's last-layer state at the last prompt token. It is dl-9's
switch with three outputs.
- It is refit each night on every P and Q day item so far, plus the negatives.
- In training it is taught with where-each-item-came-from labels. Nothing tells it the kind at test.

## Arms (all generated live at night 5, with the same torch seed per pass)
- **S:** the shared adapter, always on.
- **X:** the router's choice: base, P-expert or Q-expert.
- **M:** soft mix, with the P-expert at p(P) and the Q-expert at p(Q).
- **R:** X's choices shuffled over the same 600 requests.
- **Report-only:**
  - O: oracle, where the true kind picks the expert and the panel goes to the base.
  - AP: the P-expert always on.
  - AQ: the Q-expert always on.

## Tests
- **P TEST:** 100 fresh puzzles x 20 guesses at T 1.5 ("lucky").
- **Q TEST:** 200 fresh expressions, greedy. It is scored two ways:
  - lenient: the last integer in the reply is the value;
  - strict: the reply is the bare value.
- **HARM:** the 300-item panel (lost = right at base, wrong now).

H2 and the INCONCLUSIVE guard use lenient scoring, so that learning the bare-answer format alone does not count as
learning arithmetic. Strict is reported beside it. Lenient is "last integer", not "anywhere": an echoed "6 - 3" would
otherwise count whenever the value equals an operand.

## Marks (night 5 unless stated; score() computes them)
- **H1 forgetting stopped:** X panel lost <= 5 on each seed, and the X lost sum <= 0.25 x the S lost sum.
- **H2 learning kept:** on each seed, X's P gain >= 0.9 x S's P gain, and X's lenient Q gain >= 0.9 x S's lenient Q
  gain. Gain is over the base, and a negative S gain counts as 0.
- **H3 router picks right on look-alikes:** on night 1 AND night 5, on each seed:
  - P TEST sent to the P-expert for >= 95 of 100;
  - Q TEST sent to the Q-expert for >= 190 of 200;
  - panel sent to the base for >= 285 of 300;
  - the 119 "bigger" items sent to the base for >= 113.
- **H4 choosing beats chance:** X gain >= 2 x R gain on P and on Q (sums), and the X lost sum <= the R lost sum.

**Verdict:** PASS = H1-H4. INCONCLUSIVE if base P lucky < 10, the S lost sum < 20, or S's lenient Q gain sum < 10.

**Proved wrong** (a router learned from where items came from cannot keep both on look-alike requests) if, on either
seed at night 5, any of these holds:
- X lost > 0.5 x S lost;
- X gain < 0.8 x S gain on P or on Q (when S's gain is above 0);
- fewer than 89 of the 119 "bigger" items were sent to the base.

## Graded row for helpful spill (not a mark)
Kept share = S's gained panel items that the arm also gets right, divided by S's gained items. It is reported for X,
M and O, per seed, with that arm's lost count. The grades:
- none: under 10%;
- some: 10-49%;
- most: 50% or more.

A grade counts as "kept without harm" only when the arm's lost count is <= 5.

## Reported
- The router's choices each night: P TEST, Q TEST, the panel by kind, the held-out Luna look-alikes, and the held-out
  base questions.
- M's mean probabilities on the "bigger" items.
- AP and AQ: panel lost and gained, and P and Q gains.
- Strict Q gains for every arm.
- Reworded rows at night 5: P under GLM's 4 other frames and Q under Luna's other frames. For each, the router's
  choice and greedy right for base, expert and X.
- **Words row** (Thread manager point 5): the first 100 Q TEST items written in words by code ("nineteen times
  three"), in Luna's frame and never trained. It reports the router's choice, and right for base, Q-expert and X. It
  shows whether the router routes on content or on symbols.
- Minutes.

## Limits stated now
- Two skills, both arithmetic, one frozen 1B, and 2 seeds.
- In training the router is taught with where-each-item-came-from labels. Nothing tells it the kind at test.
- S trains on about twice the rows each expert trains on (P rows + Q rows vs P rows or Q rows). dl-6 found forgetting
  tracks the total amount trained, so H1's comparison with S is partly an amount effect. The AP and AQ rows show each
  expert's own spill with no router.
- Q targets are code-made values, not the 1B's own words, and Q's gain may be partly the bare-answer format. That is
  why H2 uses lenient scoring and strict is reported beside it.
- The look-alikes are Luna's everyday number questions with the panel's number templates and synonyms kept out. So
  H3's 119 "bigger" items test whether the router generalises to a template it never saw.
- Live generation for each arm adds sampling noise to "lucky".
- The asks that make the base write its own questions are dl-7's fixed asks, as in dl-9. They never reach a training
  row or the router's inputs.

## Predictions (fixed now)
- Base Q greedy right, lenient: about 15-25% of 200 (the probe gave 8 of 45).
- H3 on night 1 is the riskiest mark.
- If H3 passes, I expect H1 and H2 to pass.
- M keeps "some" spill at most, because a router fit on separable kinds gives near 0/1 probabilities.
- The words row: I expect the router to send most word-form items to the base, because it routes on symbols.
