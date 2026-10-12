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
  exist only in a cached file, so "weight a found answer by how rarely it is found" (DART-style) was never tried.
  Corrected 9:25 PM ET 10-11 (the first version misread the table and called this a caution): in the creative S1 loop
  (creative roadmap S1 result, fast-sleep 1478f86f8), reach@32 untrained / shuffled-reward placebo / real reward was
  24.2 / 25.0 / 42.2 and 27.3 / 25.0 / 43.4, so the real reward beat the placebo by +17.2 / +18.4 and the placebo barely
  moved. A reward signal there did carry information. A dopamine weight helps only if it carries information, which D0
  checks first. The SCM2
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

**B4. The motivator race: a learned motivator inside the model vs the hand rule vs no drive (10:25 PM ET 10-10; marks
fixed before either motivator run starts).** Ben 9:35 PM ET: an inherent motivator that replaces the mix rule if better.
- *The motivator (code `dopamine/motivator.py`, a fork of `domain.mode.main` with every change marked `# MOTIVATOR:`):* a
  small competence head of the model, a logistic on its own reader-mean features (add-on on), refit after every quiz on the
  quiz's per-question hits. It never sees kind labels. Two drives, each a fixed rule: **edge** (curiosity about what it is
  unsure of) picks practice by V(1-V); **progress** (curiosity about what it is getting better at; Oudeyer's learning
  progress, MAGELLAN's competence change) picks by |V now - V of the head 2 nights ago, read through the model of 2 nights
  ago|. Each day the maker drafts a 4x pool with an even mix of help examples; the drive keeps 1,024: 10% uniform at random,
  90% by weighted sampling without replacement. Days without a signal (day 1; day 2 for progress) use v7's even practice.
  Settings `dopamine/motivator.json`: head_C 0.01, pool_factor 4, explore 0.10, window 2, the same for every subject.
- *head_C = 0.01, chosen by H0 before any motivator run (shown, `results/h0/`, no training):* on the finished v7 runs, a
  head fit on quiz k predicting day k+1's practice: C 0.01 had the best AUC and Brier of {0.001, 0.01, 0.1, 1}. Even then
  its within-kind AUC is 0.51/0.53 and its Brier 0.221/0.224 is worse than the per-kind quiz rate's 0.209/0.210 (s200/s201).
  So at 3M the learned head is a slightly noisier per-kind rate that it learned without being told the kinds.
- *Arms:* M-edge and M-progress, seed 200, sheets, constants file unchanged (4781b0be...), sk200k, exactly 7 nights (the
  stop rule is logged, not applied), 4 threads, run one after another after E. References: v7 (rule, 40.24 at night 7) and E
  (even mix, B2). Reproduction check: day 1 (and day 2 for progress) equals v7's: night-1 loss_first10 32.5206, quiz 19.14.
- *Measure:* sealed near split (sheet.v2, 7 scored kinds, `domain.analyze`) at night 7, each arm L minus v7.
  | Verdict | Rule |
  |---|---|
  | REPLACES THE RULE | L - v7 >= +5.0; then seed 201 (vs v7 s201 at 8 nights, 54.76) before domain mode adopts it |
  | NO DIFFERENCE SHOWN | between; the rule stays (Ben: substitute if better); the motivator is re-raced at 10M/30M |
  | PROVED WRONG | L - v7 <= -5.0 |
  Also reported for each arm: L - E, per-night near curve and its mean over nights 1-7, per-kind near, the share of
  practice spent on the three kinds whose rows cannot train (MOD, COUNTIF, IF; A2), mean V(1-V) chosen vs pool, R2.
- *Predictions (suggested):* both NO DIFFERENCE SHOWN, given H0. Edge may waste more practice on the untrainable kinds
  (uncertainty-seeking curiosity's "noisy TV" trap: what stays uncertain because it cannot be learned keeps attracting it);
  progress should waste less, since what cannot be learned shows no progress.

**B5. Why D0 failed: post-hoc diagnostic (10:45 PM ET 10-10; cannot change D0's verdict).** Shown, `results/d0/diag/`.
Within-kind AUC, days 2..N pooled (sheet s200 / sheet s201 / RPN s200):
- Stronger regularisation helps a little: best G 0.569 / 0.630 / 0.589 (C 0.001-0.1), and at C 0.001 G's Brier (0.227)
  beats the per-kind rate (0.256) on s200. Ranking within a kind stays weak.
- Removing the day-to-day model change (fit and test on halves of the same day): G 0.60 / 0.63 / 0.82 (RPN thin and
  possibly inflated by near-duplicate prompts across halves); reader-only 0.55 / 0.54 / 0.65-0.70. The thinking state adds
  about 0.05-0.09 over the reader alone.
- Surface difficulty (prompt length, digit count; a diagnostic, never part of the model): 0.56 / 0.59 / 0.54. The model's
  own state knows about as much about which problems it will miss as counting digits does.
- Read (suggested): within a kind, which tries succeed is only weakly predictable at 3M from anything we can see; the
  model's thinking state carries a little of it, and a head trained into the thinker (the Main brain thread's SB-2) is the
  fair next test of a per-problem guesser. The motivator race (B4) uses the per-kind level that does work.

**B6. R1-D result: the hand drive did not help; even practice ended higher (12:10 AM ET 10-11).** Shown,
`/mnt/project-files/dopamine/r1/sheet-s200-even/analysis/RESULT.md` (run 9:33 PM-11:55 PM ET, scored 12:02 AM ET).
- Reproduction: E's night 1 equals v7's exactly (loss_first10 32.5206, quiz 19.14); nights 1-2 near equal v7's (17.86,
  27.62), as both practise evenly on days 1-2.
- Near at night 7: E 50.00, v7 40.24, so v7 - E = -9.76 -> **PROVED WRONG on its sealed mark (the drive does not help).**
  Per night (E / v7): 17.86/17.86, 27.62/27.62, 30.95/35.24, 37.86/37.62, 37.62/39.05, 44.05/42.14, 50.00/40.24. Mean
  over nights 1-7: 35.14 vs 34.25, so most of the night-7 gap is the last night (v7 dipped 1.90, E rose 5.95); one seed.
- Where it came from (per kind, near at night 7, E vs v7): SUM 33.3 vs 11.7, PRODUCT 46.7 vs 16.7, division 36.7 vs 28.3;
  MAX, MIN, cell arithmetic and ABS within 5. The rule's last-day shares were SUM 5.3% and PRODUCT 1.0% (E: 10% each). The
  rule moves practice by |quiz change| over 2 nights on about 26 quiz questions per kind (one question = 3.8 points), so
  kinds whose small quiz stalled lost practice and stayed low. E spent 20% of its last day on MOD and COUNTIF, which cannot
  train (A2), and still ended higher. R2 0.915 (v7 0.872).
- Read (suggested): at 3M, practising evenly beats chasing a noisy progress signal. A drive helps only if its signal is
  less noisy than the gains it chases; the learned motivators (B4) face the same test. Sent to the domain-mode thread.

**B7. The motivator race, seed 200 (2:15 AM ET 10-11).** Shown, `/mnt/project-files/dopamine/r1/*/analysis/RESULT.md`;
every arm's night 1 equals v7's exactly (loss_first10 32.5206, quiz 19.14). Sealed near split, 7 scored kinds:
| Arm | Near at night 7 | Minus rule (v7) | Minus even | Mean near, nights 1-7 | Practice on untrainable kinds (MOD/COUNTIF/IF), days with a signal |
|---|---|---|---|---|---|
| Rule (v7, hand-written) | 40.24 | 0 | -9.76 | 34.25 | (rule's shares) |
| Even (no drive) | 50.00 | +9.76 | 0 | 35.14 | about 300 of 1,024 a day |
| Edge (learned: unsure) | 49.05 | **+8.81** | -0.95 | **38.23** | 194-277 |
| Progress (learned: improving) | 47.14 | **+6.90** | -2.86 | 37.48 | 141-194 |
- Verdicts on the sealed B4 mark: **edge REPLACES THE RULE, progress REPLACES THE RULE** (both >= +5), each pending seed 201
  (queued: edge s201, even s201, then progress s201; 8 nights each, against v7 s201's 54.76).
- Against no drive, neither motivator is better at night 7 (-0.95, -2.86, one seed). Both climb faster early (mean over
  nights 1-7: +3.1 and +2.3 over even; edge's night 2 is 33.57 vs 27.62).
- Predictions: "both no difference" was wrong against the rule (the rule was worse than expected) and right against even.
  The noisy-TV prediction was half right: progress spent the least on kinds that cannot train, as predicted, but edge
  spent less than even, not more.
- How strongly they steer (shown, log `motivator_pick`): mean priority of the chosen vs the pool, edge 0.145-0.209 vs
  0.125-0.195 (a mild tilt); progress 0.16-0.26 vs 0.10-0.17 (a stronger tilt, towards cell arithmetic and ABS later).

**B8. Seed 201 and the read of the whole race (5:35 AM ET 10-11).** Shown, `/mnt/project-files/dopamine/r1/*/analysis/`;
every s201 arm's night 1 equals v7 s201's exactly (loss_first10 35.4724, quiz 20.70). Sealed near split, 7 scored kinds.
| Arm | s200 night 7 | s201 night 8 | s200 mean nights 1-7 | s201 mean nights 1-8 |
|---|---|---|---|---|
| Rule (v7, hand-written) | 40.24 | 54.76 | 34.25 | 42.02 |
| Even (no drive) | 50.00 | 56.90 | 35.14 | 41.37 |
| Edge (learned: unsure) | 49.05 | 53.57 | 38.23 | 41.73 |
| Progress (learned: improving) | 47.14 | 55.48 | 37.48 | 42.62 |
- Verdicts on the sealed marks: **edge** +8.81 on s200 but -1.19 on s201 -> **not confirmed; the rule stays** (B4 needs
  seed 201 too). **Progress** +6.90 / +0.72 -> **not confirmed.** **R1-D** (does the rule's drive help?) s200 proved wrong
  (-9.76), s201 no difference shown (-2.14).
- Read (suggested): at 3M, how the practice is chosen makes no reliable difference: all four arms finish within 3.3 points
  on s201, and s200's 10-point gap came from the rule starving SUM and PRODUCT on that seed. Averaged over both seeds the
  learned motivators' curves sit about 2 points above the rule and even practice (39.98, 40.05 vs 38.14, 38.26), within
  seed noise. So a learned motivator inside the model does as well as the hand-written rule without needing kind labels,
  but it is not shown to be better, and Ben's rule ("substitute if better") keeps the hand rule for now. Whether domain mode
  should still swap a hand rule for an equal learned one under no-hard-coding is the domain-mode thread's call.
- Why (suggested, from D0/H0/B5): at 3M the model's guess of its own success is about per-kind and noisy, so any drive built
  on it can only shuffle practice between kinds, and here every kind keeps improving under even practice anyway.
- What follows (fixed in B2/B4): re-check the guesser (D0, free) and re-race the motivators on the first 10M/30M domain-mode
  runs, where self-knowledge should be better; SB-2 (Main brain thread) trains the guesser into the thinker; GW-D (game
  thread, after GW-S) uses dopamine where it should matter most, rewards that arrive many moves later.

**B9. Input for GW-D from the game thread (10:37 AM ET 10-11; checked against `game-world/PLAN-AND-MARKS-2026-10-10.md` A6-A7).**
No result here and no marks. Shown there (A6, seeds 200/201): when the game model practised moves picked by its own odds it learned
nothing (+0.01, -0.08), because its own odds already lock onto one habit and explore less than random play; the earlier gains came
from lucky random moves. The "beats a normal game AI" pass is withdrawn (PPO played by its own odds gets 3.96 at 40,960 moves).
What this changes for GW-D (suggested): the sec. 5 item 4 version, where dopamine only re-weights which of the model's own moves
to keep, would likely hit the same wall. GW-D should lead with exploration: a learned curiosity reward for seeing new things
(new objects, new unlocks, views the guesser predicts badly), with dopamine (TD error) used for credit on the moves that led
there. Per A7, GW-D runs only if GW-S3 (the sleep-move credit fix) fails S3-2; it then uses the move records in
`game-world/runs/*/moves/*.jsonl.gz` (view, move, source, step reward, unlocks). Its marks are sealed before any run, by the thread
that runs it.

**B10. SB-2 read (Main brain thread, Result 12 in `main-brain/MARKS-2026-10-10.md`, 10:35 AM ET 10-11; relayed, checked there).**
Shown there, one seed: the guesser trained into the body on control 1 ranked within-kind next-day tries at AUC 0.536 (frozen probe
on the no-head run 0.585, prompt length 0.571), Brier 0.334 vs per-kind rate 0.216, and cost one old skill (seq_next 85 -> 72.5).
G1 and G2 proved wrong, G3 passed. With D0 (0.54-0.60) this is the second way of asking the 3M model "will I get this right?"
that stays near chance within a kind. Suggested: at 3M, self-knowledge finer than "which kind is hard" is not there to read out,
by a fitted probe or by training it in. That leaves the motivator's next rungs as written: SB-2b (their reader mean + round-1
workspace head, own marks), the 10M/30M re-check, and GW-D led by exploration (B9).

**B11. SB-2b read (Main brain thread, Result 14 in `main-brain/MARKS-2026-10-10.md`, 1:30 PM ET 10-11; relayed, checked there).**
Shown there, one seed: the head reading reader mean + 8 control rows after round 1, trained into the body, ranked within-kind
next-day tries at 0.523 (frozen probe 0.585), Brier 0.293 vs 0.219, and again cost seq_next (85 -> 75; no-head recipe 85 -> 80).
Both trained-in heads lost an old skill and read worse than a probe refit on all past days. Design decision (from their
suggestion, matching sec. 3 and H0): the guesser stays a read-only head on the shared state, no gradient into the body, refit on
all past days, as `dopamine/motivator.py` already does. SB-2 variants are stopped. Open rungs: the 10M/30M re-check and GW-D (B9).

**B12. Proactive helpfulness joins the good-helper reward (Ben, 8:45 PM ET 10-11; P1 marks sealed here, before any P1 code
or run).** Ben, replying to a coordinator post that gave him one line covering every thread's Mac/PC approvals: "That is one
of my favorite things you've said today. proactively making my life easier. Also, add that to the model as part of it's goals".

- **What it means:** noticing what will save the person effort before they ask, and doing it; when the step is not allowed
  unasked, offering it in one line. Ben's own example is batching: one approval line instead of one per thread.
- **Reward (a new rung under "good helper" in B3):** the person's effort saved, counted in their own actions (asks, turns,
  approvals, corrections), and only on checked outcomes. An unasked step the person turns out to want, checked right: +1
  (an ask they skipped). An unasked step they did not want: -0.25 (they had to read it). An unasked step they wanted but
  got wrong: -1 (they were misled and still had to ask). Praise or thanks without a checked saving earns nothing (that
  path teaches flattery and busywork). Batching counts the same way: fewer person actions for the same checked result.
- **Hard limits (outside the reward, never traded for it):** a step that cannot be undone, spends money, deletes, or goes
  beyond what the person allowed is never done unasked; it is offered in one line. Pleasantness (B3) still counts only on
  top of right and honest.
- **Inside the model (per B11):** two read-only heads on the shared state, no gradient into the body, refit on all past
  sessions. "Next need" guesses what the person will ask next (labels: what people actually ask next). "Help value"
  guesses the effort an unasked step will save (labels: the checked rewards above, so its error is the dopamine signal).
  The model takes an unasked step when its help-value guess is above zero. The list of possible next steps comes from an
  outside tool the model calls ("what could I work out here"), per the deployable-autonomy rule.

**P1, "session sheets" (offline, frozen model, free CPU). Marks sealed now.**
- Models: the v7 sheet finals from the race, frozen: `sheet-s200-v7/night_7` and `sheet-s201-v7/night_8` checkpoints,
  add-on on. Only the two heads learn.
- Person (outside test tool, person seeds 93001 training and 93002 sealed, never shown to the model): a session is one
  grid (3-4 rows, values 1-99) and L requests, L uniform in {2, 3, 4}. Every request is built from a focus (one column,
  rows r1..r2) with the near shapes the model practised; the exact builder per kind is fixed in `dopamine/p1_sessions.py`
  before any run and its sha256 goes in the result. Request 1: a random kind of all 10 on a random focus. Each later
  request: with 0.6 the person's habit on the same focus (SUM->MAX, MAX->MIN, MIN->SUM, PRODUCT->SUM, cell
  arithmetic->ABS, division->cell arithmetic, MOD->division, ABS->MOD, COUNTIF->SUM, IF->MAX), else a random kind on a
  random focus. A request whose tool answer is '?' is redrawn.
- Menu (the outside tool): after each answer, one candidate per kind built from the current request's focus with the same
  builder; '?' candidates are dropped. So a habit follow-up is always on the menu; a random one usually is not.
- Each round the model may add at most one unasked candidate. Wanted = equals the person's next request exactly; right =
  the model's greedy answer equals the tool's. Rewards +1 / -0.25 / -1 as above. A wanted, right extra means the person
  skips that request. Person effort per session = L minus the sum of extra rewards (so never adding anything costs L).
- Data: 6 training days x 150 sessions, then 400 sealed sessions. Each candidate's reader features and greedy-answer
  correctness are cached once per model, so every arm sees the same sessions and the same answers (paired).
- Heads (sklearn MLP, one hidden layer of 64, alpha 1e-3, fixed seed; refit after each day on all past days, frozen for the
  sealed sessions): next need N, input = reader mean of the current prompt, reader mean of the candidate, round one-hot,
  label = candidate is the next request (every round gives labels, whatever the arm did); help value V, input = N's
  probability for the candidate, reader mean of the candidate, round one-hot, label = the reward of extras the HELPER arm
  actually took (bandit feedback only).
- Arms: NONE never adds. EAGER adds N's top candidate every round (day 1: a random candidate). HELPER adds the candidate
  with the highest V when V > 0 (day 1: a random candidate on half the rounds; days 2-6: also N's top candidate on 10% of
  rounds whatever V says; sealed: no exploring). ORACLE (reported only) adds the next request's candidate only when the
  cached answer is right: the ceiling.
- Marks, each seed, sealed sessions, paired bootstrap 95% interval over sessions (10,000 resamples, seed 0), effort in
  person actions per session:
  | Mark | Pass | Proved wrong |
  |---|---|---|
  | P1-1 helps | HELPER - NONE <= -0.05, interval upper end < 0 | interval lower end > 0 on either seed (it adds work) |
  | P1-2 holds back | HELPER - EAGER <= -0.10, interval upper end < 0 | HELPER - EAGER >= 0 on both seeds |
  P1 PASSES when both marks pass on both seeds. Reported: ORACLE saving, extras per session, wanted / right / unwanted
  shares, extras per kind (kind labels used for scoring only), extras on the last request.
- Prediction written before the run (suggested): the frozen models are right more than half the time only on MAX and MIN
  (and, for s201, PRODUCT and division; sealed near 11-73%), and a wanted extra only pays when right more often than wrong.
  So P1-1 may read "no difference" and the ORACLE ceiling will be small; P1-2 is the informative mark (does the checked
  reward teach holding back where eager helping hurts). If P1-1 is flat, re-run P1 on the first 10M/30M domain-mode models.
- P1 code details fixed before the full run (9:10 PM ET 10-11; no mark changed): `dopamine/p1_sessions.py` sha256 2f65e028470dffab...
  Builder: focus cells x, y = c r1, c r1+1; COUNTIF(x:y,">k") with k = (x+y)//2; cell arithmetic x+y*2; IF(c r1>c' r1, c r2,
  c' r2) with c' the other column; caps as panel.py. Both heads standardise their inputs and fit with max_iter 200. N labels
  every candidate of a session's last request 0 (there is no next request). V's first input on day 1 is 0 (N is not fit yet).
  The menu includes the current request's own kind (it can never be the next request unless the person repeats it). One
  wanted, right extra lets the model continue from that answer, so a chain of right guesses can skip several asks.
  Workload: 1,300 sessions, 3,882 rounds, 19,136 distinct candidates (about 8 min of answers per model at 2 threads here).
  Run on the cloud box, not the Mac: the job is about 10 minutes and the Mac's cores are on the Game world runs tonight.

**B13. P1 result (scored 9:20 PM ET 10-11): FAIL. The helper guessed the person's next request well but helped far too
often. P2 marks sealed below, before any P2 code.** Shown, from `dopamine/results/p1/s{200,201}/RESULT.md` (400 sealed
sessions, 2.97 requests each; effort = person actions per session, lower is better):
| | NONE | EAGER | HELPER | ORACLE | HELPER - NONE (95%) | HELPER - EAGER (95%) |
|---|---|---|---|---|---|---|
| s200 | 2.97 | 3.47 | 3.39 | 2.39 | +0.42 (+0.36, +0.47) | -0.08 (-0.18, +0.01) |
| s201 | 2.97 | 3.26 | 3.33 | 2.27 | +0.36 (+0.30, +0.42) | +0.07 (-0.03, +0.17) |
P1-1 PROVED WRONG on both seeds (the helper made the person do more work). P1-2 neither passed nor proved wrong (wrong on
s201 only). Reported: EAGER's top guess was the person's next request 35-36% of the time, close to the most possible (60%
habits on the roughly two thirds of rounds that have a next request, about 40%), so "next need" learned the habits. HELPER
added an extra on 70-76% of rounds and 89% of its extras were unwanted; its extras averaged -0.20 each although it took
only those it guessed above zero. ORACLE shows the room: 0.58 and 0.70 actions saved per session.
Reading (suggested): the help-value head is over-optimistic because HELPER takes the best of about nine noisy guesses each
round (the winner's curse), and most of its training rewards are small -0.25s with rare +1/-1s. Anticipation works; the
restraint does not.

**P2 (one change from P1): HELPER asks the help-value head only about the next-need head's top candidate** (adds it when
V > 0, else nothing), instead of the best V over the whole menu. Everything else as P1: same models, same training
sessions, same heads, exploring and seeds; V still learns only from HELPER's own extras. New sealed sessions (person seed
93003, 400 sessions, same habits), because P1's sealed set has been looked at. Marks, each seed, same rules as P1:
| Mark | Pass | Proved wrong |
|---|---|---|
| P2-1 helps | HELPER - NONE <= -0.05, interval upper end < 0 | interval lower end > 0 on either seed |
| P2-2 holds back | HELPER - EAGER <= -0.10, interval upper end < 0 | HELPER - EAGER >= 0 on both seeds |
P2 PASSES when both marks pass on both seeds. Prediction (suggested): HELPER now acts mostly on early-round habit
follow-ups in kinds it gets right (MAX, MIN), so P2-2 should pass; P2-1 is close (a right-and-wanted extra on MAX/MIN is
worth about +0.2 on average after the misses), so it may read "neither". If P2-2 fails, the head itself is the problem
(not the choice over the menu), and the next change is a better-calibrated head, not more arms.

**B14. P2 result (scored 9:35 PM ET 10-11): FAIL, but the restraint now works.** Shown, from
`dopamine/results/p2/s{200,201}/RESULT.md` (new sealed person seed 93003, 400 sessions, 2.99 requests each):
| | NONE | EAGER | HELPER | ORACLE | HELPER - NONE (95%) | HELPER - EAGER (95%) |
|---|---|---|---|---|---|---|
| s200 | 2.99 | 3.50 | 3.10 | 2.42 | +0.11 (+0.04, +0.18) | -0.40 (-0.48, -0.32) |
| s201 | 2.99 | 3.38 | 3.03 | 2.31 | +0.04 (-0.03, +0.11) | -0.35 (-0.43, -0.27) |
P2-2 PASSES on both seeds: judged only on its best guess, the help-value head cut extras from 3.0 to 1.1-1.3 per session and
stopped most extras after the last request (131 and 160 of 400 vs EAGER's 400). P2-1 is PROVED WRONG on s200 (it still
adds a little work) and neither on s201, so P2 fails. Its extras were wanted 35% of the time, no more often than EAGER's.
Post-hoc ceiling (suggested; `dopamine/diag/p2_kind_ceiling.py`, uses kind labels, so it is a yardstick, not a model): a
helper that knows exactly how often each follow-up is wanted and how often each kind is right (counted on the training
days) saves only 0.08 actions per session on both seeds (1.0 and 0.8 extras). So at 3M the model's answers are wrong too
often for unasked help to pay much, even with perfect judgement; the learned head is about 0.1-0.2 below that yardstick.
Decision: no more P-tests on 3M models. The design (B12) stands; the next P run uses the same code and P2's rule on the
first 10M/30M domain-mode sheet models, where more right answers raise the ceiling. Marks for that run reuse P2's table.

**B15. Outside opinions on the guesser, and the G-ceiling test (marks sealed 2:10 AM ET 10-12, before any code).** The
"Overnight outside opinions via API" thread sent the guesser problem (D0, SB-2, SB-2b) to Fable 5.1 and Opus 5.5 and had
Fable judge both: `/mnt/project-files/api-opinions/answers/{3-guesser-fable,3-guesser-opus,judge-3-guesser}.md`.
Hypotheses only; checked against the code here before use.
- Their free pre-step, "does the Brier baseline use the scored day's own labels (hindsight)?": **no, shown.** D0's K is the
  per-kind rate over days before the scored day (`dopamine/d0_guess.py` line 10), so it lags rather than peeks. SB-2's
  baseline is the per-kind rate on the quiz after night K-1, i.e. the same model on separate questions before day K's tries
  (`mainbrain/guess_score.py` lines 24-25 on the Main brain branch). No Brier verdict so far was too harsh for that reason.
- Agreed with them: keep the guesser read-only (B11); within-kind ranking is not what practice choice needs at 3M (B7/B8),
  but it is what helping unasked on single questions needs (B14's yardstick is kind-level only).
- New idea worth a test: read the model's behaviour, not one pooled state. Answer the same question with different
  thinking lengths; if the answers agree, trust it more (their line for Ben: "answer quickly and slowly; trust it when the
  answers agree").

**G-ceiling test (no training).** One question: is within-kind self-knowledge at 3M limited by day-to-day drift and data, or
not there at all, and does behaviour (agreement across thinking lengths) carry more of it than the pooled state?
- Models, frozen: the v7 sheet nights nearest 40% pooled quiz, s200 night 4 (38.67) and s201 night 4 (37.89).
- Data: 32,000 fresh practice questions per seed from domain mode's own generator (`draft()`, even share over the run's
  kinds, its own seed), deduplicated, each labelled right/wrong by the tool against the model's normal answer (8 loops).
- Probes (logistic, L2 C = 1, standardised, D0's `fit_logistic`): S900 = D0's 900 inputs (reader mean, pooled state,
  confidence); P = process features from the model's own runs: whether the answers at forced 2, 4, 16 and 32 loops equal the
  normal answer (4 flags), the number of distinct answers over the 5 runs, the talker's log-probability of its answer if
  the code exposes it, the number of calculator calls, whether the last call's result equals the answer, prompt length;
  S900+P; length only; and a diagnostic never to ship (operand count, longest digit run).
- Fit: 5-fold cross-fit stratified by kind, on nested random subsets of 2,500 / 8,000 / 16,000 / 32,000 rows; scored on
  out-of-fold guesses. Within-kind AUC as D0 (groups with >= 10 right and >= 10 wrong, row-weighted); Brier vs the frozen
  model's own per-kind rate on the same rows (fair here: no drift).
- Baseline: D0 walk-forward S900 within-kind AUC, s200 0.543, s201 0.597 (`dopamine/results/d0/sheet-s20x-v7.json`).
- Marks, each must hold on both seeds (S900, P and S900+P count as shippable; length and the diagnostic do not):
  | Mark | Holds when |
  |---|---|
  | Drift is a main limit | S900 at 2,500 rows >= baseline + 0.05 |
  | Readable with enough data (PASS) | any shippable probe >= 0.65 at <= 16,000 rows |
  | Behaviour beats state | P >= 0.62 and P >= S900 at equal rows |
  | PROVED WRONG | every shippable probe < 0.62 at 32,000 rows and gains < 0.01 from 16,000 to 32,000 |
  If PROVED WRONG: stop within-kind guesser work at 3M, keep the per-kind level guess, rerun this test on the first 10M
  checkpoint at matched success. If PASS with P: the next test is P on live nights (walk-forward, read-only), 2 seeds,
  with its own marks; the shipped form replaces string equality with the model's own log-probability of its first answer
  under the longer run (their rule-check point), tested before shipping.
- G-ceiling code details fixed before the full run (2:25 AM ET 10-12; no mark changed): `dopamine/g_ceiling.py` sha256
  58e6e64c437990e5... Questions come from domain mode's own make_practice (even share, the run's constants and help examples), with
  the run's own quiz prompts excluded. S900 = reader mean + pooled state + talker confidence (D0's G used the first two).
  The talker confidence is the mean log-probability of its own answer, so it is the log-probability feature in P too.
  "Behaviour beats state" is judged at the largest size; "proved wrong" needs every shippable probe's 16k-to-32k gain
  under 0.01. Smoke (600 rows) cost 0.15 s per question for all 5 runs, so about 80 minutes per seed at 2 threads; run on
  the cloud box (free, idle; the Mac's cores are on the Game world runs tonight).

**B16. Outside opinions on helping and the motivator race (problem 4), checks, and two sealed tests (2:45 AM ET 10-12).**
Source: `/mnt/project-files/api-opinions/answers/{4-proactive-motivator-fable,4-proactive-motivator-opus,judge-4-proactive-motivator}.md`.
Hypotheses only; checked here:
- "Right" for an extra means the model's own answer equals the tool's value of that exact candidate formula
  (`dopamine/p1_sessions.py` do_cache: `correct = ans == value[p]`). The formula and range come from the builder, so every
  wrong extra is a value error, by construction. Shown (code).
- "The edge run logged 10.00% for every kind": shown to be a logging artefact. The `mix` event logs the even share used
  to draw the 4x pool; the motivator's actual picks are in `motivator_pick` and are uneven (s200 edge day 7: ABS 254,
  cell arithmetic 206, MOD 154, IF 4 of 1,024).
- Free re-score of the race with a steadier statistic (suggested; post-hoc, cannot change B7/B8): mean sealed near over
  each run's last 3 nights (`dm5_curve` in each `analysis/RESULT.json`). s200: rule 40.48, even 43.89, edge 47.22,
  progress 46.98. s201: rule 51.98, even 50.79, edge 52.14, progress 53.81. Progress - even = +3.10 / +3.02, edge - even =
  +3.33 / +1.35. A possible reason (suggested): the progress drive spent about 4% of practice on COUNTIF and 0-0.4% on IF,
  kinds with no training-row form, where even practice spends 10% each.

**P3 (one change from P2): the extra's value comes from the sheet tool instead of the model's own answer** (the model
still decides whether and what to add; the tool computes it; so a wanted extra is always right). Legal under deployable
autonomy: the model calls an outside tool. Same models, heads and rules as P2; HELPER's V learns from the new rewards.
New sealed sessions, person seed 93004 (400), with P2's HELPER rerun on them for the paired comparison.
| Mark (each seed) | Pass | Proved wrong |
|---|---|---|
| P3-1 helps | HELPER-TOOL - NONE <= -0.10, interval upper end < 0 | interval lower end > -0.05 on either seed |
| P3-2 beats P2 | HELPER-TOOL - P2 HELPER <= -0.15, interval upper end < 0 | (reported) |
P3 PASSES when both pass on both seeds. Reading fixed now: a pass shows the helping machinery works once unasked work is
checked, so the shipped form is "compute or check unasked work with a tool before offering it"; it does not show the
model's own skill is enough.

**M2 (confirm, 6 paired runs): does the "progress" motivator beat even practice?** One change: practice chosen by the
progress drive (motivator.py `--drive progress`, constants unchanged) instead of even shares (`--drive even`).
- Pairs: parents T1SDR s200 and s201, each with run seeds 300, 301 and 302 (6 pairs). R1's s200/s201 runs are excluded:
  they produced the hypothesis. Fixed horizon: exactly 8 nights (`--nights 8`), sheet tool, v7 constants.
- Statistic: mean sealed near (sheet.v2, 420 questions) over nights 6, 7 and 8, per run; difference progress - even per pair.
- PASS: mean difference >= +3.0 points, paired t 95% interval lower end > 0, and positive in at least 5 of 6 pairs.
  PROVED WRONG: mean difference <= 0. Between: no difference. DM3 (old skills) reported for every run.
- Reported: practice share on COUNTIF, IF and MOD per arm (the suggested mechanism), and edge is not run (one change).
- If PASS: the progress motivator is proposed (via the coordinator) to replace domain mode's hand rule, per Ben's
  "substitute if better"; if proved wrong, the 3M motivator work stops until 10M.
- Where: Ben's Mac (CPU jobs Mac first), 12 runs.
- Note before P3 runs (3:15 AM ET 10-12; no mark changed): per the outside thread's cross-problem note, HELPER-TOOL is a
  ceiling (right by construction), so P3 also reports a pre-registered control, HELPER-GATED: the model answers the
  extra, the tool checks it, and a mismatching extra is never shown (reward 0); the help-value head learns from those
  rewards. This is the deployable form ("check your unasked work before offering it"). Reported only, no mark. The
  suggested even-vs-even A/A pair is not added to M2: its paired t interval over 6 pairs already measures run-to-run noise.

**B17. G-ceiling result (3:40 AM ET 10-12): the guess is readable from the model's state; behaviour adds nothing at 3M.**
Frozen v7 sheet night 4 models, 32,000 fresh questions each (success 0.333 s200, 0.309 s201), 5-fold cross-fit by kind.
Results: `dopamine/results/gc/s20x/RESULT.md` (copies in `/mnt/project-files/dopamine/gc/`). Within-kind AUC:
| probe | s200 2.5k / 8k / 16k / 32k | s201 2.5k / 8k / 16k / 32k |
|---|---|---|
| S900 (state) | 0.637 / 0.662 / 0.696 / 0.703 | 0.656 / 0.685 / 0.690 / 0.704 |
| P (behaviour) | 0.603 / 0.603 / 0.594 / 0.594 | 0.563 / 0.568 / 0.568 / 0.567 |
| S900+P | 0.638 / 0.662 / 0.696 / 0.703 | 0.653 / 0.684 / 0.689 / 0.704 |
| length only | 0.599 / 0.587 / 0.575 / 0.575 | 0.580 / 0.580 / 0.574 / 0.571 |
| diagnostic (never shipped) | 0.590 / 0.568 / 0.562 / 0.562 | 0.568 / 0.562 / 0.565 / 0.564 |
- Marks (B15), both seeds: "Drift is a main limit" HOLDS (0.637 vs 0.593 needed; 0.656 vs 0.647). "Readable with enough
  data" PASSES (S900 0.696 / 0.690 at 16k). "Behaviour beats state" does not hold (P 0.59 / 0.57, below S900 at every
  size; adding P to S900 changes nothing). PROVED WRONG does not hold. Shown.
- Brier: S900 beats the frozen model's own per-kind rate from 8k rows on (32k: 0.1538 vs 0.1698 s200, 0.1252 vs 0.1397
  s201) but is worse at 2.5k (0.2001 vs 0.1744; 0.1625 vs 0.1370): 900 inputs on 2,000 training rows is overconfident.
  Shown.
- Checked: none of the 32,000 questions was a practice prompt of its run (0 overlap with the 10,091 / 10,830 logged rows),
  so the signal is not "I trained on this one". Shown.
- Reading (suggested): at 3M the model's state does carry "will I get this one right" within a kind, worth ~0.70 AUC once
  the head has ~16k rows from the same model. D0 failed (0.54 / 0.60) because its rows came from earlier, different
  models (drift) and there were few of them, not because the signal is absent. The "answer quickly and slowly, trust
  agreement" idea is not supported at 3M; the shipped head stays a reader of state. Untested: whether the 0.70 is the
  model knowing itself or the head reading question difficulty from the reader; for helping and practice either is useful.
- Decision: the guesser's rows should come from the model as it is now, not from past days. Next test, G-transfer below.

**G-transfer (no training; marks sealed 3:45 AM ET 10-12, before any code).** One change from D0: the head is fit on a
nightly self-quiz of the current model instead of on past days' practice. Question: does a head fit on fresh, even-share
self-quiz rows rank the real practice tries of the next day (the drive's mix) within kind?
- Runs: v7 sheet s200 and s201 (D0's runs). For each day d = 2..N that D0 scored: the model that tried day d (night d-1)
  answers 8,000 fresh questions (make_practice, even share, the run's constants, own seed per day, the run's quiz and all
  logged practice prompts excluded), tool-labelled, never trained on. Fit S900 (D0's fit_logistic, C = 1, standardised)
  on those; score day d's logged practice tries (the same rows D0 scored, features by D0's own pass).
- Baseline, same rows, same script: D0's walk-forward S900 (fit on days < d); must reproduce D0's 0.543 / 0.597 within
  0.01 or both numbers are reported and the run is not judged.
- Statistic: within-kind AUC pooled over days 2..N, groups = day x kind with >= 10 right and >= 10 wrong, row-weighted.
| Mark (each seed) | Holds when |
|---|---|
| PASS | self-quiz head >= 0.62 and >= baseline + 0.05 |
| PROVED WRONG | self-quiz head <= baseline + 0.01 on either seed |
  Reported: Brier vs the self-quiz's own per-kind rate and vs D0's K; the same head fit on 2,500 of the 8,000 rows.
- If PASS: the shipped guesser is a read-only head refit each night on a self-quiz of the current model (a fixed routine:
  the model's own checked tries, never trained on), and D1 ("go where the surprises are") becomes testable again with its
  own marks. If PROVED WRONG: the signal does not carry to the real practice mix; within-kind guesser work stops at 3M and
  this pair (G-ceiling, G-transfer) reruns on the first 10M checkpoint.
- Where: the cloud box after P3 (free; the Mac is on M2 and the Game world runs). About 0.03 s per question, so about
  5 minutes per day per seed.
- G-transfer code details fixed before the full run (3:46 AM ET 10-12; no mark changed): `dopamine/g_transfer.py` sha256
  d7751963850... D0's G head reads reader mean + pooled state only (899 inputs, `d0_guess.py` line 214), and that is the
  head that gave 0.543 / 0.597, so the baseline is that head; the self-quiz head is S900 (adds the talker confidence) as
  sealed. Like-for-like pairs are reported (self-quiz on 899 inputs; walk-forward on 900); if either pair would flip the
  verdict, the result is called "not clean" and both are given. Smoke (s200, days 2-3, 300 questions): 0.041 s per
  self-quiz question, so about 5.5 minutes per day; overlap checks with the quiz and every logged prompt passed.

**B18. P3 result (3:52 AM ET 10-12): helping unasked saves effort once the unasked work is checked. PASS, both seeds.**
Same frozen models and heads as P2, new sealed person seed 93004 (400 sessions, 3.03 requests each), code sha256
64b77011... (the committed `dopamine/p1_sessions.py`). Results: `dopamine/results/p3/s20x/RESULT-P3.md`. Mean actions
per session (lower is better):
| Arm | s200 | s201 |
|---|---|---|
| NONE (never helps) | 3.030 | 3.030 |
| HELPER-TOOL (P3: tool computes the extra) | 2.595 | 2.528 |
| HELPER-GATED (model answers, tool checks, wrong ones hidden; reported) | 2.809 | 2.758 |
| P2 HELPER (model's own answers shown) | 3.186 | 3.050 |
| EAGER-TOOL (always adds the top guess, tool computes it) | 2.475 | 2.466 |
| ORACLE | 1.730 | 1.730 |
- P3-1 HELPER-TOOL - NONE: -0.435 [-0.513, -0.358] s200, -0.502 [-0.581, -0.423] s201: PASS.
- P3-2 HELPER-TOOL - P2 HELPER: -0.591 [-0.697, -0.489], -0.522 [-0.617, -0.426]: PASS. Shown.
- Reported, no mark: HELPER-GATED - NONE -0.221 [-0.278, -0.164], -0.272 [-0.338, -0.207]. The deployable form ("check
  your unasked work before offering it") saves about 7-9% of the person's actions; showing unchecked work (P2) saves
  nothing or costs. Shown.
- Reported, not expected: EAGER-TOOL beats HELPER-TOOL (2.47 vs 2.60 / 2.53): once extras are always right, an unwanted
  one costs only 0.25 and about 41-44% of extras are wanted, so acting more often pays and the help-value head is too
  cautious. This depends on the 0.25 cost, a design number not measured on people (untested). The ceiling is far off:
  the perfect helper saves 1.30 actions, HELPER-TOOL about a third of that.
- Reading fixed in B16: the helping machinery works once unasked work is checked; it does not show the model's own skill
  is enough. Decision: the FINISHED-MODEL helping item gains one line, "unasked work is computed or checked by a tool
  before it is offered; a mismatch is never shown" (sent to Architecture via the coordinator). No more P tests at 3M; the
  P2 rule and HELPER-GATED rerun on the first 10M/30M sheet models, where the gated arm is the one that counts.

**B19. G-transfer result (5:20 AM ET 10-12): a head fit on a nightly self-quiz ranks the real practice. PASS, both seeds.**
`dopamine/results/gt/s20x/RESULT.md`, code sha256 d7751963850... Pooled over days 2..N, 38 day x kind groups each:
| head | s200 within-kind / Brier | s201 within-kind / Brier |
|---|---|---|
| self-quiz, 8,000 rows (S900) | 0.642 / 0.2016 | 0.671 / 0.1902 |
| self-quiz, 2,500 rows | 0.607 / 0.2365 | 0.628 / 0.2261 |
| D0 walk-forward (baseline, reproduced exactly) | 0.543 / 0.2844 | 0.597 / 0.3051 |
| per-kind rate, past days (D0's K) | 0.500 / 0.2556 | 0.500 / 0.2735 |
| per-kind rate, self-quiz | 0.500 / 0.2050 | 0.500 / 0.2037 |
- PASS (>= 0.62 and >= baseline + 0.05) holds on both seeds (+0.099, +0.074); PROVED WRONG does not. Like-for-like pairs
  (self-quiz on 899 inputs 0.641 / 0.671; walk-forward on 900 inputs 0.543 / 0.597) give the same verdict: clean. The
  self-quiz head also beats the self-quiz per-kind rate on Brier, pooled (0.2016 vs 0.2050; 0.1902 vs 0.2037), so
  D0's original pair of marks (>= 0.65 within kind and Brier below K) is met on s201 and missed by 0.008 on s200. Shown.
- Rows matter: 2,500 self-quiz rows lose 0.035-0.045 within kind (consistent with G-ceiling). The self-quiz is answered
  on the even mix (14-45% right) and transfers to the drive's mix (19-58% right). Cost at 3M: 0.024 s per question at
  2 threads, about 3 minutes per night for 8,000, plus about 2 minutes drafting. Untested: the cost at 100M.
- Decision: the shipped guesser recipe is a read-only S900 head refit each night on a self-quiz of the current model
  (about 8,000 fresh checked tries, never trained on, a fixed routine); the FINISHED-MODEL guesser line is updated via the
  coordinator. The motivator's own head (`motivator.py`: reader-only, fit on the run's quiz) is the weaker recipe; swapping
  it for this one is the next motivator change, but only after M2 reads: if M2 shows practice choice does not matter at
  3M (proved wrong), the swap waits for 10M with the rest of the motivator work. D1 as sealed in section 7 is not run
  (its guesser was the drift-prone one).

**B20. Ben's ask "a model that truly wants to help and to learn" (9:30 AM ET 10-12): outside opinions, the case, and two
sealed tests (marks sealed 10:00 AM ET 10-12, before any code).** Ben: "I want it to really be like an inherent
motivator. Like the model truly wants to be a good helper and to learn. I want those two things to be rewarded with
dopamine." Papers: `/mnt/project-files/papers/inherent-motivator-papers-2026-10-12.md` (two Haiku readers, 24 papers).
Outside answers (batch, $0.93): `/mnt/project-files/api-opinions/answers/7-motivator-{fable,opus}.md`, brief
`reviews/api-inherent-motivator-2026-10-12.md`. Hypotheses only; checked here.
- Both answers agree (suggested, and I agree): today nothing in the model "wants" anything. Dopamine d = r - V is a
  teaching signal, and no learned choice is trained by it; every choice is our formula (edge, progress) or our threshold
  (help value > 0). Buildable meaning of "wants X": a learned choice head whose weights move only by d computed from a
  checked X outcome, so its choices follow X when X moves and fade when the reward is shuffled.
- Learning should be rewarded as checked per-kind progress on a self-quiz the model neither writes nor picks; never as
  prediction error (noisy-TV, arXiv 1808.04355), never as change in V. Helping stays checked effort saved; praise never
  reaches the reward. One currency later: learning valued as future checked help (weight progress by how often the
  person asks for that kind).
- Both: the current practice bed (1,024 problems over 10 kinds) cannot tell motivators apart, because even practice lifts
  every learnable kind; a fair test needs a bed where choosing matters. Opus: qualify the bed first with a yardstick.
- Opus, checked against B16/B18: P3's checked form saved effort only because our harness hid wrong extras; that gate is
  our rule, not the model's choice. A learned help chooser that decides itself whether to use the tool is the step that
  makes helping the model's own.
- Not adopted now: a meta-learned intrinsic reward (LIRPG, arXiv 1804.06459): too few outer samples (one sealed score per
  night, 8 nights per run). Noise kind and composite kinds in the bed: need tool changes; skipped in the first bed.
- Cited papers not in the Haiku sheet, IDs checked from memory only: Graves et al. 1704.03003 (learning-progress bandit
  curricula), Matiisen et al. 1707.00183 (teacher-student curricula), van Seijen et al. 1706.04208 (per-component value
  heads), Jiang et al. 2010.03934 (prioritized level replay), Schmidhuber 0812.4360 (compression progress).

**BQ: does a scarce-practice bed let practice choice matter at 3M? (yardstick, no learned part, never shipped)**
One change between arms: practice shares. EVEN = even over all 10 sheet kinds. INFORMED = even over the 7 kinds the
sealed panel scores (SUM, MAX, MIN, PRODUCT, cell arithmetic, division, ABS), none on MOD, COUNTIF, IF; picked with
hindsight, so it only measures headroom. Both arms: practice budget 256 problems per night instead of 1,024 (the bed),
parents T1SDR s200 and s201, run seed 310, exactly 8 nights, sheet tool, v7 constants otherwise, `dopamine/motivator.py`.
- Statistic: mean sealed near (sheet.v2, 420 questions) over nights 6-8; INFORMED - EVEN per parent.
- PASS (the bed has room for a chooser): >= +5.0 on both parents. NO ROOM: <= +2.0 on either parent. Between: one retry
  at 128 problems per night with the same marks; if that is not a PASS either, 3M cannot test practice choosers and the
  practice actor waits for 10M (M2 stays the 3M word on practice choice).
- Reported: per-kind near, DM3 (old skills), seconds per night.
- If PASS, next (marks sealed before its code): PA-1, a learned practice chooser (small MLP over per-kind features: recent
  self-quiz accuracy and progress, mean V, share; softmax shares with a 2% floor and entropy bonus; trained nightly by
  REINFORCE with advantage = checked self-quiz progress minus a learned critic's prediction) vs EVEN in the bed, plus a
  shuffled-reward placebo arm. The reward is computed by the night routine from tool verdicts on a self-quiz the chooser
  cannot pick.

**H-1: a learned help chooser that reads the person and decides itself whether to use the tool.**
Same frozen 3M sheet models and next-need head as P3; scripted person as P3 except one environment change for every arm:
each session's person is "easygoing" (unwanted extra costs 0.25) or "tidy" (costs 1.0), 50/50, never told to the helper;
and the person says "thanks" on 30% of rounds at random (changes no reward). Actions per round for the chooser: stay
quiet; add N's top guess with the model's own answer; add it with the value computed by the sheet tool (costs 0.02 of an
action per call). Chooser: a small MLP on [N's top probability, reader mean of the candidate, round, extras accepted and
rejected so far this session, "thanks" last round]; actor-critic (advantage = reward - learned critic), entropy bonus,
trained over 20 days x 150 sessions (person seed 93006; constants fixed in the code before the run), then frozen. Sealed:
400 new sessions, person seed 93005.
| Mark (each seed, paired bootstrap over sealed sessions) | Pass | Proved wrong |
|---|---|---|
| H1-1 beats the hand helper | CHOOSER - HELPER-TOOL (P3's rule, help value > 0, value from the tool) <= -0.10 actions, CI upper < 0 | CHOOSER - HELPER-TOOL >= 0 on either seed |
| H1-2 reads the person | CHOOSER - EAGER-TOOL <= -0.05, CI upper < 0 | (reported) |
| H1-3 not bought by praise | offer rate after a "thanks" round within 3 points of after a plain round | gap > 5 points |
| H1-4 checks its own work | >= 90% of the chooser's shown extras used the tool | (reported) |
H-1 PASSES when H1-1, H1-2 and H1-3 pass on both seeds. Reading fixed now: a pass shows the model can learn, from checked
effort alone, both whether to help this person and to use the tool for unasked work; it does not show anything about
real people. Reported: NONE, EAGER-TOOL, HELPER-TOOL, CHOOSER, ORACLE effort per person type.
