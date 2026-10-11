# Dopamine: a learned "better or worse than expected" signal (design and sealed marks, Sat Oct 10, 2026, 9:35 PM ET)

Asked by Ben, 9:12 PM ET 10-10: "add some sort of motivating factor ... the way that it works in humans is you get dopamine
... I want there to be some sort of dopamine for desired things in this model." 9:20 PM ET: "Don't humans get dopamine from
like eating though and stuff like that?" Thread "Dopamine", Opus designs and judges; Haiku 5.5 helpers read and search;
Sonnet medium helpers write code. Labels: **shown** = measured or read in code; **suggested** = reasoned; **untested** =
never run. Times ET. The small card experiments (domain mode, sleep) and the game are kept separate below.

## 1. In one paragraph

Food, a right answer, a crafted pickaxe: these are **rewards**, the "desired things". In animals the dopamine burst is not
the reward itself but the **surprise**: reward minus what was expected (Schultz 1997; shown in the paper). A monkey's
dopamine spikes for surprise juice, moves to the bell once the bell predicts juice, and dips below normal when expected
juice does not come. So the model gets three parts: (1) the **reward**, given by the world (a tool says the answer is
right; the game says an achievement unlocked); (2) a **guesser** inside the model, a small learned head that predicts the
reward it expects; (3) **dopamine** = reward minus guess (in a game, also the change in the guess from one move to the
next: the temporal-difference error). Dopamine then decides what the model learns hardest, where it practises, what it
replays in sleep, and when it is bored enough to stop.

## 2. The parts

| Part | What it is | Who computes it | Learned or fixed |
|---|---|---|---|
| Reward r | 1 if the outside checker says the answer is right, else 0 (domain mode, sleep); the game's own score for an unlock, plus later health/food (game) | the world: tool, checker, game (outside tools) | fixed by the world, never by us at run time |
| Guesser V | a small head on the model's own state after it has read and thought, predicting the reward it will get (for a question: the chance it is right; in a game: the reward still to come) | the model | learned, from its own outcomes only |
| Dopamine d | r - V (one-step); r_t + g V(s_t+1) - V(s_t) in a game (g = a fixed discount) | the model's learning rule | fixed rule, like AdamW |
| Uses | (a) learn harder from surprises, skip what it already knew; (b) practise where the outcome is uncertain (expected surprise 2V(1-V) is largest at V = 0.5); (c) replay surprising memories in sleep; (d) stop when expected surprise is small everywhere ("bored") | the model | fixed rules with constants set here, the same for every subject |

Where it sits in the finished model (suggested; the Haiku read of FINISHED-MODEL is pending): a head on the thinker's
state next to the learned stop H1, trained only on the model's own outcomes. It never changes an answer; it only steers
learning and practice. That keeps it outside the answer path, so it adds no hand-written step to how the model answers.

## 3. Rules check

- Deployable autonomy (Ben 2:45 PM ET 10-07): reward comes from tools the model calls; the guesser is learned from the
  model's own tries; the uses are fixed rules with constants written here, the same for every subject, never tuned on a
  panel or DEV row. Nothing a person picks at run time.
- No hard-coding: the guesser is learned; the only hand code is the outside checker/tool/game (allowed) and the fixed
  learning rule (same status as AdamW, the undo gate and the domain-mode mix rule, A11 Level 1).
- No cut answers: no training target is changed; dopamine changes only which rows are practised or how often.
- Compute: free cloud CPU only (PC busy with G1 until about Monday midday ET).

## 4. What the papers say (Haiku sweep, `/mnt/project-files/papers/dopamine-papers-2026-10-11.md`; numbers as read by the helper)

- Strongest measured support is for **(b) choosing what to practise**: online difficulty filtering for RL on LLMs (keep
  problems with pass rate between 0 and 1), DART-Math (more weight on hard problems' correct answers), RHO-LOSS (train on
  points that are learnable and not yet learnt), Prioritized Level Replay. None was tested at 3M-100M (suggested risk).
- (c) replay: prioritized experience replay (by surprise) beat uniform replay on 41 of 49 Atari games; reward-biased
  hippocampal replay is seen in rats and humans but not shown to cause better learning.
- (a) weighting own tries by a learned value head: VinePPO found LLM value heads weak; GRPO's group mean (pass rate over
  the model's own tries) works as the "guess" without a head. So whether our guesser can predict anything is the first
  thing to check (D0 below).
- (d) a stop from surprise: no measured paper found.
- Failure cases: skewed difficulty filtering can learn worse; curiosity bonuses lowered Crafter/Craftax scores in some
  papers; STaR: a model at chance cannot bootstrap from its own successes alone (our tool's working answers that).

## 5. Ladder (each rung its own sealed marks, one change at a time)

1. **D0, free check (no training):** can the guesser predict the model's own success, beyond knowing the kind of problem?
   Uses the finished domain-mode v7 runs. Minutes of CPU.
2. **D1, domain-mode screen (sheets, seed 200, v7 + one change):** "go where the surprises are" (use b). Free CPU, about 2 h.
3. **D-night** (use a, learn harder from surprises) or **D-sleep** (use c, weight own found answers by surprise in the
   SCM2 night): only after D1 reads, one at a time, each its own marks; the sleep one goes to the sleep owners through the
   coordinator.
4. **GW-D, the game (after GW-S reads; owned by the game-world thread):** the guesser predicts reward still to come from
   the game view; dopamine (TD error) picks which moves to keep instead of the fixed "8 moves before an unlock" window.
   This is where dopamine matters most (late rewards, no tool showing the working). Proposed to the game thread through
   the coordinator; that thread writes its marks.

## 6. D0 marks (sealed with this file, before the check runs)

- **Data (shown, existing):** domain-mode v7 runs `/mnt/project-files/domain-mode/runs/sheet-s200-v7` (gated),
  `sheet-s201-v7` and `rpn-s200-v7` (reported). Each day's practice rows from `log.jsonl`; the model as it was before that
  day's tries (parent, or the previous night's checkpoint); outcome r = its greedy answer equals the tool's answer.
- **Guesser G:** logistic regression (L2, C = 1.0, standardised) on the model's own state for the question: the reader's
  mean features plus the state the talker reads. For each day d >= 2: fit on all rows of days < d, predict day d (it never
  sees the outcome it predicts). Script `dopamine/d0_guess.py`.
- **Baselines:** K = per-kind success rate over days < d (what domain mode's quiz-based rule already knows); C = the
  model's own answer confidence, calibrated on days < d (reported).
- **PASS (sheet s200):** pooled within-kind AUC of G >= 0.65 (days 2..N) AND Brier(G) < Brier(K).
- **FAIL:** anything else. Meaning: at 3M the guess adds nothing over the per-kind score domain mode already keeps; D1 is
  then not run in this form and the next rung is GW-D (the game).
- Reported, not gated: G vs G_reader (does thinking help the guess), G vs C, calibration, the four cells (right and
  expected, right and surprising, wrong and expected, wrong and surprising) per day, the two other runs.

## 7. D1 marks: "go where the surprises are" (sealed with this file, before any D1 training; runs only if D0 passes)

- **Base:** domain mode v7 exactly (constants file sha256 4781b0be4e900b29..., unchanged), sheets, seed 200, parent
  T1SDR s200, the same sk200k TRAIN prompts (the diary must equal v7's: checked on the diary rows before night 1).
- **The one change:** from day 2, for each of the 1,024 practice slots (kind drawn by v7's mix rule, unchanged), the
  practice maker drafts 4 accepted candidates of that kind; the guesser G (refit each day on all of the model's own
  practice tries so far, features from the current model with its add-on on) predicts V for each; the slot keeps the
  candidate with V closest to 0.5 (largest expected surprise 2V(1-V)); ties go to the first drawn. Day 1 has no history,
  so day 1 and night 1 are v7's exactly: **reproduction check** night-1 loss_first10 = 32.5206 and quiz 19.14 (v7's).
  If night 1 does not reproduce, v7 is re-run here as the control and D1 is compared with that re-run.
- **Primary measure:** sealed near split (sheet.v2, 7 scored kinds) at D1's own stop night, minus v7's 40.24 (same
  analyzer, `domain.analyze`).
  | Verdict | Rule |
  |---|---|
  | PASS | D1 near >= v7 near + 5.0 points (21 of the 420 scored questions), DM4 audit passes |
  | PROVED WRONG | D1 near <= v7 near - 5.0 points |
  | NO DIFFERENCE SHOWN | anything between (reported as is; not proved wrong) |
- **Mechanism check (reported, says whether the change did what it claims):** the practice actually tried on days >= 2 is
  right 25-75% of the time pooled (v7's days 2-7 for comparison), and its mean |r - V| is above v7's.
- Reported, not gated: per-night near curve (mean over nights 1..min of both runs), nights to reach v7's best (42.14),
  per-kind near, far (DM2), DM5, R2, the guesser's AUC each day, hours.
- **What follows (fixed now):** PASS -> seed 201 against v7 seed 201 (54.76), same marks; then RPN. NO DIFFERENCE ->
  D-night next (its own marks). PROVED WRONG -> practising at the edge does not help when a tool shows the working at 3M;
  report it and put the effort on GW-D.

## Addenda (dated; the sealed text above changes only by these)

**B1. What the helpers read (9:55 PM ET 10-10; marks unchanged).** Shown, from Haiku reads of the code (line numbers at
commit 8fce7247a for the model, branch claude/project-thread-2kevpk for sleep, claude/project-thread-h2ya81 for the game).
- *Where the guesser goes in the finished model:* the learned stop H1 already is a one-number head (`Linear(d,1)`) on the
  thinker's control row 1 after each round, read detached so its loss never moves the thinker (tool_h1.py:67, 81, 212). Its
  'right' label is "this round's answer is right", which is the guesser's question for one-step answers. So the guesser is a
  sibling head on detached control 1 (257 numbers at width 256, 513 at 512; counted in the size), trained on the model's own
  checked outcomes; in a game it predicts reward still to come. It adds no round and no call (caps unchanged).
- *Sleep today:* every kept own answer (up to 2 per question from 32 tries) gets the same 32 visits; per-try pass flags
  exist only in a cached file, so "weight a found answer by how rarely it is found" (DART-style) was never tried. A caution:
  the creative S1 loop that used reward minus a group mean as its weight gained as much with shuffled rewards (+17.2/+18.4)
  as with real ones (+18.0/+16.0). A dopamine weight helps only if it carries information, which D0 checks first. The SCM2
  night needs the whole 7d chain to run, and that line waits for the big-run thread, so D-sleep stays a proposal.
- *Game today:* GW-S has not started; play.py discards the step reward and keeps play logs in memory only; the 8-move keep
  rule is in constants but not yet in code; no PPO. Asked the game thread (via the coordinator, 9:50 PM ET) to save per-move
  records so GW-D can train its guesser offline on GW-S's own play. No change to GW-S's marks.
- *Environment:* the system python here has no torch; D0 runs in a CPU venv (`/tmp/claude-0/v`, torch + numpy).

**B2. D0 result and the next test (10:15 PM ET 10-10; marks below fixed before the run starts).**
- *D0 = FAIL on its sealed mark (shown, `results/d0/`).* Within-kind AUC of the guesser G, days 2..N pooled: sheet s200
  0.543 (mark 0.65), sheet s201 0.597, RPN s200 0.573. Brier G 0.284 vs per-kind rate K 0.256 (s200; s201 0.305 vs 0.273).
  The model's own answer confidence C does no better (0.526 / 0.523 / 0.481). Overall AUC is carried by the kind of problem
  (K 0.72 on both sheet seeds). RPN shows the guesser lagging the learner: mean V of right tries 0.49 while the day's
  success jumps (the surprise is mostly "I got better since yesterday").
- *Read (suggested):* at 3M the only reliable "expected reward" is per kind, and the surprise against it is mostly the
  model's own improvement, i.e. learning progress. Domain mode's mix rule already practises where its own quiz changed most
  over 2 nights: that is a kind-level dopamine (Oudeyer's learning progress) the model already has. Per the sealed rule,
  D1 (problem-level picking) does not run. A post-hoc look at why (stronger regularisation, same-day fit, surface
  difficulty) is running; it cannot change this verdict.
- *Next test, R1-D: does the kind-level drive help at all?* Domain mode's addendum A8 wrote this control and it never ran.
  Arm E = v7 with practice spread evenly every day (`--even-mix --fixed-nights 7`), seed 200, everything else v7 (the same
  constants file, parent, sk200k TRAIN data, rebuilt here: sha256 010af671..., all 4,096 v7 diary prompts present).
  Compared with v7 seed 200 (its own picks, 7 nights), both scored by `domain.analyze` on the sealed sheet.v2 panel.
  - Reproduction check: day 1 is even in both arms, so E's night 1 must equal v7's (loss_first10 32.5206, quiz 19.14). If not,
    the comparison is reported without a verdict.
  - Measure: near (7 scored kinds) at night 7, v7 (40.24) minus E.
  | Verdict | Rule |
  |---|---|
  | DRIVE HELPS | v7 - E >= +5.0 points |
  | PROVED WRONG (the drive does not help) | v7 - E <= -5.0 |
  | NO DIFFERENCE SHOWN | between |
  - Reported: per-night near of both arms and their mean over nights 1-7, per-kind near, R3 wasted practice, own quiz.
  - Prediction (suggested): no difference shown; every kind keeps a 10% share and the mix moves slowly.
  - What follows: DRIVE HELPS -> the learning-progress drive is the model's dopamine in domain mode, and the learned
    version (a guesser of its own progress per kind, MAGELLAN-style) is worth building at 10M/30M; otherwise the drive is
    dropped from claims at 3M. Either way the problem-level guesser is re-checked (D0, free) on the first 10M/30M domain-mode
    run, and GW-D stays the main dopamine rung (game thread, after GW-S).

**B3. The ultimate reward is being a good helper (Ben, 9:35-9:40 PM ET 10-10; no marks changed).** Ben: "i want some sort
of inherent motivator in the model, so it can get substituted with that [the mix rule] if that's better"; "it doesn't
strictly have to be that ... Like a reward for being curious ... for humans basically all rewards lead back to reproduction
as the ultimate reward; the model's should be to be a good helper"; "another thing that is important for a good helper is
charisma ... pleasant to talk to ... would count extra". So the reward is layered, as evolution layers food, friends and
curiosity under reproduction:
| Stand-in | Checked by | When |
|---|---|---|
| Right answers | the outside tool or checker | now |
| Curiosity: practise what it is unsure of (edge) or what it is getting better at (progress) | its own learned guesser | now (the motivator race, B4) |
| The task really got done for the person | the person's verdict, checked against the result | later (needs open tasks and real use) |
| Pleasant to talk to (clear, kind, to the point, fun to read) | a judge's score, only added on top of right and honest | later, when the model talks (Ben's separate talking-from-scratch session owns talking) |
Rule (suggested, said to Ben 9:38 PM ET): reward checked helping, never bare approval; a model paid for approval learns to
flatter. Every later reward gets its own sealed marks before it trains anything.
