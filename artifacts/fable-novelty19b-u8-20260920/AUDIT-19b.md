# Experiment 19b — independent adversarial audit

Auditor: independent audit agent, 20 September 2026. Same standards as the experiment-19
audit. I am not a builder: no builder file was edited. The only files I wrote are this
one and `audit-scratch/`.

Everything below is something I ran or read myself. Where I could not run a check I say
so rather than inferring it from the builder's own tests. The builders' test suites were
re-run, but nothing in this verdict rests on them.

---

## 0. What was audited, re-hashed from disk

| File | sha256 |
| --- | --- |
| `scripts/fable_novelty19b_data.py` | `1467112295e4df51351152d438e137076fd83e8fbdf21deb9ff01af723947a88` |
| `tests/test_fable_novelty19b_data.py` | `955cc2d92e5439350af2150eb3ee0e81980d4f921212c3aa12cfdff924bec3f2` |
| `scripts/fable_novelty19b_train.py` | `2c4602a4e39fd74a11c299ec6aa09dc3d6388b52999cbf324b4c6955c37e14dd` |
| `tests/test_fable_novelty19b_train.py` | `654e0641ac4789120a423d88527c8c3c39c3e4f24eeee2e3a806a539e332ecf9` |
| `artifacts/fable-novelty19b-u8-20260920/run_data.sh` | `f7d4d1bc72e80583887ebcf5206295164f0255bfe9524201362db01a2656a3b3` |
| `artifacts/fable-novelty19b-u8-20260920/run_offline.sh` | `97a351b189f0d93f0dabd4455bb9ccaaca00d3cb86be8575ae8a274fd7b46ac3` |
| `artifacts/fable-novelty19b-u8-20260920/run_score.sh` | `d5a2612ebacb16537c5998898342d86b900b494173a2a0545505e9882252514b` |
| `artifacts/fable-novelty19b-u8-20260920/FABLE-PREDICTIONS.md` | `2298881d27ed1fe4455a986066256995afbbf65f1e540f4806828127f0552659` |
| `design/v3/19-development-readout-and-next-step.md` | `6d95f596d0a40911336d106f35d1d2e7387b82b225f07f93b654633e03714abf` |

Every one matches the prefix I was given. The two frozen experiment-19 modules are
**unchanged**: `scripts/fable_novelty19_data.py` = `ef1df0e149aa4741a22f7185fadb9eaeb054b072d50c09a1ad2a196a998ae9de`,
`scripts/fable_novelty19_train.py` = `77644a1f15e6e683b2260261b04411a6ee30c8bb74f80121a8ef7318749cd5a8`.

Astra's design was read in full, including "One next experiment" and "Prospective marks".

**Test suites** (plain scripts, not pytest; `OMP_NUM_THREADS=1`):

| Suite | Result |
| --- | --- |
| `tests/test_fable_novelty19b_data.py` | 35/35 passed |
| `tests/test_fable_novelty19b_train.py` | 23 passed, 0 failed, 0 skipped |
| `tests/test_fable_novelty19_data.py` (frozen) | 53 passed, 0 failed, 0 skipped |
| `tests/test_fable_novelty19_train.py` (frozen) | 32 passed, 0 failed, 0 skipped |

---

## 1. The process deviation: artifacts built before the freeze

`run_data.sh` was run before any freeze, so `buffers-{1900,1901,1902}/`, `dev-panels/`
(38 cells) and `audit/audit-19{00,01,02}.json` already existed when this audit began.

**State check.** `artifacts/fable-novelty19b-u8-20260920/runs` does not exist and
`scores/` is empty. No training and no scoring has run. `logs/waves.log` shows
`run_offline.sh` and `run_score.sh` invoked at 22:47:24Z and correctly *refusing*
(`OFFLINE_FAILED … missing buffers`, `SCORE_FAILED … no dev-panels`), the data wave at
22:48–22:50Z, and a second data invocation at 22:50:15Z in which every stage SKIPped.

**Rebuild.** I rebuilt all three seeds' buffers and the whole 38-cell panel suite into
`audit-scratch/` using the current script bytes (the module's CLI supports `--out`, so no
patching was needed). Result:

* `buffer-U5.pt`, `buffer-U8.pt`, `forbidden-semantics.json`, `forbidden-worlds.json`,
  `offline-order.json` and **all 38 cell JSONs are byte-identical** to the registered
  artifacts.
* The only differences are wall-clock sidecars (`*.meta.json`) and recorded absolute
  output paths: 44 path-only fields in the panel manifest, 2 in each buffer `audit.json`,
  3 in each buffer `manifest.json` (the third being `audit_sha256`, which is itself a
  function of the two recorded paths).

Registered buffer hashes, seed 1900:
`buffer-U5.pt = 4a909b69485e01674b48caafe06f85a805db5bf7334733c10e794707c19ec4f3`,
`buffer-U8.pt = 658c208fa69df673764e872d42b68c95b4a235b722ad25fc3c9c9455f82c0e9f`.

**Outcome-independence.** Nothing in these artifacts can have been influenced by an
outcome. There was no model, no checkpoint and no score in this experiment when they were
built; the build is a deterministic function of experiment 19's frozen memory worlds, the
seeds and the frozen exclusion sets, which my rebuild reproduces exactly without any
checkpoint present. The sampler's keys (`{ns}:{seed}:{world}:{candidate}`) contain no arm
and no result.

`audit/audit-19xx.json`: three distinct files, 31/31 checks each, `passed: true`, no
absent checks.

**One real deviation to record in the freeze:** `run_data.sh` has mtime 18:50:09, *later*
than the artifacts it produced (18:48–18:49). The exact launcher bytes under audit are
therefore not the bytes that ran. The data module's own mtime (18:41:15) predates the
build, and my rebuild — which used the module's default arguments — reproduces the
artifacts byte for byte, so the artifacts are provably the default-argument build of the
current module bytes and the launcher edit cannot have changed them. See MINOR-1.

---

## 2. Attack (a) — the one-change claim

My own decoder parsed the six `.pt` files; the builder's audit was not consulted.

| Claim | Result |
| --- | --- |
| U5 support ⊆ {1..5}, U8 ⊆ {1..8} and U8 actually reaches 8 | true, all three seeds |
| Zero composite-r10 items (c≥2 ending in 10) | **0 in all six buffers**, counted from the `.pt` files |
| Terminal rule r∈{8,9,10} at c=1, {8,9} otherwise | 0 violations in all six buffers |
| Identical world rows and identical owner order across arms | true, all three seeds |
| Length law recomputed from the frozen RNG keys | 0 mismatches over every accepted item |
| Subject binding shared across arms on slots both arms accepted | 4,030 / 4,027 / 4,019 shared slots, **0 start mismatches** |
| `STREAM_MAPPING_SHA256` | `685264df864fd31974ae0857f8566a35d3fb7af51d55696e102c59996d266142`, and my own digest of `STREAM_MAPPING` reproduces it |
| U5 item-identical to experiment 19's U | `item_view_sha256` equal per seed over all 4,096 items: 1900 `54f9b13c…`, 1901 `80e7d1ff…`, 1902 `40b3e110…` |

Accepted histograms, seed 1900: U5 `{1:804, 2:843, 3:790, 4:839, 5:820}`, endings
`{8:1948, 9:1879, 10:269}`; U8 `{1:515, 2:487, 3:512, 4:529, 5:515, 6:505, 7:521, 8:512}`,
endings `{8:2019, 9:1904, 10:173}`. r=10 appears only at c=1, as the terminal rule requires.

Shared world-index order: one `offline-order.json` per seed, shared by both arms,
2,000 rows × 16 indices in 0..1023, namespace `astra-novelty19-offline-order-v1`, and the
builder's audit check `offline_order_matches_experiment_19` binds it to experiment 19's
own order.

## 3. Attack (b) — panels

* 38 cells, **64 units each**, cell list matches the registered 38.
* All visited people distinct on **both sides of every unit in every cell** (this covers
  c=6..8 in 16-person worlds, which is where Astra requires it).
* Balanced answers: every cell has answers 12..27, four units each.
* One ending per cell.
* Panel worlds (2,816 signatures) ∩ 19b buffer worlds (3,072 signatures) = **0**.
* The panel build's exclusion union is verified against the operator history, experiment
  19's training/replay/candidate/dev artifacts and the 19b buffers; the module hash- and
  count-verifies each source *before* creating the output folder.

**E edit pairs, checked with my own interpreter.** For all six E cells (384 pair units) I
walked each side's visible memory from the question alone and re-derived the answer and
the chain:

| Cell | my walk reproduces every answer | every chain | question identical both sides | rows edited | edit on the chain | answer changed |
| --- | --- | --- | --- | --- | --- | --- |
| E-c5-link / E-c8-link | yes | yes | yes | 1 | 64/64 | 64/64 |
| E-c5-value / E-c8-value | yes | yes | yes | 2 | 64/64 | 64/64 |
| E-c5-irrelevant / E-c8-irrelevant | yes | yes | yes | 2 | 0/64 | 0/64 |

That is exactly the interpreter-only construction Astra asks for: the twin differs only in
memory rows, never in the question, and the expected answer changes for link and endpoint-
value edits and does not change for irrelevant edits.

**The confirmation lock.** `build_dev_panels` calls
`validate_dev_passed(experiment, seeds=…)` before it builds anything when
`--confirmation` is passed, and refuses the confirmation namespace outright without that
flag (`fable_novelty19b_data.py:757`, `:762`). I attacked the validator directly with a
genuine 19b unlock record as the starting point; every mutation was refused:

| Probe | Result |
| --- | --- |
| right shape, experiment-19 schema string | refused (schema) |
| one offline checkpoint entry removed | refused (missing entries) |
| an extra checkpoint entry added | refused (unexpected entries) |
| a checkpoint hash replaced by the string `PASSED` | refused (not sha256) |
| `dev_panels.manifest_sha256` not matching the folder on disk | refused |
| empty file | refused |
| experiment 19's own `DEV-PASSED.json` | **could not be tested — experiment 19 FAILED and has no `DEV-PASSED.json` on disk.** The schema string differs (`novelty19b-dev-passed-v1` vs `novelty19-dev-passed-v1`) and the wrong-schema probe above is refused, so the path is closed, but I did not run that exact file. |

## 4. Attack (c) — the trainer

* **Awake start.** `fable_novelty19b_train.py:509-510`: `TR.verify_recorded_sha(path)`
  runs **before** `torch.load`. The checkpoint's phase, arch, seed and `updates_done`
  (6,000) are then checked, and `run_phase` checks phase/seed again.
* **Optimizer reset.** `fable_novelty19_train.py:593-598` (frozen): on the offline branch
  the optimizer is rebuilt, the policy generator is re-seeded to
  `D_GENERATOR_BASE + seed` and `torch.manual_seed` is set to the same value. Both arms
  of a seed therefore start from an identical optimizer state and identical policy RNG.
* **Shapes and costs, all frozen and unmodified:** 16 worlds × 4 questions per update
  (`offline_record`), `D_K = 16` → 1,024 episodes/update, `D_CALL_COST = 0.01`, reward =
  exact-answer match, the frozen LR/entropy schedule via `dispatcher_schedule`. 19b passes
  nothing that could change any of these.
* **Caps.** `D_TRAIN_CAP = 8`, `D_EVAL_CAP = 16`, unchanged. I ran the cap probe myself
  on disposable seed 9991: `stop_sampled_after_the_last_lookup: true`,
  `cap_length_answer_terminates_normally: true`, `exhausted_episode_fails: true`,
  `override_needed: false`, `passed: true` — i.e. STOP is sampled after the 8th executed
  lookup, an 8-call answer terminates as `answered`, and an episode still running at the
  cap keeps `over_cap` and answer 0.
* **Not present, confirmed by reading:** no remaining-count feature, no gold path, no
  forced continuation, no halting loss, no success-adaptive schedule, no best-checkpoint
  or intermediate-panel selection, no seed replacement, no extra budget.
* **Work ledger.** The wrapper at `:394-398` calls the original `dispatcher_update` and
  `return row` — the *same object*, not a copy — so the row chained into
  `update_fingerprint` and written to the frozen log is the frozen function's own object.
  `work_row` only reads fields. `--no-work-ledger` exists so this can be demonstrated.
* **Final checkpoint only.** Enforced downstream by `TR.checkpoint_binding`; my synthetic
  "mid-run 1,500-update checkpoint offered as the result" attack was rejected (see §5).

## 5. Attack (d) — the gates against Astra's five conditions

The five conditions are read over cell groups **derived from the cell specifications**
(hops, world size, ending, pair-ness) and cross-checked against the data module's
published `MARKS` lists; a disagreement is a refusal
(`fable_novelty19b_train.py:302-332`). `expected_group_sizes()` pins
bounded = 4 N + 8 P + 9 L = 21, contrast = 3, guards = 6, F = 7, H = 4, and a shape
mismatch makes the whole rule undetermined.

I built 21 adversarial synthetic score tables on **disposable seeds 999001–999003** (no
registered training or scoring; every score file is synthetic JSON; fabricated run
directories carry a `completion.json` so `checkpoint_binding` is genuinely exercised) and
ran `gates` then `report` exactly as `run_score.sh` does. The single fixture substitution
was setting `SEEDS` to the disposable triple in **both** modules — patching only one is
refused by `check_layout_agrees` ("the training and data modules disagree"), which is
itself a defence worth recording.

| Attack | gates | rule | `DEV-PASSED.json` |
| --- | --- | --- | --- |
| a true full pass (control) | ok | PASS | **written and accepted by `validate_dev_passed`** |
| one bounded cell at 57/64 in one seed | ok | FAIL (`999002:bounded_competence`) | not written |
| one long cell strict 57 with answers 64 | ok | FAIL — answers alone do not rescue | not written |
| one F cell at 60/64 (mark 61) | ok | FAIL (`retention`) | not written |
| one E guard cell at 57/64 strict pairs | ok | FAIL (`guards`) | not written |
| **gain of exactly 13** (boundary) | ok | PASS | written |
| **gain of exactly 12** (boundary) | ok | FAIL, all three seeds | not written |
| **H loss of exactly 6** vs the awake anchor | ok | PASS | written |
| **H loss of exactly 7** vs the awake anchor | ok | FAIL, all three seeds | not written |
| one awake anchor never scored | ok | undetermined | not written |
| one U5 control never scored | ok | undetermined | not written |
| NaN counts in one cell | ok | crash (`ValueError`) | not written |
| swapped arm labels on one seed | ok | FAIL (rejected by `checkpoint_binding`) | not written |
| mixed source fingerprints across runs | **REFUSED**, names `offline-D-s999003-U8` | undetermined | not written |
| drifted 19b **data** script between runs | **REFUSED**, names `offline-D-s999002-U5` | undetermined | not written |
| one run with no fingerprint at all | **REFUSED**, names `awake-D-s999001` | undetermined | not written |
| the same run scored twice | ok | FAIL (provenance: conflicts) | not written |
| one run scored on a different panel suite | ok | FAIL (provenance) | not written |
| a mid-run 1,500-update checkpoint as the result | ok | FAIL | not written |
| the two arms scored on different units in a contrast cell | ok | undetermined, contrast abstains | not written |

Twenty-one for twenty-one behave as the preregistration requires, and `DEV-PASSED.json`
appeared **only** on a true full pass. Note in particular:

* **The H boundary is exactly where it should be:** loss 6 passes, loss 7 fails
  (`row['…_loss'] < H_LOSS_LIMIT`, `:938-939`).
* **The gain boundary is exactly where it should be:** +13 passes, +12 fails, and it is
  computed unit-by-unit on matched `unit_index` lists with wins/losses/ties published
  (`paired_strict`, `:881-894`); mismatched unit lists abstain rather than compare.
* **The awake anchor is scored and cannot select.** `run_score.sh` scores the three
  experiment-19 awake finals on 19b's fresh panels, read-only. The anchor is used only as
  the H-retention baseline in `condition_retention`; there is no code path in which a
  seed is chosen, replaced or dropped. If the anchor is missing, H is *undetermined*, so
  an unscored anchor can never help.
* The **source fingerprint covers both 19b scripts and the 19b data script**
  (`source_fingerprint()`, `:729-741`), so a data-script drift between runs is caught —
  demonstrated above.

**The builder's judgement calls.** I could not find a written list of 14 judgement calls
anywhere on disk (`artifacts/fable-novelty19b-u8-20260920/`, the module docstrings, the
logs); what follows is my own reading of the discretionary points in the code. My view:
**none of them requires a design ruling**, but two should be recorded in the freeze.

| Judgement | My reading |
| --- | --- |
| H-loss limit applied to **both** answers and strict | Astra writes "no H-cell loss ≥7/64" without naming a metric. Applying it to both is strictly more conservative than either single reading, so it cannot manufacture a pass. **Record it; no ruling needed.** |
| A missing endpoint is **undetermined**, not failed | Correct and honest: nothing was observed. `None` never unlocks anything, and provenance also turns `None`. No ruling needed. |
| Per-unit flags added to the score JSON | Necessary — Astra's condition 2 is "on identical units" and the frozen score file records cell totals only. The flags use the same both-twins-must-pass rule as `V3.aggregate`. See MINOR-4 for the one safeguard I would add. |
| Cell groups derived structurally, then cross-checked against the published `MARKS` | Strictly stronger than either alone. No ruling needed. |
| `bounded` includes the three r10 long cells that are also the contrast cells | Matches Astra's text (condition 1 covers "all nine c=6..8 cells"). No ruling needed. |
| U5's own bounded competence reported but never a pass condition | Matches Astra's interpretive paragraph. No ruling needed. |
| Confirmation marks recorded but no confirmation built | Matches "Only after the new development conjunction passes…". No ruling needed. |
| `report --seeds` subset cannot unlock | `dev_passed_payload` refuses any seed set other than the registered triple. Correct. |

## 6. Attack (e) — the launchers

* **`set -u` and `set -o pipefail` are set in all three launchers; `set -e` is not.** Every
  command's exit code is nevertheless checked explicitly, `mkdir` is `|| exit 1`, and
  `pipefail` means the `… | tee gates.txt` pipelines in `run_score.sh` still report the
  Python exit code. I found no unchecked failure path.
* **Refusal to overwrite.** `run_offline.sh` SKIPs any run directory that already holds
  `completion.json`; `run_score.sh` SKIPs any score file that exists, refuses to score a
  run without `completion.json` or without its final checkpoint, and skips `report`
  rather than passing `--overwrite`. `score` writes with `write_new`, which refuses an
  existing file. Observed in `waves.log`: the second data invocation SKIPped every stage.
* **Loud failure.** Every failure path prints `OFFLINE_FAILED` / `SCORE_FAILED` to
  `waves.log` and exits non-zero; per-job status files are collected after `wait`.
* **Six one-thread processes.** `run_offline.sh` exports `OMP_NUM_THREADS=1` and
  `VECLIB_MAXIMUM_THREADS=1` and launches all six (3 seeds × 2 arms) together, so no
  machine-state difference can track the arm. `run_score.sh` runs 9 jobs at concurrency 3.
* **Bare `./run_*.sh`.** All three files are mode `644` — **not executable** — so
  `./run_offline.sh` fails immediately with "permission denied" and does nothing. That is
  safe, but it is not what "bare `./run_*.sh` is safe" was meant to establish; the
  intended invocation, given in each header, is `bash run_offline.sh`. See MINOR-5.
* **Timing.** The builder projects U8 ≈ 14–21 min for 2,000 updates six-way concurrent. I
  ran a disposable probe (model seed 9991, this audit's own rebuilt buffer copy, nothing
  written, ≤ 2 processes, under 3 minutes). A first probe was uninformative — an untrained
  disposable model executes almost no lookups (mean_calls ≈ 0.09) — so I replayed the
  frozen update body with a policy hook forcing exactly *k* executed lookups:

  | forced lookups | measured mean_calls | s/update (2 concurrent) | projected 2,000 updates |
  | --- | --- | --- | --- |
  | 5 | 5.0 | 0.292 | 9.7 min |
  | 8 | 8.0 | 0.348 | 11.6 min |

  Ratio f(8)/f(5) = **1.19** here, against the builder's measured 1.42–1.67. My absolute
  per-update cost is ~4× the builder's, almost certainly because three other agent jobs
  were running on this machine throughout. The projection is therefore plausible but
  optimistic under load; at six-way concurrency the wave may exceed 30 minutes. This
  cannot lose work: `--budget-seconds 1200` stops at a chunk boundary and
  `run_offline.sh` re-issues the same command up to 8 rounds with 4 chunks of 500. See
  NOTE-1.

---

## 7. Findings

### BLOCKER
None.

### MAJOR
None.

### MINOR

**MINOR-1 — the launcher under audit is not the launcher that ran.**
`artifacts/fable-novelty19b-u8-20260920/run_data.sh` (mtime 18:50:09) post-dates the
artifacts it produced (18:48–18:49). *Failure scenario:* if the edit had changed an
argument — a different `--memory` folder, an added `--extra-exclusion`, a different
`--offline-updates` — the frozen launcher would describe a build that never happened.
*Why it does not block:* my rebuild with the module's **default** arguments reproduces
every buffer and all 38 panels byte for byte, which is only possible if the build used
those defaults. *Condition:* the freeze manifest should record that `run_data.sh` was
edited after the build and that the binding evidence is the content rebuild, not the
script.

**MINOR-2 — `gates` exits 0 on missing endpoints, incomplete runs, conflicts and
rejected score files.** `fable_novelty19b_train.py:1233-1239` raises `SystemExit` only for
a mixed script version. *Failure scenario:* three score files are rejected as the wrong
checkpoint; `gates` prints them, exits 0, `run_score.sh` continues and finally logs
`SCORE_DONE`, so a skim of `waves.log` suggests a clean wave. *Why it does not block:* the
rule itself cannot pass — `no_conflicts` turns provenance `False` and a missing endpoint
turns it `None` — and I verified both cases produce no `DEV-PASSED.json`. *Condition:*
read `logs/gates.txt` before believing `SCORE_DONE`, or have `gates` exit non-zero when
`endpoints_missing`, `conflicts` or `rejected` is non-empty.

**MINOR-3 — a NaN in a cell count crashes `report` with an unhandled `ValueError`.**
`_counts` (`:840`) does `int(row['answers'])`. *Failure scenario:* a corrupted score file
carrying `NaN` aborts `report` with a traceback *before* `report.json` is written, so the
wave fails with no artifact at all. *Why it does not block:* it is fail-safe —
no `DEV-PASSED.json`, non-zero exit, `SCORE_FAILED` in `waves.log` — and the frozen scorer
produces integer counts, so I could not construct a realistic route to a NaN. *Condition:*
none; worth a clean refusal message eventually.

**MINOR-4 — the per-unit flags and the cell totals are never compared.** Conditions 1, 3
and 4 read `cells[cell]['strict']`; condition 2 reads `unit_flags[cell]['strict']`. Both
come from the same `native` transcripts (`unit_flags`, `:591-604`), but nothing asserts
`sum(unit_flags[c]['strict']) == cells[c]['strict']`. *Failure scenario:* a future edit to
`unit_flags` (e.g. dropping the both-twins rule) would silently move only the treatment
effect while every other condition still looked right. *Condition:* add that one-line
equality check to `score` or `collect_scores`. Cheap, and it closes the only place where
two derivations of the same measurement can diverge unnoticed.

**MINOR-5 — the launchers are not executable.** All three are mode `644`, so a bare
`./run_offline.sh` fails with "permission denied". Safe, but the freeze should say the
invocation is `bash run_offline.sh`, since an operator who tries `./` and sees
"permission denied" may `chmod +x` and re-run without reading the header.

**MINOR-6 — `check('dev_panel_hashes', True, …)` is hard-coded**
(`scripts/fable_novelty19b_data.py:1135`). The audit roster records a PASS for something
it does not evaluate. *Why it does not block:* the real verification is
`N.load_dev_panels` three lines earlier, which re-hashes every cell file against the
manifest. I proved it: I copied the panels into scratch, incremented one answer in
`L-c7-r10-p16` unit 3, and the audit aborted with
`RuntimeError: panel changed on disk: …/L-c7-r10-p16.json` — before reaching line 1135.
*Condition:* none, but the label should eventually be `check('dev_panel_hashes', panels
is not None, …)` or be removed, so no audit log ever claims a check that was not run.

### NOTE

**NOTE-1 — the timing projection is optimistic.** See §6. Measured 0.348 s/update at 8
executed lookups with 2 concurrent processes under load (≈11.6 min for 2,000 updates for
one process); six-way concurrency will be slower than the builder's 14–21 min. Harmless —
the chunked budget resumes — but the wave may need more than one invocation.

**NOTE-2 — `shared_world_order` is vacuous in the registered layout.** `resolve_buffers`
returns the same folder for both arms, so `shared_order` compares a file's hash with
itself and can never fail. This is the *strongest* form of Astra's requirement (the arms
read the same bytes, not merely equal orders), and the builder says so in the docstring;
the check simply carries no independent information.

**NOTE-3 — `report.json` does not record whether `DEV-PASSED.json` was issued.** The
unlock record contains `report_sha256`, so the report must be hashed first; the
`dev_passed` fields are therefore added to the in-memory payload after `write_new`
(`:1347-1377`). The binding is one-directional by necessity. Read `logs/report.txt`, which
does print the outcome.

**NOTE-4 — `score` itself does not check that a checkpoint is final.** It will write a
score file for a mid-run checkpoint; `checkpoint_binding` rejects it at merge time, and
`run_score.sh` refuses a run without `completion.json`. Verified by attack.

**NOTE-5 — experiment 19's `DEV-PASSED.json` could not be tested verbatim** because
experiment 19 FAILED and never wrote one. The schema-string and roster defences are
verified against a hand-made file instead.

**NOTE-6 — my U5/U8 pairing claim is precise.** The length draw uses the same key but a
different candidate list per arm, so the two arms' *lengths* on a shared slot are
correlated, not equal — which is what "only the length support changed" means. What is
strictly shared is the world bytes, the owner order, the world-index order and the subject
binding (0 start mismatches on ~4,020 shared slots per seed). This is Astra's
"outcome-independent pairing", not per-item length matching, and nothing in the design
asks for the latter.

---

## 8. Conditions attached to this verdict

1. The freeze manifest records that `run_data.sh` was edited after the artifacts were
   built, and that the binding evidence is this audit's byte-identical content rebuild
   (MINOR-1).
2. The operator reads `logs/gates.txt` — not just `SCORE_DONE` in `waves.log` — before
   treating a scoring wave as clean (MINOR-2).
3. The invocation is recorded as `bash run_*.sh`, not `./run_*.sh` (MINOR-5).
4. MINOR-4 (assert the per-unit flags sum to the cell totals) and MINOR-6 (drop the
   hard-coded `dev_panel_hashes` label) are logged as post-freeze cleanups. Neither can
   change a registered verdict as the code stands, and neither requires a rebuild.
5. No design ruling is required on any of the builder's judgement calls; the H-loss
   reading (applied to both metrics) and the undetermined treatment of a missing endpoint
   are recorded in the registration as stated in §5.

Everything Astra's design and the freeze checklist require is present and behaves
correctly under attack: the one-change claim holds item by item, the panels are fresh and
interpreter-only, the trainer is the frozen trainer with a provably inert ledger, the
cap/STOP boundary is what was registered, and the five conditions refuse every fabricated
pass I could build while admitting a true one.

FREEZE-READY: YES
