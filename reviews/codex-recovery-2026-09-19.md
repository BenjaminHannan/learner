# Card recovery implementation — 19 September 2026

**Shown:** the candidate implementation passes 45 targeted CPU contract checks.
A three-update run on an independently seeded training stream saved a checkpoint
and completed the full validation evaluation with both soft and hard request
selectors in 39.54 seconds. This is an engineering smoke check, not a learning
result. No new GPU rental was made. The village model was not changed.

**Untested:** fewer stalls, better held-out two-hop accuracy, elimination of the
70% mode, and dependable performance across training seeds. Issues 1–3 are not
closed by these checks. A successful gradient check does not establish that its
surrogate gradient improves learning.

## Changes and limits

The implementation follows the later pooled-first resolution in
[v3/07](../design/v3/07-final-resolution.md), which supersedes the earlier
token-pointer-first proposal.

| Audit concern | Work completed | Remaining measurement |
|---|---|---|
| 1: stuck runs | Compose the already tested separate key-pooling writer with the new candidate; cloned initialization preserves the original forward behavior. | Does the selected recipe reduce stalls at matched compute, across all planned seeds? |
| 2–3: held-out requests and the 70% mode | Add two independently learned address selectors over original contextual question states and fetched raw pooled values. Register 1 conditions the request; register 0 still controls ASK/HALT. No supplied relation location, role mask, intermediate answer, or label enters the request path. | Does the model learn to select the LINK first and use its result for the next request? Do relevant edits change both twins' answers correctly? |
| 5: no answer credit to retrieval | Add an independent score-only straight-through option. Forward card choices and values stay hard; the answer loss has a demonstrated gradient to retrieval scores, keys and key pooling. The companion's values are detached. | Does the biased surrogate help on hard-read evaluation? The hard ASK decision remains nondifferentiable; this is not an evidence-label-free training recipe. |
| 21: stale spend ledger | Read provider invoices and current instances, save sanitized snapshots, and update the ledger with actual displayed charges. | Attribute September 18 charges before/after the handoff before releasing the reserved amount. |
| 22: five suspended runs | Verify identities and stopped states; explicitly retain all five suspended, in accordance with v3 D38. No signals sent. | Resume or terminate only when that paused experiment is deliberately reconsidered. |

Code: [premonition_recovery.py](../scripts/premonition_recovery.py).
Tests: [test_premonition_recovery.py](../tests/test_premonition_recovery.py).
The existing [checkpoint loader](../scripts/premonition_first_card_probe.py)
recognizes the new versioned checkpoint format, so first-card diagnostics and
the causal-pair suite can load it. Historical loading paths remain unchanged.
No frozen source, historical checkpoint, historical result, or existing run
definition was overwritten.

All options default off. The legacy model has 79,748 parameters. Separate key
pooling adds 33; pooled selectors add 5,202; score-only ST adds zero. The combined
candidate has **84,983 parameters**, including the dormant legacy query head.
Binder, slots, loop-step embeddings, the full-story contextual reader and the
ordinary decoder remain. The selectors use soft attention at temperature 1 during
training; evaluation reports both soft and hard selector choices, with hard card
retrieval in both cases.

The extra immutable candidate buffers are not free: at this toy's shape they save
7,208 additional tensor bytes per question, before autograd graphs and temporary
allocations. There are 57 request candidates including NULL. ST accesses every
eligible card value per insertion. FLOP calibration runs the actual configured
model, so its matrix work is included; as in the inherited counter, elementwise
work is not included in that FLOP convention. Wall time is recorded separately.

## Verification

The 45 checks cover disabled-option parity in gold/teacher/own modes, initialization
and parameter accounting, immutable question/card content, ring eviction and NULL,
padding masks, register selection, label invariance across multiple requests,
gradient paths, dormant legacy parameters, hard-forward equality, checkpoint
round trips after an optimizer update, and the existing suite loader.

Integration checks also verified that:

- Both selector evaluation modes complete through the standard evaluator.
- An independently seeded training stream runs and is recorded.
- An unmet shared FLOP budget produces `status: incomplete` and a nonzero exit.
- An existing output directory is rejected without changing its checkpoint.
- The smoke run performs exactly the three requested optimizer updates, with zero
  loop-count mismatches.

Saved evidence:
[contract checks](../artifacts/codex-recovery-20260919/contract-checks.txt),
[integration checks](../artifacts/codex-recovery-20260919/integration-checks.json),
[full smoke report](../artifacts/codex-recovery-20260919/smoke3-eval/result.json).
The unrelated full test suite was already running when this task began; its
completion is not asserted here. No full multi-seed learning wave was launched.

## Running and evaluating a controlled comparison

Use the project's existing Python/import-root runtime. For example, this runs only
the contract checks and installs nothing:

```sh
python3 - <<'PY'
import json, os, subprocess
from pathlib import Path
r = json.loads(Path('runtime.local.json').read_text())
env = dict(os.environ, PYTHONPATH=os.pathsep.join(r['import_roots']))
raise SystemExit(subprocess.run(
    [r['python'], '-B', 'tests/test_premonition_recovery.py'], env=env).returncode)
PY
```

The runner is `scripts/premonition_recovery.py`. It requires `--steps` (an actual
update ceiling) and a new `--out` directory. It accepts `--request legacy|pooled`,
`--key-pool`, `--score-only-st`, `--seed`, `--data-seed`, `--device cpu|cuda`,
and a shared `--flop-budget`. Training is capped at 1,200 seconds by default;
evaluation is additional. Time and update caps must not be mistaken for a
completed shared-compute run. Calibration is recorded separately from training.
Phases are still scheduled by FLOP fraction; actual phase updates are saved in
`report.phases`, not inferred from nominal step labels.

**Suggested next comparison:** key-pool + legacy request versus key-pool + pooled
request, with ST off in both. Use the same explicit model/data seed within a pair,
independent data streams across pairs, the same host/precision, and one shared
calibrated FLOP cap. Rehearse the full workload, including evaluation, before fixing
the roster and budget. Then freeze those choices before examining learning results.
Do not bundle ST with the first request-head comparison. Compare score-only ST
separately against whichever fixed parent recipe is selected.

Keep failed and incomplete planned runs in the denominator. Report the unchanged
six-cell gate G, all per-seed results, and a paired test for paired outcomes. The
existing diagnostic loader supports these checkpoints; the recovery runner's
validation output alone does not constitute the full gate or certification.
Do not regenerate the existing causal-pair suite or access the sealed test split.
The 77/80 fresh-seed milestone remains unmet.

## Spend and paused work

At **2026-09-19 22:48 UTC**, Vast returned no current instances and zero current
unbilled charges/service fees. Its displayed charge rows sum to **$2.635 for
September 19** and **$2.430 for September 18**. The latter are not individually
attributed against the historical exclusion. Reserving both days gives **$5.065
allocated and $24.935 remaining** under the $30 ceiling, subject to later billing
adjustments. Account payments were excluded from spend arithmetic.

See the updated [spend ledger](../artifacts/spend-ledger.md),
[billing snapshot](../artifacts/codex-recovery-20260919/billing-snapshot.json), and
[instance snapshot](../artifacts/codex-recovery-20260919/instances-snapshot.json).
The API method was checked against
[Vast's official CLI source](https://github.com/vast-ai/vast-python/blob/master/vast.py).
No credentials, billing address, email or account payment details were retained.

PIDs **47848–47852** were all verified as the five gold-zero jobs, stopped with
zero CPU usage. They still have no final result JSONs. Keeping them paused preserves
their in-memory state and avoids adding an uncontrolled partial wave. Their process
identities and this decision are saved in
[paused-runs.json](../artifacts/codex-recovery-20260919/paused-runs.json).

The evidence files under `artifacts/` remain ignored by the existing repository
policy. This report and the new source/tests are available for version control but
are not committed; no unrelated work was staged or committed.
