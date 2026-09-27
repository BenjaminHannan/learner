# Handoff as pasted by Ben (Thread manager thread, 2026-09-27 21:34:39 UTC, message cmsg_01FuvegZXjMmeUzStiEFVnEW7UVne62bXChjECuV3jQenc)

Ben's covering instruction (21:33:55 UTC, cmsg_01FuvegZXjMmeUzStiEFVnEW7MBRKAg9WYFXj8g2bce8yz), verbatim:

> Implement and run the experiment in the attached handoff.
>
> Start by checking the existing repository implementation. Make the smallest change needed for random versus blank-count grid replay. Run the implementation checks, freeze the protocol and decision rules, then run the two-seed pilot on already-authorized compute.
>
> Keep everything else fixed. Do not add methods, change the model, or start another review round. Resolve routine details from the code; report any material blocker rather than silently changing the experiment.
>
> Return the actual per-seed results, which old successes were lost, whether addition and maze learning suffered, the registered verdict, and the code/artifact locations. Do not launch paid work or a larger confirmation study without existing authorization.

The handoff, verbatim:

---

# Claude implementation handoff: test random versus blank-count grid replay

## Assignment

Work in Ben's existing small puzzle-reasoner repository. Implement, validate, preregister, and run the two-arm pilot below on already-authorized compute. This is a testing assignment, not another adversarial review or literature survey.

The question is: with the SAME model and SAME amount and timing of old-grid practice, does choosing grids with more blank cells preserve grid performance better than choosing grids randomly?

Do not add current-loss scoring, MIR/damage prediction, distillation, extra experts, frozen weights, scratchpad changes, a different replay schedule, or additional experimental arms. Resolve routine implementation details from the repository rather than asking Ben to design them. Report a material blocker instead of silently substituting a different experiment.

The protocol below is an untested pilot. Its numerical decision margins are practical screening rules, not statistical guarantees. No new result is supplied by this handoff.

## 1. Locate and verify the existing implementation

Start with these paths, which a previous audit reported; locate their actual equivalents if they have moved:

- artifacts/codex-autoroute-20260927/RESULTS.md
- artifacts/codex-autoroute-20260927/run_experiment.py
- artifacts/codex-autoroute-20260927/auto_model.py
- artifacts/codex-autoroute-20260927/hard_replay/RESULTS.md
- scripts/claude_rsn358a_envs.py
- scripts/claude_mirreview_grid_forgetting.py

Use the dense looping model WITH THE LEARNED FRONT END from the replay-allocation experiment. Do not substitute the older supplied-puzzle-kind-embedding model. Count its actual parameters, including the front end.

Reported setup to verify, not blindly overwrite into code:
- Approximately 1.65 million parameters; two transformer blocks, width 256, eight attention heads; feed-forward layers 256 -> 1024 -> 256.
- The same blocks update a carried state repeatedly.
- Training: 1–16 total rounds, gradients through the last 1 to min(total rounds, 6) rounds. Preserve the actual sampling distributions.
- Batch 64, FP32, AdamW, peak learning rate 0.001, betas (0.9, 0.95), weight decay 0.1, gradient clipping at 1.0.
- Fresh optimizer each phase; 100-step warm-up, then cosine decay to zero.
- Reported loss: answer-cell cross-entropy plus 0.5 times stopping-head loss, averaged over gradient-bearing rounds. Preserve the existing masks, reductions, and targets.
- Reported evaluation: from round 3, stop when stop probability exceeds 0.5 and the answer has been unchanged for three rounds; otherwise read at round 48. Preserve the actual implementation.
- Grid training/replay reportedly draws transformed presentations from 3,000 fixed base puzzles per size, created at run start. Transformations include row/column permutations, transposition, and symbol renaming. Do NOT replace these with unlimited newly generated bases.

Record verified code/configuration and discrepancies in the experiment manifest. Material discrepancies affecting the intended comparison must be resolved before training; do not hide them.

Motivation, supplied by a prior repository audit and not independently reverified by this handoff:
- Under later replay, grids5 scores were approximately 195.7 after grid training, 125.8 after addition, and 167.0 after mazes.
- Among initially solved 5x5 grids, final losses were about 0.4% for fewer than 10 blanks versus 33% for at least 16 blanks.
- This association concerns final forgetting, not a demonstrated cause or a successful replay intervention. Whether it applies to the after-addition loss is untested.
- More-blank replay has not been demonstrated to help. Easy practice may still be useful, and repeated selection may concentrate on a small number of bases.

## 2. Freeze the experiment before outcome inspection

Create a new, clearly named experiment directory without overwriting earlier experiments or unrelated work. Record the starting commit, patch, configuration, environment/backend, and code hashes.

Choose and register two fresh training seeds before inspecting any model scores. Do not select seeds for favorable Phase-A performance. If a seed is used elsewhere, choose an unused one before launching the pilot and record the rule.

Freeze the protocol, exact schedule, seed map, evaluation-generation procedure, and decision rules before generating the new sealed evaluation panels. Record panel hashes before training. Smoke tests use separate disposable data, not the sealed panels.

Do not change settings, stop for apparent success, replace weak seeds, or add arms after seeing results. An infrastructure failure may be resumed from a valid checkpoint without changing the protocol; document it. A broken comparison is invalid/incomplete, not a negative scientific result.

## 3. Two arms; identical training schedule

Use arm names `random` and `blank` to avoid confusing the blank-selection arm with Phase B.

Phase A — learn grids:
- 2,500 grid batches, original 4x4/5x5 size mixture.

Phase B — learn addition with grid replay:
- 2,500 total real updates.
- 2,375 addition batches, original 1–4 digit mixture.
- 125 grid-replay batches.

Phase C — learn mazes with grid and addition replay:
- 1,500 total real updates.
- 1,225 maze batches, original 5x5/7x7 mixture.
- 200 grid-replay batches.
- 75 addition-replay batches.

Copy the EXACT late-replay slot placement from the existing implementation, not just these totals. Do not invent a new evenly spaced approximation.

For each seed, train A ONCE and save the complete model/buffer state and required reproducibility state. Branch `random` and `blank` from that identical A checkpoint. Keep the same training base pools. Reset optimizers at phase boundaries exactly as the baseline does; do not carry Phase-A optimizer moments into B if the baseline resets them.

Both arms train all the same normally trainable parameters. There is no model growth or freezing.

## 4. The only intervention: selection inside grid-replay slots

At each scheduled grid-replay slot in B or C:

1. Draw the ordinary grid size using the unchanged baseline distribution. Every batch remains single-size.
2. Generate 256 candidate presentations of that size using the original training-base sampler and transformations. The paired arms receive the same candidate pool for the same seed/phase/slot.
3. Select exactly 64 candidate indices:
   - `random`: uniform selection without replacement from the 256 indices.
   - `blank`: select the 64 with the largest number of blank puzzle cells, with preregistered random tie-breaking.
4. Apply ONE ordinary training update on those 64 puzzles.

Count blanks using the generator's actual puzzle-cell blank mask or its verified equivalent. Exclude symbol legends, padding, delimiters, and other non-puzzle tokens. Selection must not depend on model predictions, target-answer difficulty, test performance, or hand-supplied test-time task labels.

Preserve the original base-sampling behavior. Distinct candidate indices may share a base if the baseline samples bases with replacement. Do not silently impose base deduplication, diversity limits, an easy-example quota, or a random/selected mixture. This pilot tests pure top-64-of-256 selection within the ordinary size draw.

The chosen grids receive the existing training objective, round sampling, optimizer, and batch construction. Do not give `blank` extra optimizer updates or auxiliary losses.

Addition-replay slots in C remain ordinary random addition replay. All new-kind batches remain unchanged and matched across arms. There are no candidate-model scoring passes or shadow updates in this experiment.

## 5. Pairing and implementation checks

Use separately reproducible random streams for model initialization, training-base creation, new-kind batches, grid size/candidate draws, addition replay, selection/tie-breaking, and real training-round/stochastic choices. The implementation may use an equivalent deterministic seed map keyed by seed, phase, logical slot, and stream purpose.

Candidate generation and selection must not shift future addition/maze examples or training-depth draws. Record stream seeds and enough batch/pool fingerprints to verify matching. Backend nondeterminism must be disclosed, not mistaken for a different A starting point.

Before the full pilot, run small disposable checks establishing:
- Both continuations load byte-identical A parameters/buffers and the same bases.
- Random selection is uniform over candidate indices and selects exactly 64.
- Blank selection picks the correct top counts, including cutoff ties.
- Blank counting ignores non-board tokens and remains correct under the allowed transformations.
- Selected and unselected targets still pass the existing generator/answer checks.
- Replay counts and exact slot positions match the frozen schedule.
- Real non-grid batches, size draws, and training-round streams match across paired arms despite different selected grids.
- Selection has no side effects on the model, optimizer, or unrelated random streams.

Do not turn these checks into an extra training study. Inspect the actual candidate/base blank-count distribution and log it; do not change the policy because the distribution is inconvenient.

## 6. Evaluation: measure retention, not only final recovery

Use fresh sealed panels from evaluation streams separate from training and candidate generation. Aim for the registered 200-item panel per category under the existing evaluation distribution:

- grids4, grids5, grids6
- sums1, sums2, sums3, sums4, sums6
- maze5, maze7

Use the same panels for all paired arms and seeds. Keep extrapolation (grids6, sums6) separate from trained-size performance.

Audit training/test overlap, including equivalent grid presentations under supported transformations. Different random seeds or base IDs alone do not prove independence. State exactly what the audit verifies and any limits; do not change training generators silently to obtain a cleaner claim.

Record distinct maze instances and duplicate multiplicities. Report the registered panel score and unique-instance diagnostics separately when duplicates occur; do not portray repeated puzzles as independent test cases or silently replace the evaluation distribution.

Save A, B, and C checkpoints. Only score the sealed panels after all pilot training is complete; do not use intermediate sealed-test results for checkpoint choice or adjustments.

PRIMARY OUTCOME:
Whole-puzzle grids5 accuracy immediately AFTER PHASE B, using NORMAL LEARNED STOPPING.

Record both total accuracy and individual correctness transitions. For grids at B and C:
- Lost: correct after A, wrong at that later boundary.
- Gained: wrong after A, correct at that later boundary.
- Retained: correct at both.

For addition retention at C, use B as the acquisition reference. Report raw counts, counts per 200, and loss as a fraction of previously correct cases where defined. New successes must not conceal lost old successes.

Report grids4/grids5 at A, B, C; each trained addition length after B and C; final maze5/maze7; and extrapolation separately. Report grids5 losses by blank-count group (<10, 10–12, 13–15, >=16) at BOTH B and C.

Fixed-round, any-round, and stopping-round diagnostics may explain errors, but must not replace normal-stopping scores. Use existing reliable evaluator support and record additional evaluation cost; do not expand this into a new stopping-method experiment.

## 7. Fixed pilot decision rules

Let delta_s = grids5_after_B(blank, seed s) - grids5_after_B(random, seed s), measured as correct answers out of 200.

ADVANCE this specific policy to a separately authorized confirmation study only when:
- Mean delta across the two seeds is at least +10/200.
- Delta is positive in both seeds.
- In each seed, `blank` is no more than 5/200 below paired `random` on grids4 after B and C; grids5 after C; each trained addition length after B and C; and maze5 after C.
- In each seed, maze7 after C is no more than 10/200 below paired `random`.
- Mean sums4 acquisition after B in `blank` is at least 195/200.

DEPRIORITIZE this exact policy when:
- Mean delta is at most -10/200 and both seeds decline; OR
- The same protected endpoint exceeds its stated relative harm margin in both seeds.

OTHERWISE: INCONCLUSIVE.
Mixed signs, small improvements, a lone guardrail miss, or weak acquisition in both controls and treatment do not establish equality, reliable superiority, or universal failure. Do not automatically add seeds or tune selection strength to obtain a pass.

These are spending/confirmation screens, not significance tests. Keep the two seed results visible; do not count hundreds of puzzle outcomes as hundreds of independent training runs.

Report system readiness SEPARATELY from selector benefit:
- Existing final grids5 bar: mean at least 180/200 and each seed at least 160/200.
- Report addition acquisition, final addition retention, and maze tolerances separately.
- As a report-only proposed close-retention benchmark, show whether each trained-size panel loses no more than 10 previously solved puzzles per 200 at every later measured boundary. Grids reference A; addition references B. This is a proposed benchmark, not an established user tolerance or an extra pilot advancement gate.

A net accuracy gain without reduced loss of previously mastered puzzles must be described accurately. A final-only gain is a recovery result, not evidence that the intermediate collapse was prevented.

## 8. Compute and artifacts

Planned real training work:
2 shared A prefixes x 2,500 + 4 B–C continuations x 4,000 = 21,000 optimizer updates.

That excludes smoke checks, candidate generation, evaluation, and logging. No measured wall-clock or rental estimate is supplied. Measure actual overhead; this is not an equal-compute efficiency claim.

Use available local/free resources by default and honor existing resource limits. This handoff does not authorize new paid spending. Any already-authorized rented job must respect the reported $4-per-job ceiling and any project-wide budget; do not split work into multiple jobs to evade authorization. Do not automatically launch six-seed confirmation or a different method.

Keep reproducible, compact artifacts in the new experiment directory:
- Frozen PROTOCOL.md / PASSMARKS.md, configuration/seed manifest, code hashes, and patch.
- Verified model/optimizer/generator details and preflight results.
- Shared A and both arms' B/C checkpoints, with sufficient state for valid recovery.
- Per-grid-replay candidate regeneration keys or compact pool records, base IDs, blank counts, and selected indices.
- Per-base selection counts and coverage by phase and size; candidate versus selected blank-count distributions.
- Per-puzzle phase-end correctness, normal stop rounds, and available diagnostics.
- Per-seed scores, lost/gained counts, every guardrail result, measured runtime/resource use, and any protocol deviations.
- RESULTS.md with one of ADVANCE / DEPRIORITIZE / INCONCLUSIVE, or INVALID/INCOMPLETE if the comparison could not be completed correctly.

No need to save every internal latent state. Preserve earlier experiments and unrelated work.

## 9. Report back to Ben

Start with a plain-language result, then a compact per-seed table containing:
- Grids5 after A, B, C for each arm.
- After-B paired difference and individual old-grid losses.
- Sums4 after B and C.
- Maze7 after C.
- Decision and any failed protections.

Provide exact commands, artifact locations, and hashes. State what actually ran, what is only planned, and any remaining limitations.

A win means this specified grid-specific practice rule helped in this pilot. It does not prove indefinite learning, a better architecture, autonomous skill discovery, or best use of compute. A loss is not a refutation of all targeted replay, current-loss selection, or MIR.

Begin with repository verification and the minimal selector patch, then the smoke checks, registration, and the pilot. Do not start another design/review loop.

## Provenance

This handoff implements the latest supplied two-arm R-versus-B review, particularly its protocol, after-addition primary outcome, paired-seed design, and practical decision rules. Repository details and historical measurements are attributed to the supplied Claude audit dated 2026-09-27 and must be checked against the repository. Implementation instructions above operationalize that plan; they are not new experimental findings.
