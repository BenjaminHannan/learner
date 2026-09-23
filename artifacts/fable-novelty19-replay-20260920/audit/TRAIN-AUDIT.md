# novelty-19 — INDEPENDENT ADVERSARIAL AUDIT OF THE TRAINING / SCORING SIDE

Auditor: independent (adversarial) reviewer. 2026-09-20.
Read-only on everything outside `artifacts/fable-novelty19-replay-20260920/audit/`.
No registered seed was run: every number below comes from disposable seed **9991**.

## Identities audited

| file | sha256 | lines |
|---|---|---|
| `scripts/fable_novelty19_train.py` | `1a5943e3669273adcc64bc56a068ae8cfe780bd3b18fbd1febe09b5c39f9369d` | 1843 |
| `tests/test_fable_novelty19_train.py` | `abce2bf4a5904e1a23d18c0f6ff7e39da3e386dcf4c0de3801b6e8413363a015` | 940 |
| `design/v3/19-rulings-1.md` | `af4cc0d45ee5a346738ab1023c152b4bf1821111c350ae0f4a6c85205ca06079` | 53 |
| `artifacts/.../FORGETTING-READOUT-v2.md` | `9d1a0b5b5ccc4ca993d951c88d5d5d3fb9204374914aeea5643ec35253c05ef8` | 17 |
| `scripts/fable_novelty19_data.py` (dependency only) | `6e5c8f70c9351135e7498032d4c41146245b37df1e3c209d345e3b53781e5d89` | 2426 |

The trainer's sha matches the expected `1a5943e3…`.

## Fixture (disposable seed 9991, all under `audit/scratch2/`)

```
operator-history --out ophist                      21.4 s
dev-panels --out dev --operator-history ophist      2.3 s   manifest af7e7aa6…
awake-stream --seed 9991 --updates 200 --out awake  1.7 s
memory --seed 9991 --stream awake --out mem --worlds 64
buffers --seed 9991 --memory mem --out buf --dev-panels dev --offline-updates 30
```

Training/scoring runs: `awake {D,T} × {whole 1×8, chunked 3+3+2}`,
`offline {D,T} × {R,G,U} × 6 updates`, plus scored cells and nine synthetic attacks.

Own probe scripts (do not import the builder's tests):
`audit/train_probes.py`, `audit/train_probes2.py`, `audit/report_attacks.py`;
outputs `audit/train-probes.json`, `audit/train-probes2.json`, `audit/report-attacks.json`.

---

## VERDICT TABLE

| # | area | verdict |
|---|---|---|
| 1 | arm fairness in training (identical start, reset optimizers, identical schedule/order/shapes; D and T on identical awake questions) | **PASS** |
| 2 | the frozen operator stays frozen, and its sha check cannot be skipped | **PASS** |
| 3 | resume: chunked == unchunked bit-identity; a killed chunk cannot be silently accepted; the budget stop cannot change the result | **PASS** (2 notes) |
| 4 | native scoring per architecture; T's capacity 12; D's eval cap 16; partial-cell refusal; oracle diagnostic isolation | **PASS on the scoring logic; FAIL on provenance** — the registered caps and the completeness of a checkpoint are recorded but never re-checked (must-fix 3 and 4) |
| 5 | gates and the report; can a false pass / false trigger / hidden missing run be printed, and can `DEV-PASSED.json` be written when it should not be? | **FAIL** — `DEV-PASSED.json` can be written for a non-registered seed set, and the confirmation lockout accepts any bytes (must-fix 1 and 2) |
| 6 | anything in training that could expose the held-out types (c≥2 with r=10; c=4/5 in R) | **PASS** |
| 7 | wall-clock / host-dependent behaviour beyond float noise | **PASS** (3 notes) |

**FREEZE-READY (training side): NO** — must-fix 1 and 2 are integrity defects in the
confirmation lockout and must be closed before the hash freeze. Must-fix 3–5 are cheap and
should go in the same patch.

> Cross-reference added after the data re-check (20 Sep, see `DATA-AUDIT.md` "Re-check 2"):
> the patched data module now ships `validate_dev_passed`, which I verified refuses ten
> distinct bad `DEV-PASSED.json` flags (empty, malformed, wrong schema, wrong seed set,
> missing report hash, mismatched dev-panel manifest hash, missing or non-hex checkpoint
> entries) and re-hashes the dev-panel manifest on disk. **Training-side must-fix 2 is
> therefore a one-line fix:** have `guard_confirmation` call
> `fable_novelty19_data.validate_dev_passed(experiment, seeds=REGISTERED_SEEDS)` instead of
> `Path(experiment)/'DEV-PASSED.json'.exists()`. Must-fix 1 (`report --seeds` writing the
> flag for a non-registered seed set) is unaffected by the data patch and still stands:
> `dev_passed_payload` must compare its seeds against `REGISTERED_SEEDS` before writing, or
> the unlock must stop being auto-written at all, as the module docstring says it should be.
>
> **FREEZE-READY (data side): YES, conditional on one small fix (R2-7).** The two verdicts
> are independent: the data module can be frozen without the trainer, but no confirmation
> scoring may be run until training must-fix 1 and 2 are closed.

---

## 1. Arm fairness in training — PASS

**Offline arms start from byte-identical awake-final weights.** Run `run_phase` with
`phase='offline'` loads the awake checkpoint with `load_weights_only(..., strict=True)` and
re-computes the fingerprint. Measured on seed 9991:

```
runs/awake-D-whole  final_weight_fingerprint e216551f9f8c85ae…
runs/off-D-R  init e216551f…   runs/off-D-G  init e216551f…   runs/off-D-U  init e216551f…
runs/awake-T-whole  final 48e8d108a1dbf5a8…
runs/off-T-R  init 48e8d108…   runs/off-T-G  init 48e8d108…   runs/off-T-U  init 48e8d108…
```

**Optimizers are truly reset.** `run_phase` builds a fresh `AdamW` at the offline boundary
in every arm (`fable_novelty19_train.py:523`). Reading the AdamW state out of the
checkpoints (`train-probes.json → optimizer_reset`): every offline checkpoint after 6
updates carries `step == 6` for all 34 (D) / 55 (T) state entries, while the awake
checkpoint after 8 updates carries `step == 8`. Nothing of the awake moments survives.
`generator` and the torch global seed are also re-seeded to the same
`D_GENERATOR_BASE + seed` in all three arms, so the arms share the sampling stream.

**Same update count, order, batch shapes and schedule; only the buffer differs.** All three
arms read the same `offline-order.json` (`read_offline_order` additionally rebuilds the
order from its namespace and aborts if it does not reproduce). Rebuilding the first six
updates for each arm independently (`train_probes.py → arm_fairness`):

```
item counts per update   R/G/U = [64,64,64,64,64,64]
owner vectors identical  True
story bytes identical    True        (sha256 over the merged story list)
story row counts identical True
```

so the world bytes, the world order, the owner/visit structure and the batch item count are
shared; only the question tokens differ. The learning-rate and entropy schedules are pure
functions of `(update, total)` and are arm-independent.

**D and T consume identical awake questions per seed.** `data_fingerprint` is a running
sha256 over the raw question bytes of every update. Seed 9991, 8 awake updates:
`D = f8c846112ff72f15…`, `T = f8c846112ff72f15…` — identical. The same holds per arm
offline (`R = 53f24ab5…`, `G = c9ed3e1b…`, `U = c5ca70ed…` for **both** architectures).
*Note N7 below*: nothing in `gates`/`report` ever compares these digests automatically.

## 2. The frozen operator stays frozen — PASS

`train-probes.json → frozen_operator`:

```
sha256 e7e5b6f3a6bfecf3890538bd0a14af7f5189b1565329e5cf411b52dd4d4dfbec  == registered
all parameters requires_grad == False        True
model.training                               False   (eval mode)
operator parameters in the optimizer         False
operator parameters inside the dispatcher    False   (79,316 vs 24,035 params, disjoint)
fingerprint unchanged after a forward pass   True
foreign checkpoint refused                   True  ("frozen operator SHA-256 mismatch … Aborting")
```

The sha check **cannot** be skipped: `verified_operator` is called at both sites with the
default `expect=OPERATOR_SHA256`, there is no CLI flag that sets `expect=None`, and
`--operator` only changes the *path* — the bytes must still hash to the registered value.
`str(path) == 'oracle'` is rejected outright. `run_phase` re-checks
`operator.fingerprint == operator_before` after every chunk (line 567) and `score` re-checks
it after every cell (line 934); `score` also refuses a checkpoint whose stored
`operator_fingerprint` differs (line 893).

Training and scoring both use the **full** operator grid, not the depth-limited closure:
`V3.train_table` falls back to `operator.table` whenever `cap > V1.MAX_CALLS = 4`, and
`D_TRAIN_CAP = 8`; `V3.prepare_side` (the scoring path) always uses `operator.table`. So the
cap change between training (8) and evaluation (16) cannot truncate the operator table.

## 3. Resume — PASS, 2 notes

**Bit-identity.** Seed 9991, 8 awake updates, uninterrupted (`--chunk-updates 8`) versus
three separate invocations at `--chunk-updates 3 --budget-seconds 0`:

| run | chunks | final weight fingerprint | update fingerprint |
|---|---|---|---|
| `awake-D-whole` | 1 | `e216551f9f8c85ae…` | `6ab6bd8e4bf5e410…` |
| `awake-D-chunk` | 3 (resumed from `ckpt-000006.pt`) | `e216551f9f8c85ae…` | `6ab6bd8e4bf5e410…` |
| `awake-T-whole` | 1 | `48e8d108a1dbf5a8…` | `9f666e5908ec40d8…` |
| `awake-T-chunk` | 3 (resumed) | `48e8d108a1dbf5a8…` | `9f666e5908ec40d8…` |

This covers the RLOO sampling stream for D: `save_state` stores both
`torch.get_rng_state()` and the dedicated `torch.Generator` state, and `load_state` restores
both. The budget stop therefore cannot change the result — it only moves the chunk
boundary, and the boundary is not an input to anything.

**A killed chunk cannot leave a half-written checkpoint that is later accepted.**
- `save_state` refuses to overwrite an existing `ckpt-*.pt`.
- The chunk log is opened with mode `'x'`, so a re-run of a chunk that died mid-way exits
  with `refusing to overwrite …/log-000000-000003.jsonl` (verified, `train-probes2.json →
  killed_chunk_resume`).
- A truncated checkpoint is refused by torch's own container check
  (`PytorchStreamReader failed reading zip archive`) rather than silently loaded
  (verified by truncating `ckpt-000006.pt` to half its bytes).

*Note N2*: the price of the `'x'` log is that the operator must delete the stale
`log-*.jsonl` by hand before a killed wave can be resumed. That manual step is nowhere
documented, and deleting files inside a run directory is exactly the kind of hand-edit the
rest of the design forbids. Document it (deleting a log is harmless; deleting a checkpoint
is not).

*Note N5 / must-fix 5*: `chunk-*.json` records `checkpoint_sha256`, but `load_state` never
re-hashes the checkpoint it resumes from. Truncation is caught by torch; a silent
corruption inside a tensor blob is not.

## 4. Scoring — scoring logic PASS, provenance FAIL

**Native scoring is the frozen scripts' logic.** D goes through
`V3.operator_on_chains` → `V4.score_side_v4` → `V3.aggregate`; T goes through
`B1.side_items` → `LE.CappedModel` → `B1.model_emitter` → `B1.evaluate_side` →
`B1.aggregate`. Nothing is re-implemented in the trainer; `answers` and `strict` come
straight out of the frozen aggregators.

**T's fixed output capacity 12 versus the frozen length-eval default.** `LE.decode_cap`
defaults to `hops + 1 + 3`, i.e. 5 at c=1 rising to exactly 12 at c=8
(`train-probes.json → capacity_limits.default_per_cell_caps`). The registered fixed 12 is
therefore **≥ the default for every cell and equal at c=8**. Greedy decoding emits a prefix,
so a larger cap can only turn a "no END inside the cap" failure into a scored answer and can
never remove one; the strict criterion needs exactly `hops+1` tokens plus END, which fits in
both. So the fixed capacity is a weak *advantage* to T relative to how T was scored before,
never a handicap — the conservative direction for a control architecture.

**No position clamping is possible at c ≤ 8.** Measured on the real panels:

| cell | c | needed output len | needed row-position index | needed output-step index | slots | `unscorable_reason` |
|---|---|---|---|---|---|---|
| `F-c1-r8` | 1 | 2 | 9 | 11 | 16 / 16 | `None` |
| `E-c5-link` | 5 | 6 | 9 | 11 | 16 / 16 | `None` |
| `L-c6-prac` | 6 | 7 | 9 | 11 | 16 / 16 | `None` |
| `L-c8-prac` / `L-c8-held` | 8 | 9 | 10 | 11 | 16 / 16 | `None` |

The worst index used anywhere is 11 against 16 slots. The clamp guard is live, not
decorative: scoring `L-c8-held` at `--capacity 20` is refused with
`output step index 19 >= OUT_STEP_SLOTS=16`.

**`_trained_hops` does not change any scoring decision.** It feeds only
`LE.trained_ranges`, whose output appears in `cell_limits` as annotation fields. Computing
`cell_limits` with `train_hops=(1,2,3)` and with `(1,2,3,4,5)` gives an identical
`unscorable_reason` for every cell tested (`decision_independent_of_trained_hops: true`).

**D's eval cap 16 versus the training cap 8** is handled as the spec says
(`D_TRAIN_CAP = 8` in `dispatcher_update`, `D_EVAL_CAP = 16` as the `score` default) and the
operator table is cap-independent (above).

**Partial-cell refusal and `registered_cells()`.** `score` refuses any suite whose cells do
not all hold the manifest's `n`, and `--cells` splits work by cell only. In practice the
refusal is unreachable because the data module's own per-file hash fires first
(`RuntimeError: panel changed on disk` — verified twice, with and without rewriting the
manifest `files` entry). Defence in depth; PASS. Scoring runs inside
`with N.registered_cells()`, and `V3.CELLS` is verified restored afterwards
(25 → 57 → 25 entries, dict and order both equal to the originals).

**The oracle diagnostic can never feed a mark or a gate.** `row['oracle_operator']` is a
nested sub-dict; `marked` is computed from `row['answers']`/`row['strict']`, which come from
the *trained*-operator aggregate. `oracle_operator` occurs at exactly four places in the
file (lines 838, 841, 898, 961) and at none of them is it read by `awake_fit_gate`,
`primary_verdict`, `secondary_family`, `development_rule`, `forgetting_screen` or
`calls_ceiling`. PASS.

**Provenance failures (must-fix 3 and 4):**

- *A mid-run checkpoint scores and merges as if it were the run.* Scoring
  `runs/awake-D-chunk/ckpt-000003.pt` succeeds, writes `updates_done: 3,
  total_updates: 8`, and `collect_scores` keys the entry only on
  `(arch, seed, phase, arm)` → `awake-D-s9991`. Nothing ever requires
  `updates_done == total_updates` or `total_updates == AWAKE_UPDATES/OFFLINE_UPDATES`.
- *The registered caps are recorded but never re-checked.* `--eval-cap 4` and
  `--eval-cap 64` are both accepted for D and are written into the score file; `--capacity 9`
  is accepted for T. `collect_scores`, `gates` and `report` never read `eval_cap`,
  `output_capacity` or `oracle_operator_diagnostic` back, so score files made at different
  caps merge silently into one run, and `calls_ceiling` always divides by the registered
  constant (16 / 12) whatever cap actually produced the number.

## 5. Gates and the report — FAIL

What is **correct** (verified with synthetic score files, `report-attacks.json`):

- A **missing run** is never a pass: dropping `offline-D-s1902-G` makes the primary verdict,
  the development rule and every table entry `(missing)`, and `DEV-PASSED.json` is not
  written (`the registered development rule is undetermined`).
- **Conflicting score files** are caught: a second file for one run with different cell rows
  produced 32 `two different scores for one cell` conflicts, `evidence_complete` `False`,
  development rule `fail`, no `DEV-PASSED.json`. The first file (in sorted order) is kept and
  the conflict is reported, never silently overwritten.
- The **primary rule** is per cell and per seed with no averaging, requires both
  `answers ≥ 58` and `strict ≥ 58` in the treatment arm and `strict_gain ≥ 13` over that
  seed's own R arm, and is `None` (never `False`, never `True`) if either side is absent.
- The **awake-fit gate** is `≥ 61/64` on both metrics in all 7 F cells.
- The **forgetting screen** matches ruling 7 exactly:

  | forged scenario | outcome | correct? |
  |---|---|---|
  | one cell, one metric, −7 in seeds 1900+1901 | `TRIGGER` on `R\|F-c2-r8\|answers` etc. | yes |
  | −7 in 1900 on `F-c2-r8`, −7 in 1901 on `F-c3-r8` | `NO-TRIGGER` | yes — different cells cannot replicate |
  | H cell with awake 57/64 and a −17 drop in all 3 seeds | `NO-TRIGGER`, every seed `not_eligible` | yes — the 58/64 eligibility mark bites |
  | drops in 1900+1901, seed 1902 fails the awake-fit gate | `TRIGGER` | yes — the two replications are gate-passing seeds |

  Answers and strict are separate combos and are never added; the denominator stays the
  number of seeds; `UNDETERMINED` is emitted when evidence is missing or a seed failed the
  gate, and `NO-TRIGGER` only on complete evidence.

What **fails**:

**F-1 (must-fix 1) — `report --seeds` can unlock confirmation with a non-registered seed
set.** `report --exp … --seeds 9991` on a forged one-seed experiment printed
`registered development rule (D-G): PASS` and **wrote `DEV-PASSED.json`** containing

```json
{"schema": "novelty19-dev-passed-v1", "seeds": [9991],
 "awake_checkpoints": {"D-9991": "…", "T-9991": "…"}, …}
```

against `N.AWAKE_CHECKPOINT_KEYS == ('D-1900','D-1901','D-1902','T-1900','T-1901','T-1902')`.
`dev_passed_payload` writes `awake_keys_expected` into the *sidecar* but never compares the
payload to it, and never compares `seeds` to `REGISTERED_SEEDS`. The registered rule is a
three-seed rule; a one-seed (or one-non-registered-seed) run must not be able to produce the
unlock file.

**F-2 (must-fix 2) — the confirmation lockout tests `Path.exists()` and nothing else.**
`guard_confirmation` accepts a `DEV-PASSED.json` containing `{}`, containing
`{"schema": "something-else"}`, containing a one-seed payload, or containing the literal
text `this is not json at all` — in every case it returns
`is_confirmation: True, dev_passed: <path>` and scoring proceeds. Only the *absence* of the
file is refused (verified: `refusing to score confirmation panels: no …/DEV-PASSED.json`).
The file's sha256 is recorded, which is provenance, not a check. The guard must parse the
file, require `schema == N.DEV_PASSED_SCHEMA`, `seeds == REGISTERED_SEEDS`, all 6 + 18
checkpoint hashes present and hex64, and `dev_panels.manifest_sha256` equal to the manifest
of the suite actually being scored.

*(Taken together F-1 and F-2 mean one `report` invocation with a hand-chosen `--seeds`, or a
single hand-made file of any content, opens the confirmation suite. The docstring at line 51
says the flag is "written by hand ONLY after development passes"; the implementation writes
it automatically at line 1476.)*

**Not a false pass but worth stating:** `collect_scores` trusts the *contents* of the score
JSONs (it never re-hashes the checkpoints they name, and `checkpoint_sha256` values that
point at nothing are accepted). All nine of my forged experiments were built that way. This
is inherent to a file-merging report and is acceptable **provided** must-fix 1–4 are closed,
because those are the checks that turn "a file exists" into "the registered run happened".

## 6. Exposure of the held-out types in training — PASS

- `awake` and `offline` never open a panel directory. The only panel-derived value that
  reaches a training run is `index['exclusion']['union_sha256']`, recorded in
  `inputs_record` as a hash.
- `_trained_hops` returns only call counts — `(1,2,3)` for awake and R, `(1,2,3,4,5)` for G
  and U. No relation id, no people identity, no cell name. It is consumed only by
  `LE.trained_ranges` at *scoring* time, and (§4) it cannot change a scoring decision.
- No diagnostic is computed on development panels during training. `dispatcher_failure_shapes`
  and `LE.wrong_breakdown` run only inside `score`, on the panel being scored.
- The relation-10 / c=4,5 exclusions are enforced upstream in the data module (audited
  separately); the trainer adds no fallback path that could re-introduce them — a feed that
  runs out raises `RuntimeError`, it does not synthesise a replacement.

## 7. Wall-clock / host-dependent behaviour — PASS, 3 notes

- The only wall-clock control flow is `--budget-seconds`, which moves a chunk boundary;
  §3 shows the boundary does not change the result.
- `torch.set_num_threads(1)` in `main` and again in `configure()`; CPU-only; both
  architectures reproduce exactly across invocations on this host.
- *Note N3*: `WAVE_DEADLINE = 1500` is defined and never used.
- *Note N6*: `completion.json`, `chunk-*.json`, the score files and `report.json` all embed
  `created_unix`, `seconds`, `peak_rss_bytes` and `host`, so they are not hash-reproducible.
  The data module now keeps wall-clock in `.meta.json` sidecars; the trainer does not follow
  that convention. Nothing gates on these fields, so this is presentation, not integrity —
  but `report_sha256` inside `DEV-PASSED.json` therefore hashes a file that a second
  identical `report` run would not reproduce.
- *Note*: `base_checkout()` resolves the operator path by walking for `.claude/worktrees`;
  on a different layout it falls back to the worktree root and then exits loudly with
  `frozen operator checkpoint not found`. Loud, so acceptable.
- `peak_rss_bytes` branches on `sys.platform == 'darwin'`; a Linux run reports KiB×1024.
  Cosmetic.

---

## MUST FIX BEFORE FREEZING

1. **`report` must refuse to write `DEV-PASSED.json` unless the evidence is the registered
   three-seed set.** Require `tuple(seeds) == REGISTERED_SEEDS` and
   `set(awake_checkpoints) == set(N.AWAKE_CHECKPOINT_KEYS)` and
   `set(offline_checkpoints) == set(N.OFFLINE_CHECKPOINT_KEYS)` before writing; otherwise
   add a `problems` entry. (Verified exploitable: `--seeds 9991` wrote the flag.)
2. **`guard_confirmation` must validate the contents of `DEV-PASSED.json`, not its
   existence.** Parse it; require the schema string, the registered seeds, 24 hex64
   checkpoint hashes and a `dev_panels.manifest_sha256` equal to the manifest of the suite
   being scored. (Verified exploitable: `{}` and even non-JSON bytes unlock confirmation.)
3. **Require complete runs in `collect_scores`.** Reject (or mark incomplete) any score file
   with `updates_done != total_updates`, or with `total_updates` not equal to the registered
   `AWAKE_UPDATES` / `OFFLINE_UPDATES`. (Verified: a 3-of-8-update checkpoint merged as the
   run.)
4. **Re-check the registered scoring knobs when merging.** `collect_scores` should carry
   `eval_cap`, `output_capacity` and `oracle_operator_diagnostic` and conflict on anything
   other than 16 / 12, so that a file produced at `--eval-cap 4` or `--capacity 9` cannot
   merge into a registered run and so that `calls_ceiling` divides by the cap that was
   actually used.
5. **Verify the checkpoint hash on resume.** `load_state` should compare `sha(path)` with the
   `checkpoint_sha256` recorded in the matching `chunk-*.json` before trusting it.

## NOTE ONLY

- N1 `awake_fit_gate` returns `None` when one F cell fails *and* another is missing; a
  definite failure should dominate an absence. Conservative for the unlock (`None` blocks
  `DEV-PASSED`), but it mislabels a failing run as undetermined in the forgetting screen's
  `awake_fit_gate` column.
- N2 Document that resuming a killed chunk requires deleting the stale `log-*.jsonl`.
- N3 `WAVE_DEADLINE` is dead code — remove it or use it.
- N4 `load_weights_only`'s fingerprint check is
  `awake_saved.get('final_weight_fingerprint', initial_fingerprint)`, so an awake checkpoint
  that lacks the key passes silently. Make the key mandatory.
- N5 The module docstring says `DEV-PASSED.json` is "written by hand ONLY"; `report` writes
  it automatically. Align the text with the code (and, with must-fix 1 in place, auto-writing
  is defensible).
- N6 Move wall-clock/host/RSS out of `completion.json`, `chunk-*.json`, the score files and
  `report.json` into `.meta.json` sidecars, matching the data module, so the training
  artifacts are hash-reproducible too.
- N7 Nothing automatically asserts that D and T share a seed's `data_fingerprint`. The
  digests are recorded and I verified equality by hand on seed 9991; a one-line check in
  `gates` would make it a registered fact.
- N8 `torch.load(..., weights_only=False)` is used for every checkpoint. Self-produced files
  only, but `weights_only=True` plus an explicit allow-list would remove the class.
- N9 (no action) T's fixed capacity 12 is ≥ the frozen per-cell default at every cell and
  equal at c=8, so the registered capacity can only help T; no clamping occurs at c ≤ 8.

---

# Re-check 2 — final confirmation pass (training side)

Subject: `scripts/fable_novelty19_train.py` sha256
`d020d8c27e257bd6194b73efef3f5a4884b3a35ffd5d741bd32e9f6ff4306e14` (2,135 lines, was 1,843),
tests `1b8de84d2f47353321376b14dad8145d3f6e176b558e0ea3dc4246f95e357d8f`. Both shas
reproduced locally. Disposable seed 9991 only; the three registered-seed fixtures in
§6 are fabricated JSON documents — **no model was trained on 1900/1901/1902**.
Evidence: `train-recheck.json`, `train-recheck-resume.json`, `train-recheck-mix.json`.

## 1. The five exploits, re-run

| # | exploit | outcome |
|---|---|---|
| 1 | write `DEV-PASSED` for a non-registered seed set (`--seeds 9991`) | **closed** — `report` exits 1, no file written; `dev_passed_payload` refuses before composing anything |
| 2 | unlock confirmation with a garbage/empty `DEV-PASSED` | **closed** — 6/6 bad files refused (empty, not-JSON, `{}`, wrong schema, one-seed, missing 18/18 offline checkpoints); only the registered-and-complete file is accepted, `validated_by: fable_novelty19_data.validate_dev_passed` |
| 3 | merge a mid-run checkpoint's score as final | **closed** — the score file is written but `collect_scores` rejects it with 5 reasons (`updates_done=3`, `total_updates=8`, completion disagrees on the file, sha mismatch, run recorded 8 updates) and the run is left absent, so it prints as missing rather than merging |
| 4 | merge score files taken at different caps | **closed** — only the registered cell merges (`eval_cap 16`); the `--eval-cap 4` and `--eval-cap 64` files are rejected by name and reason; a *real* off-cap score run is flagged `registered_caps: false` |
| 5 | resume from a tampered or orphan checkpoint | **closed** — orphan refused (*"refusing to resume from an unaccounted checkpoint"*), byte-tampered refused (*"the checkpoint has changed on disk since it was written"*), swapped-from-another-run refused identically, foreign-architecture refused; clean control resumes and reaches `48e8d108a1dbf5a8` |

Exploit 5 needed care: deleting only the last checkpoint short-circuits with *"already holds 8
updates"*, so the probe also removes `completion.json` and the trailing chunk/log to force a
real resume from `ckpt-000006.pt`. The results above are from that corrected probe
(`train-recheck-resume.json`).

## 2. Is the training path really unchanged?

Every fingerprint reproduces my pre-patch evidence on seed 9991:

- awake D weight/update `e216551f9f8c85ae` / `6ab6bd8e4bf5e410`; awake T `48e8d108a1dbf5a8` /
  `9f666e5908ec40d8`;
- data fingerprint `f8c846112ff72f15` for both architectures (so D and T consumed identical
  question bytes);
- offline data fingerprints R `53f24ab53fb19c39`, G `c9ed3e1b55403b50`, U `c5ca70ed8a7d54f6`;
  all three arms initialise from the awake final.

The training/optimizer/RNG path is byte-identical to the version audited. **Builder's claim
confirmed.**

## 3. The `panels_folder` omission — reasoning right, hole remains

`guard_confirmation` deliberately calls `N.validate_dev_passed(experiment, seeds=REGISTERED_SEEDS)`
*without* `panels_folder`. **That reasoning is correct**: the manifest hash recorded inside
`DEV-PASSED.json` is the *development* suite the verdict was computed on, while `--panels` at
confirmation time is the *confirmation* suite, so passing `panels_folder` would compare two
different directories and always fail.

But a hole remains, in the other direction. The confirmation panel manifest records its own
`dev_passed.sha256` (`dd31133354c7c12f24…` in my fixture) — the unlock that authorised it —
and **nothing compares it with the unlock actually presented at scoring time**. I built a
second, independently valid `DEV-PASSED.json` (sha `8ea9774c096d3a0c9f6f1c4f96cbcf5d0d8612e82c3979239d0e975aacc9a80f`)
and the guard accepted it for a suite that records a different one: `guard_accepts_a_different_valid_unlock: true`,
`guard_compares_suite_to_unlock: false`.

Consequence: the "development passed without recipe changes" guarantee is enforced only as
*"some* valid development pass exists", not *"the one this confirmation suite was built
under"*. A failed development round followed by a tweak, a re-run and a fresh unlock would
still unlock a confirmation suite built before the tweak. **Must-fix M-1** — one comparison in
`guard_confirmation` between the panel manifest's `dev_passed.sha256` and `record['sha256']`.

## 4. Note N6 (wall-clock/host/RSS inside hashed artifacts) — NOT a blocker

Measured, not argued: the checkpoint `.pt` contains `source_fingerprint` and **no** wall-clock
keys, and its sha256 is reproducible across two independent writes of the same run
(`aea33fb4c0a51c6e` both times). Weight, update and data fingerprints are all reproducible.
Wall-clock/host/RSS (`created_unix`, `host`, `peak_rss_bytes`, `seconds`) appear only in
`completion.json`, `chunk-*.json`, the score files and the report — documents whose shas are
*recorded for provenance*, never *required to match* across a re-run. Nothing the experiment
asserts depends on them. **Note only**; the sidecar cleanup remains desirable for symmetry
with the data module but is not a freeze blocker.

## 5. Note N8 (`torch.load` without `weights_only`) — NOT a blocker

The patch added `verify_recorded_sha` *before* `torch.load` in `load_state` and
`load_weights_only`, so the **resume path hashes first**. The **scoring path does not**:
`load_run_checkpoint` (line 895) calls `torch.load(Path(path), map_location='cpu',
weights_only=False)` with no prior hash check. It then checks `arch`, loads the state dict
with `strict=True`, and compares `weight_fingerprint(model)` against the stored value — so a
*modified* checkpoint is still caught, and `score` records `checkpoint_sha256=sha(path)`
which `checkpoint_binding` re-hashes and compares at collect time. The residual exposure is
unpickling arbitrary code from a file before it is authenticated, on self-produced files only.
**Note only**, with the standing recommendation: move `verify_recorded_sha` above the
`torch.load` in `load_run_checkpoint` too, matching the resume path.

## 6. One frozen script version — neither enforced nor detected

`checkpoint_sha256` embeds the trainer's `source_fingerprint`, so all registered runs must be
produced by one frozen script version. I tested whether the report would notice a mix.

Fixture: 24 fabricated `novelty19-score` documents for the registered seeds under
`scratch3/exp-mix/` (JSON only, no training), with `D-1900-awake-None.json` given a
`source_fingerprint.novelty19_train` of `'9'*64` while the other 23 carry the real one —
2 distinct fingerprints on disk.

Result (`train-recheck-mix.json`):

- `collect_scores` merges **24 / 24 runs**, `conflicts: []`, `rejected: []`;
- the run entry's fields are `arch, arm, caps, cells, checkpoint, checkpoint_sha256,
  data_fingerprint, n_per_cell, panel_guard, panel_manifest_sha256, panels, phase, seed,
  sources, total_updates, update_fingerprint, updates_done` — **`source_fingerprint` is not
  among them**;
- the fake sha appears nowhere in the collected structure.

Source-level confirmation: `source_fingerprint` is *written* at lines 194 (definition), 646,
704, 1069, 1346, 1707, 2130, and **read back nowhere**. Line 1348 explicitly excludes it from
what is printed. The only cross-run consistency check, `identical_questions`, compares
`data_fingerprint` between D and T — not the script version. The report writes the *reporting
process's own* fingerprint, which says nothing about the runs it summarises.

**Answer to the coordinator's question: the report neither enforces nor detects a mixed
trainer version.** **Must-fix M-2** — carry `source_fingerprint` into the run entry in
`collect_scores` and assert a single distinct value across runs in `gates`, the same shape as
`identical_questions`. Both are small; without them, "one frozen script version" is a launch
instruction rather than a checked fact, and the strongest artifact of record cannot
retrospectively prove it held.

## Remaining must-fix

- **M-1** `guard_confirmation` does not compare the confirmation suite's recorded
  `dev_passed.sha256` with the unlock presented; any valid unlock opens any suite.
- **M-2** a mixed trainer `source_fingerprint` across registered runs is recorded but never
  compared, by `collect_scores`, `gates` or `report`.

Notes N6 and N8 are assessed above as non-blocking. N1–N5, N7, N9 stand as previously written.

**FREEZE-READY (training side): NO** — two small must-fix items (M-1, M-2) remain; every one
of the five exploits is closed and the training path is confirmed byte-identical.

---

# Re-check 3 — M-1, M-2, N8 (training side only)

Subject: `scripts/fable_novelty19_train.py` sha256
`77644a1f15e6e683b2260261b04411a6ee30c8bb74f80121a8ef7318749cd5a8` (2,255 lines, was 2,135),
tests `788894bb97774c844cc1e58f9107e47c61796756db96d9279e78637804ae84df`. Data module
unchanged at `ef1df0e1…`. All three shas reproduced locally. Disposable seed 9991; the
registered-seed material in §2 is fabricated JSON — **no model was trained on 1900/1901/1902**.
Evidence: `train-recheck3.json`, `train-recheck3-m1.json`, from `train_recheck3.py` and
`train_recheck3_m1.py`.

## 1. M-1 — the confirmation suite is now bound to its own unlock: CLOSED

`build_dev_panels(confirmation=True)` writes the verdict it unlocked on into the confirmation
manifest; `guard_confirmation` now hashes the presented `DEV-PASSED.json` and requires equality.

My fixture suite records `dev_passed.sha256 = 4fe42220f81b1cd6…`, which is exactly the sha of
the unlock it was built from.

| case | result |
|---|---|
| the original unlock (control) | **accepted**, `dev_passed_bound_to_suite: true` |
| a second, independently valid unlock (`16394cc0a16f8c4c…`) | **refused** — *"This is a VALID verdict but not THE one these panels were unlocked by"* |
| manifest `dev_passed.sha256` removed | **refused** — *"records no dev_passed.sha256, so there is nothing tying this suite to the verdict that unlocked it"* |
| manifest `dev_passed.sha256` blanked | **refused**, same message |
| whole `dev_passed` block removed | **refused**, same message |
| the original unlock again (control after restore) | **accepted** |

A legitimately matching unlock still passes, and a development suite is untouched
(`guard_confirmation(dev, False, None)` → `is_confirmation: false`, kind `development`).

*Fixture note, stated because it matters:* my first attempt was **inconclusive** —
`guard_confirmation` validates against the module global `REGISTERED_SEEDS`, so a seed-9991
unlock is refused on the seed check before the binding check is reached, and every case
came back "refused" for the wrong reason. The table above comes from a re-run in which that
global alone is set to `(9991,)`; the binding logic under test is untouched.

## 2. M-2 — one frozen script version is now a checked fact: CLOSED

`collect_scores` carries `source_fingerprint` into each run entry and raises a
`'two trainer versions for one run'` conflict when two waves of one run disagree; the new
`trainer_version()` compares across runs; `gates` and `report` both consume it.

**The fingerprint covers the data script.** It is a 10-field dict —
`novelty19_train`, **`novelty19_data`**, `dispatcher`, `dispatcher_v3`, `dispatcher_v4`,
`baseline`, `baseline_v2`, `baseline_length_eval`, `canonical_operator`, `torch` — so a data-script
drift between runs is caught, and comparison is over the whole dict, not just this file.

Fixture: 18 fabricated finished runs and 24 score documents for the registered seeds, cells
filled from **real** scored rows (one genuine D row and one genuine T row from seed 9991, so
the report renders a real document rather than a stub).

| scenario | merged | `passed` | gates | report |
|---|---|---|---|---|
| uniform (control) | 24 | **true** | rc 0 | *"one frozen script version (1 distinct)"*, rc 0 |
| one run from another trainer version | 24 | **false** | rc 1, names `['awake-D-s1900']`, differing `['novelty19_train']` | *"MIXED (2 distinct)"*, names the run, rc 1 |
| one run from a drifted **data** script | 24 | **false** | rc 1, differing `['novelty19_data']`, names the run | *"MIXED (2 distinct)"*, names the run, rc 1 |
| one run with a **null** fingerprint | 24 | **false** | rc 1, *"1 without a fingerprint"*, names the run | names it under *runs with no fingerprint*, rc 1 |
| one run with the field **absent** | 24 | **false** | rc 1, same | same, rc 1 |

Both commands refuse and both name the offending run. `gates` writes its artifact first and
*then* raises, so the record of the refusal survives. In every failing scenario no
`DEV-PASSED.json` was written. `development_rule.evidence_complete` also folds in
`trainer_versions`, `runs_from_another_version` and `runs_without_a_fingerprint`.

Note only (cosmetic): when the offending run's fingerprint is null or absent the report line
reads *"MIXED (1 distinct)"* — accurate for the count of comparable versions but mildly
confusing; the *"runs with no fingerprint"* line immediately below gives the real reason.

## 3. N8 — hash before load: CLOSED

`load_run_checkpoint` now opens with `recorded = verify_recorded_sha(path)` **before**
`saved = torch.load(Path(path), map_location='cpu', weights_only=False)` — verified by
position in the function body, not by grep alone. The resume path (`load_state`,
`load_weights_only`) still hashes first. The scoring path and the resume path are now
consistent; nothing is deserialised before it is authenticated.

## 4. Training path still byte-identical

Fresh 8-update awake runs on the rebuilt seed-9991 stream:

- awake **D** `e216551f9f8c85ae…`
- awake **T** `48e8d108a1dbf5a8…`
- data fingerprint `f8c846112ff72f15…` for **both** architectures

All three reproduce my earlier evidence exactly. The training/optimizer/RNG path is unchanged
by this patch.

## Reproduce

```bash
cd <worktree>
export OMP_NUM_THREADS=1
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
S=artifacts/fable-novelty19-replay-20260920/audit/scratch4
$PY -B scripts/fable_novelty19_data.py operator-history --out $S/ophist --quiet
$PY -B scripts/fable_novelty19_data.py dev-panels --out $S/dev --n 8 --operator-history $S/ophist --quiet
$PY -B scripts/fable_novelty19_data.py awake-stream --seed 9991 --updates 200 --out $S/awake --dev-panels $S/dev --quiet
$PY -B scripts/fable_novelty19_data.py memory  --seed 9991 --stream $S/awake --out $S/mem --worlds 64
$PY -B scripts/fable_novelty19_data.py buffers --seed 9991 --memory $S/mem --out $S/buf --dev-panels $S/dev --offline-updates 30
for A in D T; do $PY -B scripts/fable_novelty19_train.py awake --arch $A --seed 9991 \
    --out $S/runs/awake-$A --stream $S/awake --updates 8 --quiet; done
cd artifacts/fable-novelty19-replay-20260920/audit
$PY -B train_recheck3.py      # M-2, N8, fingerprints (M-1 section inconclusive by design)
$PY -B train_recheck3_m1.py   # M-1 with the seed global substituted
```

The `scratch4/` fixture (≈ 65 MB) was deleted after these measurements.

## Status of the earlier items

M-1 closed, M-2 closed, N8 closed. N6 remains a note (assessed in Re-check 2: the checkpoint
`.pt` carries no wall-clock keys and its sha is reproducible). N1–N5, N7, N9 stand as written;
none can change a registered verdict. The only new observation is the cosmetic report wording
in §2, note-only.

**FREEZE-READY (training side): YES.**
