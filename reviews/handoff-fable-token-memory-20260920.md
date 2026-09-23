# FABLE HANDOFF — finish the access-fix experiments; intelligence is the actual goal

You are continuing Ben Hannan's Premonition work. Read this handoff, then inspect
the current files/processes: the snapshot below will age. Do not restart completed
or still-running jobs.

## Ben's request and what success means

Ben asked what was worse in our model than a transformer, then **"solve those"**,
then emphasized **"Also my biggest concern is intelligence"**. His latest request
is to create this handoff for you to continue.

The earlier answer identified hard one-card retrieval, a break in answer-to-search
gradients, question-blind line compression, and too many coupled routing decisions.
We built a transformer-based successor to remove those structural bottlenecks.
**Do not equate that implementation work, training accuracy, or added attention
with intelligence. The decisive issue is learning operations that transfer to
unseen combinations and respond correctly to changed facts.**

Continue the existing runs, complete the registered evaluations and report their
actual results. Keep failed attempts in the comparison. No claim that the reasoning
problem is solved unless the registered tests support it. No general-intelligence
or scaling-law claim is warranted by this toy even if its narrow tests pass.

## Workspace and authorization

- Canonical repository: `/Users/ben-hannan/Desktop/projects/beautiful-model`.
  `/Users/ben-hannan/Downloads/beautiful-model` resolves to it.
- Working Python, already installed:
  `/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12`
- Use `-B`. These scripts load existing dependency roots from `runtime.local.json`;
  system Python alone did not have torch. Torch is 2.14.0, CPU, one thread per job.
- Ben authorized local implementation, tests and training with the later requests.
  The original pasted handoff's analysis-only restriction applied to the earlier
  design turn; do not reimpose it on completion of these authorized experiments.
- Retain the no-GPU, no-SSH, no-paid-resources, no-installs and no-external-messaging
  boundaries. Do not inspect credentials or `~/.config/vastai/`.
- The repository was already heavily dirty. All this work is additive. Do not
  overwrite other contributors' files or alter any experiment's frozen source
  closure. No commits, PRs, deployments or model-default changes were requested.
- Ben appreciates simple, candid progress updates, roughly once a minute while
  work is active. Do not ask for renewed permission to finish the authorized work.

## Immediate live state — 2026-09-20 01:52:46 UTC

**Three scaled-initialization jobs were still running.** They target exactly
6,000 updates each and have their own time caps. At the snapshot all had logged
4,000 updates; latest training-batch accuracies were 95.3%, 96.9%, 100%. Those are
NOT held-out results.

| Seed | OS PID at snapshot | Original tool session ID | Log |
|---|---:|---:|---|
| 0 | 6310 | 68493 | `artifacts/codex-token-scaled-20260920/seed-0.log` |
| 1 | 6311 | 5392 | `artifacts/codex-token-scaled-20260920/seed-1.log` |
| 2 | 6312 | 5692 | `artifacts/codex-token-scaled-20260920/seed-2.log` |

Tool session IDs may not be usable from your task. Prefer OS process inspection,
logs and `seed-N/completion.json`. PIDs may exit or be reused: verify the complete
command before taking any action. Do not launch duplicates. Do not kill them.

Useful read-only check:

```sh
pgrep -fl 'premonition_token_(evidence|scaled|reasoning_probe).*'
```

The answer-only roster and the original-initialization guided roster are fully
finished, with all three per-seed completion files. Their original tool sessions
were respectively `99770, 97439, 63350` and `91423, 12998, 86604`.

## The model actually built

Main source: `scripts/premonition_token_memory.py`, class `TokenMemoryReasoner`.

- 79,316 parameters versus original Premonition's 79,748.
- Width 48, four attention heads, three shared recurrent read steps.
- One small transformer encodes each complete story line, retaining EVERY real
  token state. Another encodes the visible question through `[answer]`.
- Every recurrent step attends over the current question state plus its immutable
  original encoding, then cross-attends softly to all eligible story tokens.
- No hard top-k, ASK gate, entity binder, teacher card insertion or pooled card
  value. All causal non-question lines, including fillers, are eligible.
- Padding is compacted without dropping real tokens; key/value projections are
  cached per visit. A zero NULL row handles empty memory.
- Inference gets only visible memory tokens, question tokens, visit ownership and
  causal line eligibility. No supplied semantic positions, relation indices,
  role masks, gold cards or intermediate answers.
- The final question position predicts one of all 68 token IDs through a tied
  classifier. EOS is appended deterministically. This is a single-token toy
  answerer, not an open-domain language model. Line order is ignored.
- Training and inference use the SAME soft forward. This changes the original
  hard-card inference contract, so answering its six tests does not earn official
  hard-retrieval G_pair admission or G_cert.

The model is already transformer-based. We have NOT run a separate standard
full-context transformer baseline. Do not claim this experiment measures a
general transformer-versus-Premonition advantage.

## Three recipes — retain all of them

### A. Answer-only token memory — COMPLETE, FAILED

Folder: `artifacts/codex-token-memory-20260920/`.
Runner: `scripts/premonition_token_memory_run.py`.

Seeds 0,1,2; exact historical data stream (seed 1101), 16 visits/update; respective
update counts 12,251 / 12,250 / 12,250. Final answer CE only. AdamW .001, warmup
100 updates, betas (.9,.99), decay .1, clip 1. Linear/embedding initialization
N(0,.02). All finished. Each used about **26.82%** of the original model's counted
training-FLOP ceiling, not equal spent compute.

Learning stayed weak; no seed passed the six tests. `REPORT.md`, `completion.json`
and `reasoning-probe/results.json` already exist here.

### B. Same model with ordered supporting-line feedback — COMPLETE, FAILED TRANSFER

Folder: `artifacts/codex-token-evidence-20260920/`.
Sources: `scripts/premonition_token_evidence.py` and
`scripts/premonition_token_evidence_run.py`.

Exactly the same model, initial weights per seed, optimizer, data and update
exposure as A. The single change is the training objective:

```text
L = answer CE + 0.5 * ordered supporting-line attention CE
```

For two-hop questions, the auxiliary trains attention at the final question row
toward the link line at step 1 and the endpoint line at steps 2/3. One-hop targets
repeat their sole evidence line. Attention is averaged over heads and summed over
all tokens in that line. Labels remain outside model forward. **This is stronger
ordered TRAINING supervision; disclose it.** It is not discovery from answers
alone. There are no supplied roles or evidence at inference.

All three completed the full exposure and used the same counted FLOPs as A.
They learned familiar questions but **failed unseen relation composition**.
No seed passed all six original or all six fresh tests.

Fresh counts, each denominator 512, column order c1..c6:

| Seed | One-hop | Practised 2-hop | Held-out 2-hop | Changed-link pair | Changed-value pair | Irrelevant pair |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 506 | 474 | 40 | 3 | 8 | 29 |
| 1 | 512 | 512 | 103 | 29 | 73 | 107 |
| 2 | 512 | 512 | 46 | 0 | 14 | 61 |

This is the most important result already known: near-perfect familiar-question
performance did not transfer. Do not let the impressive training curves obscure
that failure. The guided mean fresh held-out accuracy is only **12.3%**.

### C. Guided model with width-scaled starting weights — RUNNING AT SNAPSHOT

Folder: `artifacts/codex-token-scaled-20260920/`.
Runner: `scripts/premonition_token_scaled_run.py`.
Initializer: `scripts/premonition_token_initialization_probe.py::rescale`.

Same model and guided loss. Starting LINEAR weights are rescaled from std .02 to
`1/sqrt(3*fan_in)`, retaining the same initial normal draws. Embeddings remain
unchanged. This matches the variance, not the distribution, of default PyTorch
uniform Linear initialization.

Chosen from a separate TRAINING-ONLY diagnostic: at 1,000 updates its final-batch
accuracy was 43.75%, versus 6.25% without rescaling, using the same diagnostic
initialization seed 774111 and data seed 774112. No held-out evaluation selected
this initialization. Both diagnostic logs are retained in A's folder.

The fixed C roster is again seeds 0,1,2, but **6,000 updates each**, not the full
historical exposure. Therefore it is not a matched-exposure comparison to A/B or
the original. The plan discloses this. Caps: 900 training seconds and 1,200 total
seconds per job; no seed replacement or checkpoint selection. The running
commands automatically save and evaluate their final models. Do not extend this
budget or continue training silently in response to scores.

## Current fresh-panel comparison

Means across three fixed seeds. These are not independent pooled trials across
seeds; all seeds see the same worlds.

| Test | Original saved Premonition | A: answers only | B: guided |
|---|---:|---:|---:|
| One-hop | 100.0% | 8.9% | 99.6% |
| Practised two-hop | 99.3% | 8.5% | 97.5% |
| Held-out two-hop | 33.3% | 8.2% | 12.3% |
| Changed-link pairs, both correct | 20.5% | 0.0% | 2.1% |
| Changed-value pairs, both correct | 27.7% | 0.1% | 6.2% |
| Irrelevant pairs, both correct and same | 31.5% | 6.4% | 12.8% |

Original controls also pass the complete six-cell gate in 0/3 of this roster.
These three original seeds were historically learned runs, not a representative
reliability sample of all 40 original seeds.

## Evaluation contract and files

1. Original unchanged panel:
   `artifacts/claude-pairsuite-20260919/manifest.json`.
   c1/c2/c3 have 2048 worlds; c4/c5/c6 have 1024 pairs.
   Cutoffs: 1969, 1969, 1876, 945, 945, 945.
2. Fresh panels were generated and exact-interpreter-audited BEFORE training:
   A's `fresh-*.pt` files. Seeds 202609201001..202609201006; 512 units per cell.
   Raw accuracy screens: >=487 for c1/c2, >=461 for c3..c6. These fresh cutoffs
   are not confidence-certified admission thresholds.
3. Registered narrow success requires every fixed seed to finish its registered
   exposure, pass all six original answer cutoffs, and confirm on all six fresh
   screens. Report failures and the no-increase-in-stuck safeguard. Do not promote
   merely because survivors improve.
4. Each job saves `model.pt`, `training.json`, `old-evaluation.json`,
   `fresh-evaluation.json`, `memory-lesion.json`, `completion.json` under `seed-N/`.
   Checkpoint files include optimizer and RNG state for recovery, but the runners
   do not have a resume command. Do not accidentally rerun into existing folders.
5. A also contains `plain-fresh-evaluation.json` for each original checkpoint,
   freshly rescored with native parity and world-isolation checks. Original old
   panel results are in
   `artifacts/codex-memnn-comparison-20260919-v2/seed-N/plain-evaluation.json`.
6. Sources, checkpoints, panels and plans are hashed. **Do not edit registered
   model/runner/test dependencies while completing these runs.** New files are
   fine. The plan-load functions intentionally reject changed source closures.

## Secondary intelligence probes, already registered

Sources: `scripts/premonition_token_memory_stress.py` and
`scripts/premonition_token_reasoning_probe.py`.

The generated data lives in A's `stress/` directory, with an immutable manifest.
Every recipe has `reasoning-probe/plan.json` pointing to those same data.

- 12-person worlds: one-hop, practised two-hop and held-out two-hop, 512 each.
- Three-hop held-out questions: a second LINK token, 512 worlds. This changes
  BOTH depth and syntax, so a failure cannot be attributed solely to depth.
- Each saved model is scored at 3 and 6 read steps, with identical weights and
  no additional learning. More steps are not assumed to help.

A's probe is complete (`reasoning-probe/results.json`). B's and C's probes remain
to be run. These are secondary diagnostics, never checkpoint/seed selection.

## Exact next actions

Work from the canonical repo. Use the explicit Python above.

1. Inspect logs/completion files and the scaled-job processes. Let still-running
   bounded jobs finish. If a job failed or hit its cap, retain and report that
   outcome; do not silently replace it.
2. B is complete, so its registered reasoning probe can run now:

```sh
/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12 -B scripts/premonition_token_reasoning_probe.py run --out artifacts/codex-token-evidence-20260920
```

3. When all C jobs have completion files, run the same probe for C:

```sh
/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12 -B scripts/premonition_token_reasoning_probe.py run --out artifacts/codex-token-scaled-20260920
```

4. When all nine completions and all three probe result files exist:

```sh
/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12 -B scripts/premonition_token_report.py
```

This aggregation script has been written and syntax-checked but not yet executed
because C is unfinished. Review any failure rather than assuming its output is
correct. It should create A's `comparison.json` and `COMPARISON.md`, verify source,
data/checkpoint identity and paired A/B initialization, and include ALL recipes,
the original controls, stress results, actual compute and limitations. It refuses
overwrites. If partial output already exists, inspect it before retrying.

5. Verify the final tables against raw counts, especially old-vs-fresh denominators
   and the shortened C exposure. Show Ben the comparison in plain English, leading
   with whether unseen-rule transfer actually improved. State what is still not
   solved. Do not call this equal-compute, official G_pair, certified reliability,
   scalable intelligence, or a general transformer benchmark.
6. Only after completing that evidence should you decide the next design. A/B
   already show that accessible words, connected gradients and learned familiar
   answers do not enforce compositional reuse. If C also fails, focus diagnosis
   on the terminal relation/person binding and shared lookup operation, not
   merely more attention, larger parameters or more loops. The earlier design
   and its counterexamples are in `design/v3/14-relation-fix.md` and
   `design/v3/15-relation-fix-review.md`; proposed fixes are not proven fixes.

## Verification already completed

- `tests/test_premonition_token_memory.py`: 11 passed — size, gradients, all-token
  access, causality, empty memory, padding/order invariance, isolation, identical
  train/eval policy, checkpoint reload, question anchor and counted FLOPs.
- `tests/test_premonition_memnn.py`: 9 passed — shared adapter, oracle-field
  exclusion, consecutive frozen-stream parity and other baseline checks.
- `tests/test_premonition_token_evidence.py`: 2 passed — exact visible training
  stream/answers, valid causal evidence targets, gradients and exact FLOP count.
- 22 tests total. See A's `verification.json`.
- Each finished job verifies unchanged evaluation weights and identical outputs
  after reload. Sources remain unchanged. A's initial and B's initial weight
  fingerprints should match per seed; the aggregate script checks this.
- Counted FLOPs follow the existing project's matmul convention; elementwise
  operations and optimizer work are excluded. No paid compute was used.

Main explanatory design note:
`reviews/premonition-token-memory-20260920.md`.

Finish the current evidence cleanly before starting another experiment. Ben's
concern is intelligence, and a candid negative result is more useful than
presenting a structural rewrite or high training accuracy as a reasoning fix.
