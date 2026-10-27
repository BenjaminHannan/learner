# 65 — Counter dictionary experiment (muse): SD-SSM-style fixed-matrix dictionary vs saturation-penalised scalar

## 1. Context

Experiment 59 tested doc 57's signed-scalar counter (`lam = tanh(w)` per counter) against the 43K-v2 hand-balanced control. Result (registered FAIL, 0/3): the flip family (`lam -> -1`) was found in every seed, but the stay family never saturated (max `lam` 0.76), and hardening `lam` to +/-1 broke ROTL1 — the skill that needs the stay/last-place counter. Soft reads were 72/72 exact in all 3 seeds, so the trained solution leaned on unsaturated `lam` values that hardening destroyed. Control 43K-v2 is exact to 512 digits 3/3. Doc 57 section 5 names the escalation: the SD-SSM-style dictionary (Terzic et al., AAAI 2025) — per counter a small dictionary of dense 2x2 transition matrices combined by a learned softmax selector.

## 2. Arms (one change each vs `scripts/fable_counter59_signed.py`, which is imported as the rig)

**DICT** (`DictCounter`, overrides only `cases()` again): per counter a fixed dictionary of two matrices, `{I, FLIP=[[0,1],[1,0]]}` — no learned matrix entries — combined by a learned 2-way selector logit `s_c` (`softmax` over {stay, flip}). Soft transition `M_c = p_stay*I + p_flip*FLIP` (doubly stochastic, so rows stay pseudo-distributions); state unrolls from the fixed start `[1,0]` exactly like the rig's tape (`s <- s @ M`, forward/backward split and flatten unchanged, so the readout table is untouched). Hardened read (`HARD=1`): argmax selector, i.e. exactly `I` or exactly `FLIP`. Init `s_c ~ N(0,1)`: random sign per counter, no hand balance. Parameters: 16 selector logits vs 8 scalars (exp 59) vs 48 softmax entries (43K-v2). Both endpoints are vertices of a 1-simplex rather than ends of a tanh range, so the stay family has a saturating discrete attractor (`p(stay) -> 1`) instead of an asymptotic one.

**SIGNED-SAT**: experiment 59's scalar verbatim plus a saturation penalty `0.01*(1-lam^2)` (mean over counters) added to the per-batch loss — the minimal fix for "gradient never pushed |lam|->1 on the stay side". One added line in a copied training loop; data, optimiser, seeds, updates identical.

**Control**: 43K-v2 `BalancedStart` unchanged.

## 3. Why DICT should succeed where the scalar failed

The scalar's stay endpoint (`lam=+1`) is reached only as `w -> +inf` with vanishing gradient (`d lam/dw = 1-lam^2 -> 0`); the optimiser settled at `lam ~ 0.5-0.76`, good enough for soft reads, fatal under hardening. The dictionary moves saturation from the state dynamics into the selector: `p(stay) = softmax(s_c)` saturates with *non-vanishing* logit gradient along the way, and hardening the selector (argmax) matches what was trained if the selector is confident — the same harden-after-fit pattern the sleep recipe (exps 45/46) already relies on. Both families are symmetric by construction: `I` and `FLIP` are equidistant in selector space, and `P(all 8 counters pick the same family at init)` is small.

## 4. Risks

The selector can still sit at 50/50 (same unsaturated-trap, one level up); the audit (D4) checks confidence, not just accuracy. Convex mixing of `I`/`FLIP` mid-training yields non-invertible transitions, which may slow or strand learning. 3 seeds cannot prove init-proofness either way.

## 5. Run

3 seeds x 3 arms (6001/6002/6003), train lengths 4-12, sealed eval lengths {4-12,16,32,64} + 512 probe, `HARD=1` reads, 100 fresh inputs/skill/length (20 at 512), sequential, `OMP_NUM_THREADS=1`, `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B`. Marks D1-D5 in `artifacts/fable-counter60-20260921/PASSMARKS.md`, sealed before the run. A registered FAIL stays a FAIL.

## What it means / What it does not mean

It means the dictionary is the doc-57-escalated, still-minimal replacement: fixed signed-capable matrices plus a learned discrete choice, with the saturation problem moved to a softmax where hardening is principled. It does not mean the dictionary is proven better — that is what the sealed 3x3 wave decides — nor does it claim mod-3 counting (a scalar/2-dictionary still only spans 2-cycles and fixed points; rotations remain future work).
