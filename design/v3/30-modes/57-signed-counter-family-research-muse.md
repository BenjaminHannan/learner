# 57 — Signed counter family: verification + one replacement proposal (research scout, muse)

## 1. What was checked

All four leads from doc 45 exist. Citations verified 2026-09-22:

1. Grazzi et al., "Unlocking State-Tracking in Linear RNNs Through Negative Eigenvalues", ICLR 2025, arXiv:2411.12537 — https://arxiv.org/abs/2411.12537
2. Khavari et al., "Parity Requires Unified Input Dependence and Negative Eigenvalues in SSMs", ICML 2025 Workshop (MOSS), arXiv:2508.07395 — https://arxiv.org/abs/2508.07395
3. Terzic et al., "On the Expressiveness and Length Generalization of Selective State Space Models on Regular Languages" (SD-SSM), AAAI 2025 — https://ojs.aaai.org/index.php/AAAI/article/view/34301 (preprint https://arxiv.org/abs/2412.19350)
4. Abbe et al., "Learning High-Degree Parities: The Crucial Role of the Initialization", ICLR 2025 Poster — https://arxiv.org/abs/2412.04910 (OpenReview https://openreview.net/forum?id=OuNIWgGGif)

## 2. What each paper actually says about parity/counting robustly

**Paper 1 (Grazzi et al.).** Finite-precision linear RNNs whose transition matrices have only positive eigenvalues *cannot* solve parity; extending the eigenvalue range to include negatives fixes it (Mamba/DeltaNet experiments), and stable 1.3B pre-training is shown. Two further claims matter: counting mod 3 needs *non-triangular* matrices, and any regular language is learnable with transitions that are products of (I − outer-product) matrices with eigenvalues in [−1, 1]. Relevance: our softmax-row step matrices are non-negative by construction, so the flip (eigenvalue −1) lives in a small corner of parameter space — consistent with 1-in-6 seeds never finding it before the balanced start.

**Paper 2 (Khavari et al.).** For diagonal SSMs, splitting the two ingredients across layers still fails: input-dependence in one layer + negative eigenvalues in another does *not* solve parity. One recurrence layer must have *both*. Caveat for us: their parity is over *input content* (running XOR of bits). Our 43J/43K counters clock *position index* (flip every step regardless of digit), so unconditional signed steps suffice here; token-dependence becomes relevant only when we later count input content (digit sums, carry chains). Claim that our exact position-clock setting needs unified input dependence: not found.

**Paper 3 (Terzic et al., SD-SSM).** A dictionary of *dense* trainable transition matrices combined per-step by a softmax selector (convex combination driven by the input), with LayerNorm+linear readout, is the first single-layer selective SSM with ≥99.9% length generalisation across their FSA suite (trained on lengths 4–8, tested to 500); diagonal variants fail on non-commutative automata (e.g. D30). Relevance: if we later make counters input-dependent, the recipe is 2–4 dense 2×2 matrices + learned selector, not one fragile recurrence. No evidence found that the dictionary alone removes init sensitivity without the dense (signed-capable) matrices.

**Paper 4 (Abbe et al.).** For full/almost-full parities on MLPs, discrete Rademacher init succeeds where Gaussian-perturbed init (σ above constant) fails; positive result tolerates perturbation up to σ=O(d⁻¹); initial-gradient-alignment measure explains the gap. Different setting (feedforward, content parity), but the warning transfers: our 5/6 → 9/9 story looks like an init problem, and sign-symmetric/discrete init is the principled fix, not a hand-placed lean.

## 3. Proposed replacement: signed-scalar counter ("tanh-eigenvalue clock")

Single change to `LearnedParity.cases()` in `scripts/fable_learnedparity43j.py`; table, clues, loss, trainer untouched; output shape unchanged `[n, 2*N_COUNTERS*K]` with K=2.

- Replace per-counter start vector (K) + full K×K softmax step (K²) with one signed scalar per counter: `lam_c = tanh(w_c)`, state `x_0 = 1`, `x_t = lam_c^l * 1`, emitted as pseudo-distribution `p_t = [(1+x_t)/2, (1-x_t)/2]`.
- `lam=-1` is exactly the flip/odd-even counter (alternates one-hot); `lam=+1` is exactly the stay/last-place counter (constant). Values in between are the learnable path; readout table is unchanged because `p_t` has the same shape and one-hot endpoints as today's softmax rows.
- **Parameters:** 2·N_COUNTERS logits (8 at N=4) vs today's 2NK + 2NK² (16 + 32 = 48 rows/entries → 40 free). Table params unchanged.
- **Init:** `w_c ~ N(0, 1)` (Gaussian, then tanh). Sign of `w_c` decides flip vs stay family, so P(all 8 counters same sign) = 2/256 ≈ 0.8%, vs the old geometry where "lean flip" was a small corner (empirically ~1/6 total failure). No hand-split list; symmetry is broken by the random sign, and gradient pushes |lam|→1 because only ±1 give length-stable signals.
- **Why the balanced start becomes unnecessary:** the target dynamics (−1 and +1) are now interior-symmetric points of a 1-D range instead of corners of a simplex; every counter starts at lam≈0 (maximal gradient d lam/dw = 1) rather than near a flat softmax corner, and the two useful endpoints are equidistant in parameter space.

## 4. Marks to seal (before any run)

3 seeds × 2 arms (signed-scalar vs 43K-v2 control), train lengths 4–12 only: per-seed exact-match on lengths {4–12 train, 16, 32, 64} plus a 512 probe (report, not gate). Seal: all 6 skills, HARD=1 reads, eigenvalue audit (`lam_flip+1`, `lam_stay−1`). Pass bar (suggested): control and proposal each reported per-seed, no averaging; proposal seals iff 3/3 seeds exact at ≤64 on all skills. Log per-counter `lam_c` so the flip/stay assignment is auditable.

## 5. Falsification signature

Proposal is falsified if any seed shows: train-length failure on odd/even-dependent skills (not just long-length decay), or audit finds no counter with `lam < −0.9` (flip never found), or 512-probe fails while 64 passes *identically* in both arms (failure is readout, not counter). If signed-scalar fails this way, escalate to the 2-matrix SD-SSM-style dictionary, not back to hand-leaning.

## 6. Mod 3?

No — not in this 1-D signed family: a scalar in [−1,1] can only encode 2-cycle (flip) or fixed point, never a 3-cycle. Paper 1 says mod 3 needs non-triangular (in practice rotation/complex) transitions. Upgrade path when base-3 tasks arrive: per-counter 2×2 rotation dictionary `{I, R120, R240}` with learned selector, or complex-λ with |λ|=1; K must become 3 (or a 2-D continuous state). Today's proposal deliberately does not claim mod-3.

## What it means / What it does not mean

It means the four papers are real and converge: parity needs a signed (−1-capable) transition, and our softmax simplex hid −1 in a corner — the tanh-scalar fix puts ±1 on equal footing in a single `cases()` change. It does not mean token-dependence, mod-3 counting, or init-proofness is proven for our rig — those need the sealed 3×2 run above, and mod-3 needs a rotation family we have not built.
