# 21b — "New names" (Experiment 21 / M1): rulings on the builder's Q1–Q10

**Fable reviewer, at Ben's request, 20 September 2026 — not an Astra document.**

Status: rulings on a built, un-run experiment. I ran no training and edited no existing file. This
file is meant to be hashed, together with the script, tests, launchers, pool and panels, **before**
`run_train.sh` is started. It supplements §5 of
`design/v3/21-teachable-assistant-roadmap-fable-review.md`; where the two disagree, this file wins
(the only such place is Q1).

What I read: `artifacts/fable-newnames21-20260920/BUILD-NOTES.md` (all of it),
`scripts/fable_newnames21.py` (model, training loop, code assignment, scoring, verdict logic),
`scripts/astra_canonical_operator.py` (`execute`, `training_batch`),
`scripts/premonition_token_memory.py` (`optimizer_for`).

One read-only measurement I made for these rulings (loading six finished checkpoints, no training):
the trained **control** entity rows in `artifacts/fable-operator-grow-blind-20260920/…seed-0..5/final.pt`.

| seed | entity-row length (min / mean / max) | value-row mean length | entity rows, mean \|cos\| | max \|cos\| | entity output bias range |
|---|---|---|---|---|---|
| 0 | 1.09 / 1.19 / 1.24 | 0.81 | 0.198 | 0.392 | −0.27 … +0.13 |
| 1 | 1.09 / 1.16 / 1.21 | 0.95 | 0.242 | 0.502 | −0.49 … −0.19 |
| 2 | 1.14 / 1.29 / 1.36 | 0.99 | 0.258 | 0.528 | −0.72 … −0.38 |
| 3 | 1.11 / 1.17 / 1.21 | 1.13 | 0.256 | 0.546 | −0.48 … −0.12 |
| 4 | 1.16 / 1.22 / 1.28 | 0.94 | 0.249 | 0.479 | −0.65 … −0.36 |
| 5 | 1.31 / 1.36 / 1.44 | 0.87 | 0.252 | 0.492 | −0.81 … −0.48 |

Two facts from that table drive several rulings below:

* **F1 — the control's names end up about 8–10 times longer than they start** (start ≈ 0.139,
  finish ≈ 1.2). So the treatment's `code_scale` has real work to do: it must travel from 0.139 to
  roughly 1.2.
* **F2 — the control's own trained names are *more* alike than random codes are.** Trained entity
  rows have mean |cos| 0.20–0.26 and max 0.39–0.55 among 16; random unit codes in 48 dimensions have
  mean |cos| 0.116 (builder's figure) and a 16-code world will typically have a max around 0.4. So
  for the gated test (pick 1 of 16), "random names collide too much at width 48" is **not** a
  credible obstacle — the control already succeeds with worse geometry. Collisions only become a
  live question for the open-set scoring (1 of 1,024 or 4,096; pool max |cos| 0.699). See Q5 and §3.

---

## 1. Rulings

### Q1 — world stream: keep the frozen `random.Random(1101)`, shared by arms and by seeds. **Confirmed as built. No code change.**

My §5 wording ("per-seed world stream") was loose and the builder was right to catch it. The two
instructions conflict, and "the control is the registered recipe exactly as is" is the one that
matters: it is what makes the 50-update bit-identity proof possible and what lets the 48/48
grow-blind history stand behind the control. What I actually needed from that sentence is already
true in the build: **both arms see identical worlds in identical order** (the batch is drawn before
the code generator is touched).

Limitation to state in the report, in these words or close to them: *"The three seeds differ in the
model's starting weights, the blind-curriculum stream and (treatment only) the name stream. They do
not differ in the training worlds. The result is therefore conditional on one world stream; it says
nothing about other world streams."* This is the same limitation the registered grow-blind
population already carries.

### Q2 — the control's "own marks" = the same ten cutoffs (487/487/461/461/461/461/487/487/461/461) on the fresh panels. **Confirmed as built. No code change.**

Holding the control to what earlier runs *happened to achieve* would be a mark chosen from data,
which is exactly what registration exists to prevent. The control's job here is narrow: show that
the recipe, on this machine, on these fresh panels, still trains. The registered cutoffs do that.

`VOID` if fewer than 2 of 3 control seeds pass stands as built — including the awkward case
"control 1/3, treatment 3/3". In that case everything is still reported, no claim is made, and the
experiment is re-registered with fresh seeds (2103–2105). I accept that cost; a control that does
not reproduce means I cannot tell what the machine is doing.

Reporting rule (words only, no verdict effect): if a treatment seed fails **and** the control with
the same seed number also fails with the never-started signature, say so next to the verdict
("failure matched in control"). Note that the two arms' same-numbered seeds share the base
initialisation of rows 0–51 and the curriculum stream, so a matched failure points at the start-up
lottery, not at names. It still counts as a treatment failure.

### Q3 — codes are re-drawn for every visit of every update. **Confirmed as built. No code change.**

This is the whole point of the experiment. The model must never be able to treat a particular code
as a particular person across worlds; any weaker schedule lets it partly memorise names and would
make the reserved-code test less meaningful. For the record, the numbers: 6,000 updates × 16 visits
× 16 codes = 1,536,000 code uses over 3,072 training codes ≈ 500 uses per code, each time attached
to a different person in a different world. Codes carry no information, so there is nothing to
memorise and 78,534 parameters could not hold 3,072 × 48 numbers anyway. That is why my prediction
for "passes on training-pool names but fails on reserved names" is only 0.05.

### Q4 — `code_scale` stays a single learned scalar, not shared with the value rows, initialised at 0.13856. **Confirmed as built, plus one logging-only code change (C1 below).**

Reasons to keep it learned:

* F1: the control's names grow about 9×. A fixed scale of 0.139 would hand the treatment a
  handicap the control does not have, and a failure would then be uninterpretable (names, or
  scale?). "Fixed scale, nothing learned" is a legitimate harder arm, but it is a second change and
  is **not** run now.
* Not sharing it with the value rows: the value rows are ordinary trained parameters in both arms.
  Tying them to the scale would change the control-side parameterisation — a second change.
* AdamW's weight decay (0.1) applies to `code_scale` and `entity_output_bias` because the frozen
  recipe decays every parameter. Leave it. At scale ≈ 1.2 the decay pull is about 1.2 × 10⁻⁴ per
  update against an Adam step of up to 10⁻³; it is not the binding force.

**The risk I want on the record before the run (new, from F1).** Adam moves any single parameter by
at most about the learning rate per update. In the control, each name is 48 separate parameters, so
a name's length can grow by up to ≈ 10⁻³ × √48 ≈ 0.007 per update. In the treatment the length of
every name is one parameter, so it can grow by at most ≈ 0.001 per update — **about seven times
slower**. Getting from 0.139 to ≈ 1.2 needs at least ≈ 1,100 updates at full speed (including the
100-update warm-up). The curriculum's first growth step is at update 1,500. So the treatment may be
"speed-limited" on name length during exactly the period when the control finds its feet. The rest
of the network can compensate (layer norms, a longer answer vector), so I do not think this is
fatal, and I am **not** changing the design for it: a larger starting scale or a private learning
rate for the scalar would each be a second change. But it must be visible, hence C1, and it has a
named, numeric flag:

> **Speed-limit flag (descriptive, no verdict effect):** a treatment seed is flagged
> "scale speed-limited" if `code_scale` ≥ 0.50 at update 500 **or** ≥ 0.90 at update 1,000.
> (The theoretical ceilings are ≈ 0.59 and ≈ 1.09; the flag fires at about 85 % of the ceiling's
> growth. Adam on a noisy gradient almost never sustains that unless the gradient is pushing one
> way the whole time.)

If a treatment seed fails and the flag fired, the first follow-up (separate registration) is the
same experiment with the scalar given a 7× learning rate, nothing else changed.

If the "attributes fine, LINK at chance" signature fires, the first thing to read is the
`code_scale` trace: did it move at all, did it hit the speed limit, where did it finish relative to
the value rows' length (F1's table gives the control's reference values: names ≈ 1.2, values ≈ 0.95).

#### C1 — the only code change I am ordering (logging only)

File: `scripts/fable_newnames21.py`, function `train_run`. Three edits, nothing else.

(a) Before the training loop (next to `flops, intervals = 0, []`), add:

```python
        scale_trace = []
```

(b) Replace the existing heartbeat block

```python
            if log_every and updates_done % 500 == 0:
                print(json.dumps(dict(arm=arm, seed=seed, updates=updates_done,
                                      training_seconds=time.monotonic()-training_start)),
                      flush=True)
```

with

```python
            if updates_done % 500 == 0:
                beat = dict(arm=arm, seed=seed, updates=updates_done,
                            training_seconds=time.monotonic()-training_start)
                if arm == 'treatment':
                    beat.update(code_scale=float(model.code_scale.detach()),
                                entity_output_bias=float(model.entity_output_bias.detach()))
                    scale_trace.append(dict(updates=updates_done,
                                            code_scale=beat['code_scale'],
                                            entity_output_bias=beat['entity_output_bias']))
                if log_every:
                    print(json.dumps(beat), flush=True)
```

(the trace is recorded even if the heartbeat print is switched off).

(c) In the `training = dict(...)` that becomes `training.json`, add one key:

```python
                        scale_trace=scale_trace if arm == 'treatment' else None,
```

What the auditor checks for C1:

1. The diff of `scripts/fable_newnames21.py` touches only those three places (plus, if the builder
   wishes, a test asserting the new key). No change to the model, optimiser, RNG use, batch order,
   code assignment, scoring or verdict code.
2. It reads two tensors with `.detach()` and converts to Python floats; it consumes no random
   numbers and changes no tensor. Proof by run, not by argument: a 50-update **treatment** run
   (seed 2100) gives the same final fingerprint before and after C1, and the 50-update **control**
   bit-identity with the registered grow-blind recipe is re-proved after C1 (the script's source
   fingerprint changes, so `control-equivalence.json` must be produced by the post-C1 script).
3. All tests pass after C1.

The "speed-limit flag" is computed by hand from `scale_trace` in the report; it does not need code.

### Q5 — gated scoring stays at the world's 16 bound codes. **Confirmed as built.** A descriptive open-set scoring is specified now (hashed with this file), built later as a separate additive script on the frozen checkpoints.

The builder's reading is right: the control chooses among 16 entity rows plus the 52 other tokens,
so the treatment must too, or the comparison stops being one change. And the builder is also right
that "pick the right person out of thousands of unseen names" is the claim the roadmap eventually
needs. Both are served by keeping them apart:

**Open-set scoring (descriptive; never feeds the verdict; may be built and run after the gate table
exists, because it uses only `final.pt` and the already-frozen reserved panels).**

* New file, e.g. `scripts/fable_newnames21_openset.py`; imports the experiment module; edits nothing.
* Population: on the **reserved-code** panels, every question whose first operation is LINK — the
  same calls that `first_link_stage` counts — first operator call only. Treatment checkpoints only.
* For each such call take the operator's answer vector `a` (the output of `CanonicalOperator.forward`
  before the output product) and the true next person's code `u`.
* Candidate sets: **(A)** the 52 base rows + all **1,024 reserved** codes; **(B)** the 52 base rows +
  all **4,096** pool codes. Logit for a code `w` is `code_scale · a·w + entity_output_bias`; base-row
  logits exactly as in the model. The 16 bound codes are already inside both sets.
* Report per seed, pooled over the ten cells and per cell: accuracy under (A) and (B); the same
  calls' 16-candidate accuracy for reference; mean and 5th-percentile of `cos(a, u)`; mean and
  5th-percentile of the margin `a·u − max_{w≠u} a·w` over all 4,096 codes; and, among errors, the
  |cos| between the true code and the code chosen (are mistakes collisions with look-alike names, or
  diffuse?).
* This is the measurement the outside review can only estimate from an armchair. See §3.

Attribute questions need no open-set version: their answers are value tokens, identical in both arms.

### Q6 — panel codes stay seed-independent. **Confirmed as built. No code change.**

The worry ("one unlucky draw of names shared by all seeds") is smaller than it looks, because a
panel is not one draw: every world in every chunk gets its own 16 codes, so a 512-question cell
already averages over many independent draws. What seed-independent panels buy is worth more: every
seed sits the *same exam*, so seed-to-seed differences are differences between models, and the
reserved-vs-training-pool comparison is exact. Per-seed panel codes would mix name luck into the
seed variance I am trying to read.

Auditor check (no code change): for each cell, the `reserved` and `train` scorings use the same
worlds and the same questions in the same order; only the code subset differs.

### Q7 — failure-signature thresholds. **Confirmed as built. No code change.**

* **Never started:** cells `c1` and `c2` both ≤ 64/512 (2 × the 1/16 chance rate).
* **Attributes fine, LINK at chance ("scale bug"):** every one-call attribute relation (cells `c1`
  and `p12-1`) ≥ 0.90 **and** every cell's first-stage LINK accuracy ≤ 0.125.

These are deliberately strict, so they will sometimes not fire when a failure is "sort of" one of
them (say attributes 0.97, LINK 0.30). That is acceptable: the raw split is printed for every seed,
and a failure that matches neither signature is reported as **"unnamed failure"** — not re-labelled
after the fact. Signatures are read on the reserved scoring (and also printed for the training-pool
scoring), as built. They describe; they never change a verdict.

### Q8 — predictions, restated for hashing

The four from §5, **exactly**:

| # | Statement | Probability |
|---|---|---|
| P1 | The treatment passes in 3/3 seeds (all ten reserved-code cells ≥ cutoff and paired mark met) | **0.35** |
| P2 | The treatment passes in at least 1 seed | **0.65** |
| P3 | Any seed passes on training-pool codes but fails on reserved codes | **0.05** |
| P4 | The control reproduces (≥ 2/3 seeds meet the ten cutoffs) | **0.85** |

Added now, before any data. None of these affects the verdict; all go in the predictions ledger and
are scored afterwards.

| # | Statement | Probability |
|---|---|---|
| P5 | At least one treatment seed shows the **never-started** signature (reserved scoring) | 0.30 |
| P6 | At least one treatment seed shows the **attributes-fine-LINK-at-chance** signature | 0.12 |
| P7 | At least one treatment seed fails with **neither** signature ("unnamed failure") | 0.35 |
| P8 | At least one treatment seed trips the **speed-limit flag** (Q4) | 0.25 |
| P9 | In every treatment seed that passes, final `code_scale` lies in [0.7, 2.5] (void if no seed passes) | 0.65 |
| P10 | Open-set (A), 1,024 reserved codes: pooled first-stage-LINK accuracy ≥ 0.90 in every passing treatment seed (void if none) | 0.50 |
| P11 | Open-set (B), all 4,096 codes: same statistic ≥ 0.90 in every passing treatment seed (void if none) | 0.40 |
| P12 | `wide64-attr` ≥ 0.90 in every passing treatment seed (void if none) | 0.55 |
| P13 | `wide64-link` ≥ 0.90 in every passing treatment seed (void if none) | 0.35 |
| P14 | At least one control seed shows the never-started signature | 0.10 |

Why P1 is only 0.35 when F2 says geometry is fine: the risk is not geometry, it is *learning
dynamics* — a start-up lottery made somewhat worse by names that never stay put (the model cannot
lean on a stable identity for anyone while it is finding the lookup trick), plus the scale speed
limit. I am genuinely unsure, which is what 0.35 means.

### Q9 — 12-person cells keep 16 bound codes. **Confirmed as built. No code change.**

In the control, a 12-person world still has all 16 entity rows in the output, four of them naming
nobody; those four are live wrong answers. Binding 16 codes reproduces that exactly. Binding only 12
would make the treatment's exam easier than the control's on precisely the cells where two of the
four strictest marks (487) sit. Faithful beats tidy.

### Q10 — the paired mark is one-sided (reserved − training-pool ≥ −13/512 on every cell). **Confirmed as built. No code change.**

The mark exists to catch one thing: doing worse on never-seen names than on seen ones. Doing better
on never-seen names is not a failure of generalisation and must not fail the seed.

One reporting addition (words only): because the training/reserved split is a random cut of
identically made codes, the honest expectation is a difference near zero in **both** directions. If
any cell shows |reserved − training-pool| > 13 in **either** direction, print the line
"paired difference larger than expected — check panel-code luck or a binding bug" beside it. A large
positive gap is not a pass with honours; it is a reason to look for a bug.

---

## 2. Rulings summary

| Q | Ruling | Code change |
|---|---|---|
| Q1 | Frozen `random.Random(1101)`, shared by arms and seeds; limitation sentence in report | none |
| Q2 | Control's marks = the same ten cutoffs; VOID rule stands; "failure matched in control" wording | none |
| Q3 | Codes re-drawn every visit of every update | none |
| Q4 | One learned scalar, not shared with value rows, init 0.13856; speed-limit flag defined | **C1 (logging only)** |
| Q5 | Gate on 16 candidates; open-set scoring specified here, separate additive script later | none now |
| Q6 | Seed-independent panel codes | none |
| Q7 | Builder's thresholds confirmed; "unnamed failure" category | none |
| Q8 | P1–P4 restated exactly; P5–P14 added | none |
| Q9 | 16 bound codes on 12-person cells | none |
| Q10 | One-sided paired mark; two-sided warning line in the report | none |

---

## 3. Should M1 wait for the outside (GPT-6 Pro) review? **No. I agree with the coordinator: freeze and run M1 as designed; any pointer/copy-output variant is a separate, later experiment.**

1. **The run is the measurement the review would be guessing at.** "Do codes collide, and are the
   softmax margins big enough at width 48?" is an empirical question. M1 costs nothing and takes
   under half an hour; the open-set scoring (Q5) then reports the actual margins and whether errors
   are look-alike collisions. An analysis without those numbers cannot settle it; an analysis *with*
   them is much more useful. Send the results to the outside reviewer afterwards.
2. **For the gated test the collision worry is already answered** (F2): the control's trained names
   are more alike than random codes, and it passes. Collisions can only bite at 1,024–4,096
   candidates, which is descriptive here.
3. **A copy/pointer output is a second change.** It replaces the output head for person answers. If
   M1 were run with both new names and a new output and failed, nobody could say which one did it.
   One change at a time is Ben's own rule.
4. **Freezing now protects the registration.** Changing a design after reading an opinion is fine;
   changing it after reading data is not. Hashing today removes the temptation entirely. Whatever
   the outside review says, this registration is not amended after launch.

My own view on the pointer question, so it is on record before either the data or the outside
answer: comparing the answer vector with candidate codes *is already* a pointer-by-content, and it
is adequate for 16 candidates. A true copy output (attend over the story rows and copy the token
found there) does not need the answer vector to carry a clean 48-number direction, so it should
scale better to thousands of names and is probably the right design by M3 (4,096 facts). The
trigger for registering it as its own experiment ("M1c"): open-set (B) accuracy below 0.90 in
passing seeds, or `wide64-link` weak, or the outside review gives a concrete argument that survives
the measured margins. Ask the outside reviewer to state a number for open-set (B) accuracy before
seeing ours; that makes their analysis checkable too.

---

## 4. What each verdict licenses

* **PASS (3/3):** permitted sentence — *"On this toy, with one world stream and three seeds, an
  operator trained with names re-assigned at random every time answers lookup and chained questions
  about 1,024 names it never trained on, choosing among the 16 names in the story."* Not permitted:
  "open vocabulary", "learns new words", anything about English, anything about choosing among
  thousands (that is the open-set scoring, descriptive, and is reported as such). Next: M1b / M2 per
  the roadmap, and the open-set script.
* **PARTIAL (2/3):** no claim. Report in full. Next: fresh registration with more seeds
  (2103–2108), nothing else changed.
* **FAIL:** no claim. Read signatures and the `code_scale` trace in the order given in Q4. A
  speed-limited or LINK-at-chance failure → the 7×-learning-rate-scalar follow-up. A never-started
  failure → it is the start-up lottery again, and names made it worse; that is a finding about the
  recipe, not about names.
* **VOID / INCOMPLETE:** no claim. A wave killed by the time cap may be re-run **once**, unchanged,
  same seeds, only if no score file has been opened; otherwise fresh seeds 2103–2105 under a new
  registration.

---

## 5. Conditions before launch (numbered; all must hold)

1. C1 applied exactly as written in Q4; no other change to `scripts/fable_newnames21.py`.
2. Independent auditor confirms the C1 diff touches only the three named places (plus tests).
3. All tests pass after C1.
4. After C1: 50-update control run is bit-identical to the registered grow-blind recipe (re-proved
   with the post-C1 script), and the 50-update treatment fingerprint (seed 2100) equals the pre-C1
   one.
5. `run_data.sh` completed with the post-C1 script: `pool/pool.json`, `panels/manifest.json`,
   `panels/audit.json`, `control-equivalence.json` exist and their gates passed.
6. Auditor confirms, per cell, that the `reserved` and `train` scorings share worlds, questions and
   order, differing only in the code subset (Q6), and that reserved codes appear nowhere in the
   training code stream (first 50 updates checked directly; the subset construction checked by
   reading).
7. SHA-256 recorded, in a new pre-registration note in the experiment folder and as a new entry in
   the predictions ledger, for: this file; `design/v3/21-teachable-assistant-roadmap-fable-review.md`;
   `scripts/fable_newnames21.py`; `tests/test_fable_newnames21.py`; the three launchers;
   `pool/pool.json`; `panels/manifest.json`. Predictions P1–P14 are entered in the ledger with the
   probabilities above. All of this is timestamped **before** `run_train.sh` starts.
8. The Mac is not running another heavy job during the wave (the projected 23 minutes already
   assumes some contention; the watchdog caps 1,680 / 1,740 / 1,770 s stand and are not raised).
9. No scoring until all six training runs have written `completion.json`. Heartbeats may be watched:
   they contain time and `code_scale`, not accuracy.
10. M1 does not wait for the outside review, and the registration is not amended after launch for
    any reason, including that review.
11. Reporting: every seed, every cell, all three scorings (control / reserved / training-pool), both
    signatures, the `scale_trace`, the speed-limit flag, the wide-64 cells, the Q1 limitation
    sentence, and only the §4 wording for whichever verdict occurs.

---

## 6. Five lines for Ben

1. The builder did a careful job and I changed almost nothing: nine of the ten questions are "yes, as built", and the one code change only writes two extra numbers into the log — it cannot affect training, and the auditor can prove that by running 50 steps before and after.
2. I checked six of your already-trained models and found that the names they learned are actually *more* alike than the random names we are about to use, so "random names will get confused with each other" is not a real danger for this test; the real danger is whether learning gets going at all when names never stay put.
3. I also found one thing worth watching: in the new version the "loudness" of all names is a single dial, and the optimiser can only turn a single dial slowly — about seven times slower than the old version could grow its names — so the log will now show that dial, and I wrote down in advance what "too slow" looks like.
4. Don't wait for the outside review: this run is free, takes under half an hour, and produces the very measurements that review would otherwise have to guess; a "copy the name from the story" output is a good idea for later but is a second change, so it gets its own experiment.
5. My honest odds, written down before any data: 35 % it works in all three runs, 65 % it works in at least one, 85 % the old version still works as a check — and if it passes, the only thing we may say is that it handles names it never saw *when choosing among the 16 in the story*, nothing bigger.
