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
