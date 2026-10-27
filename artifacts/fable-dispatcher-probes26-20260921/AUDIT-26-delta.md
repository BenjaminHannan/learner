FREEZE-READY: YES

# Experiment 26 — independent audit, delta re-audit of revision 2

Auditor: independent reviewer (did not build the probe). This file supplements
`AUDIT-26.md` (sha256 `0929d0ebc3119e9f46a8dbdba749589ddb79c4c8550f546d36a991d600606414`,
first line `FREEZE-READY: NO`) and does not replace it. Same rules as round 1: everything
below was run in a scratch area outside the repository, no file in the repository was
edited, and **no probe was run on the nine experiment-19/19b checkpoints**.

## Delta re-audit (revision 2)

### 0. What is under audit now

| file | sha256 | note |
|---|---|---|
| `scripts/fable_dispatcher_probes26.py` | `f78ca888c7d0c1381cd5c0dbd1e1363b6c2b6699a5f1db728fecc621253af228` | 1327 lines (was 1147) |
| `tests/test_fable_dispatcher_probes26.py` | `22c11a14b7c2d17486705f738093e2e622fa1618af9a6188068dfc55f773de21` | 21 checks (was 17) |
| `artifacts/.../BUILD-NOTES.md` | `981c8d0f542f11129e0e1d07e660c3b2b427cb44fc07e3afe1fdf2a21a641f60` | §9 added |
| `design/v3/26-...-fable-review.md` | `7d7708e79e7b755bfa47d50bd7aeb8b550d02b20930a313ad1547a7337a09f45` | **unchanged** — the spec was not touched |
| `FABLE-PREDICTIONS.md` | `72c6130d29e8af9e73c3752cc6aec9acc0655465060bb33243895ba07989664b` | unchanged, matches its `.sha256.txt` |
| `artifacts/fable-predictions-ledger.md` | `425315c68649ecc6410e417830aaa4adeffb3f43fd4f8d55c279087c65713f72` | P102–P117 all `pending` |

All three quoted hashes match the bytes on disk. `AUDIT-26.md` was not modified by the
builder.

### 1. Did anything but the registration plumbing change? No.

Three independent checks, all negative for drift:

1. **Constants and logic read by hand.** `NAMESPACE`, `PANEL_N=64`, `CELLS26`,
   `EVAL_CAP`, `BLOCK=32`, `PROBE_SEED=260921`, `MARK_R1=61`, `MARK_R3=59`,
   `MARK_R2=48`, `MARK_R5=16`, `MARK_R7_RATIO=0.10`, `MARK_R7_MARGIN=0.01`,
   `assert MARK_R3 == V4.CELL_MARK`, the §2 checkpoint registry and the five design code
   hashes are unchanged. `classify_first_fault`, `r_flags`, `family_holds`,
   `positive_control` and the bodies of rows D0, D1, D2a, D2b, D3, D4, D4′, D5 are
   byte-identical to revision 1; the only edit inside `decision_rows` is the new
   incomplete-set short-circuit placed *after* the D0 check.
2. **Panel sha256 is still
   `dc176e886f3d0eb9a444dd64d64ca57a1496ac07184f6875859716a515591a34`** — the same value
   as revision 1 and as the panel I built independently in round 1. Rebuilt twice more
   during this delta (once from a deliberately edited copy of the script) and identical
   both times.
3. **The 12 positive-control probe outputs are unchanged.** I re-ran the whole control
   arm under revision 2 into a fresh scratch directory and compared every
   `probe-*.json` field-by-field against the revision-1 outputs I kept from round 1,
   stripping only `seconds`, `created_unix`, `verified_unix` and the two new keys
   (`probe_source_sha256`, `forecasts`): **12 of 12 identical, 0 differing fields.**
   Every probe-A category count, every probe-B strict count under all five
   interventions, every probe-C S0/S3/S5 bucket and every probe-D geometry number is
   bit-for-bit what revision 1 produced. This is also a second determinism confirmation,
   across two runs of two different builds of the script.

The positive control still **PASSES** in revision 2 (12/12 R1(4); 6/6 R2 on the
learned-position arms; 3/3 R3 on v4-ctx; 3/3 subject-only ≥ 59 on v4-reg). The 21-check
test suite passes: `ALL 21 CHECKS PASSED`.

### 2. B1 — I could not defeat it (4 attempts)

I built a mirror of the worktree in scratch (symlinked `design/` and `artifacts/`, real
`scripts/`) holding a one-comment-edited copy of the probe script, sha
`1846df3962811f4b71c007ac1597621d65e4c56320a0336ea41614ae005f655c` — exactly what a
builder fixing a D0 failure would produce.

| attack | result |
|---|---|
| edited script resumes into the existing 11-of-12 run (`probe --ckpt v4-ctx-s2`) | **refused** before touching the folder, naming both hashes and telling the operator to start a fresh `--out` |
| edited script writes the report over that run | **refused** identically |
| edited script builds its own fresh run, then the *real* script reads it | **refused** (symmetric) |
| documents from the edited script smuggled into a run whose manifest matches, incl. one with the key deleted | **refused** by `read_documents`, naming the offending file |
| `probe_source_sha256` deleted from the manifest | **refused** (`… was written by None`) |

`probe` calls `read_documents` *before* it writes anything, so the dangerous case — a
mixed folder where the skip-if-exists resume silently keeps broken-script outputs — now
aborts instead. B1 is discharged.

Residual (not a finding, recorded for the file): the guard compares hashes held in files
the builder can also rewrite, so it stops accidents and version mixing, not a determined
forger. The audit trail is this file plus the sha in the report header.

### 3. B2 — I could not defeat it (5 attempts)

| attack | result |
|---|---|
| `--suffix final` with 12/12 control, 0/9 registered | **refused**, naming all nine missing ids |
| `--suffix final` with 12/12 control and 7/9 registered (fabricated documents carrying the real ids) | **refused**: `registered 7/9: missing 19b-U8-s1901, 19b-U8-s1902` |
| `--suffix final` with 9/9 registered but 11/12 control | **refused**: `positive control 11/12: missing v4-reg-s2` |
| interim report (any other suffix) with 7/9 | prints `3. DECISION TABLE (not evaluable)`, lists the two missing ids, **no D-row printed at all** |
| control-only report | header reads `CONTROL ONLY (no section-6 decision table)` and section 3 says the table is not evaluated; no D-row |

The revision-1 failure — a control-only report printing `D4 FIRED` — is gone. Two
independent mechanisms now stand between a partial set and a decision row (the
`--suffix final` gate and the `decision_rows` short-circuit), and the header always
prints `positive control N of 12` / `registered set N of 9`. With a complete fabricated
12 + 9 set the rows do print, so the gate is not simply suppressing everything. B2 is
discharged.

Informational: only the literal suffix `control` selects control-only mode
(`--suffix control2` is labelled `interim`). Harmless — with the registered set absent
the interim path prints no D-row either.

### 4. M1 and M2 behave as claimed

**M1.** `panel --n 8` is refused with an explanation that every §5 threshold is an
absolute count out of 64. `panel --dev --n 8` builds an 80-unit panel marked
`dev_panel: true`; `probe` and `report` both refuse it without `--dev`. Editing
`dev_panel` back to `false` by hand does not help — `load_panel` independently checks
`n_per_cell` and the cell tuple against the constants (and the panel sha would differ
anyway). Defence in depth, as claimed.

**M2.** The manifest of the clean run records `predictions_sha256 72c6130d…`,
`predictions_recorded_sha256 72c6130d…`, `predictions_matches_its_record: true` and
`ledger_sha256 425315c6…`, every probe output carries the same block, and the report
header prints forecasts sha, match flag, ledger sha, spec sha, panel sha and probe
source sha. Combined with round 1 (where I confirmed the forecasts predate every probe
output), the run is now bound to the frozen forecast text.

**M3** (19-U dropped; weight identity with 19b-U5 stated in the header), **M4**
(per-cell oracle/trained agreement plus worst cell printed for every checkpoint) and
**MINOR 1** (the R4(d) reading printed in section 2 and stored as `r4_reading` in
`report*.json`) are all present in the output I generated.

### 5. Rulings on the six unfixed MINORs — all acceptable for freeze

- **MINOR 2** (`STOP_LATE` for an exactly-length `over_cap` transcript) — **acceptable.**
  Unreachable at cap 16 with hops ≤ 8, and touching the classifier after the forecasts
  were frozen would be worse than the blemish.
- **MINOR 6** (R6/R6′ compare a raw count with 48 while the denominator is
  `reached_step_2`) — **acceptable as code**, with one reading rule I am imposing rather
  than a code change: if a registered checkpoint's `k8-held` probe C shows
  `reached_step_2 < 48`, R6 and R6′ cannot both be false "about pointers", and D4 / D4′ /
  D5 must be reported as **not evaluable for that seed**, not as D5 (`no single
  account`) firing. `reached_step_2` is logged and printed, so this is checkable from the
  report. It was 64/64 in all 12 control checkpoints.
- **MINOR 7** (outputs not byte-reproducible) — **acceptable.** Adding a content hash
  after the forecasts were frozen is a format change for little gain. The verification
  recipe, which I used successfully twice in this delta, is: compare two probe JSONs
  after recursively deleting the keys `seconds`, `created_unix`, `verified_unix`,
  `probe_source_sha256`, `forecasts`.
- **MINOR 8** (partial-write window) — **acceptable, and revision 2 improved it.** A
  truncated `probe-*.json` is no longer silently skipped on resume: `read_documents`
  parses every output before `probe` writes, so the next command dies on the malformed
  file. The stack trace is not a friendly message, but it is loud, which is what matters.
- **MINOR 9** (`third=4` hard-coded) — **acceptable.** I confirmed `V1.pad_questions`
  left-aligns (`left = 0`) in round 1.
- **MINOR 10** (unhashed `training.json`, `sha()`→`torch.load` TOCTOU) — **acceptable.**
  Descriptive fields only; weights and arm are hash-checked.

One further non-blocking observation: the forecast hashes are taken when the panel is
built and printed from the manifest — the report does not re-hash `FABLE-PREDICTIONS.md`
at report time, so a later edit of that file would not be caught by the report itself.
The `.sha256.txt` record, the ledger and this audit file all pin `72c6130d…`, which is
sufficient.

### 6. Verdict

**FREEZE-READY: YES.** Both blocking findings are fixed and I could not defeat either;
all four majors are fixed; nothing in the probe, forcing, classifier, threshold or
decision-row logic changed, proven by 12 of 12 byte-identical control outputs and an
unchanged panel sha256. The script may be frozen at
`f78ca888c7d0c1381cd5c0dbd1e1363b6c2b6699a5f1db728fecc621253af228` and run on the nine
registered checkpoints.

Conditions carried into the reading of the result, none of which require a code change:
(1) the §5 R6/R6′ rule in item 5 above; (2) if the report ever prints
`code unchanged False`, that run is void; (3) the claim limits in §7 of the spec stand —
probes B and C hand components to the model, so no number in this experiment licenses a
claim that the system did anything autonomously, and the result licenses at most one
training experiment, separately registered.
