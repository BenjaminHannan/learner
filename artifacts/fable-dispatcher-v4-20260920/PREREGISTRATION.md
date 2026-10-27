# Dispatcher v4 — can the controller LEARN the two bookkeeping features it was handed? (draft, written 2026-09-20 before any registered v4 run)

## The question

v3 showed that a 15,522-parameter pointer/copy controller, trained by RLOO on final-answer reward over 1–3-hop questions in 6-person worlds, executes 4–8-hop questions in 16-person worlds with correct paths and voluntary stopping: every one of the 25 frozen cells ≥ 59/64 on answers *and* strict path, in 3/3 seeds.

That result depends on two features the **executor hands the model for free**:

1. **the recency flag** — every transcript candidate carries an "is the most recent result" bit;
2. **the relative offsets** — every question position carries (this position) − (the previously chosen op pointer) and (this position) − (the previously chosen subject pointer), clipped to [−3, 3], with one "not applicable" slot.

Switch either off and k ≥ 4 collapses to roughly 4/64. So v3's headline is a claim about a controller *plus two hand-written pieces of bookkeeping*, not about a controller.

A reviewer localised the mechanism at `scripts/fable_dispatcher.py` ~line 635 (`Dispatcher.advance`). Without the offsets, the k−1 repeated `LINK` tokens of a k-hop question have **literally identical candidate keys**, and the GRU state update is fed the chosen *tokens* and the result but never the chosen *positions*. The controller therefore has no channel at all that says which LINK it already used; it would have to count through its recurrent state alone. The evidence matches: in the no-offsets seed-0 checkpoint, forcing the correct **operation** pointer lifts 4-hop from 6/64 to 64/64, while forcing the subject or the stop bit does not.

**v4 asks: if both hand-written features are deleted and replaced by mechanisms the model has to drive itself, does the v3 result survive?**

## What changes, arm by arm — one or two changes each, nothing else

Everything else is v3's registered recipe, unchanged: the same frozen lookup operator (`astra_canonical_operator_seed-1/final.pt`), the same world/question builders, training hop counts 1,2,3, 6-person training worlds, 16 visits × 4 questions per update, training cap 4 calls, evaluation cap 16 calls, call cost 0.01 in the learning signal only, RLOO K = 16, entropy bonus 0.2 → 0.02 linear, lr 3e-3 with 100-update warmup, grad clip 1.0, AdamW(0.9, 0.99, wd 0.01), 6,000 updates, final checkpoint only, no resume, no checkpoint selection, seeds 0/1/2, and the **same frozen panels** (`artifacts/fable-dispatcher-v3-20260920/panels`, manifest sha256 `5c9b4507cf4197beccd933d2cb27b424cbbec13bdbb0f774d8b3bd9ca83867e7`, on which the frozen operator answers 7,296/7,296 chain stages, so every failure is the dispatcher's).

| arm | recency flag | relative offsets | learned replacement | parameters |
|---|---|---|---|---|
| `v3-repro` | supplied | supplied | none | 15,522 |
| `reg` | **deleted** | supplied | A: state register with a write gate | 17,635 |
| `ctx` | supplied | **deleted** | B: bidirectional question encoder + selected positions into the state update | 21,922 |
| `reg+ctx` | **deleted** | **deleted** | A and B | 24,035 |

**`v3-repro` is a faithfulness control, not a science arm.** It must reproduce v3's computation exactly. `tests/test_fable_dispatcher_v4.py` checks four things at tolerance 0 on the same batch and seed: byte-identical parameters at construction, identical recorded logits and recurrent states at every step, identical gradients, and an identical AdamW parameter update. If it diverges, every other v4 number is void.

### A. `--learned-register` (replaces the recency flag)

No recency marker exists anywhere: the `recent` embedding is **deleted from the module**, and the feature channel is a constant zero that nothing reads. Two transcript slots holding the same token are now indistinguishable.

Instead the controller owns a state register `r` (one width-32 vector) with a model-controlled write gate. After each call, with `u = [token(result) ; state]`:

```
g = sigmoid(register_gate(u))                  # one scalar per row, logged
r = g * tanh(register_write(u)) + (1 - g) * r
```

The **subject and operation pointer queries** are formed from `state + r`; the stop head still reads `state` alone, as in v3. `r` starts at a learned `register_start` initialised to zeros, so step 0 of an episode is numerically v3's step 0. The model must learn to keep "the person I am standing on" in `r` itself, and then find it by content-matching against the result tokens in the transcript.

Added: `register_start` 32, `register_write` 2,080, `register_gate` 65 = **2,177**; `recent` (64) removed.

### B. `--contextual-positions` (replaces the relative offsets)

No offset feature exists anywhere: `offset_op` and `offset_subject` are **deleted from the module**, and their channels are a constant "not applicable" that nothing reads. Instead:

* a small **bidirectional GRU encoder** (two GRUCells of width/2 = 16, one left-to-right, one right-to-left, over the same per-token step vectors the existing question reader uses) gives each question position a contextual representation `ctx[p] = [forward_p ; backward_p]`, added to that candidate's key exactly where the two offset embeddings used to be added. Transcript result slots get the zero vector.
* **the reviewer's point:** the contextual representations of the two *selected* positions are fed into the state update —
  `step = transcript([tok_s ; tok_o ; tok_r]) + selected([ctx_subject ; ctx_op])`, then `state = GRUCell(step, state)`. The recurrence finally observes *where* it pointed, not only *what* it read.

Added: `encoder_forward` 2,400, `encoder_backward` 2,400, two start vectors 32, `selected` 2,080 = **6,912**; `offset_op` + `offset_subject` (512) removed.

**Why a recurrent encoder rather than learned absolute positions.** An earlier arm with one embedding per index scored 0/64 at k = 8: index 9 of a question is never visited when training stops at k = 3, so its embedding keeps its random initial value and the logits there are noise. A recurrent encoder has **no per-index parameter at all** — the same GRUCell weights produce position 3 and position 9 — so the representation at an unseen depth is the continuation of a dynamic that *was* trained rather than an untrained parameter. Concretely a k-hop question is `[4, ENT, LINK × (k−1), REL, 5]`; the backward state at a LINK position is a function of the suffix (how many LINKs remain before the terminal relation) and the forward state a function of how many have been passed. The controller's own state also advances by iterating one learned map, so "match the query to the position representation" is a relation that *can* hold past the trained lengths. This is a real chance, not a guarantee — a GRU can saturate, and then depth 4 and depth 8 become indistinguishable. Whether it does is exactly what the experiment measures. A test checks the necessary condition directly: at k = 8, v3-without-offsets gives every repeated LINK position the *same* key, while the encoder separates all 21 pairs.

## What is still supplied — say it plainly

v4 removes two bookkeeping features. It does **not** remove the scaffolding, and the scaffolding is substantial:

* **the pointer action space** — at each step the controller chooses one candidate as the subject and one as the operation from a fixed candidate set (question positions + transcript result slots), plus a CONTINUE/STOP bit. It never emits free text.
* **type validation by the executor** — the executor checks that the chosen subject token is an entity id and the chosen operation is one of 8/9/10/11, and kills the episode otherwise.
* **the transcript structure** — results are appended to an ordered slot array that the model can point at. Memory *exists*; the model is not asked to invent it.
* **the recurrent state** — a GRU cell that reads the question left to right and is advanced once per call. Sequence structure is given.
* **the tool** — the frozen lookup operator was itself trained with intermediate labels, and answers canonical `[4, ENT, OP, 5]` queries.
* **the curriculum** — 1-, 2- and 3-hop questions, pairwise-distinct chains, held-out relation 10 never a multi-hop training terminal.

So the test is narrow and should be described narrowly: **memory and sequence structure are still given; what v4 tests is whether the model can LEARN the updates that the two bookkeeping features used to perform for it** — "which transcript entry is the current one" and "which repeated operation token comes next".

## What the dev budget already showed (training stream only, dev seeds ≥ 996000, never the frozen panels)

Two short dev runs were spent before writing this. They say nothing about generalisation — they only rule out "the arm cannot optimise at all", which v3's preregistration had to leave untested.

* **Throughput.** 200 updates per arm at the registered batch size, four concurrent: v3-repro 5.84, reg 5.62, ctx 5.46, reg+ctx 5.53 updates/s. The two new mechanisms cost about 6%.
* **Learning, `reg+ctx`, ~3,550 updates, dev seeds 996001 and 996002** (time-capped on purpose): mean training reward 0.75 → 0.99 by update 500 and 0.992–0.999 from update 1,500 on; invalid actions 0.96 → ~0.0000; over-cap ~0.00002; mean calls settling at 2.13–2.19 against a true mean hop count of 2.0. The `v3-repro` reference on the same dev seed reaches 1.0000 and stays there, so `reg+ctx` is slightly noisier but is learning the 1–3-hop stream.
* **The write gate is used and not saturated**: mean 0.51 → 0.74–0.87 early (the register is written on most calls while the policy is forming) → 0.47–0.56 with 43–52% of writes above 0.5 by update 3,000. Neither stuck at 0 (never writes) nor at 1 (overwrites everything).
* **Nothing was tuned.** No hyper-parameter, initialisation or architecture choice was changed after seeing these curves.

## Pass marks

Per seed separately, per cell, 64 units per cell, greedy episodes, final checkpoint only:

* **answers ≥ 59/64 AND strict path ≥ 59/64** (subjects, operations, stop point and every returned token correct; voluntary stop; no cap hit; no invalid action) on every one of the 25 cells: k = 1..8 × {practised terminal, held-out terminal 10} in 16-person worlds, the six 6-person k = 1..3 cells, and the three k = 5 held-out twin-pair cells (changed link, changed endpoint value, irrelevant edit; the irrelevant-edit cell additionally requires identical twin answers).
* The **length-generalisation claim rests on k = 4..8 only.** k ≤ 3 is in-distribution for length.
* An incomplete run (time cap hit before 6,000 updates) is a **failure**, not a partial result.
* `reg+ctx` is the arm the headline hangs on. `reg` and `ctx` exist to say *which* replacement carries the load if `reg+ctx` partly fails.
* Time cap 1,700 s per job; a wave of three seeds is one thread each and must finish under 25 minutes.

## Readings

* **`reg+ctx` passes in ≥ 2/3 seeds** → shown on this toy: a controller given a pointer action space, a transcript and a GRU, and *no* hand-written recency or offset features, learns the bookkeeping itself well enough to execute 4–8-hop decompositions it was never trained on. Still not general intelligence; the lookup tool was trained with intermediate labels, and the action space, type checking, memory structure and curriculum are all supplied.
* **`reg` passes, `ctx` fails** → the offsets, not the recency flag, were the load-bearing hint, and the bidirectional encoder is not a sufficient replacement. Report the first failing length per seed and the failing component from the intervention diagnosis.
* **`ctx` passes, `reg` fails** → the recency flag was load-bearing and the learned register did not learn to hold the current person. The logged write gate should say why (stuck near 0 = never writes; stuck near 1 = overwrites every call; healthy = writes on the hops that matter).
* **Either single arm passes but `reg+ctx` fails** → the two replacements are individually adequate and jointly too hard to optimise under this budget; that is an optimisation result, not a representational one, and must be labelled as such.
* **Everything fails** → v3's result was a property of the supplied bookkeeping, and this architecture does not learn it from final-answer reward alone at this scale. Say that plainly; do not re-tune and re-report.
* **`v3-repro` diverges from v3 at tolerance 0** → the refactor is unfaithful and nothing else here is reportable.

Low final *training* reward is an optimisation failure and must be read separately from generalisation. Every arm's final training reward, the reward curve, the write-gate trace and the per-cell intervention diagnosis are reported whatever the outcome.

## Fable's predictions

Written 2026-09-20 by Fable before any registered v4 run. Dev evidence only shows `reg+ctx` can optimise its training reward (0.99+); no v4 model has been scored on any panel.
Scope notes from Astra's audit 18 §7, adopted: (a) the panels are the reused v3 DEVELOPMENT panels — any pass here must be confirmed on the fresh dispatcher suite
(`artifacts/fable-confirmation-panels-20260920/dispatcher`, mark 464/512) before any claim; (b) the pass mark I apply is the originally registered **58/64** on answers,
strict path and pair unit-pass (the script also prints its 59 mark; both are reported); (c) `v3-repro` runs on v4's data namespace, so it is a same-stream control for
the other arms, not a replay of the registered v3 trajectory; (d) repeated LINK tokens being indistinguishable was never a proof that v3-no-offsets *could not* work;
(e) parameters are not matched: 15,522 / 17,635 / 21,922 / 24,035 — reported, not hidden. Memory, the pointer action space, type validation and the transcript are still supplied.

| id | forecast (seeds 0/1/2, 25 development cells, mark 58) | p | falsified by |
|---|---|---|---|
| P41 | `v3-repro` passes every cell in 3/3 seeds | 0.80 | any seed misses a cell |
| P42 | `reg+ctx` (both supplied hints removed) passes every cell in ≥ 1 seed | 0.35 | 0 seeds |
| P43 | `reg+ctx` passes every cell in ≥ 2/3 seeds | 0.15 | ≤ 1 |
| P44 | `reg` (learned register, offsets kept) passes in ≥ 2/3 | 0.45 | ≤ 1 |
| P45 | `ctx` (contextual positions, recent flag kept) passes in ≥ 2/3 | 0.30 | ≤ 1 |
| P46 | every failing `reg+ctx` seed passes all k ≤ 3 cells and first fails at k = 4 or 5 (extrapolation, not fitting, is what breaks) | 0.70 | a failing seed that misses a k ≤ 3 cell, or first fails at k ≥ 6 |
