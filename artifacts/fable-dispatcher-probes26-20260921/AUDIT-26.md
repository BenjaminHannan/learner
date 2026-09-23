FREEZE-READY: NO

# Experiment 26 — independent audit

Auditor: Claude (Opus 5) subagent, 2026-09-21. I did not build any of this. Binding
specification `design/v3/26-dispatcher-stop-probes-registration-fable-review.md`,
sha256 `7d7708e79e7b755bfa47d50bd7aeb8b550d02b20930a313ad1547a7337a09f45` — **verified
on disk, matches**.

Under audit (all hashes verified on disk, all match the builder's table):

| file | sha256 |
|---|---|
| `scripts/fable_dispatcher_probes26.py` | `c0f91f971cd7d6b88fe5ffcaecee2f218da70f894f83976294ef6e967c749ef3` |
| `tests/test_fable_dispatcher_probes26.py` | `8770edf3ed324c306adfb334b201cfca4556e52c3243b9e6699c1ac5ba0c70ed` |
| `artifacts/fable-dispatcher-probes26-20260921/BUILD-NOTES.md` | `91ecc88e093219fe4126e5454d2bf614016430882a6849afd85bedae7c526534` |

**Verdict.** The instrument itself is sound: the forcing windows, the classifier, every
section-5 threshold, the panel and the determinism all check out under independent
re-derivation, and the positive control **passes** when I run it myself. What is not yet
safe is the *registration plumbing around* the instrument: the output folder does not pin
the version of the script that wrote each file, and the report will print a full
section-6 decision table from an incomplete registered set. Both are small, local fixes.
Two BLOCKING, four MAJOR, eleven MINOR.

This file is the only thing I wrote into `artifacts/fable-dispatcher-probes26-20260921/`.
Everything I ran went to a scratch directory outside the repository. I edited no script,
test, spec, ledger or artifact, committed nothing, and used no machine but this Mac.

---

## 1. What I ran

* `tests/test_fable_dispatcher_probes26.py` — **17/17 pass**, ~15 s.
* `panel` + `probe` on **all twelve v4 known-answer control checkpoints** + `report`,
  into scratch. 12/12 probes succeeded, 11.0–11.4 s each, ≈ 2.4 min total (matches
  BUILD-NOTES §5 and is far inside §8's 25-minute hard stop).
* `panel` + one control checkpoint a **second** time into a fresh scratch directory, for
  determinism.
* My own scripts (scratch only) for: panel disjointness, hash-bypass attempts,
  end-to-end verification of the forced-prefix windows, the 19/19b load path, and a
  cross-check of the control against the registered v4 `score/diagnosis.json`.
* The one exception the brief asked for: **`TR.load_run_checkpoint(path, 'D')` exercised
  on real 19/19b bytes — load only.**

I ran **no probe and no rollout** on any experiment-19/19b checkpoint, loaded no
`test.pt`, and wrote nothing into `artifacts/` except this file.

### 1.1 The 19/19b load path works (load only, no behaviour)

All nine registered checkpoints (and the three optional 19-U) load cleanly through
`TR.load_run_checkpoint(path, 'D')`: recorded-sha check passes, `arch == 'D'`,
`state_dict` loads `strict=True`, the stored `final_weight_fingerprint` matches, and
`P.load_model`'s arm assertion passes (`flags = {learned_register: true,
contextual_positions: true}` = `reg+ctx` for all twelve). Every one has the same 34
state-dict keys and **24,035** controller parameters (103,351 with the frozen operator,
as §7.5 says). Metadata is as §2 describes: 19-awake = phase `awake`, 6,000 updates;
19b-U5/U8 = phase `offline`, arm label `U5`/`U8`, 2,000 updates. No rollout was run and
no behaviour was printed. **BUILD-NOTES §7 item 1 is now discharged.**

### 1.2 The positive control passes, independently

Run by me, from a panel I built myself, on all twelve v4 checkpoints:

```
VERDICT: PASSED
R1(4) in 12/12 v4 checkpoints:                           12/12  ok
R2 in >= 5 of the 6 learned-position v4 checkpoints:       6/6  ok
R3 in 3/3 v4-ctx:                                          3/3  ok
subject-only strict >= 59/64 on k8-held in >= 2 of 3 v4-reg: 3/3 ok
```

The picture is the known one: `ctx` fails free-running from k4 with `OP_EARLY_ATTR` 64/64
and is rescued 64/64 by operation-only; `reg` fails with `SUBJECT` and is rescued by
subject-only but not by operation-only; `reg+ctx` shows both. Panel sha256
`dc176e886f3d0eb9a444dd64d64ca57a1496ac07184f6875859716a515591a34`.

This does **not** discharge BUILD-NOTES §7 item 2 for the registered run — the
coordinator must still produce the control inside the registered output directory — but
it is strong evidence the script will pass it there, and P102/P112 are very likely TRUE.

Two already-frozen forecasts are effectively settled by the control alone, and I record
them here so nobody is surprised: **P109** (R6 in ≥ 2 of 3 v4-`ctx`) looks **TRUE** —
R6 held 3/3, S3 gave `REL` 64/64 in every v4-`ctx` seed; **P110** (geometry ratio ≤ 0.10
in ≥ 2 of 3 v4-`ctx`) looks **FALSE** — the ratios are 0.1184, 0.2584, 0.3442. Both were
registered before any probe existed, so nothing is contaminated; these numbers are from
my scratch run and must be reproduced by the coordinator's own control run before being
quoted.

### 1.3 Cross-check against the registered v4 diagnosis (BUILD-NOTES §7 item 6)

The script never reads `diagnosis.json`, so I compared by hand. Registered
`artifacts/fable-dispatcher-v4-20260920/{arm}/seed-0/score/diagnosis.json` (answers,
strict) versus my probe-26 run on the fresh panel:

| arm | cell | registered op-only | probe-26 op-only | registered subj-only | probe-26 subj-only | registered op+subj | probe-26 op+subj |
|---|---|---|---|---|---|---|---|
| ctx | k8-held | 64/64 | 64 | 4/0 | 0 | 64/64 | 64 |
| reg | k8-held | 6/1 | 1 | 64/64 | 64 | 64/64 | 64 |
| reg-ctx | k4-held | 50/49 | 46 | 4/0 | 0 | 64/64 | 64 |

Same picture, small differences where the units differ. The control is doing what §5
says it should.

---

## 2. BLOCKING

### B1 — Resume can silently mix outputs from different script versions

`manifest.json` records `probe_source_sha256`, and every `probe-*.json` records its own.
**Nothing ever compares them.** `load_panel` re-verifies the five *imported* modules and
the specification against the manifest, but not `fable_dispatcher_probes26.py` itself;
`report` checks only `panel_sha256` per document.

This is not theoretical — it is the exact path §6 row D0 prescribes. If the positive
control fails, the builder edits the script and re-runs. `probe` then **skips every
checkpoint whose output already exists**, so the twelve control JSONs written by the
broken script are kept, and the registered nine are written by the fixed script. `report`
reads all twenty-one as if one instrument had produced them, and prints a decision table
over a mixture.

Fix (small, all in this script):
* `load_panel` (or `probe`) must refuse when `sha(__file__) != manifest['probe_source_sha256']`.
* `report` must refuse when any document's `probe_source_sha256` differs from the
  manifest's or from the others'.
* Because D0 legitimately requires editing the script, `probe` should additionally refuse
  to *add* to a folder whose existing outputs carry a different source hash, with a message
  telling the operator to start a fresh `--out` directory.

### B2 — The report prints a section-6 decision table from an incomplete registered set

`report` refuses only when there are **zero** documents. The positive control catches a
missing *control* checkpoint (→ D0, correctly). Once the control is complete and passing,
nothing checks that the **nine registered checkpoints are present**.

Demonstrated: the control-only report that BUILD-NOTES §4(a) itself prescribes
(`report --suffix control`, twelve v4 documents, **no** registered checkpoint probed at
all) printed a fully formatted section 4:

```
D1   -      same picture as v4: a healthy STOP behind an operation pointer ...
D2a  -      a real premature STOP exists in the cap-8 family that v4 did not have
D2b  -      long practice under a per-call cost damaged STOP itself
D3   -      after practice pushes the operation pointer out, ...
D4   FIRED  "counts calls" is the accurate description
D5   -      no single account
```

D1–D3 read as findings about 19-awake/U5/U8. Nothing was probed. D5 did not fire here
only because D4 happened to fire; with a different control outcome the same partial run
would have printed `D5 FIRED — no single account; no training experiment is licensed`,
which is a registered decision drawn from an empty registered set. The same hazard
applies to a `--suffix final` report written after a loop that died at, say, seven of
nine, and the header line `checkpoints probed 12 of 24` does not help (21 of 24 is the
*complete* registered case, because the optional family is counted).

Fix:
* `decision_rows` must return a single explicit "registered set incomplete — D1–D5 not
  evaluable" row unless every id in `REGISTERED_IDS` has a document.
* The report header must print `registered checkpoints: N of 9` and `control: N of 12`
  separately from the 24-count.

---

## 3. MAJOR

### M1 — The panel size and cell list are not pinned

`panel` exposes `--n` (default 64) with no validation, and `probe`/`report` never assert
`manifest['n_per_cell'] == 64` or `manifest['cells'] == CELLS26`. Every section-5
threshold is an absolute count out of 64. A panel built with `--n 8` (a plausible
copy-paste from the test knobs) yields cells where R1/R2/R3/R5/R6 are arithmetically
unreachable, every flag goes False, and the report prints `D5 FIRED` without any error.
`probe` and `report` must refuse a manifest whose `n_per_cell` is not `PANEL_N` or whose
`cells` are not exactly `CELLS26`, unless an explicit `--dev` flag is passed. **Must change.**

### M2 — Nothing binds the probe output to the frozen forecasts

The manifest pins the specification, the five imported modules, the frozen operator, all
24 checkpoints, the panel and (unenforced, see B1) the script. It does **not** record the
sha256 of `artifacts/fable-predictions-ledger.md` or of
`artifacts/fable-dispatcher-probes26-20260921/FABLE-PREDICTIONS.md`. Nothing is committed
to git — the repository has one commit and every experiment-26 file is untracked — so the
only evidence that P102–P117 predate the run is file mtimes. `panel` should record both
hashes (and `FABLE-PREDICTIONS.sha256.txt`'s recorded value) in the manifest, and the
report should print them. **Must change** — it is two lines and it is the difference
between a registered forecast and an unverifiable claim.

(The ordering itself is fine today: spec 20:17, `FABLE-PREDICTIONS.md` 20:28 hashing to
`72c6130d…` exactly as its `.sha256.txt` records, script 20:47, ledger 20:49, BUILD-NOTES
20:51, **and no probe output exists anywhere in the repository**. Checklist item 1 is
satisfied. It is just not *pinned*.)

### M3 — The optional 19-U family is weight-identical to 19b-U5

I loaded both and hashed the state dicts. For all three seeds:

| seed | `19b-U5` state-dict sha | `19-U` state-dict sha | identical |
|---|---|---|---|
| 1900 | `e17b05d3c4c118c5…` | `e17b05d3c4c118c5…` | **yes** |
| 1901 | `45dc2f948a3513e7…` | `45dc2f948a3513e7…` | **yes** |
| 1902 | `cfc3825f55692138…` | `cfc3825f55692138…` | **yes** |

The files differ in bytes (different runs, different `arm` label `U5` vs `U`, different
recorded sha256) but the weights are identical: 19b's `U5` arm reproduced experiment 19's
uniform arm bit-for-bit. §2 presents them as two families and §6 calls 19-U an
"optional descriptive family". Probing it would produce a numerically identical second
copy of 19b-U5 and any report listing both as separate families would double-count.
**Either skip 19-U entirely, or the report must state the weight identity in the same
breath.** (Not blocking: 19-U is excluded from the decision table.)

### M4 — §10's oracle-agreement number is computed but not printed

The per-checkpoint JSON holds `probe_a.agreement.same_category`; the report prints only
the `OPERATOR > 2/64` flag. §10's last checklist item asks for both. Print the agreement
count per cell (or the minimum over cells) in the report. Cheap; without it the auditor
of the *result* has to open the JSON.

---

## 4. MINOR

1. **R4(d)'s reading is not named in the output.** §5's "operation-only strict < 59" is
   per-cell-ambiguous; the builder implemented `NOT(≥59 on both kd-prac and kd-held)`
   (judgement call 5). That is the looser of the two readings and it makes R4 — hence
   row D3 — easier to fire. P106 is a scored forecast whose wording is equally ambiguous.
   The report must print one line naming the reading used; the per-cell numbers are in
   the JSON, so nothing needs re-running.
2. **`STOP_LATE` for an exactly-length transcript with status `over_cap`** is not "the
   full chain is correct and further calls follow". Unreachable at cap 16 with hops ≤ 8;
   leave it, but it is a stretch of §4 category 6.
3. **Probe C's S5 cannot discriminate.** Its "next position" *is* the attribute, and
   `_offset_category` tests `REL` first, so S5's `NEXT` bucket is 0 by construction and
   `REL` at S5 is consistent with both hypotheses. The spec designed it that way; the
   report must not read S5 as evidence for "counts calls". (The builder flagged the
   analogous S0 `NEXT`/`THIRD` coincidence but not this one.)
4. **"Native" logits are native *given the handed prefix*.** `operation_scores` are
   computed with the forced subject already selected, and `stop_scores` after the forced
   action's state update. That is the right instrument, but the word "native" in the JSON
   and report should be qualified.
5. **§2's "stops on any change" is not enforced for the code hashes.** `build_panel`
   records `code_unchanged_since_design` and continues. It is `True` today (I verified all
   five modules and the operator against §2). If a run ever prints `code unchanged False`,
   that run is void — say so in the report text.
6. **R6/R6′ denominators.** Both compare a raw count against 48 while the denominator is
   `reached_step_2`, not 64. Correct per §5's literal "≥ 48/64", but a checkpoint with a
   strong STOP can end episodes at step 0 or 1 (STOP is never forced in probe C) and then
   both flags fail into "mixed" for a reason that is not about pointers. `reached_step_2`
   is logged; the report prints it. Watch it on the 19/19b runs.
7. **Probe outputs are not byte-reproducible.** Re-running one control checkpoint into a
   fresh directory gave a JSON identical in every field except `seconds`, `created_unix`
   and `verified_unix` (verified: stripped-content sha `a87f78c86505e719…` both times;
   panel sha256 identical). A reviewer cannot therefore verify a probe by file hash.
   Recording a content hash with the volatile fields excluded would fix it.
8. **Partial-write window.** `write_new` opens `'x'` then dumps; a crash mid-dump leaves a
   truncated file that `probe`'s resume will skip and `report` will fail to parse. Loud,
   but a `.tmp`-then-rename would be cleaner.
9. **`third=4` is hard-coded** in `probe_checkpoint` rather than derived as `left + 4`.
   Correct because `V1.pad_questions` left-aligns (`left = 0`), which I confirmed, but it
   is a silent coupling.
10. **`V4.load_checkpoint` re-reads `training.json`**, which is not hashed, for the
    descriptive `arm/seed/updates/train_cap/call_cost` fields. The weights and flags are
    hash- and arm-checked, so nothing load-bearing depends on it. Also a theoretical
    TOCTOU window between `sha(path)` and `torch.load(path)`.
11. **File-name deviation from §9** (`fable_dispatcher_probes26.py` /
    `test_fable_dispatcher_probes26.py` / `artifacts/fable-dispatcher-probes26-20260921/`
    instead of §9's names). Coordinator-instructed and documented in BUILD-NOTES §2.
    **Acceptable** — but the final report should record it, because §9 is part of the
    frozen spec.

---

## 5. What I verified and found correct

**Forcing windows (checked end-to-end on real episodes, v4-ctx-s0, not just the policy
function).** On `k5-held` under `force_operation+subject`: every executed step with
`step < hops` had subject pointer `1` (step 0) / `width + step - 1` and operation pointer
`left + 2 + step` — **0 violations in 64 episodes** — and **nothing** was forced at
`step >= hops`. Under `force_stop` the stop bit equalled `step == hops - 1` inside the
chain and was free outside — **0 violations**. STOP is forced only in the `force_stop`
kind. Probe C on `k8-held`: steps 0 and 1 matched the condition's forced positions
exactly for S0 (2,3), S3 (5,6) and S5 (7,8) — **0 violations** — and step 2 was the
model's own choice in all 64 rows of all three conditions. `V3.intervention_policy` is
used unchanged. Matches §4 and §10.

**Probe A classifier.** The eight categories and their order reproduce §4 exactly:
`OPERATOR` (both pointers right, result wrong) → `OP_EARLY_ATTR` (relation where the chain
links) → `OP_RUN_ON` (LINK where the chain ends) → `SUBJECT` (operation right, subject
wrong) → `STOP_EARLY` (correct proper prefix, `answered`) → `STOP_LATE` (full chain,
further calls, `answered`/`over_cap`) → `INVALID` (sub-typed from the `pointers` row whose
stop entry is `-1`) → `OTHER`. Precedence is enforced by construction: an in-transcript
mismatch is found before any length or status test, so categories 1–4 beat 5–8, and
within the mismatch the §4 order is followed literally. The function is pure and does not
mutate its inputs (tested). The extra `question` argument (judgement call 1) is part of
the unit, not a label.

**Every §5 threshold, at the boundary.** R1 `≥ 61` on both `kd-prac` and `kd-held`;
R2 `OP_EARLY_ATTR ≥ 48` on `k8-held` from the trained-operator free run; R3
`force_operation ≥ 59` on both k8 cells (`MARK_R3 == V4.CELL_MARK == 59`, asserted at
import); R4(d) = `not R3-at-d and R1(d)`; R5 `max(k4-held, k5-held) STOP_EARLY ≥ 16` from
the `force_operation+subject` episodes classified by the same classifier; R6 `REL ≥ 48`
and R6′ `NEXT + THIRD + OTHER_LINK ≥ 48` at step 2 of S3 on `k8-held`; R7
`ratio ≤ 0.10 AND adjacent-unused-LINK |margin| ≤ 0.01` at step 2 of S0. Every one is
`>=` where §5 writes "≥" and `<` where it writes "<", and the builder's tests exercise
both sides of each boundary. No number is averaged across seeds; the family rule is
`≥ 2 of 3` and requires exactly three members.

**Every §6 row.** D0 short-circuits (and correctly also fires when the control set is
incomplete). D1 = R1(4) and R1(5) in **3/3** seeds of all three registered families **and**
R2 for 19-awake at the family rule. D2a = R5 for 19-awake. D2b = R5 for U8 and not for
19-awake and not for U5. D3 = R4(6) for U5 or U8. D4 / D4′ = R6 / R6′ for v4-`ctx`. D5 =
no other row fired. All match §6 as written. The table licenses at most one training
experiment. (See B2 for the gating defect around it.)

**Panel.** Namespace `fable-probe26-v1`; ten cells `k3…k8-{prac,held}`; indices 0–63; 640
units; `V3.audit_unit` passes on every one; single-sided only; greedy everywhere;
`EVAL_CAP == V3.EVAL_CAP == 16`; `V1.configure()` pins torch to one thread. I rebuilt the
panel twice in two directories and got the identical sha256
`dc176e886f3d0eb9a444dd64d64ca57a1496ac07184f6875859716a515591a34`. Disjointness is
stronger than namespace-distinctness: comparing full unit contents (question, chain,
answer **and** memory) against 128 units per cell from `fable-dispatcher-v4-throwaway`,
`fable-dispatcher-v3-panel`, `fable-dispatcher-v3-train`, `fable-dispatcher-v4-train`,
`astra-novelty19-dev-v1` and `astra-novelty19-confirm-v1` gives **zero overlap** in every
case, and all 640 probe units are distinct from one another. The script contains no
reference to `load_panels`, `build_panels`, `diagnosis.json`, `transcripts.json` or
`DEV-PASSED`, and reads no panel file from disk.

**Hash verification cannot be bypassed.** `resolve_entry` refuses any id or path that is
not one of the 24 (`/etc/hosts`, the run directory instead of the file, a made-up seed —
all refused), refuses a `--family` that does not match the id, and `load_model` hashes
the file and refuses before `torch.load` is reached (refused when I handed it a wrong
expected digest). `panel` verifies all 24 checkpoints plus the frozen operator at once and
records them. The operator goes through `TR.verified_operator()` and its fingerprint is
asserted unchanged at the end of every probe. The 19/19b path adds
`TR.verify_recorded_sha` plus the stored weight fingerprint. Static guards in the tests
fail the build on `torch.save`, `optimizer.step`, `loss.backward`, `.train()` or the
string `test.pt`. Nothing trains.

**Native logits are the model's own.** Confirmed by reading `rollout_v4`: `record` stores
`subject_scores`, `operation_scores` and `stop_scores` as produced by the model, before
`pick()` applies the forced overwrite (`fable_dispatcher_v4.py:493-499`). The builder's
test additionally shows a forced run whose forced choices equal a free run's greedy
choices produces bit-identical recorded tensors. The second `rollout_v4` used to read them
is asserted, per cell, to agree with `score_side_v4` on answers and strict. §10's
hand-check item is satisfied. (See MINOR 4 on the wording.)

**Determinism.** One control checkpoint probed twice into two fresh directories: the two
`probe-*.json` are identical in every field once `seconds`, `created_unix` and
`verified_unix` are removed (stripped-content sha256 `a87f78c8…` both times); the panel
sha256 and all code hashes are identical. `torch.manual_seed(260921)` is set at the start
of every probe and nothing samples.

**Timing.** 11.0–11.4 s per checkpoint here, matching BUILD-NOTES. The full 21-checkpoint
registered run plus panel and report is ≈ 4–5 minutes on one thread — inside §8's 10–15
minute estimate and nowhere near its 25-minute stop.

---

## 6. Rulings on the fifteen judgement calls (BUILD-NOTES §3)

| # | subject | ruling |
|---|---|---|
| 1 | classifier also takes the raw question | **acceptable** — the question is part of the unit; no label, still pure |
| 2 | classifier cases §4 does not enumerate | **acceptable** — all four readings follow §4's own order; see MINOR 2 for the one stretch |
| 3 | native logits from a second `rollout_v4`, asserted equal to `score_side_v4` | **acceptable** — the assert is per cell on answers and strict, and tested |
| 4 | block size 32 | **acceptable** — the block the registered scorers used |
| 5 | R4(d) as the mirror of R3 (`not both ≥ 59`) | **acceptable, but must be named in the report** (MINOR 1) — it is the looser reading and D3/P106 turn on it |
| 6 | R5 = the larger of `k4-held` / `k5-held` | **acceptable** — §5 says "or" |
| 7 | R6′ counts `NEXT + THIRD + OTHER_LINK` | **acceptable and correct** — at S3, `THIRD` is one of §5's "other LINK"s; excluding it would have understated R6′ |
| 8 | R7's margin read on `k8-held` at S0 | **acceptable** — R6 is defined on `k8-held`; `k8-prac` is logged identically |
| 9 | probe D pools `k3-prac + k3-held`, pairs (3,4)(4,5)(5,6) | **acceptable** — per-cell medians also written |
| 10 | "not-yet-used LINK" = not yet chosen as the operation pointer, from the episode's own `pointers` | **acceptable** |
| 11 | both margin sign conventions logged under explicit names | **acceptable** — good practice |
| 12 | 19-U optional, by id only, outside the control and the decision table | **acceptable as plumbing, but see M3** — it is weight-identical to 19b-U5 and adds no information |
| 13 | on a failed/incomplete control, print the data tables then D0 only | **acceptable for that case, but incomplete** — it gates on a failed control and not on a missing registered set (**B2**) |
| 14 | no seed to choose; `torch.manual_seed(260921)` anyway; determinism spot-checked | **acceptable** — I reproduced the determinism independently |
| 15 | integrity: hash before load, panel verifies all 24, code re-checked at probe time, operator fingerprint asserted | **acceptable for the checkpoints and the imported modules; incomplete for the script's own version (B1), the panel size (M1) and the forecast binding (M2)** |

Plus BUILD-NOTES §2's file-name deviation from §9: **acceptable** (coordinator-instructed,
documented), and it must be recorded in the final report.

---

## 7. §10 checklist, item by item

| § 10 item | verdict |
|---|---|
| Spec sha and ledger P102–P117 predate the first probe output | **pass** — spec hash matches; `FABLE-PREDICTIONS.md` hashes to its recorded `72c6130d…`; no probe output exists anywhere in the repo. Not *pinned* — see **M2** |
| All 24 checkpoint hashes equal §2; operator hash equals §2; code hashes unchanged since `panel` | **pass** — verified all 24 plus the operator plus the five modules; code-vs-design is recorded but not enforced (MINOR 5) |
| Panel namespace `fable-probe26-v1`; no unit from any registered/dev/confirmation panel | **pass** — zero full-unit overlap against six namespaces; no panel file is read |
| Every rollout greedy; cap 16; single thread | **pass** |
| Positive control evaluated and reported first; if it failed nothing else interpreted | **pass for a failing control; fails for an incomplete registered set** — see **B2** |
| Forcing stops at `step == hops` (B) / `step == 2` (C); STOP never forced except `force_stop` | **pass** — verified end-to-end, 0 violations |
| Native logits are the model's own, taken before the forced overwrite | **pass** — source-read plus the builder's bit-identity test |
| No forced-run number described as the controller succeeding | **pass** — claim limits are carried into every JSON and the report; columns are labelled by intervention |
| Every seed listed; no averages; thresholds exactly §5 | **pass** |
| The report names the rows that fired and licenses at most one training experiment | **pass in content, fails in gating** — see **B2** |
| Oracle and trained runs agree on the fault category; `OPERATOR > 2/64` flagged | **partial** — the flag is printed (no cell exceeded 2/64 in my 12-checkpoint control run); the agreement count is computed but not printed — see **M4** |

---

## 8. What must change before the freeze

Blocking, in this order:

1. **B1** — pin the probe script's own sha256: `probe` refuses a folder whose manifest or
   existing outputs carry a different `probe_source_sha256`; `report` refuses a mixed set.
2. **B2** — `report` must declare the registered set incomplete and refuse to print
   D1–D5 until all nine `REGISTERED_IDS` have documents; header must show
   `control N/12` and `registered N/9` separately.

Should change in the same edit (all small):

3. **M1** — refuse a manifest whose `n_per_cell != 64` or whose `cells != CELLS26`.
4. **M2** — record the sha256 of the ledger and of `FABLE-PREDICTIONS.md` in the manifest
   and print them in the report.
5. **M3** — drop 19-U, or make the report state that it is weight-identical to 19b-U5.
6. **M4** — print the oracle/trained fault-category agreement count.
7. **MINOR 1** — print one line naming the R4(d) reading.

After those edits the script's sha256 changes, so BUILD-NOTES §1, the §2 tables and any
already-written scratch output must be regenerated, and the registered run must start
from an **empty** output directory. The specification, the ledger and the forecasts do
**not** need to change: nothing I found alters what is being asked or predicted, only
whether the plumbing can be trusted to answer it honestly.

Nothing I found casts doubt on the instrument itself. My independent positive control
passes, the forcing is exactly what §4 specifies, the thresholds are exactly §5, the
decision rows are exactly §6, the panel is fresh and disjoint, and the whole thing is
deterministic and reproduces the registered v4 picture. Fix B1 and B2 and this is ready.
