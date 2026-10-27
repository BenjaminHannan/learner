# DRAFT: learned scratchpad-only number-puzzle experiment

This draft is not the registration. Before any registered training, replace this with PASSMARKS.md, pin final settings and source hashes in EXPERIMENT.json/SEAL-code.json, commit, pull --rebase, and push to main. No pushed PASSMARKS may subsequently change; addenda can only add.

## Question and single change

Does a learned episode-local scratch-card store improve transfer of the small fixed-env recurrent puzzle net to unseen number hands? Candidate = baseline plus the store in SELECTED-DESIGN.md. There is no bookmark restore, alternative-answer supervision, solver-labelled memory, hand-written numeric addressing, inference search or task-kind input. Final-answer and exact-match halt losses, puzzle generation, core settings and stop policy remain paired.

SHOWN prerequisite: our own resized MPS fixed-env baseline reaches933/962 practice exact (96.99%) and0/100 own-dev at25,000 steps; evidence was committed before candidate implementation. The registered supervisor additionally requires the completed60,000-step baseline diagnostic's final practice exact>=.95. This is an admissibility check, not a registered outcome or early-stopping choice.

## Frozen settings and prediction

Planned: M3 Pro, torch 2.11.0, MPS float32, 2×d256, 8 heads, 60,000 steps, batch128, lr0.0003, warmup1000, Latin pool20,000. Training uses 1–16 rounds with at most6 graded; own-stop evaluation uses48 rounds and the inherited v2 stability/halt rule. All extra parameters count: baseline1,646,494 and candidate1,659,424, a0.7853% difference. Report runtime and available MPS allocation readings. This torch version has no MPS peak-memory API; do not label post-step allocation samples as the true peak. Weight matching does not match compute.

Four paired seeds:9276101,9276102,9276103,9276104. Shared initial core tensors and full training item/round streams must hash identically within a seed. Original1062 four-number practice hands are used in registered runs; the diagnostic962/100 split is exclusively for diagnosis. No five-number practice. Both arms learn sums, grids and numbers together. Alternate arm order across seeds to reduce order effects. All eight final checkpoints must be complete and frozen before the fresh five-number panel is drawn or any registered panel is scored. No best-checkpoint selection or seed replacement for poor performance.

SUGGESTED pre-run prediction: the baseline will fit practice while generalizing poorly. The scratchpad may produce a modest improvement, but final-answer-only retrieval is difficult and I predict it will not clear the strong N1/N2 targets. I predict N3 and N4 will pass; N5 is uncertain and I do not predict a pass. No empirical candidate outcome is known. These predictions cannot alter any marks or stopping decisions.

## Panels and fixed evaluation

- N1: immutable artifacts/claude-rsn358i-20260926/tests/numbers4.jsonl,300 hands. This panel was scored in earlier experiments and in this task under the earlier explicit development permission. It is not novel. No further tuning uses it.
- N2:300 new five-number target24 hands, seed9276501, drawn only after this registration is pushed and all eight checkpoints are frozen. Draw600 unique solvable hands with existing five_hands, exclude hands in old seed35832's300 panel, then take the first300. Abort if insufficient; no adaptive refill. Input-order seed9276502. No training overlap is possible by hand length; verify and record0 overlap. This is the cleanest test.
- N3: immutable358i sums4.jsonl and grids5.jsonl,300 each. Do not substitute older358a panels.
- Report-only: immutable358i numbers5.jsonl (old seed35832),300 items. This cannot satisfy N2.
- Integrity hashes are pinned in EXPERIMENT.json and the generated fresh panel receipt. Parse each of the five panels once for the entire fixed frozen-checkpoint sweep, reuse the in-memory items, and perform no tuning after exposure. Subsequent independent checker recounts read saved predictions and panel data but never rerun model inference.

Score every condition by exact validity at the net's own stop, using the existing checker only after prediction. Store complete48-round prediction/halt traces to independently reconstruct the stop. Stored-answer exactness is diagnostic, not the success measure.

For every candidate, run two fixed inference conditions on the same checkpoint and items: intact; then K,V zeroed immediately before EVERY card read from round0. Keep all learned weights, controllers, static slot-address vectors, total rounds and stop rules. Wiping only at the start is insufficient because the ordinary store already resets per puzzle. Record both conditions on all five panels; only numbers4 and fresh numbers5 enter N5. Both conditions also receive the hidden-field poison test. Baselines receive normal evaluation and poison checks.

## Immutable marks

Each score is a valid count out of300. Means are across all four seeds; paired gaps are candidate minus baseline, or intact candidate minus the same candidate with cards wiped.

- N1, practised size: candidate mean numbers4>=100, AND candidate exceeds paired baseline by>=60 on EVERY seed.
- N2, bigger: candidate mean fresh numbers5>=30, AND candidate strictly beats baseline on at least3/4 seeds.
- N3, no harm: for EACH of sums4 and grids5, absolute candidate-minus-baseline mean difference<=5, AND no seed falls more than10 below baseline.
- N4, no label: every item in both arms gets env0. Changing the hidden kind field among all kind values must leave full logits, raw halts and predictions identical on a representative item from every scored panel, including candidate intact and wiped conditions. Verify tensorization separately on mixed/poisoned items.
- N5, useful cards: on numbers4, mean intact-minus-wiped>=10; on fresh numbers5, mean intact-minus-wiped>=5; on EACH panel the difference must be strictly positive for at least3/4 seeds.

Overall PASS requires all N1–N5 and intact provenance/integrity checks. Complete evidence with any failed mark is FAIL. Missing/inconsistent evidence is INCOMPLETE, not a performance failure or a pass. Preserve each mark's result, even when another already fails.

## What would prove the idea wrong

- Proved wrong: candidate's mean numbers4 improvement over baseline<=10.
- Proved wrong for bigger hands: candidate's mean fresh numbers5 improvement over baseline<=5.
- Proved wrong for useful memory on a panel: intact candidate's mean does not exceed its wiped mean (gap<=0). Record this separately for numbers4 and fresh numbers5. The joint useful-memory claim on both panels is proved wrong if either flag is true. Positive gaps below the N5 thresholds fail N5 without satisfying this stronger null flag.

A card-wipe penalty establishes useful dependence on the stored contents under this intervention. It does not prove arithmetic representations, branching, backtracking, or a neuroscience analogy; activation-distribution shifts remain an interpretive limitation. Improved candidate-versus-baseline scores and a wipe penalty are both required for the proposed claim.

## Audit, failure handling and scope

Pin source/runtime versions and all inference/training/checker dependencies. Audit core gradients each step and accumulated per-card-parameter gradients, distinguishing expected no-future-read one-round cases from missing training paths. Validate episode reset, checkpoint reload, baseline/core initialization pairing, exact wipe equivalence to the same checkpoint's plain core, and the parameter budget before registration. Check no competing GPU-capable ML process before every GPU phase; run one GPU job at a time and never stop others' processes.

Do not retry an interrupted sealed sweep silently. Preserve claim/receipt and partial evidence and document any recovery before resuming. No new architecture, hyperparameters, seeds, revised marks or adaptive panel generation after registration. Stop our experiment work if account usage remaining falls below20%.

Every result is labelled SHOWN, SUGGESTED or UNTESTED. Results include minutes per run, all paired scores, both wipe differences, immutable marks, and an independent inference-free recount. A PASS is evidence only; Ben alone approves a build change. This experiment concerns only the small puzzle nets and makes no claim about the1B chat model or joined build.
