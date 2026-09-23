**Draft — baseline v2 controls · 20 September 2026 · Track A validation only**

Status: design draft, not frozen and not launch authorization. Preserve all v1 sources, hashes, checkpoints and registrations. No training until the Mac's registered waves are idle and the resource guard admits the job. This draft complements, rather than changes, A-ev.

**Question.** Is the baseline's failure to learn attribute lookup affected by the initialization mismatch, supporting-line supervision, or their interaction? A model that cannot fit ordinary lookup cannot yet adjudicate length composition.

**Fixed comparison.** Implement an additive v2 entry point with the same 69-token vocabulary, END=68, line mask, causal row encoding, width 48, three layers, four heads, hidden width 208, tied embeddings, loss masking and greedy scorer. No changes to query format, embedding decay, positions, depth or curriculum in this experiment.

| Arm | Linear initialization | Supporting-line loss |
| --- | --- | --- |
| I0-H0 | normal std 0.02 | 0 |
| I0-H1 | normal std 0.02 | 0.5 |
| I1-H0 | same draws rescaled to std 1/sqrt(3*fan_in) | 0 |
| I1-H1, primary fairness control | same draws rescaled to std 1/sqrt(3*fan_in) | 0.5 |

Rescale only Linear weights, exactly as the operator; do not rescale embeddings or biases. Supporting-line loss uses the already checked last-layer, head-mean targets at positions predicting each result, excluding END. This matches availability of line labels but not the operator's internal allocation of evidence loss across three reads.

Seeds: 1200, 1201, 1202, paired across arms. World RNG namespace: `astra-baseline-v2-fit:seed`. The same worlds, questions, targets and ordering must be identical across the four arms. Independent model and data RNGs. Freeze their complete starting states and source hashes. Do not substitute a successful dev seed.

Use 6,000 updates, 16 worlds × four questions per update; six people; uniform requested hop length 1–3; relation 10 excluded as a terminal at lengths ≥2. AdamW lr 1e-3, warmup 100, decay during the final third to 1e-4, betas (0.9,0.99), epsilon 1e-8, weight decay 0.1 on all parameters, clip 1.0. Final checkpoint only. A-ev or other historical runs are contextual, not substitutes for paired cells unless their complete recipe/stream matches.

Timing must be measured on a throwaway forward/backward check when idle; execute resumable chunks ≤1,200 seconds with full optimizer/RNG restoration if the fixed update budget cannot fit a wave. A timeout is incomplete, not an architecture failure. No outcome-dependent extensions. Record actual matmul FLOPs, padding, wall time and inference cost. Do not claim equal total System S compute until dispatcher costs are counted.

**Validation and fit gates.** Before training, generate separate development-fit and untouched confirmation validation panels under the shared protocol in [the validation draft](/Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/18-validation-and-operator-swap-v2-preregistration-draft.md). Add every panel signature to exclusions. Fit panels: 512 independently drawn questions per cell, six-person full stories, k=1/2/3 with practised terminal relations plus k=1 held-out terminal relation. Equal-relation one-hop diagnostic strata must be reported.

Every 100 updates log training accuracy separately for intermediate people, terminal answers and END, plus exact sequence accuracy. Report loss and gradient norm. Aggregate token accuracy is secondary. Evaluate the fixed development-fit panel at the final update only for the gate; no checkpoint selection.

A seed clears the prerequisite only if one-hop final answers and exact greedy sequences each reach 487/512 in both one-hop fit cells, and practised k=2/3 strict sequences and answers each reach 461/512. Also report per-token teacher-forced metrics. Failure means “lookup/sequence fit prerequisite failed under this recipe,” not “more training would necessarily fix it.” Each seed and arm is reported; no averaging rescues failure.

Only a preregistered, fit-qualified configuration proceeds to untouched length-generalization confirmation. To avoid selecting the primary retrospectively, nominate I1-H1 now; other arms are causal controls and exploratory for generalization. If I1-H1 fails fit, stop the comparison claim and register the next diagnostic separately. Do not silently nominate a different passing arm.

**Interpretations.** The initialization contrasts are I1-H0 versus I0-H0 and I1-H1 versus I0-H1; hint contrasts hold initialization fixed. All four failing leaves the startup cause unresolved. Better fit with rescaling implicates this initialization intervention, not every proposed gradient explanation. A hinted baseline failure still does not isolate decomposition from depth, computation, masking or position design.

**Separate next diagnostic, not folded into the four arms.** After fit succeeds, compare the fixed learned position package with a package using fixed sinusoidal within-row/question/output positions, with all other settings identical and an explicit small parameter-count difference. Same-length fit is a prerequisite in both. This removes untrained position-table rows but does not guarantee extrapolation or equalize the supplied controller features. Freeze fresh confirmation data after this design is finalized, before outcomes are read.

If even I1-H1 cannot fit one hop, register a finite small-story, one-hop overfit check with permuted entity/value assignments before launching more long runs. That check distinguishes a remaining expressivity/optimization difficulty from an evaluation bug; it does not itself certify generalization.

**Preflight requirements.** Cache/dense logits AND gradients; causal no-future leakage; loss-target shift; mixed question-length decoding; END cap; row-permutation invariance; evidence targeting; fixed paired batches; rescaling exactly as specified; no training/panel signature overlap; fresh-run outputs; dependency and checkpoint hashes. These are additions, not edits to frozen tests or registrations.

