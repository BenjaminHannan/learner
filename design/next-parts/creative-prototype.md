# Creative prototype: design v2 (worker try, varied candidates, checker, verified experiences)

Written 2026-10-03, replacing v1 of the same day after a full review. Design only: nothing was trained, run on a GPU, or
bought. No reserved, blind or consumed evaluation panel was opened.

How v2 was made: three independent Opus reviews (a critic of v1, a from-scratch design, and a CPU-only maths study that
drove the real calculator tool code) were merged into a draft. A fourth Opus pass checked the draft and found five
must-fix problems. A fifth Opus pass re-checked the fixes and found three more (the interval method, a stop gate before
the test set is spent, and an undefined persistence block) plus smaller issues. All are applied below. Reports are in
`creative-prototype-notes/`.

Sources: **v6** = the integrated design doc text (commit c5cfd9176 on `claude/premonition-launch-recovery-96c708`; the
brief calls it v5), **C.json** = `docs/premonition-status/CURRENT.json` on that branch, **code** = the calculator
pipeline on branch `claude/critical-thinking-data-128-outputs` (`data-for-design/critical-thinking-128/pipeline_code/`),
**PR23** = the critical-thinking reasoner design (PR #23), **maths** = `creative-prototype-notes/math/math-report.md`,
**check** = `creative-prototype-notes/v2-check.md`, **recheck** = `creative-prototype-notes/v2-recheck.md`.

Labels: **shown** = read in code, a checked result, or the cited doc. **suggested** = reasoning or literature.
**untested** = a plan or guess nobody has measured. Small card experiments and the village model play no part here. The
older number-puzzle work used a different model (MiniCPM5-1B with LoRA) and is cited only as a hint.

## 0. Summary for Ben

We give the model small number puzzles like "use 14, 9 and 30 once each, adding or subtracting, to make 35". A checker
can tell if an answer is right without an answer key, by redoing the steps. The model tries each practice puzzle 32
times, keeps its right answers and practises on them. Then we test on puzzles it has never seen. We compare it with the
same model with no practice, and with a copy that practised on the same number of its own rule-following tries, picked
without checking the answer. It counts only if the trained model wins by a fixed margin (10 points over no practice, 8
over that copy) and also hits its own target more often than a twin puzzle's target (same numbers, different target).
That last test shows it uses the target, not just the puzzle's rules.

Words used below: a **candidate** is one complete try (the list of calculator steps). **Luck** is the share of tries
that are right. **Seed** is one training run with its own random start; we use 3 per arm (5 if the power check in the
first CPU step says 3 are too few).

Why puzzles instead of the word problems: in today's word problems the model's calculator step is picked before it
speaks, a two-number problem has only two usable results, and all 128 of its saved answers came from a shelf of 27
numbers it saw in training (shown). Trying many times there gives no real search to learn from.

What it cannot show: with adding and subtracting, nearly every puzzle has exactly one real answer, so "creative" here
means finding it more often, not inventing many answers. A program that tries everything always wins; the claim is
about learning, never about beating search. It does not fix the talker's number shelf.

Choices made for you under your autonomy note (you can overrule any before the pass marks are sealed): the new puzzle
family; sampling the reasoner's step choices for extra tries; training the weights now because there is nowhere to put
examples in context yet; replaying saved steps exactly during training; no final-answer loss on puzzle rows; 10 rows per
update; a starting checkpoint picked by a rule that uses no test score; a control trained on solver answers; gold-step
training on new word problems for the persistence test only. Cost: about 2.5 to 4 GPU hours on your PC for the main
run, plus 1 to 2 hours for the persistence test if it runs, plus a replication; about 1.5 hours more if seeds go to 5.
$0 (untested estimates). The CPU parts can be built now.

## 1. What v1 got wrong, and what v2 keeps

| # | v1 flaw (severity) | Evidence | v2 fix |
|---|---|---|---|
| 1 | Fatal: LM temperature as the variation source | Action and pointers are argmax per loop before the LM decodes (code, `calculator_runtime_depth_compare.py`, `forward`) | Sample the call heads (section 3) |
| 2 | Fatal: arm D (gold on the same problems) | With one correct call, every accepted trace is the gold trace, so B equals D (suggested from code) | Puzzles checked without a key; a solver-trained positive control (section 8) |
| 3 | Fatal: answer-shelf confound | All 113 wrong finals were training answers; 0 of 64 off-shelf answers right (shown, PR23 F1) | Puzzles are scored on the call trace, not the talker's number |
| 4 | Fatal: no chance floors | Random calls on 2-number word problems saturate pass@32 (94% to 99.7%, computed, maths) | Exact uniform and rules-only floors (section 5) |
| 5 | Fatal: arm C1 trained on wrong answers | Harm training; v6 "do not distill known mistakes" | Rule-valid, value-blind placebo R (section 8) |
| 6 | Major: in-context arm E | The calculator path has no example slot; its 8 notebook slots are the 4 tool pairs (shown, code) | Deferred until a context path exists (section 12) |
| 7 | Major: diversity adjustment, per-problem cap | Meaningless when all accepted traces are identical | Coverage guard; variety by sign pattern |
| 8 | Major: two working checker states | v6 asks for accepted / rejected / unresolved | Three defined states (section 6) |
| 9 | Major: recipe misdescribed | Trainable parts are core, reader, prefix and tool; loss is final CE plus call CE (shown, code and v6 l.80) | Recipe stated and every change flagged (section 7) |
| 10 | Major: leaned on the "40 calls, 2 of 6 rescued" diagnostic | No receipt; the execution owner has no record (10-03) | Not cited as evidence; a sealed probe instead (section 11) |
| 11 | Major: no retention after intervening learning | v6 l.187 | Q2 with a defined, sealed intervening block (section 9) |
| 12 | Minor: statistics | Ratios on pooled samples, arms treated as independent | Seed-level t intervals on paired scores, ordered verdicts, a stop gate before the test set is spent |

Kept from v1: gold scoring is not live verification; fresh sets drawn by the certified generator from number sets
disjoint from practice, sealed by hash before any GPU stage, audited by a separate agent, and touched once per arm;
choices made on DEV, never on fresh sets; consumed panels block-listed; marks fixed before running; typed calls as
training targets, never free-text rationale; planted-violation tests for the checker; one round only; a failure table.

## 2. Facts that drive the design

- Each loop the action head (`Linear(256,3)` over the mean of h+e at question positions) picks NONE, ADD or SUB, and two
  bilinear pointer heads pick ordered references among the question's integer literals and earlier OK results. The
  runtime takes argmax. The tool runs, its result goes into a reserved value/status slot, and the core advances. Four
  loops always run (numbered 0 to 3 below, as `loop_index` in the code). After the fourth advance, `read_latent` feeds
  the prefix and the frozen LM decodes greedily (shown, code). The 8-vector prefix comes from v6 and the brief; the
  prefix module is not in the calculator code.
- So a complete call trajectory exists before any LM decoding; producing it touches the LM only through the cached
  question features and each result token's embedding (shown, code).
- Tool limits: exactly two distinct references per call, at most 8 literals and 3 prior results, at most 4 calls. A
  result enters only if it is one canonical numeric token (shown, code). In the public LFM2.5 tokenizer every integer 0
  to 999 is one token and no negative is (computed, maths), while v6 says "two-digit" results; checked on the PC in S0b.
- Training: trainable modules core, reader, prefix, tool (shown, code). Loss: final-answer CE plus averaged call CE.
  Training executes the model's own predicted calls and targets the correct call until it succeeds, then NONE (shown,
  v6 l.80). One teacher-forced example per optimizer update; about 0.41 s per update (shown, check citing C.json and
  the audit script).
- Calls fired at loop 0 in 127 of 128 consumed-panel outputs (shown, C.json and the data-branch README).
- v6 on creativity (shown): plain sampling is the first baseline; experiences count when they later improve the
  worker; replaying rescued questions is not method learning; clean restarts; rejected guesses never become context;
  no hit means no signal; checks must match the claim; restricted formal tasks may provide goal predicates; context
  reuse first, then an adapter, then replay, each needing fresh transfer and retention.
- C.json (shown): the approved curriculum is not yet admitted; `new_worked_example_supervision_authorized` is false;
  `checkpoint_selection_authorized` is false for the terminal panel; `new_Premonition_GPU_dispatch_allowed` was false at
  11:44 UTC (Ben then gave the PC GPU to Premonition at about 12:00; the execution owner's record decides).

## 3. The candidate and how it varies

A **candidate** is the full four-loop trajectory: per loop the (action, left, right) choice, the tool status and result,
and each choice's log-probability. For puzzles the trajectory is the solution ("14+30=44, 44-9=35, NONE, NONE").

| Variation source | Changes the calls? | Verdict |
|---|---|---|
| LM decode temperature | No (calls are fixed first) | Wrong lever (shown) |
| Sample action and pointers from softmax(logits / tau) each loop | Yes | **Used** for the explorer (flag F1) |
| Latent noise, multi-start; a separate explorer network | Yes | Later, one at a time |

The worker attempt stays argmax. Each candidate starts from a clean `begin_latent`; no candidate sees another or a
verdict (shown, code). Sampling uses uniforms drawn in advance per (puzzle, sample, loop, head), so every arm sees the
same random numbers (common random numbers). The sampler uses its own generator and never touches the global torch
RNG, which the eval runner checks (shown, code, per recheck).

## 4. Why puzzles, and what word problems can and cannot show

**Word problems (shown, code; computed, maths).** With two literals, the first loop has 9 head combinations; 4 are
duplicate-reference errors and the 4 valid calls give 3 distinct values, one of them negative, which the runtime returns
as an error, so 2 results are usable. With the real heads sampled independently a
random try picks the exactly right call 1 time in 12 (1 in 6 if the two pointers are drawn as a pair), so within 32
tries the call is found 94% to 99.7% of the time. With the answer key as checker, keeping the hit and training on it
equals the gold-call training the recipe already does. Without the key, the calculator cannot tell 18-7 from 18+7
(v6 l.165), so every guess is unresolved. The final number is capped by the shelf (PR23 F1).

**Make-the-target puzzles (decision D1; default yes).** "Use A, B and C, each exactly once, adding or subtracting, to
make T." Why this tests the idea honestly (suggested): the checker needs only the problem, which v6 names as deployable
for restricted formal tasks; luck is far from saturated (0.54% per uniform try on 3 numbers, computed); the graded
object is the call trace, so the shelf cannot fake a result; it exercises composition and pointers to earlier results,
which the protocol supports but no experiment has tested (v6 l.80). Why it is not "unrelated generated data" (judgment):
same reader, core, heads, calculator, loop budget and result slots, and v6 l.66's generator rule. If Ben says no, run
only the word diagnostic (section 11).

**Honest limit (computed, maths).** With add and subtract, a solution is a plus or minus for each number; 97 to 100% of
puzzles have one sign pattern; the other "solutions" are re-orderings. An exhaustive solver is used only to certify
puzzles, count solutions and compute floors, never inside the loop.

## 5. Puzzles: rules, tiers, floors

**Acceptance rule STRICT (one definition; computed in maths and checked against the real tool).** Take the OK calls in
loop order. They must form one expression tree that uses every given number exactly once as a leaf (by literal id,
never by value), uses each intermediate result exactly once later, and never uses the target literal (it is in the
question and pointable). The last OK result equals the target. NONE and ERROR loops may appear anywhere (an ERROR makes
no result). Rejection reasons: no OK call, wrong final value, a number unused or reused, the target literal used, an
intermediate result unused or used more than once.

**Training form.** Accepted runs whose OK calls fill the first m loops (`loop_index` 0 to m−1; m = numbers minus 1),
followed only by NONE. Accepted
runs in any other form count as hits for scoring but are never trained on (their count is reported).

**STOP-rule luck** (used by G2): the share of tries accepted when every loop after the call that first completes a
valid tree reaching the target is ignored (maths STRICT-STOP). It separates finding from stopping. **Also reported:**
the **rule-valid** rate (a valid tree using each number once and not the target, any final value).

**Tiers** (results assumed 0..99; random policy = uniform action, then uniform ordered pair; computed, maths):

| Tier | Rule | Distinct puzzles | Uniform hit per try | pass@8 | pass@32 |
|---|---|---|---|---|---|
| W warm-up | 2 numbers, 2..60, target a+b (if at most 99) or larger minus smaller, target not a given number | 3,283 | 6.51% | 37.1% | 75.0% |
| P practice and main test | 3 numbers, 2..40, solvable, target not a given number, no 2-number shortcut | 33,670 | 0.544% | 4.24% | 15.6% |
| T transfer | 4 numbers, 2..60, solvable, no 2- or 3-number shortcut | 2,318,380 | 0.0161% | 0.128% | 0.513% |

**Rules-only floor (computed, check).** A policy that has learned only the rules (each number once, chain the first
result into the second call, avoid the target, then stop) and picks operations and order at random hits 14.4% per try
on tier P (pass@8 66.9%); also avoiding negative steps, 25.7% per try (pass@8 85.4%). The fixed policy "add all three"
solves 26.4% of tier-P puzzles. So luck alone cannot show aiming, and pass@8 saturates for a rule-learner. This is why
the primary measure is per-try luck and why the test uses twin targets (below).

If S0b finds results up to 999 are accepted, all floors are recomputed (uniform floors fall 3 to 20% at 3 or 4 numbers).

**Splits, by number set** (the sorted given numbers; every target and wording of one number set stays in one split):
practice 1,024 P; DEV 128 P (64 twin pairs; tau, gates and the seed-spread check only); T1 256 P (main test, once);
T1b 256 P (sealed now for the replication); T2 256 P (persistence test, once); X 128 (64 T-tier plus 64 P-tier in 2
held-out templates; report only). Ten English templates with names and objects, two held out for X; S0b checks that
every rendering fits the 48-token question cap. Numbers in random
order; no other digits in the sentence.

**Twin targets.** T1, T1b, T2 and DEV are built as twin pairs: the same numbers and wording, two targets with different
sign patterns (99.6% of tier-P number sets have 2 or more valid targets, computed, check). Sign patterns are balanced
across each set as far as the pool allows, so "add all three" cannot carry a score. A target-blind policy solves both
twins equally often on average; a policy that aims solves its own target more.

## 6. Checker and acceptance states

- **Accepted:** both checkers find STRICT true.
- **Rejected:** one of the rejection reasons above, found by both checkers.
- **Unresolved:** the checkers disagree, a replay of the logged actions through the stdlib tool does not reproduce the
  logged results, or the run crashed or was cut off. Unresolved counts as no hit and never enters training.

Independence: checker A replays the action list with its own arithmetic, ignoring logged values. Checker B is written by
a different agent from the rules text alone and rebuilds the tree from `operand_references`; it does not use the
generator's solver. Neither shares code with the generator, runtime or training code. The model never sees either. Gate
before any GPU stage: A and B agree on all solver solutions of 500 puzzles from each of tiers W, P and T, on 100,000
uniformly sampled trajectories over those puzzles, and both reject 20 planted violations of each rejection reason
(reused intermediate results included).

## 7. The loop and the learning update

1. Name the worker version V0 (hashes of core, reader, prefix, tool and LM).
2. On each practice puzzle: the worker attempt (argmax), then 32 sampled candidates at the DEV-chosen tau for W's pool,
   then 32 more with different random numbers for R's pool (more for a puzzle if R's pool lacks enough rule-valid
   runs, up to 256; a puzzle still short after 256 is dropped from every arm and reported). Store every candidate with
   its state. Report v6's explorer counts: newly solved puzzles,
   duplicates, unresolved, latency.
3. W keeps at most 2 accepted training-form runs per puzzle (distinct call orders).
4. Train. The recipe changes below are shared by every trained arm and flagged:
   - **F3 full-weight update** of all four trainable parts (core, reader, prefix, tool). This is the replay-style step
     v6 puts last, taken early because no context slot or adapter exists. It is never promoted without S2.
   - **F7 forced replay**: puzzle rows execute the stored calls loop by loop (call CE toward each stored choice, the
     stored choice is executed, its result written), instead of executing predicted calls. Regression test: replaying a
     run's own argmax trajectory reproduces its logits and outputs exactly. TRAIN32 rows keep the original protocol.
   - **F6** final-answer CE weight 0 on puzzle rows (the graded object is the trace); TRAIN32 rows keep the full loss.
   - **F8** 512 updates, each accumulating 8 puzzle rows and 2 TRAIN32 rows (the recipe uses 1 row per update).
     Constant LR 1e-4 (the terminal low-LR value), fresh Adam.

Parent (flag F5): the seed-0/static terminal low-LR checkpoint, chosen by a rule that uses no panel score (stable 32/32
TRAIN finals at all three checks, v6 l.374-376; static input needs no LM forward for reader features; ties go to static
input, then low LR, then the lowest seed). The replication uses seed-1/static on T1b. If a newer worker exists before
this runs, use that named version and redo DEV.

## 8. Arms (the one change: which trajectories the model trains on)

| Arm | Trains on (same puzzles, count, updates and TRAIN32 mix) | Question it answers |
|---|---|---|
| N | Nothing (the parent, sampled the same way) | Plain sampling baseline |
| W | Its own checker-accepted runs | The prototype |
| R placebo | Its own rule-valid runs in training form from R's pool, chosen at random without looking at the value; distinct call orders, as many per puzzle as W keeps | Does aiming at the target matter, beyond learning the rules and to stop? |
| PC positive control | Solver runs in training form for the same puzzles, one drawn at random (fixed seed) per W record (flag F4) | Can this model learn these puzzles at all? |

R is matched to W on rules and shape, so a W win cannot come from learning the format. R keeps hits only at their
natural rate among rule-valid runs (about 26% if the choice among rule-valid trees were uniform, computed; V0's real
rate is measured in S3); if more than half of R's records are also accepted, the placebo is too close to W and the run
stops at the end of S3 (verdict 3). R trains mostly on wrong tries; it is a control that is never promoted, which is how
it differs from v1's harm arm. PC uses solver-made worked examples, which C.json marks unauthorized for the curriculum;
here it is a control only, never a discovery claim.

Seeds: 3 training seeds for each of W, R and PC; N is one parent. The test contract asks for 5 seeds with a 4-of-5 rule;
3 are used only if the power check in S0 shows they suffice; otherwise 5, and then each "every W seed" clause becomes
the contract's 4-of-5 rule. The DEV spread warning below can also add 2 seeds.

## 9. Measures and verdicts (fixed now; sealed by hash in a PASSMARKS file before any GPU stage)

**Primary, luck:** on T1, the share of the 32 sampled tries per puzzle that are accepted, averaged over 256 puzzles, in
percentage points. Arm differences are paired by puzzle (all arms see the same puzzles and the same pre-drawn uniforms).
All scoring of DEV, T1, T1b, T2 and X uses the DEV-chosen tau; the worker attempt is tau 0.
**Intervals** are 95% seed-level t intervals. The seed is the unit; each seed's score is its mean over the split. For W
− R use Welch's interval on the seed means; for one arm, or against N (one parent), a one-sample t interval over the
seeds' paired differences. A bootstrap that resamples twin pairs is reported beside it as a check and decides nothing.
With 3 seeds, a bootstrap that resamples seeds covers only about 80% (computed, recheck), which is why it is not used.
**Aiming (goal use):** per puzzle, the share of its tries that hit its own target minus the share whose rule-valid final
equals its twin's target; averaged over both members of every pair. A target-blind policy scores about 0.
**Secondary:** first try (argmax) twin-pair completion, both members solved, out of 128 pairs.
**Guards:** coverage (puzzles with at least one hit in 32), STOP-rule luck, TRAIN32 (rehearsed in every update, so it
measures harm, not retention).
**Report only:** uniform and rules-only floors, rule-valid rate, each arm's hit rate among rule-valid runs, sign
patterns found, violations by type, loop of first call, X slice, latency.

Marks (means over the seeds of a trained arm):
- **L1** luck: W minus N at least 10 points, every W seed above N.
- **L2** luck: W minus R at least 8 points, every W seed above the R mean, interval above 0.
- **G0** aiming: W minus R on goal use at least 5 points with interval above 0, and W's goal use above 0 with interval
  above 0.
- **G1** coverage: fails only if the upper end of the 95% interval of W minus N coverage is below −2 points (a plain
  "mean W at least N minus 2" rule false-fails 26% of the time at seed SD 5, computed, recheck).
- **G2** finding: on STOP-rule luck, W minus R at least 4 points.
- **G3** no harm on rehearsed items: per W seed, TRAIN32 calls drop at most 1 and finals at most 2.
- **PC gate:** PC minus N at least 10 points of luck and PC goal use above 0 with interval above 0.

**Ordered verdicts** (the first that applies):
1. **Void:** the sampler regression failed, the checkers disagree on any T1 candidate, or unresolved is above 1%.
2. **Inconclusive, cold start:** fewer than 100 tier-P practice puzzles have an accepted training-form run in W's pool.
   Decided at the end of S3, before any training; T1 stays sealed. No remedy in this run (never more seeds); the next
   experiment is hindsight relabelling against R.
3. **Inconclusive, placebo too close:** more than half of R's selected records are accepted runs. Decided at the end of
   S3; T1 stays sealed. Next: a separate R design, registered on its own.
4. **PASS:** L1, L2, G0, G1, G2, G3. Claim: "after training on its own checked solutions, the model aims at the target
   and solves fresh puzzles more often than a matched placebo". Not claimed: transfer, persistence, live verification.
5. **Rules only:** L1 holds, G0 fails.
6. **Sharper but narrower:** L1, L2, G0 hold, G1 fails.
7. **Gain with harm:** L1, L2, G0 hold, G3 fails.
8. **Stopping only:** L1, L2, G0, G1, G3 hold, G2 fails.
9. **Unreadable:** none of 4 to 8 applies and the PC gate fails. The limit is the model; write an outside-opinion
   prompt.
10. **Proved wrong:** the PC gate passes, and the upper end of the 95% interval is below 5 points for W minus R on luck
    and below 3 points for W minus R on goal use. With these intervals the luck clause alone fires 15 to 24% of the time
    at a true effect of 0 and 2 to 3% at a true +5 (computed, recheck), so "not shown" is the usual null outcome.
11. **Not shown:** anything else.

**Secondary marks** (named Q1 and Q2 so they are not confused with stages S1 and S2):
- **Q1 first try:** W minus N at least 8 of 128 twin pairs and W above R.
- **Q2 persistence** (stage S6, only after PASS). One block, applied identically to every W and R seed and to N: 512
  updates of 10 rows each, constant LR 1e-4, fresh Adam, all four parts, the original recipe (predicted calls executed;
  final CE plus call CE). Rows come from 2,048 new single-call ADD/SUB word problems made and sealed in S0, sharing no
  number pair with TRAIN32, the curriculum bank or any panel, and never trained on by any parent (flag F9: gold-call
  supervision on these items, for this block only). Then a process restart, then T2. Weight change = L2 distance over
  core, reader, prefix and tool from the start of the block; if its median over runs is below half the median distance
  W's main training moved, Q2 is "not scored". Outcomes: **kept** if T2 W minus R is at least half its T1 value and the
  interval's lower end is above 0; **loss shown** if the interval's upper end is below half the T1 value; otherwise
  **persistence not shown**. Even with full retention, "kept" reads true only 24% to 65% of the time at real W minus R
  gains of 8 to 15 points with 3 seeds (computed, recheck), so only "loss shown" counts as evidence of forgetting.

**Power (provisional).** L2 alone (3 W seeds against 3 R seeds, 256 puzzles, seed SD 5 points, 8-point mark): false
pass 4.5%, power 91.5% at a real 15-point gain (computed, maths, greedy unpaired model, `part3_rules.json`); a paired
simulation gives 0.2 to 0.7% false pass, 93% power at +15 and 53 to 60% at +10 (computed, recheck). A real 10-point gain
will often read as "not shown". L1's control N has no seed spread, and G0 has no power model yet. S0 re-runs the maths
with these exact rules and intervals and adds a goal-use simulation (paired twins, an assumed goal-use seed SD, a real
+8 goal-use gain). L1, L2 and G0 must each give a false pass of at most 5% and power of at least 80% (at +15 luck, or
+8 goal use), else seeds go to 5 before sealing. The joint PASS is reported from the same simulation.
**Seed-spread warning:** after training, R's seeds are scored on DEV (never a claimed score); if their range (highest
minus lowest) exceeds 19 points, add 2 seeds per arm before T1 is scored. It is a weak warning: at seed SD 5, 6 and 7
it fires 2%, 7% and 14% of the time (computed, recheck).

## 10. Stages and gates

| Stage | What | Gate | Where, cost |
|---|---|---|---|
| S0 | Generator, renderer, canonical form, twin builder, solver, floor calculator, checkers A and B, splitter, store writer; the 2,048 Q2 word problems and the 32 W0 items; power re-run with the section 9 intervals plus the goal-use simulation; seal DEV, T1, T1b, T2, X, the Q2 block and PASSMARKS | None, can start now | CPU, $0 |
| S0b | On the PC: accepted result range; every rendering fits the 48-token question cap with at most 8 literals | S0 tests pass | Windows CPU, $0 |
| S1 | Sampler patch (tau above 0 samples, tau 0 is argmax, private RNG) and forced-replay patch. Regression: tau 0 reproduces the parent's saved TRAIN32 calls and answers exactly; replay test from section 7 | S0b | GPU, minutes |
| S2 | DEV: tau in {1.0, 1.5, 2.0, 3.0}, measuring the share of tries with a second OK call; pick the most accepted (ties go lower). Cold-start gate: an accepted training-form run on at least 10% of DEV puzzles in 32 tries | S1 | GPU, minutes |
| S3 | Explore practice with V0, build both pools and the store, audit the checkers | Starts only if the S2 gate passes; otherwise stop with T1 sealed (verdict 2). **Stop gate at the end of S3, before any training:** at least 100 tier-P practice puzzles have an accepted training-form run in W's pool, and at most half of R's selected records are accepted. If either fails, stop before S4 with T1 sealed (verdict 2 or 3) | GPU, about 25 to 50 min |
| S4 | Train W, R, PC, 3 seeds each; DEV seed-spread check | S3 stop gate and audit clean | GPU, about 75 to 110 min (from C.json step timings) |
| S5 | Freeze T1 outputs for all arms, then score | PASSMARKS hash unchanged | GPU, about 30 to 60 min |
| S6 | Q2: intervening block for W, R, N; restart; T2 | Verdict PASS | GPU, about 45 to 120 min |
| S7 | Replication on seed-1/static with T1b | Verdict PASS | as S3 to S5 |

Timings other than the measured per-update cost are untested estimates (recheck `cost.py`): S1 to S5 about 2.5 to 4
hours, S6 1 to 2 hours, about 75 to 110 minutes more if seeds go to 5. W0 (section 11) runs once after S1 in minutes. S0
and S0b touch no checkpoint or panel and can run any time. GPU stages go through the single execution owner after the
English pilot and the curriculum, per Ben's priority order and the owner's current GPU record. New outputs go to new
folders; parents are copied, never changed.

## 11. Word problems: a diagnostic now, a separate test later

**W0 diagnostic (inference only).** On 32 new single-call word problems made in S0 (never a panel), half with answers on
the 27-number training shelf and half off it, run once after S1: (a) force each possible first call, then greedy; (b)
greedy calls with 32 LM-temperature samples of the final number. Predictions sealed now (suggested): off-shelf rescues
by (b) at most 2 of 16; final right after a forced right call at most 30% on off-shelf items. If off-shelf rescues reach
8 of 16, the shelf reading is wrong and word problems get their own creative test sooner. Every acceptance is labelled
"known-answer", never "verified". This replaces the unreceipted "2 of 6 rescued" figure.

**E2, a later separate experiment (sketch, untested).** Single-call ADD/SUB word problems with one or two distractor
numbers (24 programs at 4 literals). Known-answer acceptance with the three states and the Mira gap reported. Arms:
A (none), C2 (more practice on known items), B (own search-selected), G-rand (answer-key labels on an equal number of
random misses), G-all (positive control). Primary: per-try correct-call rate, chance-corrected and paired by problem;
final answers split into on-shelf, newly trained and never seen. Claim ceiling: "learning from search-selected,
key-checked labels improves fresh call choice". Gate: after PR23 C1 or the curriculum shows the talker can say off-shelf
numbers.

## 12. Experience store and the hand-off to sleep replay

One JSON line per candidate, append-only, plus a per-round manifest. Fields: schema; record id; family; instance key
(hash of canonical form and rules version); number-set key; split; problem text, template and canonical form; question
token ids and literal registry; per-loop steps (action, refs, status, value, token id, log-probability); acceptance
state, the claim it establishes ("last OK result equals target under STRICT v1"), checker A and B hashes and agreement,
reason code, training-form flag; provenance (worker version hashes, source worker or explorer, pool W or R, tau, sample
index, seed, runtime, generator, time); eligibility (positive replay yes or no, consumed panel no).

Fit to the PR23 section 6 Workspace contract (suggested): question tokens are role 0, modality 0, column = token
position; each tool result is role 3 with time = its arrival. When a context path exists, an accepted record renders as
role 2 (example), row = example index, with the trace as text ("14 + 30 = 44 ; 44 - 9 = 35"). Provenance is never an
input feature. A context-reuse arm then becomes the next one-change test, in v6's order.

For sleep replay: accepted records only, deduplicated by (instance key, canonical tree); rejected and unresolved kept
apart; consumed panels never eligible. Hindsight relabelling ("a valid tree that made 22 solves make-22") must check the
relabelled puzzle's number set against every test split, which the number-set split makes possible. Old `wins.jsonl`
rows use free-text expression steps (shown, `artifacts/claude-blurt2-20260925/*/wins/wins.jsonl`), so a converter is
needed. Expect gains to stall after about two rounds without new puzzles (suggested, ReST-EM in its setting).

## 13. Failure branches

| Verdict | Next single change |
|---|---|
| Void | Fix the cause and re-score the frozen outputs |
| Inconclusive, cold start | Stopped at the end of S3 with T1 sealed; hindsight relabelling as its own experiment against R |
| Inconclusive, placebo too close | Stopped at the end of S3 with T1 sealed; register a separate R design |
| Rules only | Stop the claim at "learned the rules"; try a second round from W, registered separately |
| Unreadable | Outside-opinion prompt; look at call timing (calls fire at loop 0) first |
| Proved wrong or not shown | Stop this line; record the result |
| Sharper but narrower | Mix R-style breadth into W's data, one change |
| Gain with harm | Lower LR or tool-only update (an adapter stand-in), one change |
| Stopping only | No claim; report the G2 gap |
| PASS, Q1 fails | Luck learned, first try not; second round (expert iteration), registered separately |
| PASS, Q2 loss shown | Hand to the sleep-replay design (retention) |
| PASS, Q2 not shown or not scored | More seeds or a larger block, one change |
| PASS | Replicate (S7) before any claim beyond one parent |

## 14. What this cannot claim

- That puzzle skill helps word problems (X and word transfer are report-only).
- Anything about the talker's number shelf (PR23 C1 and the curriculum own that).
- Known risks (untested): cold start for a 9M core on frozen embeddings; the first call is a linear choice over averaged
  features at loop 0; the parent was trained to stop after one call, so two-call tries may be rare at low tau; the seed
  SD may exceed 5 points.

## 15. Decisions and flags (defaults taken under Ben's autonomy note; Ben can overrule before PASSMARKS is sealed)

| Flag | Choice | Default |
|---|---|---|
| D1 | New task family: make-the-target puzzles in English | Yes |
| F1 | Sample the call heads at inference (explorer only) | Yes |
| F3 | Full-weight update before context reuse or an adapter | Yes |
| F4 | Positive control on solver runs | Yes, control only |
| F5 | Parent: seed-0/static low-LR terminal checkpoint, by a no-score rule | Yes, unless a newer worker exists |
| F6 | Final-answer CE weight 0 on puzzle rows | Yes |
| F7 | Forced replay of stored calls in training | Yes |
| F8 | 10 rows per update instead of 1 | Yes |
| F9 | Gold-call supervision on 2,048 new word problems, for the Q2 intervening block only | Yes, Q2 only |
| Later | Latent noise, call timing, a separate explorer, hindsight relabelling, context reuse | One at a time |

An outside opinion (Astra, or GPT with these tables pasted) on D1 and placebo R before S3 is worthwhile; the prompt is
not written yet.
