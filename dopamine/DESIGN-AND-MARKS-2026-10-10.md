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
