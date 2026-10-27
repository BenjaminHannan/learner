# Experiment 26 — builder's notes

Builder: Claude (Opus 5) subagent, 2026-09-21. Binding specification:
`design/v3/26-dispatcher-stop-probes-registration-fable-review.md`,
sha256 `7d7708e79e7b755bfa47d50bd7aeb8b550d02b20930a313ad1547a7337a09f45` — verified on disk
before anything was written, and re-verified by the script itself at `panel` time and at
every `probe` call.

Everything below is additive. No existing script, checkpoint, ledger or artifact was edited;
nothing was committed; nothing ran on BensPC or in the cloud; no `test.pt` is ever named.

## 1. What was built

**Revision 2 (2026-09-21), after the independent audit `AUDIT-26.md`
(sha256 `0929d0ebc3119e9f46a8dbdba749589ddb79c4c8550f546d36a991d600606414`, verdict
FREEZE-READY: NO).** Section 9 below lists exactly what changed. Only the three builder
files were edited; the audit file, the forecasts, the ledger and the specification were not.

| file | sha256 |
|---|---|
| `scripts/fable_dispatcher_probes26.py` | `f78ca888c7d0c1381cd5c0dbd1e1363b6c2b6699a5f1db728fecc621253af228` |
| `tests/test_fable_dispatcher_probes26.py` | `22c11a14b7c2d17486705f738093e2e622fa1618af9a6188068dfc55f773de21` |
| `artifacts/fable-dispatcher-probes26-20260921/BUILD-NOTES.md` | this file |

(Revision 1, audited: script `c0f91f97…`, tests `8770edf3…`, notes `91ecc88e…`. Because the
script's sha256 changed, **any output directory written by revision 1 is now unusable** — the
script refuses to read or extend it. The registered run must start from an empty directory,
which is the state `artifacts/fable-dispatcher-probes26-20260921/` is in.)

`artifacts/fable-dispatcher-probes26-20260921/FABLE-PREDICTIONS.md` and its `.sha256.txt`
were **not touched**. The ledger was **not touched** (P102–P117 were entered by the
coordinator before this build).

Tests: **21 checks, all passing** (plain script, no pytest), about 2 s wall-clock.

```
OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
PYTHONPATH="$(/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12 -c "import json;print(':'.join(json.load(open('/Users/ben-hannan/Desktop/projects/beautiful-model/runtime.local.json'))['import_roots']))")" \
/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12 -B \
  tests/test_fable_dispatcher_probes26.py
```

What the tests cover: the specification hash and all 24 section-2 checkpoint hashes on disk;
the five section-2 code hashes and the frozen operator hash; the new panel namespace being
new and reproducible; the probe-A classifier on **each of the eight categories plus NONE**
and on four precedence cases, and that it does not mutate its inputs; the probe-C policy
reproducing `force_operation+subject` at steps 0 and 1 exactly and forcing nothing at step 2
or later; that every probe-C forced position is a LINK look-up; that the logits in `record`
are the model's own (a forced run whose forced choices equal a free run's greedy choices has
bit-identical recorded subject/operation/STOP/state tensors — the auditor's checklist item);
that the direct `rollout_v4` used for the logits is the same episode `score_side_v4` scores;
geometry being skipped for arms without learned positions; **every section-5 threshold on
both sides of its boundary**; the positive control and every decision row including the D0
short-circuit; the 2-of-3 family rule; and an end-to-end `panel → probe → resume → report`
smoke that also proves the refuse-to-overwrite and resume behaviour. A static guard fails the
build if the script ever grows `torch.save`, `optimizer.step`, `loss.backward` or `.train()`.

Revision 2 adds four checks: the probe source sha256 is pinned (a foreign hash in the
manifest or in any probe output is refused by `load_panel`, `probe` and `report`, and nothing
is written after the refusal); `report --suffix final` is refused while the run is incomplete
and `--suffix control` prints no decision row at all; a panel of any size or cell list other
than §3's is refused without `--dev`, and a `--dev` panel cannot be read as a registered run;
and the frozen forecasts hash into the manifest and still match their own `.sha256.txt`.

## 2. Deviation from §9's file names (instructed)

§9 names `scripts/fable_probe26_fault_localisation.py`, `tests/test_fable_probe26.py` and
`artifacts/fable-probe26-20260920/`. The coordinator's build instruction names
`scripts/fable_dispatcher_probes26.py`, `tests/test_fable_dispatcher_probes26.py` and
`artifacts/fable-dispatcher-probes26-20260921/` (which already exists and holds the
forecasts). I followed the coordinator. Nothing else about §9 changed: the sub-commands are
`panel`, `probe --ckpt … [--family …]`, `report` as specified (plus a read-only `list`, and a
`--dev` guard flag added in revision 2 that marks a non-§3 panel and makes it unreadable as a
registered run).

## 3. Judgement calls and places the specification was silent

1. **Classifier inputs.** §9.4 asks for a pure function over (transcript, chain, status,
   pointers). Sub-typing an `INVALID` needs to know *which token* the illegal pointer
   carried, so the function also takes that unit's raw question tokens. It is still pure and
   still label-free (the question is part of the unit, not a label).
2. **Classifier cases §4 does not enumerate.** Decided as follows, in §4's own order:
   a correct proper prefix with status `invalid_action` → `INVALID` (category 7, not
   `STOP_EARLY`, which §4 defines as *answered*); the complete correct chain followed by an
   illegal action → `INVALID` (category 6 is defined for "answered late or over_cap" only);
   the complete correct chain with status `over_cap` → `STOP_LATE` ("never chose STOP");
   `OTHER` is reachable only at the terminal step, where a wrong operation can be a *different*
   relation (neither "relation where the chain links" nor "LINK where the chain ends").
3. **Native logits.** `V4.score_side_v4` has no `record` parameter, so the per-step native
   numbers come from a second `V4.rollout_v4` call with the same policy, the same prepared
   operator table and the same block size. The script **asserts** that this second run agrees
   with `score_side_v4` on `answers` and `strict` for every cell before using it, and a test
   checks the two episode sets are identical.
4. **Block size 32**, the default the registered v3/v4 scorers used, so the arithmetic is the
   same shape as the `diagnosis.json` the positive control is measured against. Not 64, even
   though one block per cell would have been simpler.
5. **R4(d) made precise.** §5 says "operation-only strict < 59 … and R1(d) holds, same
   depth", while R3 is defined over *both* k8 cells. R4(d) is implemented as the mirror of
   R3: NOT(operation-only ≥ 59 on both `kd-prac` and `kd-held`) AND R1(d). Per-cell numbers
   are in the JSON, so a different reading can be re-derived without re-running anything.
   *Audit ruling: acceptable, but it must be named in the output.* Revision 2 prints it in
   section 2 of every report ("R4(d) is read as: NOT (operation-only strict ≥ 59 on BOTH
   kd-prac and kd-held), with R1(d) holding") and records it in `report*.json` under
   `r4_reading`, because row D3 and forecast P106 turn on it and this is the looser reading.
6. **R5** uses the `STOP_EARLY` count from classifying the `force_operation+subject` run's own
   episodes (the same classifier as probe A), on `k4-held` or `k5-held`, whichever is larger.
7. **Probe C, S0.** "NEXT" (last forced position + 1) and "THIRD" (`left+4`) coincide at
   condition S0, so with the order REL → NEXT → THIRD → other LINK → other, S0's THIRD bucket
   is always 0 by construction. R6′ counts NEXT + THIRD + OTHER_LINK (§5 writes "NEXT + other
   LINK"; THIRD is an "other LINK" in S3, which is the condition R6/R6′ are read on).
8. **R7's margin** is read at step 2 of condition S0 on `k8-held` (R6 is defined on
   `k8-held`); `k8-prac` is logged identically, so the other reading is available.
9. **Probe D pooling.** "the k3 units" = `k3-prac` + `k3-held` pooled (128 units);
   "adjacent LINKs #3–#6" in the k8 units = the three adjacent pairs (#3,#4), (#4,#5),
   (#5,#6), i.e. question positions (4,5), (5,6), (6,7). Per-cell medians are also written.
10. **"Not-yet-used LINK"** = a LINK question position not yet chosen as the *operation*
    pointer in that episode, read from the rollout's own `pointers` record.
11. **Margins.** §4 asks for "best not-yet-used LINK minus the attribute" in probe B and
    "REL minus best LINK" in probe C. Both are logged for both probes, under explicit names,
    so no sign convention has to be guessed later.
12. **Optional family 19-U** is in the registry as group `optional`; it is probed only if
    asked for by id, and it is excluded from the positive control and from the decision table
    (as §2 says). *Audit M3: the auditor loaded 19-U and 19b-U5 and found their state dicts
    bit-identical at all three seeds — 19b's `U5` arm reproduced experiment 19's uniform arm
    exactly.* Revision 2 therefore **drops 19-U from the command lines** (it is not probed:
    it would produce a numerically identical second copy of 19b-U5 and any per-family table
    listing both would double-count), keeps it in the registry so its hashes are still
    verified at `panel` time, and states the weight identity in the report header.
13. **Report gating.** Three gates, in this order. (i) If the positive control fails or is
    incomplete, the report prints the control verdict and the raw per-checkpoint count tables
    (data) and then **D0 only** — no R-flag interpretation, no per-family counts, no other
    decision row. (ii) *Audit B2:* `--suffix final` is **refused outright** (nothing is
    written) unless all twelve control and all nine registered checkpoints have been probed;
    the refusal names what is missing. (iii) `--suffix control` prints the control section and
    the data tables and **no row of the section-6 table at all**; any other suffix with a
    passing control but an incomplete registered set prints, in place of the table, only the
    list of missing checkpoints. The report header now counts `positive control N of 12` and
    `registered set N of 9` separately from the 24-checkpoint registry.
14. **Seeds.** §3 leaves no seed to choose: the panel RNG is the namespace string and every
    rollout is greedy. `torch.manual_seed(260921)` is set at the start of every probe anyway,
    so a stray RNG could not drift. Determinism was checked by re-running one checkpoint into
    a fresh directory: the JSON is byte-identical apart from timestamps, and the panel sha256
    is identical.
15. **Integrity.** Every checkpoint's sha256 is compared with the section-2 constant *before*
    `torch.load` is reached; `panel` additionally verifies all 24 at once and records them;
    `probe` refuses if any of the five imported modules or the specification changed since
    `panel`; the frozen operator goes through `TR.verified_operator()` (hash checked before
    load) and its fingerprint is asserted unchanged at the end of every probe; the loaded
    model's `flags()` must equal the family's arm. Revision 2 adds three things the audit
    found missing: (a) **the script's own sha256 is enforced**, not merely recorded — the
    manifest and every probe output carry it, and `load_panel`, `probe` and `report` all
    refuse a mismatch rather than skipping the odd file out, so two versions can never be
    mixed by the resume path (the operator must start a fresh `--out` directory after any
    edit); (b) **the panel size and cell list are enforced** — every §5 threshold is an
    absolute count out of 64, so `panel` refuses any other `--n` or cell list without an
    explicit `--dev`, and `probe`/`report` refuse a `--dev` panel outright; (c) **the frozen
    forecasts are pinned** — `panel` records the sha256 of `FABLE-PREDICTIONS.md`, of the
    value in its own `.sha256.txt`, and of `artifacts/fable-predictions-ledger.md`, and the
    report prints all three. Nothing is committed to git, so without (c) the only evidence
    that P102–P117 predate the run is a file mtime.

## 4. The two command lines

Set these once (the `probe26` shell function is only for readability):

```sh
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
PP=$("$PY" -c "import json;print(':'.join(json.load(open('/Users/ben-hannan/Desktop/projects/beautiful-model/runtime.local.json'))['import_roots']))")
OUT=$W/artifacts/fable-dispatcher-probes26-20260921
probe26 () { ( cd "$W" && OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 PYTHONPATH="$PP" \
    "$PY" -B scripts/fable_dispatcher_probes26.py "$@" ) }
```

**(a) The panel and the positive control** (run first; it must be read before anything else):

```sh
probe26 panel --out "$OUT"
for arm in reg-ctx ctx reg v3-repro; do for s in 0 1 2; do
  probe26 probe --out "$OUT" --ckpt "v4-$arm-s$s" --family "v4-$arm"
done; done
probe26 report --out "$OUT" --suffix control
```

**(b) The registered run** — the nine experiment-19/19b checkpoints, in the same `$OUT`
directory, after (a) has been read:

```sh
for s in 1900 1901 1902; do
  probe26 probe --out "$OUT" --ckpt "19-awake-s$s"  --family 19-awake
  probe26 probe --out "$OUT" --ckpt "19b-U5-s$s"    --family 19b-U5
  probe26 probe --out "$OUT" --ckpt "19b-U8-s$s"    --family 19b-U8
done
probe26 report --out "$OUT" --suffix final
```

The optional `19-U` trio is **not** probed (audit M3: its weights are bit-identical to
19b-U5 at every seed, so it would add a duplicate family and no information). It stays in
the registry, so `panel` still verifies its three hashes.

Both are resumable and safe to re-run: `probe` skips a checkpoint whose output already
exists and never rewrites it, and `report` refuses to overwrite a report of the same suffix.
`panel` refuses to run twice. `report --suffix final` refuses until all 21 probes (12 + 9)
exist, so a loop that dies half way cannot produce a decision table.

**Both command lines require an output directory written by THIS revision of the script.**
If the script is edited again — including to fix a failed positive control, which is exactly
what §6 row D0 prescribes — every command will refuse the old directory by sha256 and the
run must start again from an empty one.

## 5. Wall-clock and size (measured on this Mac, single thread)

* `panel`: 1.1 s; `panel.json` 7.9 MB, `manifest.json` small.
* `probe`: **11.1–11.9 s per checkpoint** over five runs (§8 budgeted about 1 minute), each
  `probe-<id>.json` 160–200 KB.
* Whole positive control (12): ≈ 2.5 min. Registered nine: ≈ 2 min. The 21 probes plus panel
  and both reports: **≈ 4–5 minutes**, well inside §8's 10–15 minute estimate and its
  25-minute hard stop. (The auditor measured the same on his own run.)
* Memory: peak RSS not measured; the largest object is the 640-unit panel in memory.

## 6. What the builder ran, and what it did not

Ran, as build-time validation only, **into a scratch directory outside the repository**
(`…/scratchpad/probe26-validate`, not `artifacts/`): the full 640-unit panel, and the probe
on **seed 0 of each of the four v4 control arms** (`v4-reg-ctx-s0`, `v4-ctx-s0`, `v4-reg-s0`,
`v4-v3-repro-s0`), plus one repeat run for determinism. Those four cover every code path
(register / no register, learned positions / offsets, probes C and D present / skipped).

Revision 2 re-validated in a *second* scratch directory (`…/scratchpad/probe26-validate-v2`):
the 640-unit panel — **same panel sha256 `dc176e88…` as revision 1 and as the auditor's own
build**, so none of the audit fixes touched the units — one control probe, the `--n 8`
refusal, the `--suffix final` refusal on an incomplete run, and a `--suffix control` report.

Did **not** run: the nine experiment-19/19b checkpoints (that is the registered run), the
optional 19-U trio, the remaining eight v4 seeds, and no command at all inside
`artifacts/fable-dispatcher-probes26-20260921/`. The specification is ambiguous about
whether the builder should produce the positive control itself (§6 D0 tells the builder to
fix the script if it fails; §9 does not list a build-time run); **I took the narrower reading**
— validate on a few control checkpoints in a throwaway directory, and leave the registered
output directory empty so the coordinator's own run produces the control and the experiment
together, after the independent audit.

What the four validation runs showed (throwaway directory, seed 0 only, *not* the positive
control and not to be quoted as a result): the probe reproduces the known v4 picture — the
`ctx` arm fails free-running from k4 with `OP_EARLY_ATTR` 64/64 while `force_operation`
rescues it 64/64 and `force_operation+subject` is 64/64 at every depth; the `reg` arm fails
with `SUBJECT` and is rescued by `force_subject` (64/64 on `k8-held`) but not by
`force_operation` (0–1/64); `reg+ctx` shows both defects; oracle- and trained-operator runs
agreed on the fault category in 64/64 units and no cell had an `OPERATOR` count above 2/64.
On those four, every positive-control clause that can be evaluated from one seed was on
track. That is evidence the control will pass, not the control itself.

## 7. Unverified

1. ~~**The experiment-19/19b loading path has never been exercised against real bytes.**~~
   **Discharged by the audit** (`AUDIT-26.md` §1.1): the auditor loaded all nine registered
   checkpoints (and the three 19-U) through `TR.load_run_checkpoint(path, 'D')` — recorded-sha
   check, `strict=True` state dict, stored fingerprint, and this script's arm assertion all
   pass, 34 keys and 24,035 controller parameters each. **The builder still has not loaded
   one**, and no rollout has ever been run on one.
2. The full positive control (all twelve v4 checkpoints, three seeds each) has not been run.
3. Nothing is known about R1(8), R5, R6/R6′ or R7 on the registered checkpoints.
4. Wall-clock and determinism were measured on this Mac only, with `OMP_NUM_THREADS=1` and
   `VECLIB_MAXIMUM_THREADS=1`. Cross-machine bit-identity is not claimed.
5. The `19-U` optional family has not been probed and, after audit M3, is not meant to be:
   its weights are bit-identical to 19b-U5. If anyone does probe it by id, the report's
   per-family table would list it as a separate family — read the header note before
   treating it as independent evidence.
6. §5's positive control also references what `diagnosis.json` and `transcripts.json`
   "already show". The script does not read those files and does not compare against them
   numerically; the control is evaluated only from fresh probe outputs, as §5's four clauses
   are written.

## 8. Claim limits carried into every output

Each per-checkpoint JSON and the report repeat §7: a forced action is never an autonomous
success; every probe-B and probe-C number is a diagnostic of one component with the others
handed to it; probe C puts the controller in reachable but unpractised states, so a reading
needs agreement between the free-run fault type and at least one intervention; all of it is
descriptive development evidence on throwaway units, changing no registered result and
licensing no claim about a system; at most one training experiment can be licensed by it,
and that needs its own registration, forecasts and hashes.

Revision 2 adds two qualifications the audit asked for, in section 5 of every report: probe
C's condition **S5 cannot discriminate** (its "next position" *is* the attribute position, so
its NEXT bucket is 0 by construction and a REL majority there is consistent with both
hypotheses — R6/R6′ are read on S3 only), and the probe-B logits are the model's own but are
native **given the handed prefix** (the operation scores are computed with the forced subject
already selected). The header also prints "THIS RUN IS VOID" beside `code unchanged` if any
imported module has drifted from §2, and records the §9 file-name deviation.

## 9. What changed in revision 2 (response to `AUDIT-26.md`)

| finding | what changed |
|---|---|
| **B1** resume can mix script versions | `source_sha256()` is compared with the manifest's `probe_source_sha256` in `load_panel`, and with every probe output's in the new `read_documents()`, which `probe` calls **before** it adds anything and `report` calls before it reads anything. A mismatch is a hard refusal naming both hashes and telling the operator to start a fresh `--out`; nothing is skipped and nothing is written. Test: *the probe source sha256 is pinned (B1)*. |
| **B2** decision table from an incomplete set | `decision_rows` now returns a single `registered set incomplete — D1–D5 not evaluable` row (no D-row at all) unless every `REGISTERED_IDS` entry has a document; `--suffix final` refuses outright unless 12/12 control **and** 9/9 registered are present; `--suffix control` prints no decision row; the header counts control and registered sets separately. Test: *report gating: final and control-only (B2)*. |
| **M1** panel size not pinned | `panel` refuses any `--n` other than 64 or any cell list other than §3's without `--dev`; a `--dev` panel is marked in the manifest and `probe`/`report` refuse it; `load_panel` re-checks `n_per_cell` and `cells` against the constants even if the mark is edited away. Test: *panel size and cell list are pinned (M1)*. |
| **M2** nothing binds the run to the forecasts | `panel` records `forecasts = {predictions_sha256, predictions_recorded_sha256, predictions_matches_its_record, ledger_sha256}`; every probe output carries the manifest's copy and the report prints all of them. Test: *the frozen forecasts are hashed into the manifest (M2)*. |
| **M3** 19-U is weight-identical to 19b-U5 | dropped from command line (b); the report header states the weight identity and that 19-U is not probed. |
| **M4** §10's agreement number not printed | every checkpoint's block now prints the oracle/trained first-fault agreement per cell plus the worst cell. |
| **MINOR 1** R4(d) reading unnamed | printed in report section 2 and stored as `r4_reading` in `report*.json`. |
| **MINOR 3** S5 cannot discriminate | stated in the claim-limits section. |
| **MINOR 4** "native" logits | qualified as native *given the handed prefix* in the claim-limits section. |
| **MINOR 5** code drift recorded, not enforced | the header now marks a drifted run VOID in words. |
| **MINOR 11** §9 file-name deviation | recorded in the report header. |

Not changed, with reasons: **MINOR 2** (`STOP_LATE` for an exactly-length `over_cap`
transcript) — unreachable at cap 16 with hops ≤ 8, and changing it would change the frozen
classifier; **MINOR 6** (R6/R6′ denominators) — §5 writes the thresholds as absolute counts,
`reached_step_2` is logged and printed, and re-defining them would be a spec change;
**MINOR 7** (probe outputs not byte-reproducible because of `seconds`/`created_unix`) — not
fixed: a content hash excluding the volatile fields would have to be written *into* the file
it hashes or into a second file, which is a format change after the forecasts were frozen;
the auditor's own strip-and-hash check is the way to verify a probe, and it is recorded here;
**MINOR 8** (partial-write window on a crash mid-dump) — not fixed; `write_new` still opens
`'x'` and dumps, so a crash leaves a truncated file that `report` will fail loudly to parse
and `probe` would skip: if a probe is interrupted, delete the last `probe-*.json` before
resuming; **MINOR 9** (`third=4` hard-coded) — correct because `V1.pad_questions` left-aligns,
and the auditor confirmed it; **MINOR 10** (`V4.load_checkpoint` re-reads the unhashed
`training.json`; TOCTOU between `sha()` and `torch.load`) — descriptive fields only, and the
weights are hash- and arm-checked.

Nothing in revision 2 touches the panel (same sha256), the classifier, the forcing windows,
the thresholds or the decision rows: the changes are all registration plumbing around them.
