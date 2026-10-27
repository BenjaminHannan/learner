# Fair baseline — one ordinary transformer that writes out its reasoning (written 2026-09-20, before any registered baseline run)

## The question

System S answers the frozen v3 panels by composing two trained pieces: a 79,316-parameter **lookup transformer** that resolves one canonical 4-token query `[QUESTION, entity, relation, ANSWER]` against a story, and a 15,522-parameter **learned dispatcher** that decides, by final-answer reward alone, which query to issue next and when to stop. Registered result: **≥ 59/64 answers with exact paths on every one of the 25 cells, in 3/3 seeds**, including hop lengths 4–8 that were never trained and a terminal relation (10) that never ends a multi-hop training question.

The obvious objection is that the decomposition is doing nothing a plain model could not do. So:

> **Does a single ordinary decoder-only transformer of the same total size, trained on the same data, and *allowed to write out its intermediate reasoning steps*, reach the same panel marks?**

This is a baseline, not a rival system. Every judgement call about its design was made in its favour, and each one is written down below. If the baseline passes, S's decomposition is not what produced the result and should be reported as unnecessary. If it fails, the failure is informative only to the extent that the matching below holds — which is why the mismatches are listed as prominently as the matches.

## The baseline

`scripts/fable_baseline_transformer.py`. Input is one sequence:

```
story rows, flattened   [3 ent rel val filler.. 7] [3 ent LINK ent filler.. 7] ...
then the question       [4 ENT op_1 .. op_k 5]
then the output         steps mode:  e_1 .. e_{k-1} y END      answer-only:  y END
```

The grammar's existing NEWLINE token 7 already terminates every rendered row and is reused as the row separator; no new separator id was needed. `END` is a **new id 68** (vocabulary 69); ids 0–67 keep their exact meanings. Next-token cross entropy is applied to the **output part only**. Decoding at test time is greedy, capped at 12 emitted tokens; the model must emit `END` itself, and a run that does not is a failure.

Architecture: pre-LN, causal attention, GELU MLP, tied embeddings, no dropout. **width 48, 3 layers, 4 heads, MLP hidden 208.** Primary (`line`) variant: **94,629 parameters, 0.22 % below S's 94,838.**

Training regime, matched to S's lookup training: 6-person worlds from the v3 builder, 16 worlds × 4 questions per update, hop count uniform over {1, 2, 3}, terminal relation uniform over {8, 9, 10} at one hop and {8, 9} at k ≥ 2 (asserted: relation 10 is never the terminal relation of a multi-hop training question), chains pairwise distinct at k ≥ 2, every question's visible semantics checked against the panels' forbidden set. AdamW, lr 1e-3 with 100-step warmup then linear decay to 1e-4 over the last third, betas (0.9, 0.99), weight decay 0.1, gradient clip 1.0, 6,000 updates, final checkpoint only, no resume, no checkpoint selection. Fresh RNG namespace `fable-baseline-train:{seed}`.

## Arms

| arm | mode | positions | role |
|---|---|---|---|
| **A (primary)** | `steps` | `line` | the registered comparison against S |
| B | `answer-only` | `line` | does writing the steps help at all? |
| C | `steps` | `absolute` | ordinary absolute positions over the flat sequence |
| D | `steps` | `none` | causal mask as the only positional signal |

`--positions` selects a **positional package** — an attention mask *together with* the embeddings that go with it. This is a real confound between arms and is stated rather than buried:

* **`line`** — story tokens attend only inside their own row (causally); the question attends to every story token and causally to itself; the output attends to everything before it. Embeddings: position-within-row, a segment embedding {story, question, output}, an output-step index. This mirrors S's lookup encoder, which encodes each line independently, has within-line positions and **no inter-line order**. A consequence, tested: this variant's logits are exactly invariant to permuting story rows.
* **`absolute`** — plain full causal mask over the whole flat sequence plus ordinary learned absolute positions.
* **`none`** — plain full causal mask, no positional embedding at all.

A and B differ only in the output target, so B is a clean ablation of the chain of thought. C and D differ from A in mask *and* embeddings at once; read them as positional *packages*, not as isolated position ablations.

## Pass marks — identical to S's, every seed separately, never averaged

The frozen panels at `artifacts/fable-dispatcher-v3-20260920/panels`, manifest sha256 `5c9b4507cf4197beccd933d2cb27b424cbbec13bdbb0f774d8b3bd9ca83867e7`, verified at score time (the scorer refuses any other manifest without `--allow-other-panels`). 25 cells × 64 units.

* **answers ≥ 58/64 and strict path ≥ 58/64 on every cell**, for each of seeds 0, 1, 2 independently.
* *answer correct* = the token emitted immediately before `END` equals the interpreter's answer. No `END` inside 12 tokens is a failure.
* *strict path* (steps mode) = every emitted token equals the truth chain's results **and** `END` comes immediately after the answer. In answer-only mode strict degenerates to "exactly `y END`", so strict there carries no path information and must not be compared with A's strict column.
* Pair cells (k = 5 held-out changed-link / changed-value / irrelevant-edit) count a unit only when **both twins** are correct; the irrelevant-edit cell additionally requires the twins to give **identical** answers (reported as `unit_pass`).
* The unseen-length claim rests on k = 4…8 only. k ≤ 3 is in-distribution for length (the held-out relation is still unseen at depth ≥ 2).
* A time-capped or incomplete run is a failure, not a partial result.

## What is matched, and what is not

**Matched.** Total parameters (A: −0.22 %; D: −2.0 %). Training distribution, world builder, question builder and interpreter (imported from v3 read-only, never edited). Updates (6,000), batch shape (16 worlds × 4 questions), optimiser family, clip, final-checkpoint-only discipline, seeds 0/1/2, the semantic-overlap exclusion against the panels, and the evaluation panels themselves.

**Not matched — the baseline's disadvantages.**

1. **No supporting-line attention supervision.** S's lookup transformer was trained with an auxiliary loss pointing its attention at the gold supporting line. The baseline's registered arms get no such signal. `--evidence-aux 0.5` implements the counterpart (push the last layer's head-mean attention from each output-predicting position onto the gold supporting row); it is **OFF in every registered arm** and has only been smoke-tested. If the baseline fails, this is the first thing to try before concluding anything.
2. **No supplied tool interface.** S's dispatcher is handed a canonical query format, entity/operation type validation that rejects malformed actions outright, an "is most recent result" flag and relative-offset features over its own transcript. The baseline gets raw tokens and must invent all of that.
3. **Unrewarded exploration.** S's dispatcher was trained by reinforcement with 16 samples per question; the baseline gets one teacher-forced pass. (This cuts both ways — see below.)
4. **`absolute` arm only:** the position table is sized for the longest panel sequence (640 slots), but 6-person *training* sequences only ever reach ≈ 325 positions while 16-person *panel* sequences reach ≈ 591. **Roughly positions 325–590 of that table are never trained.** That is a genuine handicap of arm C, disclosed, not a bug. It is also why C is not the primary arm.
5. **`absolute` arm only:** its parameter count is **123,669 (+30 % over S)**, because the position table cannot be shrunk without changing what the variant means. It has *more* capacity than S, so a loss by arm C cannot be blamed on size.

**Not matched — the baseline's advantages.**

1. **Gold intermediate entities as output targets** in `steps` mode. These are the same intermediate labels S's lookup training used, but the baseline receives them as a *sequence to imitate*, which is a strictly easier signal than S's dispatcher had (the dispatcher saw only final-answer reward and never a gold action).
2. **Full attention over the whole story and over its own emitted steps at every output position.** S's dispatcher never sees the story at all; it sees only question tokens and its own transcript, and each lookup call sees the story through a single fixed 4-token query. The baseline can re-read any row at any step.
3. **No action-space bottleneck.** S must express every step as a legal query and pay for a wrong one with a wrong answer. The baseline emits tokens directly.
4. **Teacher forcing.** The baseline never has to survive its own mistakes during training; S's dispatcher trained on its own sampled trajectories.

**Compute.** The FLOP convention is the project's own (matmuls only, 2 FLOPs per MAC, ×3 for forward + backward; embeddings, softmax, norms, indexing and the optimiser excluded), so the two sides are comparable. S's lookup training was ≈ 6,000 × 2.85e9 ≈ 1.7e13 matmul FLOPs; **S's dispatcher training FLOPs were never recorded by `fable_dispatcher_v3`, so that part of S's budget is genuinely unknown and is reported as unknown, not estimated.** The baseline's measured cost is printed by the report. The baseline charges padded positions because it executes them; deflating by the padding factor (recorded per run as `padded_story_tokens_per_update` vs `real_story_tokens_per_update`) gives the useful-compute figure.

**Implementation note that is *not* a fairness choice.** The story precedes the question under every variant's causal mask, so story hidden states cannot depend on the question; the story is therefore encoded once per world and served to that world's questions as a key/value cache, and under the `line` mask its rows are additionally encoded as a batch of independent short sequences. Both are exact re-orderings of the same computation. `tests/test_fable_baseline_transformer.py` check 11 verifies the production path against a dense-mask reference that builds the whole flat sequence and writes the mask out in full (max |Δ| ≈ 1e-7).

## Measured before registration (dev seeds ≥ 990001, judged on the TRAINING STREAM only — no panel was ever scored for these)

| dev run | updates | wall | final teacher-forced token acc. | final sequence acc. |
|---|---|---|---|---|
| steps/line, lr 1e-3 (the registered recipe) | 6,000 | 818 s (7.33 upd/s) | **0.684** | 0.062 |
| steps/absolute, lr 1e-3 | 2,000 | 328 s (6.09 upd/s) | 0.377 | 0.025 |
| steps/line, lr 3e-3 | 2,500 | 355 s | 0.367 (never left the plateau) | 0.021 |

Wall time is **not** the problem: 6,000 updates of the primary arm take 13.6 minutes, comfortably inside the 1,700 s cap. Cost is 4.67e9 matmul FLOPs per update (2.81e13 for the run), i.e. **1.6× System S's lookup training per update** — and ≈ 1.1× once the padding charge is deflated.

**Fit is the problem.** The primary arm sits on a ≈ 0.37 plateau (that is roughly "predict `END` in the right place and nothing else") until about update 1,500, breaks out, and is still climbing steeply — +0.13 token accuracy per 1,000 updates between updates 4,000 and 5,000 — when the scheduled decay to 1e-4 flattens it at 0.684. **It is under-trained at the matched budget, not stuck.** lr 3e-3 is strictly worse (it never leaves the plateau), so the learning rate is not the lever.

Nothing was changed on the strength of this. The defaults stay at 6,000 updates and lr 1e-3, exactly matching S. The options, smallest first, for whoever registers the runs:

1. **`--evidence-aux 0.5`** — costs ≈ 10 % more wall time and closes mismatch 1 below (the supporting-line attention supervision S's lookup had and the baseline does not). This is the smallest change that *increases* fairness rather than spending extra compute.
2. **More updates at the same recipe** — 24,000 updates ≈ 55 min per seed (needs `--time-cap 3600`). This breaks compute matching 4:1 in the baseline's favour and must be reported as a separate, disclosed arm, not as "the" baseline.
3. Both.

A baseline that merely ran out of budget answers nothing, so registering arm A at 6,000 updates **alone** would be a weak test. The recommendation is to register the matched 6,000-update arms as specified *and* a disclosed over-budget arm, and to report them side by side.

## Readings

* **Baseline passes every cell in 3/3 seeds, arm A.** S's two-piece decomposition is not what produced the length generalisation. Report that plainly; the interesting question becomes which of the baseline's advantages (gold step targets, full re-reading) carries it.
* **Baseline passes k ≤ 3 but falls off at some length.** The comparison is then about *where* each system breaks, and the first failing length per arm is the headline number, not a pass/fail.
* **Baseline fails broadly.** Before concluding anything, run arm A with `--evidence-aux 0.5` (mismatch 1 above). Only if that also fails is "the decomposition is doing work" a defensible reading, and even then it is a claim about *this* baseline at *this* size and *this* budget, not about transformers.
* **Arm B ≈ arm A.** Writing the steps is not what matters; then arm A's advantage over S is re-reading, not chain of thought.

## Fable's predictions

Written 2026-09-20 by Fable before any registered baseline run; no panel has been scored for any baseline model.

### Operator decisions (Fable), fixed before launch

1. **Arms registered now:** A, B, C, D exactly as above (6,000 updates), plus
   **A-long: `steps`/`line`, 11,000 updates, `--time-cap 1790`**, folder `steps-line-11k`. Reason: System S's training was two phases
   (lookup ≈ 840 s + dispatcher ≈ 805 s per seed ≈ 1,650 s wall). 11,000 baseline updates ≈ 1,500 s, so A-long is inside S's *combined*
   wall-clock budget and inside the project's 30-minute wave rule. A-long is the arm I will treat as the fairest single comparison; A (6,000)
   is matched to S's lookup phase only and the dev curve says it will be under-trained.
2. **Fit gate (decides how a failure is worded, never whether a pass counts).** For each seed, take the mean teacher-forced token accuracy over the
   last 500 logged updates of `train_log.jsonl`. If it is < 0.95, that seed's failure is reported as **"under-trained — inconclusive"**, not as
   evidence that S's structure matters. A pass counts regardless of the gate.
3. **Evidence-aux arm is NOT registered yet.** Its target row has no correctness test. It will be registered separately (new folder, own
   addendum) only after such a test exists, and only if A-long fails.
4. The 24,000-update arm is not registered (55 min breaks the 30-minute rule). If A-long is gated as under-trained, the follow-up is a
   resumable two-wave version, registered separately.
5. Waves: three seeds of one arm concurrently, at most six heavy processes of mine on the machine. A time-capped run is an infrastructure
   failure only if the machine was demonstrably oversubscribed; otherwise it is a failure of the arm.

### Predictions (every seed separately; pass = the registered marks)

| arm | fit gate | k ≤ 3 seen-relation cells | held-out relation 10 at k = 2, 3 | k = 4…8 | pairs (k = 5) |
|---|---|---|---|---|---|
| A (6k) | fails gate 3/3 (≈ 0.65–0.75) | fail 3/3 | fail 3/3 | ≤ 5/64 every cell, 3/3 | 0–2/64 |
| A-long (11k) | passes gate ≥ 2/3 | pass ≥ 2/3 | **uncertain**: I lean pass in ≥ 1 seed (the last written step is a one-hop lookup from an entity the model itself wrote) but fail in ≥ 1 | fail 3/3; k ≥ 5 cells ≤ 10/64 | ≤ 5/64 |
| B (answer-only) | token accuracy meaningless (2 tokens); | k = 1 passes, k = 2, 3 below mark | ≤ 25/64 | ≤ 5/64 | ≤ 2/64 |
| C (absolute) | fails gate 3/3 | fail | fail | ≤ 5/64 | ≤ 2/64 |
| D (none) | fails gate 3/3 | fail | fail | ≤ 5/64 | ≤ 2/64 |

Why I expect k ≥ 4 to fail even when the fit is good: the `line` package has a learned **output-step index** and learned question positions,
and indices beyond 3 steps / beyond a 3-operation question are never trained. That is the same "keeping your place" problem that made the
dispatcher depend on its two supplied hints. Probability that any arm passes every cell in 3/3 seeds: about 5 %.
If A-long passes k = 4…8, I am wrong about the central claim and S's structure is unnecessary on this toy.
