# Presealed diagnostic marks, not a final claim

Seeds 0 and 1. Comparator = per-seed best of independently trained `no_communication`, `joint`, `plain`, `record_only`, `numeric_only`, all with the same symbolic translator/prior, input pools, label access, batch size, updates and learning rates. Exact six-round plain net has untied attention/dense-MLP layers. Joint is recurrent attention/dense MLP without diagnostic programs. Stored sizes are matched to compose within 0.5% by architecture-only parameter arithmetic; single-program controls are smaller and explicitly disclosed. No per-example task-ID, solver or opcode branch exists in the model. Both programs run each paired round.

## One-change causal comparison

`compose` versus `no_communication`: identical registered parameter shapes, same total and active forward program computation, identical initial state_dict (common initialization seed and constructor), same mini-batch schedule. Ablation cuts ALL program-to-board exports and ALL board-to-program feedback. Exports are replaced with zeros after real execution; no alternative output route. The transformer can still use notebook facts. Program weights are inactive for content in the cut arm and get no gradients; this is part of the intervention, not a claim of equal *useful* capacity.

Both target attention and top-2-of-4 MLP experts remain recurrent. Original heterogeneous record/numeric GRUs are diagnostic platform only; success cannot promote GRUs into the target. Raw symbolic notebook table facts reach the board through attention or program latents; only query expression enters the prompt lane. Readout and halt see board only. Output translator sees final board only.

## TRAIN and dev mechanism

Two operations: table lookup and increment modulo 10; noncommuting examples only in composition pools. TRAIN composition order lookup→increment; dev_order increment→lookup is NEVER practiced or supplied during sleep. Primitive TRAIN examples teach each operator at both expression positions, with identity opcode 117 as scaffolding; no two-operator reverse compositions in TRAIN. Training permutation cycle structures (10) and (5,5) are absent from dev: (7,3) and (6,4). Fixed ten-key schema and numerical/equality translation are disclosed priors. Uniform digit labels, randomized record order, distinct table hashes. Structure-only dev retains trained order. Reverse-order dev ALSO changes structure: order effect cannot be isolated from this split alone. No natural-language templates. No official holdout or benchmarks exist in this driver. No checkpoint or stop threshold chosen on dev.

## Budget, sealed before fitting

SPEC.json is authoritative. Per arm/seed: 512 practice updates (16 composed+16 primitive per batch), 64 recent-day updates, then 3 independent sleep draws of 128 updates, each restarted from the same awake checkpoint with a fresh AdamW optimizer. Batch 32, fp32, six full-gradient rounds, learning rates .001 awake and .0002 sleep, zero weight decay, clip norm 1. Stop loss .05 BCE on detached current TRAIN exactness; auxiliary balance .001. Every arm has the same TRAIN-only correctness supervision; plain uses fixed six layers at inference.

Practice per arm: 8,192 composed + 8,192 primitive presentations. Recent wake: 2,048. Each sleep draw: 3,328 recent + 768 earlier TRAIN presentations (26/32 recent). Total per arm/seed: 30,720 presentations; all six arms × two seeds: 368,640. Pools per seed: 640 composition, 640 primitive, 160 recent, 200 dev_structure, 200 dev_order. Fixed final awake checkpoint + three final sleep snapshots; no intermediate dev evaluations. No base checkpoint pretraining is inherited.

Serial runtime, one model/optimizer live at once. Stop at two hours overall or <2 GiB free disk. Keep exact partial evidence; never automatic retraining under a burned run name. Checkpoint estimates: ~1.3 MiB each, 48 model-only files <80 MiB; notebook/JSON/logs and one interruption model+optimizer checkpoint keep job well under 256 MiB expected (estimate, not a measured peak). GPU uses same fp32 code without caches/downloads. Source/SleepMoE context adapter is separate, random initialized, untrained by this job.

Record forward MAC components per phase and arm: executed Linear, GRU and attention/binding matrix work, plus factored pair maps. Explicitly exclude norm/nonlinearities/reductions/equality/router topk/optimizer. Backward = 2× forward is an estimate. Record seconds and memory if available. Equal updates/data and stored size do NOT imply equal compute: joint/plain active MACs differ, single programs smaller. No FLOP/speed or equal-active-weight victory claim. Main causal arm and no-communication active execution match.

## Measured noise provenance and decision

Historical measured seed span: baseline practised-loop maze F_eq 51.00 vs 51.29, 0.29 percentage points, artifacts/claude-fewex-20260927/RESULTS-EQ.md. This is a DIFFERENT task/platform and CANNOT calibrate this experiment. Numeric prototype existing two-seed rank9/rank10 scores were both 64/64 at round12: zero observed span at ceiling, also not usable composition calibration. These historical facts are context only, not evidence of a small composition noise bar.

Local noise is measured in this queued run from both seeds of all five frozen comparator arms. After all training/sleep snapshots are sealed, score comparator checkpoints once per dev split. Before scoring compose, write immutable `sol_compose_NOISE-BARS.json`: measured noise = largest absolute awake control seed gap, in percentage points; bar = max(10, 2×noise + 1). The algorithm, source paths, two seeds, denominator and floor are sealed HERE before any scores; no candidate-dependent bar or comparator. New task noise is currently UNMEASURED; the job cannot issue even DEV PROMISING until this record exists. Two seeds and different per-seed data pools give only a crude, conservative span, not confidence intervals/SE or a final statistical claim.

DEV PROMISING only when BOTH seeds, on BOTH dev splits:

- candidate ≥160 of 200;
- candidate beats strongest control by ≥the split's noise bar;
- learned stop loses ≤4 of 200 against fixed six rounds.

Otherwise NOT SHOWN ON DEV. Never use a rejection from one unlucky/gate-breaking seed. No design is REJECTED by this pilot. No final PASS, scaling, few-example, English, benchmark or generality claim. F_eq/F_few not evaluated: this is a single fixed-budget internal composition pilot.

Sleep is actual TRAIN replay gradient updates, with an external idle file checked every update; removal/SIGTERM/STOP stops at a completed update and saves model/optimizer/RNG. Report mean of THREE sleep draws and margin max(6 counts, 2×SE) for each seed, arm and split, with TRAIN retention beside dev scores. No general sleep pass/retention claim; no unrelated old kinds in this bounded job. No adaptive sleep length or dev-based acceptance. A future final test requires separate fresh holdout, measured relevant noise, ≥2 seeds, and independent recount without reading holdout items. Never rescore any existing holdout.

## Marks self-check

1. Bars exceed measured noise: local formula 2×measured span +1, floor10, recorded before candidate scoring; no composition noise exists yet, historical0.29 is not transferable.
2. Rejections: none permitted; every-seed DEV PROMISING, all other outcomes NOT SHOWN.
3. Fair comparator: higher of all five required controls, fixed in advance, not only the weakest one.
4. Plain control: same stored size ±0.5%; new table structures/order, unique table hashes and uniform answers prevent direct table/example memorization claim. Dev wins still not final proof.
5. F_few beside F_eq: both explicitly NOT EVALUATED; do not claim few-example carry-over or roadmap3/4 completion.
6. Sleep: mean of three draws, margin max(6 counts,2×SE); old-kind sleep gates remain untested.
