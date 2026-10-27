# 27 — "New names" follow-up: why the scale collapsed, and the one experiment to run next

**Fable reviewer (independent design review), 20 September 2026 — not an Astra document.**

Status: a NEW file. I edited no existing file, made no commit, used no cloud machine and no BensPC.
I ran short read-only probes (listed in section 0.2) from a scratch folder outside the repository;
every probe was single-threaded and under two minutes. Nothing here amends experiment 21: that
registration is closed, its verdict (FAIL 0/3, control 3/3) stands, and it is not re-run.

Paths are relative to the worktree
`/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27`
unless they start with `BASE/` (= `/Users/ben-hannan/Desktop/projects/beautiful-model`, read only).

---

## 0. What I read, what I ran, and what I have now been exposed to

### 0.1 Read

`artifacts/fable-newnames21-20260920/{RESULTS.md, report.txt, gates.json, FABLE-PREDICTIONS.md,
logs/train-*.log, logs/waves.log, runs/*/training.json}`; `scripts/fable_newnames21.py` (model,
trainer, scorer); `BASE/scripts/premonition_token_memory.py` (the reader and `optimizer_for`);
`BASE/scripts/astra_canonical_operator.py`; `BASE/scripts/fable_operator_startup.py`
(`training_batch_blind`, `configure_variant`); `BASE/scripts/fable_operator_variants.py`
(`_step_e0`, `lr_at`); `BASE/scripts/premonition_token_initialization_probe.py` (`rescale`);
`design/v3/21b-…`, `design/v3/25-…` (Problem 6), `design/v3/25b-…`.

### 0.2 Ran (scratch scripts `probe27.py`, `probe27b.py`, `zeroshot27.py`; nothing written to the repo)

| # | Probe | Training? | Seeds | Cost |
|---|---|---|---|---|
| A | Gradient of the registered loss on `code_scale` at initialisation, split by path (names as INPUT embeddings / names as OUTPUT rows) and by question type, first 40 batches of the registered stream | none | 2100, 2101, 2102 | 18 s total |
| B | The registered treatment recipe with the same split logged | 600 updates | fixture 9 | 34 s |
| C | B with weight decay switched off on the scalar only | 600 updates | fixture 9 | 34 s |
| D | B with the scalar's gradient allowed through ONE path only (input-only, output-only) | 600 updates each | fixture 9 | 34 s each |
| E | B with 7× learning rate on the scalar (the pre-named "M1b") | 1,000 updates | fixture 9 | 57 s |
| F | B with the scalar frozen at 1.2 | 1,500 updates | fixture 9 | 83 s |
| G | B with the scalar learned but started at 1.2 | 1,500 updates | fixture 9 | 83 s |
| H | B with the scalar frozen at its registered start value 0.13856 | 1,500 updates | fixture 9 | 83 s |
| I | No training: the three exp-21 CONTROL checkpoints with their 16 learned name rows swapped for random reserved codes, scored on frozen cells c1 and c2; plus a harness sanity arm (own rows through the same path) | none | 2100–2102 | 25 s |

Seed 9 is the builder's fixture seed; it is not, and must never become, a registered seed.

### 0.3 Exposure disclosure (this matters for my forecasts in section 5)

Before writing my forecasts I saw probe F: on fixture seed 9, with the scale frozen at 1.2, the
training-batch LINK accuracy rose from chance to 0.5–0.7 and attribute accuracy to 0.83 by update
1,500 (32 LINK and 64 attribute questions per batch, names re-drawn every world, training-pool
codes, 16-line stories only). That is one seed, a quarter of a run, the easy end of the
curriculum and no panel. It is a reason to run the experiment, not a result. I ran exactly two
frozen values (1.2 and 0.13856) and did **not** search over values.

---

## 1. Diagnosis: why `code_scale` went to zero

### 1.1 The mechanism, in one paragraph

Every name logit is `code_scale × (answer · code_j) + entity_output_bias`
(`fable_newnames21.py:524-526`). `answer` comes out of a LayerNorm, so its length is √48 ≈ 6.93
at the start, and the codes are unit vectors, so `answer · code_j` is a number of size about ±1
for every one of the 16 names. **Until the reader has learned to copy a name from the story into
`answer`, those sixteen numbers are pure noise** — and they are fresh noise every world, because
the codes are re-drawn. Noise added to logits always raises the expected cross-entropy (Jensen's
inequality: the softmax denominator grows on average, the target logit does not). The cheapest
way to remove that noise is to turn the one dial that multiplies all of it: `code_scale`. The
gradient therefore points steadily toward zero. Adam converts a small-but-steady gradient into a
full-size step (≈ learning rate per update), so the dial travels 0.139 → 0 in a few hundred
updates. Once it is at zero the names are invisible on the input side too, and then *no*
parameter in the network receives any gradient that depends on who is who: the gradient for the
copy pathway is proportional to `scale_in × scale_out`, which is now 0 × 0. Zero is not just a
low point, it is a trap: a symmetric fixed point (flipping the sign of the scale changes nothing
to first order) that the noise penalty and weight decay both make attracting.

### 1.2 What is ESTABLISHED (by the files, or by a probe whose numbers are below)

**E1 — weight decay does apply to the scalar, and it is not the cause.** `optimizer_for`
(`BASE/scripts/premonition_token_memory.py:160-161`) is one AdamW group over *all* parameters
with `weight_decay=.1`, so `code_scale` and `entity_output_bias` are decayed (21b Q4 already said
so). The pull is `lr × wd` = 10⁻⁴ of the value per update: 5 % over 500 updates. Probe C (decay
off for the scalar only) gave the same trajectory to the third decimal:

| update | 100 | 200 | 300 | 400 | 500 | 600 |
|---|---|---|---|---|---|---|
| registered (B) | 0.1139 | 0.0893 | 0.0349 | 0.0209 | 0.0119 | 0.0125 |
| no decay on scalar (C) | 0.1144 | 0.0905 | 0.0363 | 0.0220 | 0.0127 | 0.0130 |

(B reproduces the builder's fixture observation of ≈ 0.013 at update 500 and matches the
registered seeds' 0.005 / 0.016 / 0.015.)

**E2 — at initialisation the gradient on the scalar is positive (so the step is downward) in all
three registered seeds, and it comes from the OUTPUT side, from questions whose answer is a
value.** Probe A, 40 batches per seed, no training. "mean/rms" is what Adam's step is
proportional to.

| seed | total d(loss)/d(scale): mean, t, mean/rms | via INPUT path: mean (t) | via OUTPUT path: mean (t) | OUTPUT path, value-answer questions: mean, share of batches positive, t | OUTPUT path, LINK questions: mean ± sd |
|---|---|---|---|---|---|
| 2100 | +0.0258, t = 3.5, 0.49 | −0.0099 (−6.0) | +0.0357 (+4.9) | +0.0225, 97.5 %, t = 12.6 | +0.013 ± 0.047 |
| 2101 | +0.0260, t = 3.3, 0.47 | +0.0019 (+1.2) | +0.0240 (+3.0) | +0.0216, 100 %, t = 14.7 | +0.002 ± 0.051 |
| 2102 | +0.0308, t = 3.3, 0.47 | +0.0007 (+0.6) | +0.0300 (+3.4) | +0.0242, 97.5 %, t = 14.5 | +0.006 ± 0.059 |

The noise-penalty arithmetic predicts the value-question term from first principles:
(share of probability on names at the start, 16/68) × (scale, 0.1386) × (variance of
`answer·code`, 1.0) × (loss weight of value-answer questions, 0.75) = **0.0245**. Measured:
0.0216–0.0242. The LINK-question term has zero mean and large spread, exactly as it must when
`answer` knows nothing about the right name: it is the noise Adam has to average through, not a
signal. With mean/rms ≈ 0.47 and a 100-update warm-up, Adam needs roughly 350 updates to walk
0.139 down to zero — which is what the traces show.

**E3 — the output path alone reproduces the collapse; the input path alone does not.** Probe D:

| update | 100 | 200 | 300 | 400 | 500 | 600 |
|---|---|---|---|---|---|---|
| gradient through OUTPUT path only | 0.1147 | 0.0908 | 0.0358 | 0.0214 | 0.0123 | 0.0127 |
| gradient through INPUT path only | 0.1235 | 0.0955 | 0.0898 | 0.0939 | 0.1103 | 0.1411 |

After the first ~100 updates the input-path gradient is ≈ 0 (|g| < 0.002): the reader is simply
not using the names yet, so the input-only dial just random-walks. "Names are noise to an
untrained reader on the input side" is therefore **not** what kills the scale. The output-side
tie is.

**E4 — what the model learns instead is the question-type prior, and that makes the pressure
worse, not better.** In probe B the loss falls to 2.80 ≈ ln 16 = 2.77 by update 400: the model
has learned "a LINK question is answered by *some* name; an attribute question by *some* value"
(probability mass on names: 0.97 on LINK questions, 0.01 on value questions) and nothing else.
That is the same plateau the three registered seeds sat on for 6,000 updates (training-log LINK
accuracy 0.00–0.28, never sustained). Two things follow. (i) Once nearly all the mass on LINK
questions is on names, the noise penalty moves onto the LINK questions at full strength. (ii)
The answer vector keeps growing (|answer| 6.9 → 9.9 by update 600), which makes each unit of
scale *noisier*. Both push the dial further down.

**E5 — the blind curriculum is not the cause.** For the first 1,500 updates it holds stories at
16 lines for both arms (`grow_g1 = 1500`; training logs `mean_kept_lines = 16.0`), the batches
are byte-identical between arms, and the control starts up inside that window (training-log LINK
0.38–0.56 at update 750, 1.00 by 1,250 in two seeds and by 1,750 in the third). The collapse is
over by update ~400, before the control has started either. The curriculum's only contribution
is that *nothing* is learnable about names in the first few hundred updates, in either arm —
and only one arm has a single dial that can be turned off while it waits.

**E6 — it is a race, and the start value decides it.** Probe G (scale still learned, started at
1.2 instead of 0.139): the dial fell exactly as the mechanism says (1.20 → 0.91 by update 500),
then the binding signal arrived (output-path gradient turned negative from update ~400,
training-batch LINK 0.66 at update 600) and the dial turned round (0.98 at update 1,500). From
0.139 the race is lost twice over: the dial reaches zero in ~350 updates, *and* the copy
pathway's gradient is scaled by scale² = 0.019 instead of 1.44 — 75 times weaker — so binding
cannot arrive in time.

**E7 — M1b's direction is wrong (probe E).** With 7× learning rate the scalar reached 0.039 by
update 100 (against 0.114), crossed zero by update 250, and then jittered in ±0.07 for the rest
of 1,000 updates on the same ln 16 plateau (loss 2.76–2.82, LINK 0.00–0.12).

**E8 — the control does not face this trap, by construction.** Its 16 name rows are 768 separate
parameters attached to persistent identities. The noise penalty exists there too, but it is
second-order (∝ row length × variance), while the first-order terms carry real, *repeatable*
signal because entity 7 is entity 7 in every world. In the treatment every first-order term
averages to zero across re-drawn worlds, so the second-order shrink term is the only consistent
push, and it lands on one shared dial. The control finishes with name rows of length
0.98 / 1.20 / 1.39 (seeds 2100–2102, probe I; 21b measured 1.16–1.36 on six earlier seeds) and
an answer vector of length 15.0 / 10.7 / 10.6, i.e. an effective name-logit scale of
**14.6 / 12.9 / 14.6** — squarely on adjudication 25b's estimate that 16 names need ≈ 13.6.
The treatment started at 0.96 and went to 0.

### 1.3 What is HYPOTHESIS (not shown by anything on disk)

* **H1 — that the reader *can* learn to bind re-drawn random names at all at 79k parameters and
  width 48.** Experiment 21 says nothing about this (the names were off). Probe F is one fixture
  seed for a quarter of a run. This is what the next experiment is for.
* **H2 — that a frozen scale removes the problem rather than moving it.** The same noise
  pressure still exists with a frozen scale; the network's other ways of relieving it are
  (a) driving `entity_output_bias` very negative, (b) shrinking the answer vector through the
  `answer_norm` gain while growing the value rows, (c) learning to copy the name — which is the
  one we want. In probe F it took route (c) (bias stayed within ±0.26, |answer| *grew* to 9.9),
  but one seed does not establish it.
* **H3 — that three registered seeds would each have bound names had the scale not collapsed.**
  Unknown; the control itself has a documented start-up lottery.
* **H4 — why `entity_output_bias` drifted to −1.1 … −2.4 late in the registered runs.** My
  probes stop at update 1,500, where the bias is still positive (+0.2 … +0.5). The late negative
  drift is consistent with a name-blind guesser slowly improving its attribute guesses
  (seed 2100 reached 0.29 one-call attribute accuracy) and with weight decay, but I did not
  measure it and it is not needed for the diagnosis.

### 1.4 One more fact worth having (probe I, no training)

Swap random reserved codes into the *finished control* and score it cold:

| control seed | harness sanity (own rows) c1 / c2 | random codes: c1 (one-call attributes) /512 | random codes: first-stage LINK |
|---|---|---|---|
| 2100 | 512 / 512 | 274 (relations 0.48–0.64) | 0.129 |
| 2101 | 512 / 512 | 216 (0.33–0.49) | 0.201 |
| 2102 | 512 / 512 | 268 (0.32–0.67) | 0.072 |

Chance is 0.0625. So the control's way of *finding the right story line from a name* is already
about half name-general, with no training for it; its way of *saying a name* is not general at
all. The hard half of "new names" is the output side — the same side that produced the collapse.

---

## 2. Should M1b (7× learning rate on the scalar) still be run? **No.**

1. **Its trigger did not fire.** Ruling 21b licensed it for a seed that failed *and* tripped the
   speed-limit flag, or for the "attributes fine, LINK at chance" signature. Neither occurred in
   any seed.
2. **It treats the opposite illness.** M1b assumes the gradient pushes the scale *up* and the
   optimiser is too slow to follow. E2 shows the gradient pushes it *down*; a faster dial gets to
   zero sooner.
3. **Zero is a trap, not a hill.** At scale 0 the names are invisible at both ends, so nothing
   downstream can learn that they matter, so nothing ever pushes the dial back. More learning
   rate only makes the jitter around zero larger.
4. **Probe E confirms it on the fixture seed** (0.039 at update 100; ±0.07 jitter; same ln 16
   plateau for 1,000 updates).

Running it under registration would spend a wave to confirm a forecast I would put at ≤ 0.03 for
a 3/3 pass. Retire M1b. (I was the class of reviewer that pre-named it; the speed-limit analysis
in 21b Q4 was arithmetic about *how fast* the dial could move and never asked *which way* the
early gradient points. That was the miss, and P100 in the coordinator's ledger — "scale below its
start at update 500", 0.65 — was the closest anyone came.)

---

## 3. Ranked short list of single-change follow-ups

All costs are for the 8-core Mac, ≤ 6 single-thread jobs, measured from experiment 21's own wave
(660–682 s per 6,000-update run with six running at once; scoring ≈ 3 min).

### Rank 1 — freeze the name scale at 1.2 (no learned scalar)

* **The one change** (relative to experiment 21's treatment): `code_scale` stops being a
  parameter and becomes the constant 1.2, on both the input and the output side, as now.
  Trainable parameters 78,533.
* **Why 1.2:** it is where the control's own names finish. Nine finished control runs have mean
  name-row length 1.19, 1.16, 1.29, 1.17, 1.22, 1.36 (21b's table, measured *before*
  experiment 21) and 0.98, 1.20, 1.39 (exp-21 controls): mean 1.22. Declared here, never tuned.
  With the answer vector reaching ≈ 10–12 it gives an effective name-logit scale of 12–14, the
  range the control uses and 25b computed.
* **Why it addresses the diagnosed cause:** the collapse needs a dial; this removes the dial. It
  also multiplies the copy pathway's early gradient by (1.2 / 0.139)² ≈ 75.
* **Would show:** whether this reader can bind names that are re-assigned every world, and
  answer with 1,024 names it never trained on, choosing among the 16 in the story.
  **Would not show:** that a *learned* scale can work; anything about choosing among thousands
  (open-set is still descriptive); anything about English.
* **Cost:** one wave, 3 control + 3 treatment, ≈ 12 min training + 3 min scoring.
* **Main risk:** H2 — the noise pressure finds another exit (bias or answer-gain) and the model
  is name-blind again. That would be visible in the logs I ask for, and would itself be the
  trigger for Rank 3.

### Rank 2 — warm-start the treatment from a finished control checkpoint

* **The one change:** treatment weights start from a passing control run (rows 0–51 and the whole
  reader copied; names become re-drawn codes; scale as in experiment 21, started at the
  checkpoint's own mean row length).
* **Why it addresses the cause:** at the start the answer vector is already informative, so the
  first-order gradient on the scale is real signal rather than noise; and probe I says the
  line-finding half transfers cold at 42–54 %.
* **Would show:** that a reader which already knows the task can be *re-fitted* to arbitrary
  names. **Would not show:** that it can be learned from nothing with new names — which is what
  "starts knowing nothing" in the project goal asks for. It also doubles the training budget
  behind every treatment number (6,000 + 6,000 updates), so it is no longer budget-matched to the
  control.
* **Cost:** one wave (3 control-continuations + 3 treatments), ≈ 12 min, plus three existing
  checkpoints.
* **Main risk:** probe I's LINK ≈ chance means the saying-a-name half starts from nothing while
  the scale is still a learnable dial; the same shrink pressure applies on LINK questions and the
  dial may still slide. It is a weaker test and a less clean claim than Rank 1. Keep it as the
  fallback if Rank 1 fails with the **never-started** signature in seeds where the control
  started.

### Rank 3 — token-pointer copy head (25b's M1c, Stage A then Stage B)

* **The one change per stage:** Stage A changes only the output for name answers (probability of
  a name = the final read's attention mass on story tokens carrying that name) with the ordinary
  fixed name table; Stage B then swaps in re-drawn codes.
* **Why it addresses the cause:** there is no `answer · code` product on the output at all, so no
  noise logits, no output scale, nothing to collapse. It is also the design that scales to
  thousands of names (21b §3, 25 Problem 6).
* **Would show:** (A) the reader works with a copy output; (B) new names with a copy output.
  **Would not show:** that the tied design can do it.
* **Cost:** two waves at least (≈ 15 min each), plus real building: the head must be designed
  over memory *tokens* (25b's correction), it must tell a fact's object token from its subject
  token, mix with the value logits, and keep the fixed-loop scorer unchanged. More new code than
  experiment 21 itself.
* **Main risk:** two stages and a new output interface before the first word about new names; a
  Stage-A failure says nothing about names. And the input side would still need a scale decision
  (learned from 0.139 it random-walks, probe D). Run it when Rank 1 shows the pre-named
  **copy-side** failure (section 4.5), or when the open-set numbers demand it at M3.

Not on the list: M1b (section 2); "learned scale started at 1.2" as the *primary* arm — it worked
on the fixture seed (probe G) but it keeps the trap, and a seed that starts late keeps sliding
while it waits, with the binding signal weakening as scale²; it is worth exactly three
descriptive runs (section 4.2) and no more.

---

## 4. Recommendation — Experiment 27 / "M1-F": new names with the name scale frozen at 1.2

Registration-ready sketch. The builder copies `scripts/fable_newnames21.py` to a new file
(`scripts/fable_newnames27.py`) and a new artifact folder; experiment 21's files are not touched.

### 4.1 The one change

Relative to experiment 21's treatment: `code_scale` is a constant buffer equal to **1.2**, not a
parameter. It must be a buffer (or `requires_grad=False`), **not** a parameter left out of the
optimiser: a parameter with a gradient would enter `clip_grad_norm_` and change every other
parameter's update (the gradient norm is ≈ 2 at the start, so clipping is active).

### 4.2 Arms, seeds, waves

| Arm | What | Gated? | Seeds | Wave |
|---|---|---|---|---|
| control | frozen grow-blind recipe, fixed name table, exactly as experiment 21's control | VOID rule only | 2103, 2104, 2105 | 1 |
| **F** | re-drawn codes, scale **frozen at 1.2** | **yes — the verdict** | 2103, 2104, 2105 | 1 |
| L | re-drawn codes, scale **learned, started at 1.2** (experiment 21's model with one number changed) | no — descriptive, run whatever wave 1 shows | 2103, 2104, 2105 | 2 |

Wave 1: six single-thread jobs, ≈ 12 min + ≈ 3 min scoring. Wave 2: three jobs, ≈ 10 min + 2 min.
Both waves are registered and hashed together, before wave 1 starts; wave 2 is launched without
opening wave 1's scores if the coordinator wants zero forking, or straight after — its content
does not depend on wave 1 either way. Seeds 2103–2105 are the fresh seeds ruling 21b already
named; 2100–2102 are spent, 9 is a fixture.

Arm L is there because it tests the *diagnosis*, not the milestone: section 1 predicts its dial
dips and then recovers when binding arrives, and collapses if binding arrives late. It costs ten
minutes and no verdict depends on it.

### 4.3 Data

* Code pool and 3,072 / 1,024 split: **reuse the frozen pool** (`pool/pool.json`, hash-checked).
  Reserved codes have still never been trained on by any model.
* Training-code stream: new namespace `newnames27/train-codes:<seed>`; re-drawn every visit of
  every update, as ruled in 21b Q3.
* World stream: `random.Random(1101)`, shared by arms and seeds (21b Q1; same limitation
  sentence in the report).
* Panels: **fresh** ten-cell suite in a new namespace and seed base (standing ruling: fresh
  confirmation panels), same generator, same ten cells, 512 units each; panel codes in a new
  namespace, seed-independent (21b Q6); 16 bound codes on 12-person cells (21b Q9); run-time
  `forbidden` check against the union of the registered exclusion and the fresh panels.
* 50-update control bit-identity proof against the registered recipe, re-proved with the new
  script. 50-update proof that arm L with start value 0.13856 reproduces experiment 21's
  treatment fingerprint for seed 2100's first 50 updates (shows the new file changed nothing
  else).

### 4.4 Pass marks (experiment 21's, unchanged; per seed, no averaging)

* Arm F, **reserved-code** scoring: ≥ 487/512 on c1, c2, p12-1, p12-2; ≥ 461/512 on c3, c4, c5,
  c6, p12-3, s3.
* Paired: reserved minus training-pool ≥ −13/512 on every cell; two-sided warning line if
  |difference| > 13 in either direction (21b Q10).
* Control must meet the same ten cutoffs in ≥ 2/3 seeds, else **VOID**.
* **PASS = 3/3** F seeds. 2/3 = PARTIAL, no claim. Otherwise FAIL.
* Final checkpoint only; no selection; run once.

### 4.5 Pre-named failure signatures (read on reserved scoring, printed for both; describe only)

| Name | Definition (per seed) | What it would mean |
|---|---|---|
| **scale_collapsed** | arm L only: `|code_scale| < 0.05` at any logged point from update 500 on. For arm F the build must *assert* the buffer equals 1.2 at the end of training; a violation is a bug and the run is INVALID | the trap again; freezing is necessary, not merely convenient |
| **name_blind** | all ten paired differences exactly 0 **and** first-stage LINK ≤ 0.125 on every cell | names switched off by another route (H2). Sub-label from the logs: `bias_exit` if `entity_output_bias` ≤ −3.0 at the end; `gain_exit` if the mean answer-vector length at the end is < 3.5 (half its start); otherwise `unexplained` |
| **never_started** | c1 and c2 both ≤ 64/512 (as in 21) | start-up lottery; say "matched in control" if the same-numbered control seed also shows it |
| **copy_side_failure** (21's `attributes_fine_link_at_chance`, thresholds unchanged) | every one-call attribute relation ≥ 0.90 on c1 and p12-1 **and** first-stage LINK ≤ 0.125 on every cell | the reader finds the line but cannot say the name: the trigger for Rank 3 (pointer head) |
| **reserved_gap** | passes all ten cutoffs on training-pool codes, fails on reserved codes | the substantive failure: matching did not generalise to unseen names |
| **unnamed** | fails, none of the above | reported as such; not re-labelled afterwards |

### 4.6 Logging to add (logging only; must be proven inert)

Every **100** updates (experiment 21 logged every 500, which hid the whole collapse), for arms F
and L, computed under `torch.no_grad()` on the batch just trained on, consuming no random
numbers:

`code_scale`, `entity_output_bias`, mean answer-vector length, effective name scale
(= `code_scale` × that length), RMS of the `answer_norm` gain, mean length of the 16 value rows,
answer loss, LINK accuracy and attribute accuracy on the batch, and the probability mass on names
for LINK questions and for value questions. All of it into `training.json` as `trace`.

Inertness proof, as for C1 in 21b: 50-update fingerprint identical with the logging on and off,
for one F and one L fixture run; control bit-identity re-proved with the final script.

After scoring, two descriptive read-outs on the frozen checkpoints (no verdict effect): 21b Q5's
open-set scoring (A: 1,024 reserved, B: all 4,096) and 25b's "right line attended, wrong name
emitted" attention read-out, for every F seed whether it passed or not.

### 4.7 What must NOT be changed

The pool, the split and the re-draw-every-visit rule; the tied use of one vector per person for
input, story and output; the single shared learned `entity_output_bias`; the loss (answer
cross-entropy, 0.75 / 0.25); AdamW (lr 10⁻³, β 0.9 / 0.99, weight decay 0.1 on every remaining
parameter), warm-up, schedule and clipping; the grow-blind curriculum parameters; 6,000 updates ×
16 visits; width 48, 4 heads, 3 read steps; the initialisation and `rescale`; the fixed-loop
scorer; the ten cells and their cutoffs; and the number 1.2 — it is not re-tuned after any
outcome. No amendment after launch.

### 4.8 Claim limits

* **PASS (3/3):** *"On this toy, with one world stream and three seeds, an operator trained with
  names re-assigned at random every world — and with the loudness of names fixed by hand at 1.2,
  the value the ordinary version ends up at — answers lookup and chained questions about 1,024
  names it never trained on, choosing among the 16 names in the story."* The clause about the
  hand-fixed loudness is compulsory. Not permitted: "open vocabulary", "learns new words",
  anything about choosing among thousands, anything about English, "a learned scale works"
  (that is arm L, descriptive).
* **PARTIAL (2/3):** no claim; fresh registration, seeds 2106–2111, nothing else changed.
* **FAIL:** no claim. `copy_side_failure` → register Rank 3 (Stage A first). `name_blind` → read
  the sub-label; `bias_exit` or `gain_exit` also point to Rank 3, because both are the output
  side again. `never_started` with the control started → Rank 2. `reserved_gap` → that *is* the
  finding; report it and stop to think.
* **Arm L, whatever happens:** one descriptive paragraph. If L passes wherever F passes, say the
  freeze was sufficient but not shown necessary; if L collapses where F passes, say the freeze is
  necessary at this start-up speed.
* **VOID / INCOMPLETE:** as in 21b §4.

---

## 5. My forecasts (written before anything is built; see the exposure note in 0.3)

| # | Statement | Probability |
|---|---|---|
| R27-P1 | Arm F passes in 3/3 seeds (all ten reserved-code cells ≥ cutoff, paired mark met) | **0.40** |
| R27-P2 | Arm F passes in at least 1 seed | 0.72 |
| R27-P3 | The control reproduces (≥ 2/3 seeds meet the ten cutoffs) | 0.90 |
| R27-P4 | In every F seed, first-stage LINK accuracy on c2 (reserved codes) is ≥ 0.50 — i.e. binding clearly happens in all three, pass or not | 0.70 |
| R27-P5 | At least one F seed shows **name_blind** | 0.10 |
| R27-P6 | At least one F seed shows **copy_side_failure** | 0.07 |
| R27-P7 | At least one F seed fails as **unnamed** (partly learned, under a cutoff) | 0.45 |
| R27-P8 | Any F or L seed shows **reserved_gap** | 0.05 |
| R27-P9 | In every passing F seed the effective name scale at the end lies in [10, 25] (void if none pass) | 0.70 |
| R27-P10 | Arm L: in 3/3 seeds the lowest logged `code_scale` is ≤ 1.0 (the dial dips before anything else happens) | 0.85 |
| R27-P11 | Arm L: **scale_collapsed** in at least 1 seed | 0.25 |
| R27-P12 | Arm L passes in 3/3 seeds | 0.30 |
| R27-P13 | Every F seed that fails a cutoff fails it on a chained or 12-person cell while meeting the c1 cutoff (void if no F seed fails) | 0.55 |
| R27-P14 | Open-set (B), all 4,096 codes: pooled first-stage LINK ≥ 0.90 in every passing F seed (void if none) | 0.30 |

Why P1 is only 0.40 after a fixture run that visibly learned: the gate is strict (95 % on four
cells, 90 % on chained cells where per-call errors multiply), random names have look-alikes
(largest cosine among 16 ≈ 0.36–0.46) that fixed learned rows never had to tell apart at width
48, the curriculum still has to triple the story length after update 1,500, and all three seeds
must make it. Why P2 is 0.72: probe F is real evidence that the mechanism exists.

---

## 6. Five lines for Ben

1. **What went wrong:** all the names share one "loudness" dial, and before the model has learned
   to use names they are just static in its answers — so the quickest way to lower its error was
   to turn the dial to zero, which it did within about 350 steps in every run; at zero the names
   are invisible, so nothing could ever teach it to turn them back up. It never tried new names
   at all.
2. **How I know:** I measured the push on the dial at the very first step in all three runs (it
   points down every time, by the amount the arithmetic predicts), and short two-minute test runs
   showed the push comes from the *answer* side, not the reading side, and that weight decay has
   nothing to do with it.
3. **What we drop:** the planned "turn the dial seven times faster" follow-up — it just reaches
   zero seven times sooner (I checked on a practice seed).
4. **What we try next:** take the dial away — fix the loudness at 1.2, the value the ordinary
   version always ends up at — and change nothing else; same exam, same pass marks, fresh seeds
   and fresh test questions, one 15-minute wave, plus three side runs that keep the dial but
   start it at 1.2 to check my explanation.
5. **Why I think it is worth it, and how sure I am:** on one practice seed the fixed-loudness
   version started getting names right (about 60–70 % on "who is X's friend", chance is 6 %)
   within a quarter of a run; my honest odds are 40 % that all three real runs pass and 72 % that
   at least one does — and if it learns the facts but cannot *say* the names, that is the signal
   to build the "copy the name from the story" output next.
