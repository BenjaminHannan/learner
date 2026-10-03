# Creative prototype: worker try, varied candidates, checker, verified TRAIN experiences (DESIGN DRAFT)

Date 2026-10-03. Design only: nothing here was run, trained, bought or edited in the repo.
Labels on every claim: **shown** (a sealed result in a named file), **suggested** (reasoning or literature),
**untested** (a plan). "From brief" = stated in Ben's brief to this thread, not checked against a file.

**Reconciliation status (2026-10-03 13:35 UTC).** Checked against `docs/premonition-status/CURRENT.json` and the
integrated design docx (`.../FRESH-TERMINAL-EVAL-PREPARATION-v1/DESIGN-WORKING-v6/Premonition integrated model design.docx`,
commit c5cfd9176 on `claude/premonition-launch-recovery-96c708`; the brief calls it v5). Section 11 lists what
it changes in this design. Optimizer, loss and token-limit details still need a check against the code before any run.

**Rule changes from Ben (12:09 UTC, after this draft was written).** Scaling the reasoner and adding reasoning
depth (more loops) no longer need his approval, and he gave broad autonomy to use judgment where a rule only
technically says no. So V3-V5 (section 2) and extra loops are now allowed in principle. They stay out of the
first run only to keep it to one change; Q2 becomes "which one next", not "may we".

## 0. Plain-language summary for Ben

The model already tries word problems once and gets some right (15 of 128 on the last fresh test, from brief).
This part adds a "try lots of ways" step. On a practice problem, the model writes many complete solutions, each a
little different, because we let the talker pick words with some randomness. A checker program, written by
someone else and locked with a fingerprint, keeps only the solutions that are fully right: right final answer,
and every calculator step really adds up. Those kept solutions become new practice examples. We train only the
parts we are allowed to train (reader, core, prefix), never the talker.

Then we test on brand-new problems nobody has used, written and double-checked separately. We compare against
three "fake treatments": (A) no extra training at all, just sampling; (C) the same amount of training on the
model's wrong attempts, or only on things it already knew; (D) training on the official answers. If training on
its own checked lucky hits does not beat the fakes by margins we wrote down in advance, the idea failed here.

We did something like this before on a different model (a 1B model guessing number puzzles). Its lucky-guess rate
about doubled after practising its own hits, twice in a row, and practising only known answers made its guesses
all the same (shown, but on that other model, so it is a hint, not proof for this one). Its first-try answers
improved only a little and not reliably. So we measure both: luck (how often any of many tries is right) and
first try.

Nothing in this design changes the architecture. A few optional variation knobs would need your OK; they are
listed as questions and the first run does not use them.

## 1. What we already know (do not overclaim)

### 1a. Current architecture (from brief, unreconciled)
- Frozen LiquidAI/LFM2.5-1.2B-Instruct is the output LM ("talker"). A contextual reader feeds a ~9M latent core
  that runs 4 loops over internal vectors; it emits 8 learned 2048-d prefix vectors to the frozen LM. The LM does
  not automatically see the original question.
- Results so far: 15/128 correct final answers on the fresh eval (now consumed, never reused); 86 correct
  calculator calls, 71 of them followed by a wrong final answer; no checkpoint solved both members of a complete
  pair; some TRAIN32 branches reach 32/32 but transfer is unproved.
- Suggested reading of the 71: the model often does the right arithmetic but loses it on the way to the final
  answer. Accepted candidates are exactly examples where it did not lose it, so they are the natural teaching
  signal. Untested.

### 1b. OLD results, shown on a different model, not evidence for the current architecture
Model: plain MiniCPM5-1B with LoRA "sleep"; task: number puzzles ("use each of [4, 7, 8] once with + - * / to make
39"); exact code checker. Files: `artifacts/claude-blurt2-20260925/` and
`design/v3/30-modes/creative-roadmap-2026-09-25.md`.

| Run | What it measured | Result | File |
|---|---|---|---|
| blurt-1 | free guesses right | 2/1800 (T 0.6), 4/1800 (T 1.0); 69-78% used numbers not given | roadmap table |
| blurt-2 rule-keeping guesses | right on DEV misses | 42/1,740 (2.4%) | RESULTS-cpu.md |
| blurt-2 loop, first try after sleep | CPU: 6/127 -> 15, 19 (C 6, 6); GPU: 6/127 -> 13, 11 (C 5, 6) | registered FAIL overall (GPU +6 vs mark +8) | VERIFY-blurt2.md |
| blurt-2p placebo (sleep on wrong guesses) | W 14, 13 vs P 10, 9 (S0 8/120) | FAIL (W-P +4, mark +5); wrong-guess practice gave +1.5 | VERIFY-blurt2p.md |
| blurt-3 luck | lucky guesses of 1,980: 63 -> W 126, 136 vs C 85, 87; puzzles reached 27 -> 38, 38 vs C 3, 4 | PASS | VERIFY-blurt3.md |
| blurt-3r replication | of 2,010: 59 -> W 129, 148 vs C 59, 58; puzzles 29 -> 40, 43 vs C 4, 3 | PASS, replicated | VERIFY-blurt3r.md |

Lessons carried over (suggested for the new model): (i) luck is the measure that moved, first-try answers moved
little; (ii) practising only known answers collapses variety, so a known-answers-only arm is a real placebo and a
real danger; (iii) part of any gain is plain practice (+1.5 in blurt-2p), so a wrong-candidates placebo is needed;
(iv) the checker must reject answers that use numbers not in the problem.
Small card experiments and the village model play no part in this design or its claims.

## 2. Candidate generation and variation

Worker attempt = one greedy pass (temperature 0) of the full pipeline on a TRAIN problem: reader, core (4 loops),
8 prefix vectors, frozen LM writes a trace with calculator calls and a final answer. A candidate is one complete
such trace. Sampling alone is not learned creativity: generation is only the raw material; the learning claim
rests on the trained arms beating the controls (section 4).

| Variation source | Machinery | Needs approval? | First run? |
|---|---|---|---|
| V1 LM decode temperature (and top-p) | existing sampler | No: inference setting, nothing learned or wired differently (suggested) | Yes |
| V2 seed variation of V1 | existing | No | Yes (part of V1) |
| V3 Gaussian noise on the 8 prefix vectors at inference | new perturbation of the reasoning path | **Yes, QUESTION Q2** | No |
| V4 noise on core inputs or initial loop state | changes what the core reasons over | **Yes, QUESTION Q2** | No |
| V5 dropout left on at inference in reader/core | only if dropout exists; changes the reasoning path | **Yes, QUESTION Q2** | No |
| Rephrased prompts, extra loops, longer reasoning | prompt edits / extra depth | Out: prompt-based variation is not asked for; extra depth is forbidden | No |

First run: V1 only. Temperature chosen by a DEV rule fixed in advance (as in blurt-3): try T in {0.7, 1.0}
on a TRAIN-side DEV slice, pick the one with more accepted candidates; ties go to 0.7. Untested.
k = 16 candidates per TRAIN problem (k = 32 for evaluation sampling, section 5).

Why V3-V5 are interesting later (suggested): V1 varies only how the frozen LM words the plan the prefix gives
it. If the prefix itself encodes one wrong plan, temperature may never reach a different plan. V3 would vary the
plan. That is a reasoning-method change, so it needs Ben's yes and its own one-change experiment.

## 3. The checker

### 3a. What it checks (numerical word problems)
A candidate is **accepted** only if all of these hold:
1. **Final answer exact.** Parsed by a fixed parser (one number, units stripped by a fixed list); compared as an
   exact rational to the reference answer. A fixed rounding rule only where the problem says "to the nearest".
2. **Independent recomputation.** The reference answer comes from a solver program written for each family by
   the checker author, and it must agree with the problem author's stated answer. Disagreement removes the
   problem from every split (logged, not silently fixed).
3. **Calculator trace valid.** Every call parses; the checker re-executes each expression with its own evaluator
   (not the runtime calculator) and the recorded result must match; the final answer must equal the result of
   some call or a number stated in the problem.
4. **No invented numbers.** Every operand in every call is a number in the problem, a result of an earlier call,
   or on a short fixed constant list (for example 1, 2, 10, 100, 60, 1000). This blocks lucky answer-only hits,
   the blurt-1 failure (old, shown on a different model).
Answer-right but trace-invalid candidates are logged as **lucky-unsupported**, never accepted, and reported.

### 3b. Gold scoring is not unknown-live verification
This checker knows the answer. So any result here can only claim "learning from checked hits on problems with
known answers". It does not show the model can verify answers to questions nobody has solved. A later rung could
test families that are checkable without the answer (for example "find x" families checked by substituting x back),
labelled untested here.

### 3c. Independence
- Separate author: the checker code, the reference solvers and the fresh problems are written by a different
  thread from the one that writes the generator and training code. (QUESTION Q6.)
- Hash-pinned: sha256 of checker code, solver code and each problem file is written in the pass-marks file
  before any generation. A changed hash voids the run.
- Answers never visible to the model: references sit in a file read only by the checker. Training reads only
  accepted candidate text (the model's own words) and the accept bit. Gold answers reach training only in arm D.
- Splits: TRAIN (practice, generator may see problem text), DEV (a slice of TRAIN-side problems for temperature
  choice only), FRESH (section 5). The consumed 128-output fresh eval goes on a blocklist by text hash and is
  excluded from every split. Reserved user and blind panels are never opened or used.
- Luna word problems (from brief): usable only after independent checking, meaning the checker author's solver and
  a second independent solution agree. Unchecked ones are dropped, not fixed by hand.

## 4. From accepted candidates to training data

### 4a. Format (wins.jsonl-compatible, extends the agreed creative-blurt format)
One JSON line per accepted experience:
`problem_id, problem_sha, problem (text), trace (full candidate text), calls [{expr, result}], answer,
checked_by "creative-checker", checker_sha, temperature, sample_seed, try_index, k, parent_ckpt_sha,
greedy_was_right (bool), split "TRAIN", source "creative-cand"`.
Older rows (`cpu-3/wins/wins.jsonl`, 151 rows) use `problem, rows_used, steps, answer, checked_by, turn_id,
source, tries`; the new rows keep those keys (steps = calls) so the sleep thread's reader still works. Shown
(file read); compatibility with the current sleep code is untested.

### 4b. Dedup and balance
- Dedup within a problem on the canonical call sequence (whitespace stripped, numbers normalised).
- Cap: at most 2 accepted experiences per problem; if more, keep the 2 whose call sequences differ most. Keeps
  easy problems from dominating and keeps variety (lesson ii). (QUESTION Q8.)
- Arm B also keeps the parent's own greedy-right answers on TRAIN (as the old W arm did); both kinds are counted.
- Near-duplicate guard: no TRAIN problem shares template and all numbers with any FRESH problem.

### 4c. Training (rejection-sampling fine-tune)
- Trainable: reader, core, prefix only. Frozen LM. Same loss the current pipeline already uses: next-token loss
  of the frozen LM on the target trace, gradients flowing only into reader/core/prefix (from brief,
  unreconciled). Only the data changes; no new objective, no answer copying, no auxiliary heads, no latent matching.
- Same parent checkpoint, optimizer, learning rate schedule, batch size and step count as the English pilot
  (from brief, unreconciled: the exact values must be copied from the pilot config before registering).
- Exposure matched: every trained arm sees the same number of examples for the same number of steps; short arms
  repeat examples to reach the count (as blurt-3's C did).
- One round only. A second round (sample again from the trained model) is a later one-change step.

### 4d. Hand-off to sleep replay
The accepted file plus a `rejected.jsonl` summary (counts per problem, lucky-unsupported rows) go to the sleep
thread. Sleep decides how to replay them; this part only promises checked rows in the agreed format.

## 5. Arms

All arms start from the same parent; seeds 0 and 1 for every trained arm.

| Arm | Trained on | Purpose |
|---|---|---|
| A control | nothing; parent sampled exactly as at evaluation | plain sampling, no creative training |
| B treatment | parent's greedy-right TRAIN answers + accepted candidates on TRAIN misses | the idea |
| C1 placebo, wrong | same problems, same count, rejected candidates (wrong or invalid trace) instead of accepted | is it just practice on own text? |
| C2 placebo, known only | parent's greedy-right TRAIN answers only, repeated to B's count | is it just rehearsing what it knew? (collapsed variety in old runs) |
| D optional, gold SFT | gold reference traces for the same problems B won, same count | do own hits add anything over the answer key? |

Compute: 4 trained arms x 2 seeds = 8 short fine-tunes plus generation; on BensPC at $0 (QUESTION Q9). No money.

## 6. Fresh evaluation

### 6a. The set
- 256 new problems, written after the TRAIN data is frozen, by the checker author (not the generator thread),
  checked by two independent solutions. Hash-pinned before any arm is evaluated. Never used for anything else,
  touched once per arm.
- Families: F1-F3 = three families present in TRAIN, new instances (64 each, 192 total; built as 96 pairs of two
  variants of one scenario so pair completion can be counted). F4 = 64 problems from a family not in TRAIN
  (different look: for example a rates or unit family if TRAIN has none), reported separately as the transfer check.
- Luna word problems may fill a family only after independent checking (3c).

### 6b. Measures (all on FRESH, all checker-accepted, so lucky-unsupported counts as wrong)
- **Primary L, luck:** 32 samples per problem at the DEV temperature. Report luck rate per k for k in {1, 4, 16}
  with the standard unbiased pass@k estimator, and accepted samples out of 192 x 32 = 6,144. Diversity adjustment:
  a problem's hits count only up to its number of distinct accepted call sequences, so 32 copies of one trace
  count as 1 (blocks the C2-style collapse being scored as luck).
- **Primary G, first try:** greedy pass@1 on F1-F3 (out of 192).
- Secondary: coverage (problems with at least one accepted sample of 32); pair completion (both members solved
  greedy); calls right but final wrong (the "71" pattern; should fall); lucky-unsupported count; F4 versions of
  all of the above; no-harm check on a regression panel the current pipeline already uses (not a reserved panel).

### 6c. Pass marks (fixed now, before any run; numbers are proposals for Ben to accept)
Means are over the two seeds.
- **L1 luck rises:** diversity-adjusted accepted samples, B >= 1.5 x A.
- **L2 the hits caused it:** B >= 1.3 x max(C1, C2), and each B seed beats each C1 and each C2 seed.
- **L3 no collapse:** B coverage >= A coverage.
- **G1 first try:** B - A >= +13 of 192, and B - max(C1, C2) >= +8, each B seed above each C seed.
- **No harm:** regression panel drops no more than 3 points for B.
- Verdict words: L1+L2+L3 = "luck PASS"; G1 as well = "full PASS"; F4 is reported, not required.
- **Proved wrong:** mean B <= mean C1 or mean B <= mean C2 on diversity-adjusted luck. That would mean checked
  hits add nothing beyond practice.
- **Inconclusive:** fewer than 40 TRAIN misses won (problems with an accepted candidate), or A has fewer than 10
  covered FRESH problems, or the two B seeds land on opposite sides of a mark. Inconclusive is reported as such and
  is not a pass.
- D is compared, not marked: D >= B is a finding (section 7), not a failure.

### 6d. Power, honestly (suggested)
With first-try accuracy near 12% (15/128, from brief), one arm on 192 problems has a standard error of about
2.3 points (about 4.5 problems), and a difference between two arms about 6.4 problems. +13 is about 2 standard
errors, so a real +6 point gain can still miss G1. Two seeds is a small sample (the old blurt-2 gain shrank from
+11 to +6 on repeat). Luck uses 6,144 samples but they are clustered in 192 problems, so the problem, not the
sample, is the unit; a 1.5x mark is coarse on purpose.

### 6e. Teaching-to-the-test contract (TEACHING_TO_TEST_CONTRACT.md)
That memo's rules, carried over (suggested mapping, the memo was written for a different memory design):
- Nothing taught contains an answer to a scored query: FRESH text, numbers and answers never enter training.
- Scored items need something the teaching did not contain: new instances, plus F4, a family never taught.
- Touched once: each arm is evaluated on FRESH once; temperature and k are chosen on DEV, never on FRESH.
- Shortcut baseline: a "template-nearest" predictor (apply the most common TRAIN call sequence for the matching
  template to the FRESH numbers) is scored; B's G1 gain must exceed that predictor's gain over A, or the claim is
  "learned family habits", not problem solving.
- Benefit and damage reported separately (no-harm panel).

## 7. Failure branches and decision table

| Outcome | Reading | Next (one change) |
|---|---|---|
| Fewer than 40 TRAIN misses won | generator rarely hits | raise k to 64 on DEV; if still low, ask Ben about V3 prefix noise (Q2) |
| Many lucky-unsupported, few accepted | right numbers by guessing | keep checker strict; report; do not relax rule 4 |
| Luck PASS, G1 fail | same as old model: luck learned, first try not | second round of sampling from B (expert iteration), registered separately |
| Full PASS | both moved | replicate on new TRAIN and FRESH seeds before claiming; then F4 transfer as its own test |
| B about equal to C1 | it is practice on own text | stop; the checked-hit idea is not shown here |
| B about equal to C2, C2 kept variety | rehearsal explains it | stop; record that old collapse did not repeat |
| D >= B | answer key teaches as well | creative loop matters only where no key exists; move to an answer-free checkable family (3b) |
| Seeds split | noise | one replication with new seeds, registered before running |
| No-harm fails | forgetting | hand to sleep thread (retention, standing note 03) before any more creative training |
| F1-F3 pass, F4 fails | no transfer | claim limited to trained families |

## 8. Risks and leakage
- Checker bugs accept wrong traces: the checker author writes a small checker test set with known wrong traces;
  it must reject all of them before the hash is pinned. Untested.
- Generator and checker written by one author share blind spots: separate thread (Q6).
- FRESH overlap with TRAIN or the consumed 128: hash plus template-and-numbers filter; overlaps dropped and counted
  (old runs dropped 14 to 30 per set, shown in the VERIFY files).
- Gold answers leaking into B: training loader reads only accepted.jsonl; a check asserts no field named answer
  from the reference file is present.
- The frozen LM does not see the question, so a trace can be "right" for the prefix's plan but copy numbers
  wrongly; rule 4 catches numbers not in the problem. Suggested.
- Variety collapse (lesson ii) hiding as luck: diversity adjustment and L3.
- Calibration temptation: changing marks after results. Marks are fixed in the pass-marks file with its hash.
- TRAIN32 32/32 is not transfer (from brief); this design never uses TRAIN32 scores as evidence.

## 9. Roadmap placement and hand-off to sleep replay
- Placement (suggested): after the current first-try pipeline is stable enough to have a parent checkpoint, and
  before sleep replay. This part produces checked experiences; sleep replay decides how to keep them without
  forgetting (`design/research/sleep-design-2026-09-28/MAP.md` row 2: model picks what goes into replay,
  including creative wins, never tested on the current reasoner; standing note 03 Lead 2, weakest-first sampling
  of a small store, untested).
- Hand-off: accepted.jsonl (4a) plus rejected summary; sleep can test "replay accepted candidates" against
  "replay gold" with the same arms logic. The old creative rungs (open-problems shelf retried after each sleep,
  restating the problem, pieces library, tools) stay later rungs, one at a time.
- Learned stopping, compressed notes and n-grams are out of scope.

## 10. Decisions and open questions
**Decided 2026-10-03 12:14 UTC** under Ben's broad-autonomy note (relayed by the channel session): every recommended
default in brackets below is adopted, including the pass marks in 6c. Ben can overrule any of them; a change must be
made before the pass-marks file is hash-pinned. Q11 (reconcile with design v5) is still open until v5 lands.

Questions as asked (default in brackets):
Architecture or reasoning-method questions (the first run needs none of them):
- Q1 First run uses only LM sampling temperature for variety? [yes]
- Q2 Prefix or core-input noise (V3, V4, V5) as a later separate experiment? [later]
Design questions:
- Q3 Run both placebos C1 and C2? [both]
- Q4 Include gold-answer arm D? [yes]
- Q5 Fresh set of 256 (192 + 64 transfer)? [yes]
- Q6 A separate thread writes the checker and fresh problems? [yes]
- Q7 Require a valid calculator trace to accept (answer alone is not enough)? [yes]
- Q8 Cap accepted candidates per problem at 2? [2]
- Q9 Run on BensPC at $0? [yes]
- Q10 Accept the pass marks in 6c as written? [yes]
- Q11 Before running, reconcile with CURRENT.json and design v5 once they are pushed? [yes]

## 11. Reconciliation with the integrated design doc (conflicts and fixes, 2026-10-03)
Source: the docx above (paragraph claims quoted in short; all read, none run).
1. **Calls are typed requests, not free text.** The doc says the reasoner emits, per loop, no call or a typed request
   (allowed operation, ordered operand references, call id), at most one call per loop (four total), host-validated, in
   an add/subtract domain with two-digit single-token results. So a "candidate" is a sequence of typed calls plus a final
   answer, and the invented-numbers rule (3a rule 4) becomes "every operand reference points to a number in the problem or
   an earlier call result". The `expr` field in 4a becomes `op, operand_refs, call_id, result`. FIX: wording only.
2. **Arithmetic validity is not interpretation.** The doc's Mira example (18 minus 7 vs 18 plus 7) shows a calculator
   check accepts a wrong reading. FIX: the checker compares each call's operation and operand bindings to the
   generator-oracle canonical form, and reports three states (accepted / rejected / unresolved), not two. Unresolved
   candidates are kept as diagnostics and never trained on.
3. **Diversity adjustment breaks in a one-call domain.** With add/subtract and mostly one call, every correct candidate
   has the same call sequence, so "count distinct traces" collapses luck to coverage. FIX: primary luck = pass@k and
   coverage; the distinct-trace guard applies only to problems with 2 or more calls (build at least a third of FRESH
   from 2-call composition if the generator supports it, otherwise say luck measures coverage only). L1-L3 stay as written.
4. **Training on accepted candidates is a later-stage update.** The doc says verified experiences are first reused through
   context, and weight updates (adapter, replay) need separate transfer and retention evidence, with creative retry
   "not worker learning" by itself. This design's arm B updates reader, core and prefix on accepted candidates. It is
   the approved prototype step, but under the doc's rules it must be reported as "learning update from verified
   experiences" and needs a context-reuse comparison. FIX: add arm E (accepted experiences supplied as in-context
   examples at inference, no weight change) as a cheap extra control, and keep sleep replay and adapters out of scope.
5. **Existing creative diagnostic.** 40 calls, 2 of 6 practice failures rescued, 2 checked experiences saved, gold-answer
   acceptance, zero optimizer updates (doc). This is the baseline evidence for generation: it shows sampling can rescue some
   failures, but with known answers, so it is neither answer-hidden verification nor learned creativity. Plain stochastic
   sampling stays the first baseline (matches arm A). A separate learned explorer (rewarded for newly rescued problems
   against a frozen worker version) is the doc's later proposal and is out of scope here.
6. **Positive targets.** The doc prefers checked input-answer pairs over self-authored explanations. FIX: arm B trains on the
   typed-call sequence plus final answer only, never free-text rationale.
7. **Splits and consumed panels.** The doc keeps equivalent semantic instances together so paraphrases cannot leak across
   splits, and excludes every consumed panel (the 128, the 64, the 16, the 24) from positive replay. FIX: block-list all of
   them, and split TRAIN, DEV and FRESH by semantic instance, not by surface wording.
8. **No conflict found** on: frozen LM, 4 loops, 8 prefix vectors, pairs as the unit for completion, the point that gold
   checking is not answer-hidden, and that TRAIN32 scores are not transfer evidence.
