FREEZE-READY: YES

# AUDIT-27-delta — independent verification of the AUDIT-27 fixes

Experiment 27 / M1-F "new names", name-code scale frozen at 1.2.
Delta re-audit, 2026-09-20. Scope: the five items the coordinator named, nothing else.
The findings of `AUDIT-27.md` that were *recorded, not fixed* are unchanged and still stand.

**Verdict: FREEZE-READY: YES.** The single MAJOR finding of AUDIT-27 (both parts) is fixed,
correctly and narrowly. 0 BLOCKING, 0 MAJOR, 1 new MINOR (workflow friction, fail-safe).
All eight AUDIT-27 MINORs are either fixed or recorded as the audit asked.

Constraints honoured: every check ran in scratch, at most two processes, on fixture seeds
only. No registered seed (2103, 2104, 2105) was trained, scored or panelled. Nothing under
`pool/`, `panels/`, `runs/` or `scores/` was written or modified. This file is the only
thing I added. No commits, no cloud, no `test.pt` loaded.

---

## 0. Hashes

All six match the values the coordinator stated.

| file | sha256 | |
| --- | --- | --- |
| `scripts/fable_newnames27.py` | `69d54c04fdb54172ea737a4ecf0c316d7e3b5056dac4c20e3494b075f14f1530` | changed |
| `tests/test_fable_newnames27.py` | `f300b38f4a5328cadc1b95350f7e7b68316389b52ca61c58fdc37e60f2f9ecfb` | changed |
| `run_train.sh` | `2729e4af9e374a00b9b3653c9089f7ca092bc4fa51a7142105fa1912040cf39f` | changed |
| `run_score.sh` | `21e47fae8cc75a0d1b8e72dba0e3dcddd79ef7900e958ea6e95da06547ba371a` | changed |
| `BUILD-NOTES.md` | `da91661cc1ac740661089a4e4db8af0814f2b6f34a6fc4880702b7321ec065f4` | changed |
| `run_data.sh` | `62b13de0950f94c62713312e41003900972680d4b4270c2a24801541d1917798` | **unchanged** |
| `AUDIT-27.md` | `abfe12bf2c35d5080085d3d48b158933fa60c6d84b5c8c988c5b75345f800c99` | unchanged (mine) |

`scripts/fable_newnames27.py` grew from 1,441 to 1,495 lines (+54).

**New source fingerprint `6bb75f53575a0b776072fce5a28083d4408bf430d2892f490ca0d190b0e8878e`,
re-derived by me, matches.** It covers 15 files. Two are load-bearing here:

```
fable_newnames27.py   69d54c04...f1530   (the changed file)
fable_newnames21.py   14336a49...ac500   (the parent -- UNCHANGED by this diff)
```

The parent experiment's script was not touched. That matters: the control arm, the scorer,
`seed_verdict` and the code pool all live there.

**Test suite: PASSED 54, FAILED 0, SKIPPED 0**, exit 0. Seven of the 54 are new and cover
exactly the fixed ground (`test_the_registered_seeds_refuse_a_short_run`,
`test_the_registered_seeds_refuse_every_override`, `test_run_integrity_accepts_a_full_set`,
`test_run_integrity_makes_a_short_run_invalid`,
`test_run_integrity_makes_mixed_source_versions_invalid`,
`test_run_integrity_makes_a_recorded_override_invalid`,
`test_run_integrity_is_silent_when_no_run_folder_exists`). I ran my own checks first and
read the builder's tests afterwards; they agree.

---

## 1. `updates` is refused on the registered seeds, and leaves nothing on disk — VERIFIED

`fable_newnames27.py:521-527`. `updates` has joined the override dict:

```python
overrides = dict(code_scale=code_scale, code_namespace=code_namespace,
                 trace_every=None if trace_every == TRACE_EVERY else trace_every,
                 updates=None if updates == UPDATES else updates)
if seed in SEEDS:
    assert not any(v is not None for v in overrides.values()), ...
    assert not fixture_step0, ...
```

My own run, on a scratch experiment folder with scratch output paths:

| call | result | left on disk |
| --- | --- | --- |
| `train_run('F', 2103, updates=3)` | **refused** (AssertionError) | dir does not exist, `[]` |
| `train_run('F', 2104, updates=3)` | **refused** | dir does not exist, `[]` |
| `train_run('F', 2105, updates=3)` | **refused** | dir does not exist, `[]` |
| `train_run('F', 2103, updates=6001)` | **refused** | dir does not exist, `[]` |

A *longer*-than-registered run is refused too, which the fix did not have to do and is the
right side to err on.

**Nothing is left on disk because the assertion precedes the filesystem.** The order in
`train_run` is: build `overrides` → assert → `refuse_existing(...)` → `folder.mkdir(...)`.
I confirmed this by source order and empirically: after each refusal the target directory
does not exist at all — not an empty directory, not a partial one. So a refused short run
cannot later be mistaken for a dead run, and cannot trip `run_train.sh`'s "directory exists
without completion.json" branch.

**The guard does not over-block.** Two ways it could have:

- A fixture seed must still be runnable short — the whole test suite depends on it.
  `train_run('F', 9, updates=3)` succeeded and recorded `overrides: {"updates": 3}`.
- A legitimate registered run at `updates == UPDATES` must pass. Then
  `overrides['updates']` is `None`, all four values are `None`, and the assertion does not
  fire. Verified against the guard expression directly.

This closes AUDIT-27 §2.1. The demonstrated hole — a 3-update run writing
`completion.json {"complete": true}` on a registered seed and scoring normally — is gone at
the source, and now also cannot survive at the gates (§2 below). Two independent barriers.

---

## 2. `run_integrity` — VERIFIED, including that it does not false-fire

`fable_newnames27.py:999-1027`, wired into `gate_table` at 1076-1081:

```python
invalid = invalid_runs(exp)
integrity = run_integrity(exp)
if invalid or bad_buffer or integrity['problems']:
    verdict, reason = 'INVALID', (...)
elif missing:   ... INCOMPLETE
elif control_pass < 2: ... VOID
```

I built synthetic experiment folders in scratch — fabricated `training.json`,
`completion.json` and `scores/*.json` — and called `gate_table` on each.

### 2.1 It fires

| set | integrity problem reported | verdict |
| --- | --- | --- |
| `F-2104` records 3 updates | `F-2104: 3 updates, not 6000` | **INVALID** |
| `F-2105` records `overrides {'code_namespace': 'fixture'}` | `F-2105: overrides {...}` | **INVALID** |
| `control-2104` carries a different source fingerprint | `the runs were produced by 2 different source versions: [...]` | **INVALID** |
| `L-2103` records 3 updates (descriptive arm) | `L-2103: 3 updates, not 6000` | **INVALID** |

The last row matters and I checked it deliberately: arm L is descriptive and no *mark*
depends on it, but a short arm-L run still makes the experiment INVALID. That is the right
call — a mixed-provenance set is not a set.

### 2.2 It fires *ahead of* everything else

In each case below the run set carries an integrity problem **and** a second defect that
would otherwise decide the verdict:

| also true of the set | verdict | proof it was not the other branch |
| --- | --- | --- |
| `F-2105` has no score file | **INVALID** | `missing == ['F-2105']` — INCOMPLETE was available and not taken |
| control fails every cell | **INVALID** | `control_seeds_passed == 0` — VOID was available and not taken |
| arm F fails every cell | **INVALID** | `F_seeds_passed == 0` — FAIL was available and not taken |

So INVALID precedes INCOMPLETE, VOID and the marks, exactly as the design orders them.

### 2.3 The ordering is not inverted, and it does not false-fire

This is the half that a fix like this usually gets wrong, so I tested it in both directions:

| set | verdict | integrity problems |
| --- | --- | --- |
| clean full set, all marks met | **PASS** (`3/3 F seeds`) | `[]` |
| clean set, control fails every cell | **VOID** (`recipe did not reproduce`) | `[]` |
| clean set, `F-2105` unscored | **INCOMPLETE** (`missing: F-2105`) | `[]` |
| no run folders on disk at all | **INCOMPLETE** | `[]`, `runs == {}` |

A clean six-run set reports `problems: []`, one source fingerprint, six runs, and reaches
**PASS**. `run_integrity` adds no verdict of its own to a clean set, and stays silent rather
than complaining when runs are merely absent (an absent run is INCOMPLETE's business, not
INVALID's).

**The one false-fire route is closed by construction.** `run_integrity` flags
`if row.get('overrides')`. Had `train_run` written the raw override dict, a perfectly clean
run would have stored `{"code_scale": null, "code_namespace": null, "trace_every": null,
"updates": null}` — a non-empty dict, therefore truthy, therefore INVALID on every single
registered run. The builder filters it at `fable_newnames27.py:607`:

```python
overrides={k: v for k, v in overrides.items() if v is not None},
```

so a clean run records `{}`. I checked this specifically because it is the exact shape of
bug that would have turned a correct fix into a total blocker, and it would only have
surfaced at the gates, after the compute was spent.

### 2.4 It is gate-side only

`run_integrity` opens `training.json` files already on disk and returns a dict. It builds
no model, draws no batch and touches no checkpoint. It cannot change a trained number, and
the re-derivation in §3 confirms no trained number changed.

This closes AUDIT-27 §2.2 as well: with one source fingerprint required across the set, a
mid-run script edit is now *detected*, not merely recorded.

---

## 3. The diff touches no model / optimiser / data-stream / scorer code — VERIFIED

I re-ran my AUDIT-27 derivations against the new source and compared to the values recorded
in AUDIT-27 §3.1 and §3.2. **Every one reproduces exactly.**

### 3.1 Model and optimiser (fixture seed 4242)

| | AUDIT-27 | now | |
| --- | --- | --- | --- |
| trainable parameters, control / F / L | 79,316 / 78,533 / 78,534 | 79,316 / 78,533 / 78,534 | same |
| `L − F` named parameters | `{code_scale}` | `{code_scale}` | same |
| every shared weight F vs L bit-identical | true | true | same |
| initial fingerprint, F and L | `1c998ac9…a3ee` | `1c998ac97439b340…7fc2a3ee` | same |
| `code_scale` at construction | 1.2000000476837158 | 1.2000000476837158 | same |
| in `parameters()` / `requires_grad` | no / false | no / false | same |
| in `state_dict()` | yes | yes | same |
| optimiser tensors, F / L | 66 / 67 | 66 / 67 | same |
| optimiser groups / wd / lr / betas | 1 / 0.1 / 1e-3 / (0.9, 0.99) | 1 / 0.1 / 1e-3 / (0.9, 0.99) | same |

### 3.2 Control bit-identity, re-derived (fixture seed 4242, 25 updates)

```
registered_every_update_equal   true    all 26 per-update fingerprints == N.reference_updates
registered_first_difference     null
losses_equal                    true    max |difference| = 0.0
n_tensors                       65
tensors_equal                   true    exp27 control state dict == exp21 control state dict
init_equal / final_equal        true / true
flops_equal                     true
registered_params_equal         true
```

The control arm is still experiment 21's control arm, tensor for tensor, and still tracks
the registered functions at *every* update, not merely at the end.

### 3.3 Data stream and scorer

```
pool subsets          train 3072 / reserved 1024      (unchanged)
CODE_SCALE 1.2   UPDATES 6000   TRACE_EVERY 100   PAIRED_SLACK 13
CUTOFFS  c1 487  c2 487  c3 461  c4 461  c5 461  c6 461
         p12-1 487  p12-2 487  p12-3 461  s3 461
TRAIN_CODE_NAMESPACE  newnames27/train-codes
PANEL_NAMESPACE       newnames27-operator-v1-20260921
PANEL_SEED_BASE       202609212700
L start 1.2   exp21 scale 0.13856406460551018
X.seed_verdict is N.seed_verdict    -> True  (the registered scorer, not a copy)
CELL_ORDER  c1 c2 c3 c4 c5 c6 p12-1 p12-2 p12-3 s3
```

Every constant, cutoff, namespace and seed base is unchanged, the scorer is still the
parent's own function object, and `fable_newnames21.py` is byte-identical to the version I
audited. The diff is confined to the gate side and the override guard.

---

## 4. The two new shell guards cannot block a legitimate registered run

### 4.1 `run_train.sh`'s `"registered": true` guard — VERIFIED, does not block

`run_train.sh` now refuses to spend a wave on a fixture panel suite. I checked the guard
against the **real data-wave output already on disk** (read-only), which is the only test
that counts:

```
panels/newnames27-panels.json   "registered": true     -> guard PASSES
panels/audit.json               "all_clear": true
control-equivalence.json        "fingerprints_equal": true
treatment-equivalence.json      "tensors_equal": true
inertness.json                  "all_inert": true
```

All five wave-0 gates pass against the actual artifacts, so wave 1 is not blocked. The
guard can only fire if `panels` was run with a non-default `--namespace`, `--seed-base` or
`--n`, which `run_data.sh` never does. This closes AUDIT-27 MINOR-2.

### 4.2 `run_score.sh`'s stale-verdict guard — does not block wave 1; halts one later path

I simulated `check_not_stale` through the real workflow sequence:

| stage | result |
| --- | --- |
| A. fresh run, no `gates.json` yet | passes |
| B. wave-1 scores written, still no `gates.json` (the script's second call) | passes |
| C. `gates.json` + `report.txt` written at the end of a successful run | — |
| D. `run_score.sh` re-run with nothing new (all SKIP) | passes |
| E. wave 2 (arm L) scored after wave-1 `gates.json` exists | **refuses** |

**The gated path is never blocked.** A, B and D are the whole of wave 1 and its re-runs.

**MINOR-9 (new, not blocking).** Path E is the documented two-wave workflow: run wave 1,
read the verdict, then run wave 2 for the descriptive arm. On the second `run_score.sh` the
three new arm-L score files are newer than the wave-1 `gates.json`, so the guard refuses
and exits 1 — *after* the arm-L scoring has completed, so no work is lost and nothing is
corrupted. The operator must move `gates.json` (and `report.txt`) aside by hand and re-run,
which then recomputes the gates over the full nine-run set.

This is fail-safe and arguably correct — a `gates.json` without the arm-L rows really is a
verdict for a smaller set, and the message says exactly what to do. I am not asking for a
change before the freeze. Record it so the operator is not surprised at the last step:
**after wave 2, move `gates.json` and `report.txt` aside and re-run `run_score.sh`.**

---

## 5. MINOR-1 is recorded — VERIFIED

`BUILD-NOTES.md:307-317`, under the heading **"MINOR-1 — recorded, not fixed. An explicit
deviation from design 4.3."** It states the design's requirement (the arm-L equivalence
proof on seed 2100's first 50 updates), what was done instead (fixture seed 9), and why the
design's version is unreproducible here — the fresh panel suite changes the training
exclusion set, which changes the world stream, so experiment 21's on-disk seed-2100
fingerprint cannot be hit by construction and a comparison against it would fail for a
reason unrelated to the number 1.2. It closes: *"This is a knowing deviation from a binding
document and is recorded here and in the freeze note in those words."*

That is what AUDIT-27 asked for, in the register it asked for. Accepted.

---

## 6. Also noted

**AUDIT-27 MINOR-8 was fixed as well, beyond what I required.** `load_checkpoint` now
rebuilds an arm-F model at the registered 1.2 rather than at the value the checkpoint
records, and asserts the recorded value is 1.2 to float32 precision, so `check_frozen` at
load time compares against the design's number instead of the file's own claim
(`BUILD-NOTES.md:300-305`; tested by the builder with a doctored checkpoint). This is
strictly stronger than the `buffer_ok` path I had accepted as sufficient.

**Unchanged from AUDIT-27 and still standing:**

- The claim caveat (AUDIT-27 §3.1). Arm F is experiment 21's treatment with the scalar
  *removed from the parameter set*, not "pinned": the gradient clip runs over 66 tensors
  instead of 67, so every other parameter's update differs marginally from a
  pinned-parameter version. Design 4.1 demands exactly this; design 4.8's claim wording is
  compatible; **"we only changed one number" would be an over-claim.**
- MINOR-5 (control equivalence on seed 0), MINOR-6 (`FC.development_sources()` omits
  experiment 21's panels folder; base rate of collision measured at zero) and MINOR-7 (the
  100-of-6,000-update partial replay, correctly labelled) remain recorded, no action.
- Wall-clock: unchanged by this diff. Wave 1 ≈ 11 min against experiment 21's own
  six-concurrent-job anchor of 660–682 s. Well inside 30 minutes.

---

## 7. Freeze conditions

All eight conditions in AUDIT-27 §13 are met or superseded. Two operational notes remain:

1. **After wave 2, move `gates.json` and `report.txt` aside and re-run `run_score.sh`**
   (MINOR-9), or the descriptive arm-L rows will never reach a gates table.
2. **The write-up must not say "we only changed one number"** — see §6.

Nothing else is outstanding. The experiment is ready to freeze.
