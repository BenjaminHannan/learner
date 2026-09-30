# Premonition: end-to-end execution board

Started 2026-09-30 02:32 UTC (September 29, 10:32 p.m. New York).
Owner: lead coordinator. Implementation and experiments: Sol subagents.

The complete objective is **NOT SHOWN**. This board does not promote development
screens or carry old approvals forward. The user's current design and evidence
rules override older handoff notes.

## Deadline update from Ben

Deliver a runnable joined **proof of concept by 2026-09-30 07:00 America/New_York
(11:00 UTC)**. The heart is a non-English latent-state looped reasoner, notebook,
and actual overnight learning. This version deadline does not imply completion
of the full research proof or public benchmark race. Build and run the vertical
path first; retain every unpassed research gate explicitly. The lead directs and
verifies Sol work, rather than absorbing implementation from the workers.

Ben confirms his RTX 5070 Ti is reachable through Tailscale. Prefer that free
GPU for small tests. $7.50 is the total rental budget for this proof of concept;
additional funding comes after delivery. At account usage below 3% remaining,
Ben authorizes applying his available reset through supported account controls.
Initial usage check: 76% remaining, one full reset available; not redeemed.

### Release checks for the 7 a.m. version

1. A documented local command loads actual saved weights and accepts text.
2. The reasoner loops in latent state, uses a learned stop with an enforced cap,
   and passes only final state to the output translator. No language-model or
   hand-written solver silently substitutes for the reasoner.
3. A persistent notebook reaches the reasoner; the output translator cannot read
   it independently. A memory-removal control establishes whether it is used.
4. A real sleep job updates a checkpoint using allowed experience and replay;
   fresh before/after checks record new competence and old-skill retention.
   Failed candidates roll back. No gain is promised ahead of the run.
5. Two seeds and independent recount back any claimed behavioral improvement.
   A working interface alone is labelled an engineering result.
6. One model bundle, a run guide, raw evidence and a visual status report are
   committed to main. Scope limits and all failed gates remain prominent.

Ben clarified: **grammatically correct conversational sentences are required**;
symbolic-only input/output is not the requested version. Beating other models on
equal benchmarks for its scale is also a target. The comparison must disclose
the whole system's total and active parameters, including any pretrained language
component, and equal inputs/tools/budgets. A pretrained talker must not bypass
the latent reasoner. Unsupported wins or grammatical examples alone do not pass.

An overnight heartbeat is scheduled every 15 minutes in this chat to resume
coordination if needed and report meaningful changes. It must report readiness
and any unmet requirements by the deadline, then pause its recurring schedule.

### Later capabilities and optional experiments

Ben explicitly wants **audio and vision eventually**. They belong on the later
roadmap, outside tonight's required text proof of concept: thin modality
translators feed the same latent reasoner. Video is a possible extension.

The additional pictured ideas are optional, adopted only if they help: a creative
proposal-and-filter mechanism; tools/agentic jobs on request; a skills notebook;
idle curiosity and assigned-topic web research. None licenses a second model to
do the reasoner's job, unchecked web text to become trusted memory, or generated
prose to become training data. Quarantine external material, retain sources, and
test usefulness before adding complexity. These ideas do not displace tonight's
conversation, reasoner, notebook, sleep and fair-comparison work.

**Priority research update:** Ben specifically asks for research on the dreamer
and filter and says it is important. Bohr now runs the dedicated Sol research pass; the visual explainer is complete. Read the project's existing creative-model
intent; distinguish it from similarly named reinforcement-learning systems.
Study proposal diversity, filtering/verification, equal-compute controls,
latent-reasoner integration and permitted sleep data. Adoption remains dependent
on measured benefit, but the research is now explicitly requested work.

Ben further clarified the purpose: discover useful novel ideas beyond the current
model’s reliable ability, filter them, and consolidate the discoveries during
sleep so the model grows. Test next-day direct solving and transfer on new
problems, rather than memorization of selected attempts. This is a design goal,
not measured evidence. Verified internal structured solutions and outcomes may
be replayed; model-authored prose remains excluded from training.

## Design and stage order

```mermaid
flowchart LR
  A[Human text] --> B[Thin input translator]
  B --> C[Attention core + sparse MLP experts]
  C -->|Learned continue| C
  C -->|Learned stop: final state only| D[Thin output translator]
  D --> E[Text answer]
  F[Verified experience + old replay] --> G[Sleep candidate]
  G --> H[Retention and acquisition checks]
  H -->|Pass| C
  H -->|Fail| I[Keep previous checkpoint]
```

| Stage | Required evidence | Current status | Work now |
|---|---|---|---|
| 1. Components | Qualified dense reference; 2× reasoning, full few-shot ladder and half time-to-quality; stop before sleep; composition; frozen-state translator and failing controls; many nights/kinds | NOT SHOWN | Six Sol work lanes below |
| 2. Joined model | Real text → learned loop → final-state text; improvement after sleep, using the same joined weights | NOT SHOWN | Build interfaces; no substitute-rule demonstration counts |
| 3. Scale | Gains against fair plain/dense controls persist or grow across sizes and both seeds | NOT SHOWN | Wait for stage 1/2 survivor; measure compute before rental |
| 4. Public race | Locked public-benchmark protocol against open 1–2B models; contamination/provenance audit | NOT SHOWN | Final evaluations remain unopened |
| 5. Assistant | Usable general chat, auditable conversations and nightly sleep; user-supplied sealed test | NOT SHOWN | Capture/runtime scaffolding only; never access uncle questions |

## Active Sol lanes

| Lane | Worker | New files owned | Deliverable / dependency |
|---|---|---|---|
| Dreamer + filter | Bohr | artifacts/sol-dreamer-20260929, scripts/sol_dreamer_* | Primary-source research; novel internal discovery → verification → sleep consolidation; fresh transfer and retention tests |
| Spatial diagnosis | Peirce | artifacts/sol-spatial-20260929, scripts/sol_spatial_* | Two-seed +1 GRU gate-bias test, unchanged and dense controls; diagnostic, not adoption of a GRU target |
| Stop | Epicurus | artifacts/sol-stop-20260929, scripts/sol_stop_* | Actual active-row stopping, final-state contract, TRAIN-only calibration and parity |
| Composition | James | artifacts/sol-compose-20260929, scripts/sol_compose_* | Learned cross-program communication, fresh symbolic compositions, fair controls |
| Translator | Leibniz | artifacts/sol-translator-20260929, scripts/sol_translator_* | Final-state-only frozen decoder; embedding-only/no-state/shuffled/plain controls; provenance audit |
| Sleep / runtime | Bernoulli | artifacts/sol-sleep-20260929, scripts/sol_sleep_* | Multiple kinds/nights, replay provenance, rollback, assistant interface; training waits on stop evidence |

Concurrency limit is six. An independent blind recount uses the next available
Sol slot. It receives raw scored records and presealed marks only, without the
author's result narrative. No new scientific claim is accepted before that audit.

## Acceptance and experiment discipline

- Read the latest local review and retain all failed runs. Never reopen or rescore
  a consumed holdout. Recount saved correctness records without running inference.
- Seal source and checkpoint hashes, generator/split identity, seed list,
  comparator, measured-noise provenance, pass marks and full work budgets before
  each run. If noise is unavailable, a diagnostic run cannot earn SHOWN.
- The original ladder is k=1/4/16/64/256/1024/4096/16384, with 2,048 adaptation
  updates per rung. F_few uses the first four rungs. Reduced-budget pilots must
  not be compared as though they ran that protocol.
- Use the qualified width-256, two-block, 1,645,726-parameter dense reference,
  relevant improved dense comparators and plain-network controls. Match inputs,
  presentations and active work; charge replay, prefix, router, teacher, stop
  fitting, interrupted work and search. Storage alone is not a cost objection.
- The 2× reasoning criterion is ceiling-aware (double accuracy below 50%; halve
  errors above 50%), with useful absolute quality when the control is near zero.
  Full details remain in the latest review's PROOF_PROTOCOL.md; final confirmation
  needs new independent families, both seeds, and uncertainty/multiplicity checks.
- Architecture fidelity is separate from performance: whole-program top-one
  isolation is not cross-program composition; a GRU diagnostic is not the target
  recurrent attention/MLP MoE; zero-state failure alone does not exclude decoder
  reasoning from retained input.
- No model-authored text, paraphrase or template enters training. Algorithmically
  generated symbolic tasks are labelled as such, not as natural-language proof.
  Logged assistant messages are excluded from training labels.
- Downstream software can be built in parallel. Stage proof and dependent
  training cannot skip upstream gates. Sleep training follows stop readiness.

## Money and machines

Tonight's total Vast authorization: **$7.50**. New committed spend: **$0.00**.
The earlier per-spend approval rule (ask for $0.50 or more, including cost and a
cheaper option) remains in effect. No rental is launched until the job is ready,
priced and authorized. Mac jobs use handoff/queue; use pcqueue only if an available
PC is verified. Old jobs, other agents' rentals and sealed files are preserved.

Every approved rental must log price, instance ID, hard runtime/spend cutoff,
copy-back checksums and verified destruction. Do not split a larger commitment
into small rentals to evade approval.

## Initial review findings (not new experimental proof)

The read of `program_library.py` confirms a fixed route chosen during embed and
one selected program per loop. Its own counts report composition=false. The
spatial and numeric candidates use GRUCell recurrence. `real_screen.py`'s old
evaluation runs the full cap before selecting a stop: its time is not active-stop
latency. These code observations guide the new tests; historical scores remain
development evidence unless their specific seal and independent audit qualify
them. No final panel was opened during this takeover.

Sources: handoff/director-roadmap.md; handoff/director-board.md;
handoff/director-briefs/thread-helper-common.md;
reviews/premonition-moe-2026-09-29/{README,REPORT,PROOF_PROTOCOL}.md;
artifacts/claude-fewex-20260927/RESULTS-EQ.md.


## Sol integrator update — 2026-09-30 UTC

Lead is MANAGEMENT ONLY: assign tasks and evaluate self-contained Sol reports; no file reads, edits, tests, integration or git. James is sole integrator with explicit user authorization for reviewed owned main commits/pushes and watcher queue submissions. Vision published ff8703139. Heartbeat updated via supported tool, ACTIVE15-minute schedule preserved. Usage70%remaining; reset not used; budget0/$7.50.

Composition awake-only job `sol-compose-awake-20260929-benspc` now being submitted. 21-file preseal, seeds0/1, six controls/candidate arms,512updates each, zero sleep,3600s driver/4200s wrapper. Mechanics15/15; no performance evidence. Original7200s sleep draft NOT submitted. Two-seed diagnosticspan never constitutes statisticalproof. Wait fresh independentraw+presealedmarkrecount before scientificpromotion.

Sleep remains BLOCKED on exactcheckpoint learned-stopreadiness and realEnglish/notebookfactories. Bernoulli completed/closed;30/30integritymechanics not sleeptraining. Bohr alone owns dreamer/filterresearch. Source/SleepMoE contextadapter and Composer64board compatibility require owner stop/translator integration; do not relabel symbols as conversational proof.

2026-09-30 03:22 UTC integration receipt: watcher launched sol-compose-awake-20260929-benspc on RTX5070Ti torch2.11.0+cu128. PC contracts passed15/15 seeds0/1 with zero optimizer steps in contracts. Training subsequently completed all six seed0 arms by03:21:46 UTC; seed1 and frozen scoring pending. Sleep updates0. This is execution evidence, not accuracy or stop qualification. Epicurus assigned new Composer64 exact-checkpoint readiness runner; Leibniz grounding queue/factories requested for next slot. Ptolemy owns raw spatial/sleep engineering+presealed marks only; no narratives sent.

2026-09-30T03:33:29.523360+00:00: Ptolemy independent audit: spatial candidate seed0 maze9/11=64/64, seed1=0/64; BOTH-seed descriptive gate not met; no adoption.31seal/6checkpoint hashes match,3072updates/24576slots. Saved predictions lack labels; only stored correctness flags recounted, prediction-vs-label correctness unverifiable. Preserve oldrun; no regeneration/rescore. Sleep tests used empty optimizer/randommodels/canned doubles; notebook shape append never combinedreasoning; stopadapter hash changed since smoke. No learning/integration readiness. Future raw must include identities/labels/predictions/masks/source/checkpoint/versionhashes. Composition completed465.75s all12arms512updates each, zero sleep, saved screenNOTMET. D256 human-grounding + finalstateEnglish + notebook + exactcheckpoint stop + sleep is criticalpath.

2026-09-30T03:42:58.914919+00:00: Source stop readiness v2 initialqueue failed before Python (badCPU /usr/local/bin/python3), no inputs/updates/scoring. New runtime-only queue66ea20cd0 usedcached uv Python3.12; completed32.579828875s, eight stopheads fitted, zero core/sleepupdates. Sourcegate NOT MET: sums24/24both,grids20/24(seed0),21/24(seed1) vscontrols24/24. Acceptedstopreadyfalse; norescore/recalibration. Newhuman-groundcheckpoint needsseparateexacthashgate Epicurus. Leibniz questiononly/contextnotebook v2 boundedTRAINpackage nextGPU,500updates/seed3000sdriver3950swrapper; Peirce plainfactoryfollowup.

2026-09-30 04:10 UTC correction: V4 both seeds launched and FAILED before TRAIN, frozen model hash guard; optimizer0/no human weights. s0 launch04:05:33Z transport5.172s/preflight2.0s; s1 watcherlaunch04:07:42Z/preflight9.484s. Pending s1 hold arrived after completion. Preserve sealed V3/V4 and both raw failures; no rerun. New read-only cache digest/topology watcher diagnostic published; Leibniz owns new strict loader/seal/root/queues. Cached-file corruption vs symlink containment not yet resolved. Stop/sleep still blocked exact future checkpoint.

2026-09-30 04:15 UTC independent Ptolemy composition recount published: all36 raw rows matched saved labels/predictions/fixed predictions/rounds; structure24/28of200 and order27/22of200 seeds0/1 both fail sealed developmentgate. Recorded6144updates/196608presentations/zero sleep; noise spans4.5/2.5pp are diagnostic,10pp bars. Initial weights/minibatch-order hashes and chronology absent; DATA seed1 devpool hashes inconsistent with shared scored pool. Ten controlweights absent locally; only existing remote records may supplement digest verification, no rescore. No scientific promotion/no more composition GPU without fresh hypothesis/protocol.

2026-09-30 04:16 UTC actual cache diagnostic rc0, CUDA/optimizer0: five smallfiles match recordedSHA and same-model blobs. model.safetensors resolves hub/blobs/02/0223e4373a31a728f6e306f68fc58ad4b41e86054badb87928b7a491437a8b99 outside modelrepo; diagnostic refused read (actualSHA null). V5 same-repo guard must still block. Need exact-target digest diagnostic and bounded loader-policy decision; no hash bypass/cache copy/precision change.
