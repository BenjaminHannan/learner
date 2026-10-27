# AR2: concentrate old-grid replay on grid5

Prepared 2026-09-27. Commit and push this exact document to main before any AR2 model construction, software test, panel generation, throughput probe or training run. Pushed marks are immutable. Repairs must preserve this protocol and be recorded separately.

## Question and exactly one intervention

Can one label-free dense network keep grid5 near its original mastery if its existing old-grid rehearsal is concentrated on grid5? Both arms retain the full-replay timing, counts and optimizer. The candidate changes only the size of grids drawn for old-grid replay in phases B and C: always 5 instead of a uniform draw from 4 and 5. Initial phase A remains uniform grids4/5. All sums and maze practice distributions remain unchanged.

This follows AR1's registered replay-timing experiment, whose six candidate runs have completed and cannot meet M1. AR1 is not this comparison's baseline. Its panels are not reused, and none of AR2's scores or examples has been inspected. The present idea is targeted rehearsal, not a learned sleep controller or an MoE experiment. All grids4 retention after A is **untested** here; stronger grid5 scores cannot establish general preservation across sizes.

The baseline is the same label-free four-context AutoNet used in AR1, trained locally again on the new seeds and panels below. Both arms have exactly **1,646,750 trainable/model parameters** at every phase. Reuse AR1's unchanged AutoNet and sealed e4 import chain; no model copy, frozen expert, teacher, added trainable weight or request cache. The common frontend computes x=token+slot embeddings, q=mean(x over cells), p=softmax(q @ contexts.T / sqrt(256)), then adds p @ contexts. It learns only from answer and stopping losses. No kind-label target or supervised routing map.

## Request, data and seeds

- Inference accepts only rectangular token and answer-slot arrays, starts a blank recurrent state for every request, and uses the same network for every puzzle. No env, phase, kind, size field, target, metadata, filename, batch neighbor or caller-provided skill ID enters inference. Native shape and symbols are visible puzzle content. No handwritten rule chooses a skill or weights.
- Code-generated and code-checked training only, using the original sealed generators/checkers. No model-written training text, blind panel, download, spending, PC, watcher or root notebook access.
- Training seeds **61, 62, 63, 64, 65, 66**. Torch seed is the training seed, practice RNG is 5800+seed, recurrent-depth RNG is 5900+seed. Generate the same original 3,000 Latin bases at each size 4 and 5 before training.
- Final panel seeds, in training-seed order: **927206481061, 927206481062, 927206481063, 927206481064, 927206481065, 927206481066**.
- Separate context-diagnostic seeds: **927206482061, 927206482062, 927206482063, 927206482064, 927206482065, 927206482066**.
- Before writing this file, literal `rg -l --hidden --no-ignore -F` searches for all twelve seeds returned no matches (exit 1, no output), at `date -u` **Sun Sep 27 14:23:55 UTC 2026**. The search excluded .git, root notebook, .env*, .pem, .key, credentials and secrets paths. It returned filenames only, never puzzle contents or keys.
- Per seed, generate 200 unique visible requests each for grids5, sums4 and maze7, in that order, rejecting duplicate token+slot fingerprints; then shuffle the 600 with that same panel RNG. Generate a separate diagnostic set of 100 per kind with its own RNG, unique within itself and disjoint from the final set. Do not require cross-seed uniqueness; report any repeated requests across seeds.
- Reject and count exact visible-input matches between practice and either own-seed panel. Validate every generated target with its code checker, including cached panels. Panels cannot tune architecture, schedule, stopping threshold, checkpoint, training length or any hyperparameter.
- Keep the original shared practice RNG. Always consume the ordinary size choice from [4,5]; on a candidate old-grid batch only, override that size with 5 before generating it. Different sizes consume different subsequent generator draws, so individual later examples can differ across arms. Distributions and counts, not identical post-A examples, are paired. This consequence is disclosed rather than repaired with a second intervention.

## Fixed exposure and optimization

| Arm | A batches | B grids / sums | C grids / sums / mazes |
| --- | ---: | ---: | ---: |
| baseline | 2500 grids4/5 | 250 / 2250 | 75 / 75 / 1350 |
| hard_grid_replay | 2500 grids4/5 | 250 / 2250 | 75 / 75 / 1350 |

Each trajectory has exactly **6,500 optimizer steps, batch 64, and 400 old replay batches: 325 grids +75 sums**. In both arms B replay is every tenth step. In C replay is every tenth step, alternating sums first then grids. Baseline grid batches choose size 4 or 5 uniformly throughout. Candidate grid batches in B/C are all size 5. Sum sizes remain uniform 1–4; maze sizes remain 5 or 7 under the sealed sampler. Record kind-and-size batch counts per phase and require candidate B/C grid4 count zero, grid5 counts 250 and 75. No additional old-example passes, rehearsal, controller training or selection probes.

Fresh AdamW per phase: lr .001, weight decay .1, betas (.9,.95), 100-step warmup and cosine to zero over that phase. Uniform 1–16 recurrent rounds and 1–min(total,6) gradient rounds, mean answer CE +.5 stop BCE over graded rounds, gradient clipping 1. Float32 MPS with four CPU threads. No optimizer or loss change, averaging, early stopping or selected-best checkpoint. Larger replay grids may cost more wall time; report minutes and do not describe equal step counts as equal compute.

Run all twelve trajectories sequentially, baseline first on odd seeds and candidate first on even seeds. Finish all seeds regardless of early scores, except integrity, hardware failure or the user's below-20%-remaining usage stop. Preserve the latest complete update on interruption; never stop another process.

## Evaluation and controls

At A/B/C boundaries, infer all 600 shuffled requests one at a time, without padding or labels. Save predictions for all 48 rounds, stop probabilities and context probabilities before the checker examines oracle metadata. Use the first zero-based round >=2 with stop probability >.5 and predictions equal to both preceding rounds, otherwise round 48. Primary correctness is exact checker correctness at that own stop. Fixed16, any48 and mean stopping rounds are report-only. No earlier snapshot may answer later requests.

Before training and after C, test hidden-metadata poisoning, reversed order, repeated requests and save/reload invariance on two requests per kind: all outputs and stop probabilities must be identical. Check public fields are only tokens and slot, checker absence from inference, a single 1,646,750-parameter model with all weights trainable, and loss gradients reaching learned context and both dense blocks. Unit checks must verify the candidate override affects only B/C grid size and all budgets match. Common MPS training may not be bitwise reproducible even with the same seed; report each arm's A score and any observed divergence without changing the protocol. Inference invariance requirements remain binding.

For report-only context agreement after C, map each of four argmax context indices to its majority kind on the diagnostic set, ties grids then sums then mazes, and report agreement on the 600 final requests. The map never enters inference or chooses weights. Reported agreement is not a requirement that each context be one semantic skill. Native formats differ visibly; no claim covers ambiguous, reformatted or natural-language requests.

Save all raw predictions, final single state_dict, panels and hashes, source hashes, registration/software commits, batch/size/rejection counters, times and RUN-NOTE records with `date -u`, machine and PIDs. Save only latest current state if interrupted. Independently recount every phase from raw predictions and replay all twelve final checkpoints on MPS with the same software. A checksum or prediction mismatch is an integrity failure, not an acceptable numerical score difference.

## Marks, falsifier and precedence

Each panel is out of 200. Let G=grids5 after C, S=sums4 after B, L=maze7 after C, and T=grids5+sums4+maze7 after C, out of 600. Use exact six-seed integer sums for decisions.

- **M1 keep:** candidate mean G >=180 and every candidate G >=160.
- **M2 learn:** candidate mean S >=195 and mean L >=new local baseline mean L minus 10.
- **M3 overall:** candidate mean T >=new local baseline mean T plus 40, with strictly higher T on at least 5 of 6 paired seeds.
- **M4 no leak / budget:** all controls and recount pass; same declared architecture, parameter count, device, precision, software and exact steps/replay counts; recorded sizes match the sole declared intervention.
- **Proved wrong for this targeted-grid5-replay idea:** candidate mean T <=baseline mean T OR candidate mean G <=baseline mean G.

Precedence: missing/interrupted trajectories => **INCOMPLETE**; integrity/budget failure => **INVALID**; otherwise falsifier => **PROVED WRONG**; otherwise all marks => **PASS**; otherwise **FAIL (not proved wrong)**. No threshold relaxation, extra seed, pooling with AR1, post-score baseline floor or redefinition of PASS.

## Predictions and claims

Judgment before any run: PASS 25%, PROVED WRONG 25%, other FAIL 50%. I expect a grid5 benefit of roughly 10–40 items, sums after B near 200, and maze differences of either sign. These are uncertain predictions, not extra marks. Doubling expected grid5 rehearsal at fixed old-grid batch count may help; removing grid4 rehearsal, harder gradients and altered post-A example draws may also hurt. No guarantee follows from the hypothesis.

RESULTS must give the verdict in these exact words, six paired rows, independent recount commands, times, counts, limitations and claims labelled **shown / suggested / untested**, ending with plain words for Ben. A pass would establish this bounded three-format result only. It would not establish lifelong memory, grid4 retention, a learned sleep controller, or anything about the 1B chat model, reader/talker or joined build.

## Execution boundary

All new AR2 files remain below `artifacts/codex-autoroute-20260927/hard_replay/`. Never edit AR1's pushed marks, Python sources or evidence, other threads' scripts, sealed imports, notebook, handoff queues, watcher jobs or PC. Commit and push marks first, then commit and push the implemented, checked code before scientific trajectories. Use main with pull --rebase, no PR or force push. If account remaining usage falls below 20%, stop only our runs cleanly and report incomplete; no reset, credit purchase or rented compute.
