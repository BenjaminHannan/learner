# Premonition: evidence within $30

Status: proposed research roadmap; local Experiment 1 engineering is authorized.
Ben has approved starting the first-stage tests. Opus executes; Astra reviews.
Later stages will be decided after reviewing results.
No rental is authorized. New rental spending so far: **$0.00 / $30.00**.
The approximately $3.40 spent before this handoff is excluded.

The target is one credible result about memory-assisted reasoning. A small
continual-learning pilot survives, but cannot establish lifelong learning.

## Experiments and spending envelopes

Use this Mac for implementation, data checks, CPU smoke, toy learning, and
small training on CPU/MPS after measuring speed and memory. Prepare data locally
where practical. Use only Vast.ai for rented compute; never BensPC.

All rental rows below assume **one RTX 5090 at at most $0.65/hour for GPU
compute**. These are planning limits, not current offers or promised runtimes.
Each session requires a live quote and Ben's explicit yes. Setup, evaluation,
and verified download time count toward billed hours. Storage and transfer
allowances are included in the maximum, and must be checked against the offer.

| Stage / proposed rental | Expected session hours (upper planning limit) | Compute at $0.65/h | Other-charge allowance | Maximum |
|---|---:|---:|---:|---:|
| 1a: v2 A/E/E-long throughput and learning pilot | 2 | $1.30 | $0.70 | $2.00 |
| 1b: transformer and D supplied with correct evidence | 4 | $2.60 | $0.40 | $3.00 |
| 2a: screen D, D-noask, D-soft, C* | 4 | $2.60 | $0.40 | $3.00 |
| 2b: matched finalist runs, seeds 0, 1, 2 (one session per seed) | 4.5 each | $2.925 each | $0.405 each | $3.33 each; $9.99 total |
| 4-small: four-lesson procedural-learning pilot | 7 | $4.55 | $0.45 | $5.00 |
| Failure / transfer / rerun reserve | — | — | — | $7.01 |
| **Total ceiling** | | | | **$30.00** |

Unused envelopes remain unspent. Each new quote must fit both its envelope and
the remaining lifetime balance, including outstanding charges. If a rate or
transfer estimate does not fit, reduce runtime or use the Mac; do not assume a
cheap listing exists. Do not rent until measured local smoke and a prepared
remote command/artifact manifest make the session ready to use.

Vast's official pricing documentation says charges include compute, storage,
and upload/download traffic; stopping an instance does not stop storage charges:
https://docs.vast.ai/guides/instances/pricing (checked 2026-09-18).

**Survive:** experiment 1 (solvability), a narrowed experiment 2 (memory), and a
conditional four-lesson version of experiment 4. Report existing depth slices
at no new training cost. **Defer:** the full recurrence sweep, CLUTRR, 20-lesson
claim, B12/B28 scale sweep, D-local/D-noptr sweeps, and broad tuning. These are
budget omissions, not silently satisfied requirements of the full §10 verdict.
Keep all old code and artifacts.

## Build and run order

1. Establish the local baseline; preserve old implementations. Fix evaluation
   hygiene first: label-free reader/prompt inputs, safe invalid-entity scoring,
   checkpoint identity checks, separate report regimes, and C's recall window.
2. After Ben confirms Claude stopped, diagnose D's existing trainer and toy.
   First inspect gradients and train/eval agreement. Add a separate D-soft
   experiment if top-k learning is the obstacle; do not replace the agreed store.
3. Build the gold-evidence diagnostic and question-centred answer-only Core
   objective; train E and E-long using tokenizer v2 and label-free prefixes.
   Gold evidence is privileged diagnostic information, never a decision row.
4. Run a bounded CPU smoke with real village data, read-only evaluation,
   checkpoint round trip, and explicit pass/fail checks. Measure a short MPS
   pilot before selecting overnight work. A mechanics smoke does not certify
   the ≥95% reasoning threshold or the full statistical pipeline.
5. Build C* (pointers plus iterative learned retrieval with matched evidence
   and answer supervision), D-noask, and D-soft. Screen at a common small
   compute budget. Finalists use seeds **0, 1, 2**, frozen before training.
6. Only after solvability passes, run the memory comparison. Measure training
   FLOPs, processed and supervised tokens, same-device time, evaluation cost,
   and memory. Cap data reuse near three epochs; grow data or shrink budgets.
7. If memory results justify it and $5 remains, use four lessons × 32 support
   visits, fresh bindings, 64 fresh probes per lesson, and support counts
   0/1/2/4/8/16/32. Compare sequential updates, reservoir replay, frozen+retrieval,
   and one periodic replay variant on one backbone at equal update compute and
   storage. Report early/late acquisition and forgetting as a pilot only.
   Long-term sleep architecture changes still require Ben's approval.

## One success, and stop rules

**Primary success target:** on clean, label-free far questions requiring at
least two reasoning steps, D improves accuracy over D-noask by at least ten
percentage points, with a one-sided 99% visit-clustered lower bound above zero
in each of three seeds, at matched training FLOPs and fixed inference loops.
Use at least 60 visits / 100 items per cell and estimate required coverage from
pilot variance. Keep seeds separate rather than treating them as extra visits.
This is a narrower memory claim, not a pass on the full §9/§10 efficiency gates.
C* and E-long remain required context for judging whether the gain is useful.

- Gold-evidence familiar depth-1–3 / fresh-name accuracy must reach 95% before
  expansion. Allow at most two predeclared training adjustments within stage 1;
  failure returns work to local diagnosis. Never tune on the test split.
- If D-soft alone learns, report that result under its own name. Do not relabel
  it D or claim the original top-k controller worked.
- D > D-noask but not C*: retain only the memory claim. Evidence of D/C*
  equivalence within ±3 points, with C* cheaper, triggers a recommendation to
  Ben; replacing his long-term reasoner requires his approval.
- A one-sided 99% upper bound below +5 points against C on far multi-hop is
  evidence to stop that comparison. Non-significance alone is inconclusive.
- No ≥95% shallow gold result, unresolved leakage/compatibility, missing
  coverage, or failed read-only checks: no decision verdict and no next-stage
  rental. Mixed label regimes or privileged gold diagnostics never enter one
  primary verdict. All v1-tokenizer checkpoints remain retired.
- No cost may exceed $30 total. Reserve pays for failures only after a fresh
  quote and approval; it is not automatic permission to continue.

Before destroying each instance: stop training early enough for transfer;
copy the exact run-ID directory containing checkpoints, configs, tokenizer
identity, reports and logs; verify every manifest path, size and SHA256 locally;
then destroy immediately and verify termination. No wildcard artifact copies.
Request credentials only when needed; never persist, log, or echo the API key.

## Decision requested from Ben

Approve the evidence-first sequence: solvability → memory comparison → small
procedural-learning pilot, postponing the growing codebook, private-language
RL, learned sleep clock, and drives. This is a sequencing decision, not deletion
of the long-term design. Until confirmed, retain its status as **pending**.

Trainer ownership is separately pending Ben's confirmation that Claude stopped.
Neither roadmap approval nor trainer handoff authorizes a rental.
