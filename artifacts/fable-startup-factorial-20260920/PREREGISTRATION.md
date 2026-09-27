# Why does the short-story curriculum let answer-only learning START?

Written 2026-09-20 EDT, before any run of `scripts/fable_startup_factorial.py`. Drafted by
the build agent from Ben's brief. **Review and amend before running `freeze`: `freeze`
hashes this file and `check_manifest` re-verifies the hash before every worker and every
wave.**

## The question

`e0` — answer cross-entropy only, full ~45-line stories from update 0 — learns perfectly
on seed 0 and never starts on seeds 1 and 2 (seed 1 emits one constant token on every
one-hop question, 37/512; seed 2 emits 10 distinct answers, 52/512). `grow-blind` — the
same loss, but for updates < 1,500 each visit keeps only 16 uniformly random fact lines of
its 24 and no filler or gap lines, with the questions rebuilt to be answerable from those
16 — starts on 6/6 seeds.

We do not know why. `grow-blind`'s early phase changes three things at once:

1. the filler and gap lines are gone (~21 lines, roughly two thirds of the tokens);
2. only 16 of the 24 competing fact lines remain;
3. questions the kept facts cannot answer are replaced.

A reviewer asked for the causes to be separated before anything else changes. This
experiment separates 1 from 2 while holding 3 **exactly** constant, by construction.

## Part 1 — the 2×2 factorial

| arm | fact lines the model may read | filler and gap lines | equals |
| --- | --- | --- | --- |
| **A** | 16 | none | `grow-blind`'s early phase, verbatim |
| **B** | 16 | all | — |
| **C** | 24 | none | — |
| **D** | 24 | all | the full story, i.e. `e0` |

### What is held constant, and how

All four arms of a given (seed, update) share **one plan**, drawn before any arm is
chosen:

* the same worlds, from the same registered `random.Random(1101)` stream, consumed exactly
  as the base recipe consumes it (`toy_ladder.visit` per visit plus the trailing
  `randrange`) — checked against the registered batch builder;
* the same 16-fact subset, drawn **label-free** by `grow-blind`'s own selector
  `fable_operator_startup._blind_keep(vrng, rows, 16, 0.0)` (a uniform draw over the
  visible fact rows: `row[0] == [world]`, `row[1]` an entity token 52..67, `row[2]` in
  8..11);
* the same records, built from those 16 facts by `grow-blind`'s own constructors.

Arms C and D then add the other 8 fact lines back; arms B and D add the filler and gap
lines back, **in original order**. So at every update the questions, the answers and the
supporting facts are **bit-identical in all four arms**, and the arms differ only in which
story rows the model may read. The check suite asserts this directly (identical question,
owner and answer tensors; the supporting line of every record is the same *original* row
in every arm; the kept rows of each arm are a subset of the full story in original order,
with A ⊂ B ⊂ D, A ⊂ C ⊂ D). Model initialisation is `A.new_model(seed)`, identical per
seed across arms; the variant RNG is keyed `fable-startup-factorial:<seed>` with **no arm
in the key**, which is what makes the plans shared.

Causal eligibility is preserved exactly as in `grow-blind`: the question keeps its place
in the visit, counted in kept rows, and a kept line is eligible for a question iff it was
eligible in the original visit. In this generator every story row precedes every question
row, so each question's eligible set is exactly the real kept rows of its visit; the check
suite asserts that equality rather than assuming it.

### The record recipe, stated exactly

It is `grow-blind`'s, unchanged. Per visit, **from the 16 kept fact lines only**:

* each of the generator's two one-hop questions → one `one_hop` canonical record. The
  generator's question is used unchanged when its fact line is kept; otherwise it is
  replaced by `balance`'s constructor (entity uniform over the world's six people,
  relation uniform 1/3 each), rejecting draws whose fact line is not kept;
* each of the generator's two two-hop questions → a `link` record `[4, a, 11, 5]` answered
  by the kept LINK row, a `terminal` record `[4, b, r, 5]` answered by the kept attribute
  row, and a five-token `monolithic` record `[4, a, 11, r, 5]`. The generator's (a, r) is
  used when both lines are kept, else a fresh (a, r) is drawn uniformly from the pairs
  that **are** answerable from the kept facts, r ∈ {8, 9};
* safety valve, counted and never silent: if the kept facts support no two-hop question at
  all, a one-hop record is emitted in its place;
* hop count and relation come from the **visible question tokens**; every answer and every
  supporting line is read off a kept visible fact row. `row.gold`, `row.supplied`,
  `row.answer`, `row.hops` and `row.relation` are never read;
* relation 10 is never a two-hop terminal.

**Loss:** pure answer cross-entropy, 0.75 × canonical + 0.25 × monolithic, one backward
pass per group, clip 1.0, AdamW as registered — `fable_operator_variants._step_e0`
verbatim, asserted bit-for-bit by the check suite. **There is no supporting-line attention
term at any update, in any arm.** No evidence loss, no gold intermediate beyond what the
recipe above already uses.

**What is still supervised, stated plainly:** the link/terminal decomposition hands the
model the true intermediate entity as a target. `grow-blind` obtains it by reading the
visible `[world] a LINK b` row instead of from `row.gold`, which removes the *annotation*
but not the *supervision*. This experiment inherits that exactly and claims nothing more.

**Learning rate:** the registered constant phase, `1e-3 * min(1, (step+1)/100)`, which is
`fable_operator_variants.lr_at(step)` for every step < 4,000. The default run is 2,500
updates, so the whole Part 1 run sits inside that constant phase.

**No growth.** The condition is held fixed for the whole run, because the question is
which condition lets learning **start**, not whether a started model survives growth.

### The definition of "start"

Fixed here and nowhere else, and applied per seed, never averaged:

> A run has **started** iff **every** logged probe in the last 200 updates shows
> one-hop accuracy ≥ 0.90 on the fixed probe batch.

At the default `--log-every 50` that is the last 4 probes of a 2,500-update run. The probe
is a fresh draw from the **training distribution and the run's own condition** — same
world generator, same record recipe, same story size — on its own RNG streams, so its
stories are not the literal training stories but are as easy as them. This is deliberately
a near-train criterion: it asks whether the lookup is being learned at all, not whether it
generalises to full-size stories. The generalisation question is answered separately by
the c1 panel below, and a run can start and still fail c1.

### Diagnostics, every 50 updates on a FIXED probe batch

The probe batch is drawn once per run from its own two RNG streams
(`fable-startup-factorial-probe:<seed>` and `…-probe-v:<seed>`), so building it cannot
perturb training. Its questions are identical across arms (same plan mechanism); its story
rows follow the arm, so it measures the model in the condition it is actually trained in.

1. **Correct-line attention.** Attention mass on the correct supporting line at the last
   question token, per read step and per head, together with the value expected under
   uniform-over-eligible-tokens attention for that story (line tokens ÷ (eligible tokens +
   1), the +1 being the model's NULL key). Reported as absolute mass and as a ratio to the
   uniform baseline, so the four arms are comparable despite different story sizes.
2. **The routing gradient.** How one plain SGD step on the answer loss alone changes the
   correct-line mass — the exact directional derivative
   `d/dη mass(θ − η ∇L)|_{η=0} = −⟨∇L, ∇mass⟩`, and the finite difference
   `mass(θ − η∇L) − mass(θ)` at η = 1e-2, with both gradient norms and their cosine. Plain
   SGD, no Adam preconditioner and no clipping, so the sign and size are properties of the
   answer loss itself. Reported for all canonical records and for the one-hop records
   alone.
3. **Prediction collapse.** Number of distinct predicted answers, top-1 share, entropy;
   one-hop accuracy per relation (8, 9, 10); link accuracy.
4. **Training.** Loss and accuracy on that update's real batch, plus probe loss/accuracy
   and the gradient norm.

Every diagnostic runs under `torch.no_grad` or on a `deepcopy` of the model. The check
suite poisons every `.grad` with a sentinel, runs the diagnostics, and asserts every
parameter and every gradient is bit-identical; and it asserts a fully logged run and a
silent run end with the same fingerprint.

### End-of-run scoring

The final checkpoint is scored on the registered **c1** one-hop panel (512 full-size
six-person questions). The panel file is loaded **read-only**, with its sha256 re-verified
against the registered manifest; nothing is written inside any registered folder. c1's
semantics are in the registered exclusion set, which this run enforces on every training
record against the full story, so c1 is unseen. A freshly generated 512-question
full-story probe set is scored alongside it as a second, independent read.

### Readings

Stated in advance, per seed, never averaged.

* **A and C start, B and D do not** → removing the filler is sufficient; the number of
  competing facts is not the issue.
* **A and B start, C and D do not** → fewer competing facts is sufficient; the filler is
  not the issue.
* **Only A starts** → both are needed; the mechanism is total distraction, not either
  ingredient alone.
* **D starts in some seeds and not others** → there is no barrier to break, only luck and
  time; the right follow-up is Part 3 (more updates), not more curriculum.
* **All four start** → the difference is elsewhere in `grow-blind` (question replacement,
  or growth itself), and this design has answered a question that was not the question.
* **Correct-line attention (or the routing gradient) does not rise before accuracy moves**
  in the arms that start → the dilution explanation needs revision: the curriculum would
  then be helping through something other than making the right line easier to find.
* The routing gradient is the sharper instrument of the two: if its directional derivative
  is reliably positive in A and reliably near zero or negative in D, that is direct
  evidence that answer-loss updates fail to route attention in the big story. If it is
  positive in every arm, dilution is not the bottleneck and the difference must be in the
  size of the step, not its direction.

## Part 2 — freeze-before-growth transfer (`size-sweep`)

Take the arm-A checkpoint — trained **only** in condition A, no growth, no further
updates — and evaluate it with **no training** on fresh probe sets of increasing story
size: fact lines {16, 24} × filler fraction {0, 0.5, 1.0}, and the same six cells again on
16-person worlds at one hop. Reports one-hop accuracy, correct-line attention and the
uniform baseline per cell. The checkpoint's fingerprint is asserted unchanged before and
after.

Reading: if accuracy and correct-line mass hold up across all six six-person cells, the
short-story model already holds a size-independent lookup rule, and `grow-blind`'s growth
phase is only protecting something it already had. If accuracy falls as filler is added at
fixed fact count, the rule is size-dependent and the growth phase is doing real work. The
16-person cells say whether the rule also survives unfamiliar world size; a drop there
alone is a weaker finding, because 16-person worlds are out of the training distribution
in a second way.

## Part 3 — extension of the failed full-story runs (`extend`)

Condition D for **18,000 updates** under a declared schedule: warmup to 1e-3 over 100
updates, constant 1e-3 to update 16,000, then linear to 1e-4 at 18,000. Same logging as
Part 1. A checkpoint is written every `--chunk-seconds` (default 1,200 s) so each wave
stays under 30 minutes; rerunning the same command resumes. Resume restores the model, the
optimizer, the torch RNG state and **both** data-stream RNG states exactly; the check suite
proves a split run equals an unsplit run bit-for-bit.

Reading: if a D seed that failed at 6,000 updates starts by 18,000, the barrier is time,
not structure, and the whole curriculum story is about speed. If no D seed starts by
18,000 while its A twin starts within a few hundred updates, the barrier is real.

## Honesty notes and known limits

* This experiment separates causes 1 and 2 and holds cause 3 constant. It **cannot** say
  what question replacement alone does — that needs a fifth arm (full story, replaced
  questions), which is deliberately not run here because Ben asked for one careful
  experiment, not a catalogue.
* "Start" is a **train**-accuracy criterion on the probe batch. c1 is the generalisation
  read. A run can start and still fail c1; that would itself be informative and is
  reported.
* Arms differ in compute per update (arm A reads ~16 rows, arm D ~45), so they are **not**
  matched on FLOPs or on wall clock, only on updates. Any claim of the form "A learns
  faster than D" means *per update*.
* The probe batch is drawn in the run's own condition. Correct-line mass is therefore not
  directly comparable across arms in absolute terms; the uniform-baseline ratio is the
  comparable quantity, and both are reported.
* Everything this file's script writes goes to the worktree folder
  `artifacts/fable-startup-factorial-20260920`. The registered panels, the exclusion set
  and every registered source are read-only inputs, hash-verified before every worker and
  every wave.

## Fable's predictions

Written 2026-09-20 by Fable before freeze; no arm has been trained (longest run so far: 205 timing updates on dev seeds).
My forecasting record on this project is poor (3 hits / 7 misses so far), so these are stated to be scored, not trusted.
"Starts" uses the registered definition above. Seeds 0, 1, 2.

| id | forecast | p | falsified by |
|---|---|---|---|
| P13 | arm A (16 facts, no filler) starts in 3/3 seeds | 0.80 | any seed fails to start |
| P14 | arm C (24 facts, no filler) starts in ≥ 2/3 | 0.55 | ≤ 1 starts |
| P15 | arm B (16 facts, full filler) starts in ≥ 2/3 | 0.40 | ≤ 1 starts |
| P16 | arm D (full story) starts in ≥ 2/3 within 2,500 updates | 0.15 | ≥ 2 start |
| P17 | in every run that starts, correct-line attention rises to ≥ 2× its uniform-over-tokens value BEFORE one-hop accuracy first passes 0.5 | 0.70 | a starting run where accuracy passes 0.5 first |
| P18 | the routing-gradient check is positive (answer-loss step raises correct-line attention) in ≥ 80 % of probes during the first 500 updates of arm A, and in < 80 % for arm D | 0.45 | either half false |
| P19 | size sweep: arm-A checkpoints, frozen, score ≥ 0.90 one-hop on the largest story setting (24 facts, full filler) in ≥ 2/3 seeds | 0.45 | ≤ 1 seed |
| P20 | Part 3: arm D extended to 18,000 updates starts in ≥ 2/3 seeds | 0.50 | ≤ 1 starts |

If P17 fails, my "diluted attention" account of the stall is wrong or incomplete and I will say so.
