# Reasoner road map (sleep research thread, 2026-09-25 02:40 UTC)

Ben, 02:18 UTC: "architect a road map for how you plan to get to better on class". This is the learned
reasoner's lane; the Benchmarks thread owns the whole-model road map and can take this as its reasoner part.
Every step: one change, pass marks sealed first, 2 seeds, a registered FAIL stays FAIL. GPU = BensPC at night
(free) or a rented 5090 (<= $4/job, $30 total cap).

## Where we are (all verified)
- Best learned reasoner: 296 plain, 30.9M. Fresh panel 225 / 217 of 298; transfer 238 / 238 of 300;
  0 invented answers. Counting 12/30, comparing 16/30, three-step 0/30.
- 3x size: rsn-350 and rsn-351 registered FAILs (221 / 218 at best). Size is not the bottleneck now.
- Loop reasoner (the one sleep trains, the one that can "think longer"): never learned its copy phase.
  Cause found on CPU: a large random per-pass vector. rsn-353 (full-size fix) is running on a rental.
- Three-step 0/30 explained: the input slot for step 3 was never trained. rsn-355 (fix) queued on BensPC.

## Stages and gates
| stage | what | gate to move on | status |
|---|---|---|---|
| R1 | loop learns at all (rsn-353) | copy loss ≤ 0.05; fresh ≥ plain − 10 | running |
| R2 | step 3 visible (rsn-355, plain) | three-step ≥ 6/30 both seeds | queued (BensPC) |
| R3 | combine R1 + R2 on the loop | loop three-step ≥ plain's | after R1, R2 |
| R4 | one step per thinking round + "hold" (solver labels which row each round should point at) | three-step ≥ 15/30 without practising it; more rounds never lower the score | code tonight, CPU test |
| R5 | thinking stop token (learned; trained on a frozen net from "has the answer settled?") | ≥ 40% fewer rounds, ≤ 1/30 accuracy loss, rounds track steps not question length | after R4 |
| R6 | anti-shortcut practice: puzzle twins that differ by one fact | blind pair consistency +15 points | code tonight, queue BensPC |
| R7 | depth beyond 3: shared step input lets 4+ step chains be written (raise MAX_HOPS) | practise ≤ 3, answer 4-5 steps above chance | after R4 |
| R8 | sleep trains it: practice school on taught facts + checked creative wins (Fix-sleep plan 360/363) | beats no-sleep, plain extra practice AND scrambled-grade sleep on fresh blind questions | after R4 |
| R9 | grow: 3x then 10x, on the loop, equal tuning for both sizes, fresh blind panel after freeze | 3x ≥ 1x + 10 on the fresh blind panel | after R4-R6 (Ben chose "fix loop first") |
| R10 | English: the loop idea inside MiniCPM5-1B (retrofit), the only affordable route to fluent reasoning in chat | beats the plain 1B on the 331 bank's reasoning rows | after R9 |

## What "best in class" means here, honestly
- Near term (this month): a learned reasoner that beats our hand-written reasoner on fresh blind multi-step
  questions, invents nothing, and thinks longer on harder questions by its own choice. Nobody has that at
  30M with an exact notebook; it's a fair claim to aim for.
- Not this month: beating general LLMs at open-ended reasoning. Our reasoner sees anonymous symbols, not
  words (R10 is the bridge).

## Tonight (Ben asleep, 02:40 UTC)
- BensPC: rsn-355 (step-3 input), then rsn-356 (puzzle twins, R6), both sealed and queued.
- Rental: rsn-353 (loop fix).
- CPU here, free: step-3 preview on small models (plain vs loop, old vs shared input); R4 code + CPU test.
