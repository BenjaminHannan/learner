# Revised request accepted — 2026-09-27

The updated task makes Ben's learned scratch-card store the first candidate unless the diagnosis clearly justifies another choice and Ben selects it. Scratch content, write timing, and retrieval must be learned from the task objective, with no solver-generated card labels or hand-written lookup/address rules. The old single-answer supervision mismatch remains a diagnostic finding; it is not bundled into the scratch-store change.

Before Step 2, a resized fixed-env baseline must reach at least 95% exact stored-answer accuracy on its four-number practice hands. The first width128/20,000-step diagnostic did not meet that gate. A new diagnostic holds 100 hands out of the original 1,062 for dev, trains on 962, and creates fresh sums/grids dev items. None of the original 300 test hands is used for further tuning.

Disclosure: under the first task version, the old 300 four-number hands were explicitly a development panel, and this task already scored them once (2/300), alongside same-seed generated sums/grids. This prior exposure cannot be undone. The revised protocol reserves the original 358i test files for registered scoring; its N1 panel is previously seen, and the new post-registration five-number panel is the cleanest test. No fresh five-number sealed panel exists yet. Old numbers5 seed35832 will be report-only.

New protected scope: do not read the rsn358k store experiment or touch the rsn358u folder. Neither is our experiment or baseline. Training/evaluation remain local M3 Pro MPS jobs, sequential, with fresh paired seeds and usage checks.

This note changes no pushed PASSMARKS: none has been created or pushed yet. The existing RESULTS.md describes only the first diagnostic. New results will be added with their actual evidence; the original diagnostic remains archived.

## Ben's card choice and ablation requirement

Ben chose option1: small pieces of the model's internal state. A brief readable-note preference was explicitly reversed by "actually do 1". The candidate is therefore a learned latent scratch-card store, not solver-labelled calculation text.

Ben then added: "score the net again with its cards wiped at test, and the score should drop." This authorizes a preregistered intact/wiped comparison on the test panels. Both conditions are evaluated in one fixed post-training sweep on frozen checkpoints, with no tuning after the results. Wiped means zero K and V before EVERY card read from round0 onward; learned weights, address seeds, controller and inherited own-stop rule remain unchanged. Merely resetting once at the start would not be an ablation because both arms already start empty.

Proposed additional mark N5 (not yet pushed PASSMARKS): candidate intact minus wiped mean >=10/300 on numbers4 and >=5/300 on the new numbers5; strictly positive on >=75% of seeds for each panel. Intact candidate must still satisfy N1–N4 against the baseline. Passing the wipe comparison demonstrates beneficial dependence on stored card content, not that the card contents encode arithmetic or that backtracking was learned. Those stronger claims remain untested.

## Subsequent architecture request

Ben then asked to add both scratchpad and bookmark functions, followed by: "come up with a design for htat then compare against just the first and lmk what's better". COMBINED-CARD-DESIGN.md specifies a shared tokenwise card bank supporting additive scratch use and a soft partial restore of 16 of the existing 256 state coordinates. Calculated additions: 13,187 weights combined (0.8009%), 12,930 for the matched scratch-only design (0.7853%). A fair empirical architecture comparison needs separately trained variants; disabling a mode in the combined checkpoint measures dependence only. No measured winner is claimed and no extra registered arm has been silently added.

The combined store's wipe includes occupancy as well as keys and values: zero K,Z,m before every read. This keeps empty cards an exact no-op for both modes. Proposed N5 thresholds remain unchanged. The baseline gate and preregistration requirements still apply.

## Final selection: scratchpad-only

Ben subsequently chose "ok, do scratchpad only". SELECTED-DESIGN.md is now authoritative for the candidate. It uses learned projected tokenwise payloads and a tied biasless decoder, with no bookmark operation or occupancy mass. Wipe K,V before each read. The combined state-split and three-gate design above remains discussion history only. The adequately fitted baseline has now crossed the practice prerequisite (95.53% at20k; preserved96.99% checkpoint at25k) while dev numbers4 remains0/100; DIAGNOSIS.md records this before candidate implementation.
