# LINK isolation v2 — can the LINK call be learned against a QUALIFIED terminal lookup?

Written 2026-09-20 EDT, before any `fable-link-isolation-v2` run, from
`design/v3/18-link-isolation-v2-preregistration-draft.md` (the design owner's spec). The
predecessor `fable-link-isolation-20260920` (v1) was frozen and then **withdrawn before any
run**; see `artifacts/fable-link-isolation-20260920/WITHDRAWN-BEFORE-ANY-RUN.md`. Its
predictions P21–P25 are void.

**Review and amend before running `freeze`: `freeze` hashes this file and `check_manifest`
re-verifies the hash before every worker and every wave.**

Scope: Track A only. The scope is **discovering the intermediate person under a supplied
two-call decomposition**. Preserve existing staged runs and frozen isolation files. No
training during active Mac waves.

## The problem with the existing evidence

`marg-staged` activated the marginal **before attribute lookup was competent**. It therefore
does not test learning LINK against a competent terminal. Record-density and monolithic-loss
interference remain separate hypotheses and are not tested here.

The open problem is to learn the LINK call with **no label for the middle person** — only the
final answer `y` — through the exact marginal

```
-log sum_e p_link(e | S, x, LINK) * p_term(y | S, e, r)        e over the 16 entity tokens 52..67
```

A reviewer's hypothesis is **mutual interference**: both calls are the same 79,316-parameter
model, so the terminal lookup is dragged around by LINK's uncertain choices at the same time
as LINK needs a terminal lookup that already tells the candidates apart. Detaching the
gradient does not settle it, because the shared weights still move. The only way to settle it
is to make the terminal distribution literally unable to move — **after** establishing that
it is worth freezing.

## Stage A — establish the prerequisite

Attribute-only setup: **no LINK target, no supporting-line loss, no monolithic questions.**
Six attribute-answer records per visit, 16 visits per update, three relations (8, 9, 10), six
people, the rescaled 79,316-parameter operator (`I.rescale`, as the successful operator uses).

* **Curriculum:** `grow-blind`'s label-free small-story curriculum (a uniformly random subset
  of each visit's fact lines, recognised from **visible tokens only**, `--blind-lines 16`,
  grown back to the full story linearly over [G1, G2) = [750, 1500)).
* **Records:** one attribute record at each of the visit's four question lines — the
  generator's own one-hop question when its fact line is kept, a replacement drawn from the
  kept facts otherwise, and **always** a replacement at each of the two two-hop question
  lines — plus K = 2 further attribute records at the first question line. Six single-call
  attribute records per visit, all attribute. A LINK query is never constructed.
* **Loss:** the mean answer cross-entropy over those records.
* **Schedule:** 3,000 updates, the v3r lr shape rescaled to the stage length. **Retained from
  the proposal, as the spec permits**, and frozen here with every coefficient and RNG state.
* **Seeds 1400, 1401, 1402**, with **independently named** model and data RNG streams:
  `…-v2-model`, `…-v2-torch`, `…-v2-world`, `…-v2-a`, `…-v2-a-extra`, `…-v2-b`,
  `…-v2-validation`. Each seed therefore gets its own worlds. (v1 drew every seed's worlds
  from `random.Random(1101)`; that is fixed here.)
* **Output:** `stage_a.pt` — weights, optimizer state and every RNG state.

### The qualification gate

**Only the fixed final stage-A checkpoint can qualify.** On a **separate, prebuilt full-story
validation set** (`qualification`, six-person worlds), require, as integer counts:

* **≥ 487/512 attribute answers independently for each relation 8, 9 and 10**, and
* **≥ 487/512 terminal answers given the TRUE endpoint of practised two-hop questions.**

The second criterion is an **evaluator-only diagnostic**: the true endpoint is supplied to the
terminal call by the evaluator. It is never a training label and never an input to LINK.

The gate also **reports terminal discriminability**: the probability of the observed answer
under the true person versus the mean under wrong *present* people, **stratified by
answer-value collisions** (whether some wrong present person happens to hold the same answer
value).

The gate is evaluated once, by the `qualify` command, between the stage-A and stage-B waves.
It writes an immutable `qualification.json` per seed carrying the verdict, the counts, the
stage-A checkpoint's sha256 and the launch manifest's sha256.

**Stage B refuses to run for a seed** whose `qualification.json` is missing, says not
qualified, or was evaluated on a different checkpoint or a different manifest. A failed seed
is reported as **“stage A failed; stage-B hypothesis untested for this seed.”** There are no
replacement seeds, no checkpoint search and no silent extension. An extended stage A would be
a new registration.

Qualification data is **development validation**. A separate confirmation set is reserved (see
below) and is read only at final scoring.

## Stage B — shared versus frozen, plus a clean absent-candidate arm

Every arm starts from the **same** `stage_a.pt` — identical trainable weights, identical
optimizer state, identical data/RNG state — and sees **identical full stories, questions and
ordering**. The batch builder never reads which arm it is serving and the stage-B curriculum
RNG namespace does not contain the arm; the check suite asserts byte-for-byte identical
batches across arms, over eight fresh batches and again after three real updates once the
models have diverged.

Each batch: **two attribute-only records plus two marginalised two-hop records per visit; no
monolithic loss.** Coefficients stay **1/3 attribute CE + 1/3 marginal** — `marg-full`'s
equal-weight-per-record rule with the monolithic group **removed, not renormalised away**.

| arm | kind | `p_term` comes from | marginal sums over | `p_link` renormalised |
| --- | --- | --- | --- | --- |
| `shared` | primary | the trainable model, gradients through both calls | all 16 entity tokens | no |
| `frozen` | primary | a separate immutable stage-A copy, no gradients | all 16 entity tokens | no |
| `frozen-present-mask` | primary | the same immutable copy | only the people **visibly present** | **no** |
| `detached` | **diagnostic, NOT frozen**, behind `--include-detached` | the **moving trainable weights**, detached | all 16 entity tokens | no |

* **`frozen-present-mask` is the clean absent-candidate contrast.** The two primary arms sum
  over all 16 entity IDs without renormalising the full-vocabulary LINK softmax. This arm
  removes only the absent candidates and **still does not renormalise**, so the loss penalty
  for wasting LINK probability on absent identities and on non-entity tokens is preserved.
* **v1's renormalised `frozen-terminal-6` arm is NOT included.** Conditional normalisation is
  a different intervention: away from clamps it removes that penalty entirely, while native
  decoding still uses full-vocabulary argmax. It is not an isolated absent-person test.
* **`detached` is not the frozen arm** and is never relabelled as one. Its terminal
  probabilities are recomputed from the moving trainable weights with the gradient cut. It
  exists only to help separate "stable terminal behaviour" from "no marginal gradients through
  the terminal", by comparison with each primary arm. A benefit of `frozen` supports the whole
  intervention but does **not** by itself distinguish those two effects.

**Frozen-copy discipline.** The frozen copy is a `deepcopy` in `eval()` with
`requires_grad_(False)`, never given to the optimizer and never updated. Fingerprint, eval
mode, absence of `requires_grad`, absence of accumulated gradients and absence from the
optimizer's parameter groups are all checked **at initialisation, at every logged checkpoint
and at final scoring**.

**Schedule.** Frozen at **3,000 updates, warm-up over 100 updates to 1e-3, flat through 2,000,
linear decay to 1e-4 at 3,000.** 16 visits per update. **No quality-triggered budget changes.**
The worker re-checks the four schedule anchors against the manifest before its first update.

## What is measured

**Before any stage-B update and every 100 updates**, on the frozen six-person validation probe
(and on the training batch):

* **LINK full-vocabulary argmax accuracy** — the reported primary number;
* **entity-only argmax accuracy**, as a diagnostic;
* **p_link mass** on the true person / wrong-but-present people / absent identities /
  non-entity tokens (these four partition the softmax and sum to 1);
* **terminal true-person margin** — `p_term(y | true e)` against the mean
  `p_term(y | wrong present e)`; for the frozen arms the frozen copy's margin is reported
  alongside the trainable model's;
* **answer-value collision rate** — the fraction of questions where some wrong present person
  happens to hold the same answer value (the "right answer through the wrong person" route);
* **attribute accuracy by relation** (8, 9, 10) of the trainable model.

All intermediate labels are **evaluator-only**. The sixteen-person probe and the real two-call
rollout are additionally measured before the first update and after the last.

## Validation sets, frozen before training

Five sets are built and hashed **before `freeze`**, by `build-validation`:

| set | worlds | two-hop questions | attribute questions per relation | role |
| --- | --- | --- | --- | --- |
| `qualification` | six-person | 512 | 512 | stage-A gate (development validation) |
| `probe-six` | six-person | 512 | 512 | stage-B trajectory, **primary fit condition** |
| `probe-sixteen` | sixteen-person | 512 | 512 | transfer, reported separately |
| `confirm-six` | six-person | 512 | 512 | **reserved final confirmation** |
| `confirm-sixteen` | sixteen-person | 512 | 512 | transfer at final scoring |

All are full stories, drawn from fresh worlds by a dedicated validation RNG namespace, built
from **visible facts only**, never filtered by any model's correctness, and never touched by
any loss. Their **actual semantic signatures** are added to the registered exclusion set to
form the **exclusion union**, which is the `exclusion_path` every worker loads. Every training
batch is checked against that union **both as constructed** (v1's full-story check, inside the
batch builders) **and as presented** (the reduced story the model actually sees, checked on
the packed batch). The three families (`qualification`, `probe`, `confirmation`) are checked
pairwise **disjoint**, and all five are checked disjoint from the registered
`forbidden-semantics.json`, before anything is written.

## Final scoring — TWO inference systems, separately

For the frozen arms, the final confirmation scores **two different systems**:

1. **`link_plus_frozen`** — LINK from the trainable model followed by **the frozen terminal
   used in training**. This is a **two-copy** system: it spends an additional 79,316 frozen
   parameters and extra storage. A success here is an **optimization diagnostic, not a
   parameter-matched architectural win**.
2. **`trainable_two_call`** — both calls through the trainable model, the **intended
   single-model deployment**, executed by the registered executor
   `astra_canonical_operator.execute`.

`shared` and `detached` have one model and are scored on system 2 only.

**Acceptance, per qualified seed, per arm, per system, on `confirm-six`:**

* **≥ 487/512 LINK predictions** (full-vocabulary argmax equals the true middle person);
* **retained attribute accuracy ≥ 487/512 for each relation** 8, 9 and 10 — the same bar the
  stage-A gate used, so "retained" means "not below the level that qualified";
* **≥ 461/512 complete correct two-call paths AND final answers** (LINK correct *and* final
  answer correct in the same rollout).

`confirm-sixteen` is scored the same way and **reported separately**; it is transfer, not the
fit condition.

**The report always prints the ORIGINAL three-seed denominator** and names every stage-A
failure. A subset of qualified seeds is never "3/3".

## Readings, decided in advance

* **`shared` fails and `frozen` passes** → this intervention resolves a failure under the
  stated prerequisite. Further ablation is needed to assign it to terminal drift versus
  backward interference; `detached` is the first such ablation and is not decisive alone.
* **Both fail** → freezing alone did not suffice. This does **not** prove intermediate labels
  are necessary.
* **Marginal likelihood rises without true LINK accuracy** → final-answer supervision found an
  ambiguous or unintended route; read the answer-value collision rate and the
  right-answer-through-the-wrong-person split.
* **`frozen-present-mask` passes where `frozen` fails** → the absent candidates are the
  problem, and the fix is to restrict the sum, not to freeze anything.
* **A two-copy system succeeds but the single-model deployment fails** → distinguish *learning
  LINK* from *retaining terminal competence*; the deployment claim is not established.

## HONESTY: what is and is not supplied

**Supplied during training, in every arm:**

* the **decomposition itself** — that a two-hop question is answered by a LINK call followed by
  a terminal call. The marginal's form encodes it; the model is not asked to discover the
  program;
* the **token grammar**;
* **visible fact parsing** — the evaluator/adapter parses facts off visible rows;
* the visible story (a random subset of fact lines early in stage A, the full story from update
  1,500 of stage A onward and throughout stage B), the visible question tokens, and the final
  answer of every record;
* in `frozen-present-mask` only: **which identities are in this story**, read from visible
  rows. That is visible information, not a label, but it is information the other arms do not
  get, and the arm must be read that way.

**NOT supplied, at any time, in any loss, or to build any record:**

* the intermediate entity `e` — no LINK record ever receives a target, in either stage;
* any supporting-line or attention target — there is no evidence term anywhere
  (`evidence_lines_used = 0` in every batch's accounting);
* `row.gold`, `row.supplied`, `row.answer`, `row.hops`, `row.relation` — never read. The check
  suite poisons all five and asserts the batches, the losses and every gradient are identical,
  in both stages and for every arm.

**Evaluator-only diagnostics.** The true middle person and the answer-value collision flag are
labels. They are read only while a batch or a validation set is built, stored in evaluator-only
fields, and read only by the diagnostic code path. The check suite scrambles them and asserts
every loss and every gradient is bit-identical, for every arm. `batch.present` is deliberately
**not** a diagnostic — `frozen-present-mask` reads it in its loss — and the check suite asserts
that only that arm's loss changes when the mask is scrambled.

## Preflight (run as tests before any wave)

1. Poison the intermediate/evidence diagnostic fields; verify identical training losses and
   gradients in both stages and every arm.
2. Verify frozen-copy immutability: fingerprint, eval mode, no `requires_grad`, no accumulated
   gradient, not in the optimizer — at initialisation, at every logged checkpoint and at final
   scoring.
3. Verify paired batches and optimizer states across arms.
4. Verify **unrestricted (full-vocabulary) LINK argmax** is what is scored and reported;
   entity-only argmax is a diagnostic only.
5. Verify **no hidden action supervision**: no LINK record carries a target, stage A never
   builds a LINK query, and relation 10 is never a two-hop terminal.
6. Verify **train/probe exclusion**: the validation signatures are in the exclusion union and a
   planted validation signature stops a training batch.
7. Verify **complete dependency/checkpoint manifests**: every registered source, both
   validation files and this preregistration are hashed, and a single changed byte stops the
   wave.
8. Verify this report states that the **decomposition, token grammar and visible fact parsing
   remain supplied**.
9. Verify the **gate**: stage B refuses a seed with no qualification file, with
   `qualified: false`, or with a mismatched checkpoint/manifest hash.
10. Verify the **stage-B schedule anchors** (3,000 / warm-up 100 / flat through 2,000 / 1e-4 at
    3,000) and that the coefficients are exactly (1/3, 1/3).

## Cost and waves

Measured single-process, `-B`, one torch thread, on an idle Mac, with the real exclusion set
loaded (v1's cost table; v2's batches, model and reductions are identical):

| stage / arm | GFLOP/update | updates/s (1 process) | 3,000 updates |
| --- | --- | ---: | ---: |
| stage A | 0.623 | 25.7 | 117 s |
| stage B `shared` | 3.428 | 4.17 | 719 s |
| stage B `frozen` | 2.361 | 6.45 | 465 s |
| stage B `frozen-present-mask` | 2.361 | ~6.5 | ~462 s |
| stage B `detached` | ~2.4 | ~6.4 | ~470 s |

v2's own overhead, **measured** on this machine (single process, one torch thread, the real
7,080-entry exclusion union and the real 512-question sets):

| v2 addition | measured | per stage-B worker |
| --- | ---: | ---: |
| presented-signature exclusion check | 0.0098 s/update | 29 s |
| every-100 six-person measurement (no rollout) | 3.17 s | 95 s (30×) |
| every-100 train-batch diagnostic line | 0.29 s | 9 s (30×) |
| full measurement + rollout, both probes, at update 0 and at the end | 8.4 s | 17 s (2×) |
| final two-system scoring, both confirmation sets | 5.9 s | 6 s |
| rebuilding + fingerprinting the validation sets | 0.35 s | 0.4 s |
| **total v2 overhead** | | **≈ 156 s** |

Stage A adds only the presented-signature check (one record group): ≈ 15 s. `qualify` builds
the qualification set and scores three checkpoints: ≈ 5 s total, no training.

A wave is **3 seeds in parallel**, one process each, one torch thread each. At the ≈1.10
contention factor measured for three concurrent workers, the projections are:

| wave | single process | projected wall clock (3 seeds) |
| --- | ---: | ---: |
| stage A | 132 s | **≈ 2.5 min** |
| `qualify` (no training) | 5 s | **≈ 5 s** |
| stage B `shared` | 875 s | **≈ 16.1 min** |
| stage B `frozen` | 621 s | **≈ 11.4 min** |
| stage B `frozen-present-mask` | 618 s | **≈ 11.4 min** |
| stage B `detached` (optional) | 626 s | **≈ 11.5 min** |

Every wave is inside the 25-minute rule, with the worst arm at ~65 % of it.

Registered caps: `--stage-a-seconds 420` (work 660, terminate 690 s = 11.5 min) and
`--stage-b-seconds 1200` (work 1440, **terminate 1470 s = 24.5 min**) — every wave inside the
25-minute rule. A worker that exceeds its training cap raises and writes `failure.json` rather
than silently producing a short run.

## Deviations and judgment calls (where the spec was silent or ambiguous)

1. **Stage A's lr schedule is the proposal's, retained verbatim** (v3r's shape rescaled to
   3,000 updates, warm-up over its first 50). The spec fixes stage B's schedule explicitly and
   says the proposed stage-A schedule "may be retained"; retaining it keeps stage A comparable
   to `grow-blind`.
2. **Stage B runs at full story size throughout.** The curriculum's job is start-up and stage A
   finishes it (G2 = 1,500 < 3,000). This also removes a confound between the arms.
3. **Stage B restarts the lr shape** (its own warm-up over 100 updates) on top of stage A's
   restored optimizer moments. All arms get the identical schedule, so it cannot confound the
   comparison.
4. **Stage B keeps stage A's world RNG state and starts its own curriculum stream** (namespace
   `…-v2-b`), identical across arms.
5. **The retained-attribute acceptance threshold is ≥ 487/512 per relation**, the same bar the
   stage-A gate used. The spec says "retained attribute accuracy per relation" without a
   number; matching the qualification bar is the conservative reading.
6. **Acceptance is scored on `confirm-six` only**, a set reserved for final scoring and never
   measured during training. The spec reserves "a separate final confirmation set" in the
   stage-A paragraph; extending that reservation to the stage-B acceptance numbers is the
   conservative reading. The six-person **probe** remains the development trajectory.
7. **The qualification set uses six-person worlds** (stage A's training size). The spec does
   not name a world size for it.
8. **"Terminal answers given the true endpoint"** is scored by argmax of the terminal call
   `[QUESTION, true endpoint, relation, ANSWER]` over the full vocabulary, on the same visible
   story, for 512 practised (relation 8 or 9) two-hop questions.
9. **A frozen copy is constructed in every arm**, including `shared` and `detached`, so the
   runs are structurally identical; in those arms it is used only to report the frozen
   terminal margin, never in a loss.
10. **The every-100-update measurement runs on the six-person probe without the two-call
    rollout**; the rollout is measured before the first update and after the last. The spec's
    every-100 list does not include execution, and paying for it 30 times would not fit the
    25-minute wave rule for `shared`.
11. **Validation sets are rebuilt deterministically inside each worker** and checked against
    the fingerprints frozen in the manifest, rather than pickled to disk.
12. **The presented (reduced-story) exclusion check is additive** to v1's full-story check,
    answering audit §4's point that a full-story hash does not imply a reduced-story hash is
    absent.
13. **This module does not monkeypatch `astra_canonical_operator`.** It runs its own two-stage
    worker; the registered runner's ten-panel scoring is not part of this experiment.
14. **Optional cause-separation** (record count 2 vs 6 × monolithic coefficient 0 vs 1/3) is
    explicitly **not** part of this registration; the spec calls it a separate new experiment.

## Commands, in the order they must be run

```
python3.12 -B scripts/fable_link_isolation_v2.py build-validation
python3.12 -B scripts/fable_link_isolation_v2.py freeze            # [--include-detached]
python3.12 -B scripts/fable_link_isolation_v2.py wave --stage a --seeds 1400,1401,1402 --name wave-1
python3.12 -B scripts/fable_link_isolation_v2.py qualify --seeds 1400,1401,1402
python3.12 -B scripts/fable_link_isolation_v2.py wave --stage b --arm shared              --seeds <qualified> --name wave-1
python3.12 -B scripts/fable_link_isolation_v2.py wave --stage b --arm frozen              --seeds <qualified> --name wave-1
python3.12 -B scripts/fable_link_isolation_v2.py wave --stage b --arm frozen-present-mask --seeds <qualified> --name wave-1
python3.12 -B scripts/fable_link_isolation_v2.py wave --stage b --arm detached            --seeds <qualified> --name wave-1   # only if frozen at freeze time
python3.12 -B scripts/fable_link_isolation_v2.py report --seeds 1400,1401,1402
```

`wave --stage b` re-evaluates the gate for every requested seed before spawning anything and
records each refusal in the wave's `completion.json`; passing all three seeds is safe and is
the intended usage.

## Fable's predictions

Written 2026-09-20 by Fable before build-validation and freeze; no registered seed has run. Known: marg-staged-dense (shared weights, monolithic kept) gave LINK argmax
0.16 / 0.59 / 0.03 after 3,500 post-switch updates, the 0.59 arriving in the last 1,000; factorial arm A (attribute-only, small stories) started 3/3 and transferred to full
stories. My record: 5 hits / 10 misses. Seeds 1400/1401/1402; all four arms registered (detached included as the diagnostic the spec allows).

| id | forecast | p | falsified by |
|---|---|---|---|
| P34 | stage A qualifies (the registered gate) in 3/3 seeds | 0.60 | any seed refused |
| P35 | `frozen` meets the LINK acceptance (≥ 487/512, confirm-six) in ≥ 2 of the qualified seeds | 0.30 | ≤ 1 |
| P36 | `shared` meets it in ≥ 2 of the qualified seeds | 0.20 | ≥ 2 do |
| P37 | in ≥ 1 arm that misses acceptance, six-person LINK accuracy rises by ≥ 0.05 over the last 500 updates ("slow, not impossible") | 0.60 | no failing arm is still rising |
| P38 | `frozen` ends with higher six-person LINK accuracy than `shared` in ≥ 2 of the qualified seeds | 0.65 | ≤ 1 |

Reading fixed in advance: P38 true with P35 false = freezing helps but 3,000 updates are not enough; P38 false = interference through shared weights is not the main obstacle.
