# Preregistered retention-isolation tests — Codex, 2026-09-27

These marks are committed before the registered runs. They do not change any
existing project verdict. The earlier uncommitted Mac pilot (seed 27) began before
Ben supplied the commit-before-run rule and was stopped; it is exploratory only,
excluded from all marks below. Its output is retained for audit. No registered
test is selected or tuned using that pilot's scores.

## R1 — complete snapshots, two fresh seeds

**One change:** which complete trained dense network answers an old skill.
Control serves the latest sequentially trained network for every skill. Candidate
serves the immutable checkpoint saved when that skill was learned. Both serving
modes use the SAME training trajectory and deterministic scorer. The caller's
existing `Item.env` is the task identity; no task classifier is learned. This is
an engineering test of task-aware retention with extra storage, not an equal-size
continual-learning or learned-routing comparison.

Use the existing small dense `claude_rsn358e_moe` architecture and training recipe:
1,646,750 parameters; grids4/5 for 2,500 steps, sums1–4 for 2,500 steps; batch64;
AdamW lr1e-3, weight decay0.1, betas0.9/0.95, 100-step warmup then cosine; existing
random recurrent-depth schedule. Frozen checkpoints include embeddings,
attention, MLPs, normalizations, answer and stop heads. The whole next model is
trainable. No replay. All puzzle data/targets come from existing exact code.

Training seeds **29 and 30**. For seed s, independent final panels come from
seed **92000+s**, 200 grids5 and 200 sums4. Reject exact training/evaluation input
duplicates; do not print puzzle contents. No final-panel early stopping, parameter
tuning, retry-selected checkpoint or choice of training length. Save both phases'
checkpoints, per-phase scores and integer pass/fail counts. Primary score uses
the model's own stopping rule; fixed16-round exact scores are report-only.

Run locally on this Mac, MPS or CPU selected only by throughput. Report actual
device, model/checkpoint bytes, two-model total capacity, wall time and software
revision. Do not launch e4, e5, e6 or any other existing registered experiment.

Validity on EACH seed: grids5 after grids >=190/200 and sums4 after sums >=190/200.
If either fails, R1 is **INCONCLUSIVE for mastery plus retention**, even if exact
functional isolation is observed; report the failed mastery check separately.

**PASS:** validity holds on both seeds; after sums, routed grids are identical in
score to the grids snapshot and lose zero previously-correct items; weights and
all-round predictions/stop probabilities on a fixed 16-item audit subset are
bit-identical before/after sums and after serialization/reload; routing rejects
unknown task IDs and alternating grid/sum calls preserve each route's outputs.

**FAIL:** valid training but any required preservation/routing control fails.
**Proved wrong (the scoped isolation mechanism):** changing only the unrelated
candidate's weights changes even one old routed prediction or stop probability,
or corrupts an old checkpoint, with the same input and execution settings.
It cannot prove broad fixed-budget continual learning right or wrong.

Report the latest model's grids score after sums as a paired overwrite control.
If it does not forget, report that the failure was not reproduced; don't infer
an empirical retention advantage, even if isolation controls pass.

## C1 — live adapter bypass, no training or learned switch

**One change:** inactive LoRA uses exact base projection bypass instead of the
adapter-augmented answering path. Test `implementation/retention.py` using
available local model weights and already-saved adapters only. No new model
download, no adapter training, no classifier fitting. No duplicate of dl-9.

First run deterministic code-generated unit controls: exact base-off and
adapter-on parity, unchanged checkpoint keys/save-load, inactive NaN adapter
bypass, concurrent route isolation, exception/nesting restoration, expired async
scope rejection, refusal of an unfrozen shared base parameter, and refusal of
cross-request supplied KV cache through the supported generate entry point.

If the exact original MiniCPM5-1B revision
`87179e5c1f455ef22e6223592d2d61351b525bfc` is present locally, run real autoregressive
prefill/decode parity on deterministic evaluation-only inputs, alternating base /
saved adapter / base. Require bit-identical base logits and greedy output versus
the unwrapped base, and adapter-on parity with the original unwrapped LoRA
implementation. Check base tensor hashes before/after. All comparisons use the
same precision and device. Saved dl-5 adapters may serve only as **finding-only
software test fixtures** because their historical training used disallowed text;
they cannot establish eligibility for H-B or a clean training recipe.

**PASS (software behavior only):** all applicable unit and real-model parity
checks hold. **FAIL / proved wrong:** inactive routing changes the same base
output under identical settings, or changes a frozen base tensor. **INCONCLUSIVE
for real 1B serving** if the exact base weights are absent; still report unit
results, never substitute another merged model or invent 1B measurements.

Do not claim this test establishes automatic routing, prompt rewording success,
general-question retention marks F1–F5, new-skill improvement, or a dl-9 result.

## Workflow and provenance

Everything new lives below this directory. Never modify sealed/original scripts,
root notebook/, PC, watcher or other jobs. No spending, no downloads, no secrets.
Luna-written data is permitted by Ben's subsequent clarification but is not
needed for these code-generated tests. Each run records UTC start from `date -u`,
machine and its own PID in RUN-NOTE.md; RESULTS.md uses shown/suggested/untested.
Commit/rebase against main and push without force or a PR. Reviewers recheck the
raw numbers before any production use. Do not merge this into the live model.
