# AR1: later replay in one label-free dense reasoner

Prepared 2026-09-27. This exact document must be committed and pushed to main
before any model construction, software test, throughput probe or training run.
Pushed marks never change. Implementation repairs must preserve this protocol;
record them separately. No model or test has run for this task before registration.

## Question and one change

Can moving a fixed amount of grid rehearsal later in the sequence preserve the
first skill without sacrificing the next two? The candidate changes **only the
training replay schedule** relative to the paired local baseline. No frozen
experts, per-skill model copies, teacher models, extra trainable parameters,
task labels supplied to inference, or hand-written inference routing are used.
The previous R2 remains a yardstick, not evidence for this requirement.

The historical e4 baseline received an oracle `env` embedding. To satisfy this
task, BOTH new arms receive the same common label-free front end. Reuse that
table's four 256-dimensional rows as learned context vectors: let x be token
embedding plus answer-slot embedding, q = mean(x over the visible cells),
p = softmax(q @ context_vectors.T / sqrt(256)), and add p @ context_vectors to
every x. All vectors train solely through the ordinary answer and stopping
losses; there is no kind-label target, auxiliary classifier loss or class-to-
context assignment. This parameter-neutral replacement is common experimental
scaffolding, not the candidate intervention. The locally rerun baseline, not
470.17 from the cloud, defines every comparison. It is e4 dense/full-replay with
this explicitly disclosed mandatory input change, not an exact replication of
the historical labeled-input scores.

## Model, requests and data

- Exactly **1,646,750 trainable/model parameters** in each arm at every phase,
  including all context parameters. Width 256, two dense loop blocks, eight
  heads, the original half-narrow attention, state normalization and stop head.
  All parameters remain trainable. No persistent request state or skill cache.
- Public inference accepts only a `PuzzleRequest` containing rectangular token
  and answer-slot arrays. It never receives `env`, task name, size field, target,
  metadata, phase, panel name or file path. Native geometry is visible puzzle
  content, not a supplied task ID. No rule maps geometry or tokens to a skill.
  Each request starts a blank recurrent state and runs this same one network.
- The existing e4 sealed import chain supplies code generators and exact
  checkers. Practice distributions remain grids4/5, sums1–4, mazes5/7; graded
  panels are grids5, sums4 and maze7. No natural-language training text, external
  model, blind panel, download or purchased compute is used.
- Training seeds: **41, 42, 43, 44, 45, 46**, paired across both arms. Torch seed
  is the training seed; practice RNG is `5800+seed`, recurrent-depth RNG
  `5900+seed`, with the original 3,000-item Latin base pool at each practice size.
  Generators retain their original shared practice RNG. The schedule changes
  which generator consumes it; post-A example identities can therefore differ
  between arms. Data distributions and generation rules remain identical.
- Final panel RNG seeds, corresponding in order to the six training seeds:
  **927204781031, 927204781032, 927204781033, 927204781034,
  927204781035, 927204781036**. Each generates 200 unique requests per kind in
  the order grids5, sums4, maze7, rejecting duplicate visible inputs. Then shuffle
  all 600 requests with that same RNG. Every phase uses this fixed mixed order.
- Diagnostic context-mapping seeds are **927204782031–927204782036**, likewise
  paired, each generating 100 unique requests per kind. They never select model
  weights, schedule or thresholds. All 12 literal seeds were searched before
  registration with `rg -l --hidden --no-ignore -F`; no occurrence was returned.
  `.git`, root `notebook/` and secret-file patterns were excluded. This was a
  literal seed-occurrence search, not inspection or scoring of any blind panel.
- Reject and count exact visible-input matches between practice and either
  final or diagnostic panels. Replacements preserve the sampled kind and size.
  Panels are never used to choose training length, checkpoint or hyperparameters.

## Fixed budgets and update rule

| Arm | A: grids batches | B: grids / sums | C: grids / sums / mazes |
| --- | ---: | ---: | ---: |
| baseline | 2,500 | 250 / 2,250 | 75 / 75 / 1,350 |
| late_replay | 2,500 | 125 / 2,375 | 200 / 75 / 1,225 |

Both arms use exactly **6,500 optimizer steps, batch 64, 400 earlier-kind replay
batches: 325 grids and 75 sums**. The candidate moves 125 grid replay batches
from B to C. It substitutes 125 additional sums batches in B and removes 125
maze batches from C (9.26% fewer maze batches). These exposure changes are the
explicit cost of the one scheduling intervention.

Replay slots are spread by integer accumulation: at phase step i, a replay
occurs when floor(i*r/n) exceeds floor((i-1)*r/n), where r is the phase's replay
count and n its fixed steps. In C, number the replay slots j from 1; choose sums
when ceil(j*75/r) exceeds ceil((j-1)*75/r), otherwise grids. This gives the
baseline's every-tenth-step and sums/grid alternation exactly. No score changes
this schedule. A has no replay.

Use e4's fresh AdamW per phase: lr 0.001, weight decay 0.1, betas (0.9,0.95),
100-step warmup and cosine to zero over that phase. Each batch draws 1–16
recurrent rounds and 1–min(total,6) gradient rounds; use mean answer CE plus
0.5 stopping BCE over graded rounds and gradient clipping at 1.0. Float32 MPS,
four CPU threads. Both arms use the same software/device/precision. No tuning,
extra replay updates, model averaging, early stopping or chosen-best checkpoint.
All 12 trajectories run regardless of the first result, unless integrity,
hardware or the user's usage-stop rule prevents completion. Alternate paired
execution order by seed: baseline first on odd seeds, candidate first on even.

## Evaluation and integrity

At A/B/C boundaries, present the shuffled mixed stream **one request at a time**
without padding, hidden labels, batch neighbors or a hand-written router. Record
all 48 rounds of predicted tokens and stop probabilities. Select the first
round from zero-based 2 whose stop probability exceeds 0.5 and whose predictions
equal the preceding two rounds; otherwise select round 48. Only after the full
stream's predictions and stops are fixed may the offline exact checker consult
the oracle metadata. Primary correctness is the model's own stop; fixed16,
any48 and mean stopping rounds are report-only. Report pre-practice scores on
future kinds at A/B as limited carry-over observations, not general transfer.

Save raw predictions, panel fingerprints, practice/replay counters, source hashes,
timings and the final single model checkpoint. Earlier phase predictions may be
saved for audit; no earlier model is used for answering. A temporary interruption
checkpoint, if needed, is only the latest training state for exact continuation.

M4 software controls, before training and again on a fixed two requests per kind
after C: poisoned hidden metadata must leave visible requests and every output/
stop unchanged; shuffled order and repeated requests must yield identical
outputs/stops; the public interface has no label/target argument; no checker
runs inside inference; parameter count and single-model architecture hold.
Verify loss gradients reach learned context and both dense blocks. Save/reload
must reproduce the same mixed-request outputs. Any integrity failure invalidates
the run rather than counting as a capability score.

For report-only context agreement after C, assign each of the four context
argmax indices its majority true kind on the separate 300-item diagnostic set
(ties use grids, sums, mazes order), then fix that map and report agreement on
the 600-item final set. This map never enters the model or selects weights. It
describes learned context separation, not a supervised task switch; mixed exact
correctness is the graded end-to-end test. The three native formats are visibly
distinct; success cannot establish inference on ambiguous or reformatted tasks.

## Marks and falsifier — exact six-seed integer sums

Let G be grids5 after C, S be sums4 after B, L be maze7 after C and
T = grids5+sums4+maze7 after C. Each kind is out of 200 and T out of 600.

- **M1 keep:** candidate mean G >=180 AND every candidate G >=160.
- **M2 learn:** candidate mean S >=195 AND mean L >= baseline mean L −10.
- **M3 overall:** candidate mean T >= baseline mean T +40 AND candidate T is
  strictly higher on at least five of the six paired seeds.
- **M4 no leak / budget:** all integrity controls pass; every run uses exactly
  the declared parameter count, input contract, steps, batch and kind/replay
  counts, with the same MPS precision/software for both arms.
- **Proved wrong for this replay-timing idea:** candidate mean T <= baseline
  mean T **OR** candidate mean G <= baseline mean G.

Verdict precedence: missing/interrupted trajectories => **INCOMPLETE**;
integrity/budget failures => **INVALID**; otherwise the falsifier =>
**PROVED WRONG**; otherwise all M1–M4 => **PASS**; otherwise =>
**FAIL (not proved wrong)**. No post-score validity floor, threshold relaxation,
pooling with previous experiments, replacement seed, or new definition of PASS.

## Predictions and interpretation before any run

My judgment: PASS 20%, PROVED WRONG 30%, other FAIL 50%. I expect candidate
grids after C around 165–190, a T improvement around 15–55, sums after B >=195,
and a maze difference around −15 to +5. These are uncertain predictions, not
additional marks. Moving replay later may repair old grids, but may leave B's
grids too damaged or reduce maze practice too far.

The brain-inspired analogy is rehearsal during new learning; it is an analogy,
not a neuroscientific claim. Prior replay-scheduling research motivates testing
timing, but does not validate these chosen counts or this architecture:
[Learn the Time to Learn](https://arxiv.org/abs/2209.08660).

## Execution, review and stopping

All new scripts, manifests, logs and results remain under
`artifacts/codex-autoroute-20260927/`. Never alter old scripts, seals, root
notebook, handoff queues, watcher jobs or BensPC. Only our processes may stop.
Commit/push marks before the bounded preflight (software invariance, gradients,
serialization and untrained throughput only); commit/push final implementation
before scientific trajectories. No data-dependent architecture selection in
preflight. Runtime corrections preserve the hypothesis and get a separate note.

Each run records `date -u`, machine, PID, command, registration/software commit,
device, minutes and completion state. If remaining account usage drops below
20%, stop our runs cleanly and report INCOMPLETE; no reset or purchase. Training
interruptions must preserve the last complete update and mark progress honestly.
The final recount must independently score saved raw predictions for every phase
and reproduce final-checkpoint predictions under the same device/software.
RESULTS uses the marks' verdict words, all six paired rows, shown/suggested/
untested claims and a plain-language explanation. No claim concerns the 1B chat
model, joined build, or project approval.
