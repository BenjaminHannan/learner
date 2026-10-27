# Fable dispatcher pilot — preregistration (written 2026-09-19 ~23:00 EDT, before any dispatcher code ran)

Status: FABLE-REGISTERED, NOT Astra-registered. Astra fixed the pass marks (design/v3/17, "Next harder test"); the training method below is Fable's and awaits Astra's audit. Track A toy only. Local CPU, free.

## Question
With a frozen learned lookup operator, can a small learned controller that never sees the story choose its own sub-queries and its own stopping point, from final-answer feedback only, and do so on a program length (three hops) it never trained on?

## Launch rule (fixed now)
Run only if Astra's canonical-operator screen finishes all three seeds and the recursive arm R meets its registered cutoffs on c1, c2, c3 and s3 in every seed (operator adequate on six-person worlds). Dispatcher seed k uses operator checkpoint seed k, final update, weights frozen. If the rule is not met: do not run; report why; spend the night on diagnosis instead. No replacement seeds, no checkpoint selection, final update only, incomplete = failed.

## Arms (seeds 0,1,2 each; ≤6,000 updates; 16 visits/update; per-job cap 1,500 s; each wave <30 min)
1. rl — PRIMARY. Reward = 1 if returned token equals the answer, else 0. No action labels, intermediate entities or evidence. Trained on one-hop and practised two-hop only; zero three-hop; zero held-out compositions.
2. supervised — DIAGNOSTIC ceiling (gold actions on the same 1–2-hop questions). Not the registered test.
3. rl with absolute positions — ABLATION of the relative-position pointer prior I supplied.
Hyperparameters are frozen from a development phase that uses ONLY an exact symbolic stand-in operator, non-registered seeds (≥900001) and training-stream reward; no panel is consulted. The frozen values and every config tried are recorded in dev/ and hashed into the launch manifest before training.

## Pass marks (Astra's, every seed separately; 64 units per cell)
one-hop ≥61; practised two-hop ≥61; held-out two-hop ≥58; three-hop held-out ≥58 answers AND ≥58 full correct paths with a learned stop after the third result; three-hop changed-link, changed-value and irrelevant-edit pairs ≥58 pairs each (both twins correct; identical for irrelevant).

## Predeclared reading
- rl passes every cell in every seed -> shown: learned decomposition and stopping over a supplied tool interface on this toy, at an untrained length. Still not general intelligence; the pointer-with-relative-offset prior, action validation, 4-call cap and entity/op token classes are supplied.
- rl fails three-hop, supervised passes it -> optimisation failure of final-answer-only learning; capability of the architecture to hold the rule is shown, learning it from reward is not.
- both fail three-hop (but pass 1–2 hop) -> the controller learned length-specific habits; length generalisation is the limit.
- rl fails even 1–2 hop with training reward low -> optimisation failure; nothing learned about generalisation.
- rl passes and absolute-position ablation fails three-hop -> the result depends on my supplied relative-position prior; say so.
- Scores with the symbolic stand-in operator are reported beside the real-operator scores to separate controller errors from operator errors; they never substitute for a pass.

## My predictions (may be wrong; kept either way)
P1: supervised passes every cell in ≥2/3 seeds. P2: rl reaches ≥0.9 training reward in ≥2/3 seeds. P3: rl passes three-hop full-path in ≥1/3 seeds but NOT all three (I expect the registered all-seed success to FAIL). P4: absolute-position ablation gets ≤16/64 on three-hop in every seed.
