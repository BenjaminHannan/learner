# Scratchpad plus partial bookmarks: design and comparison

2026-09-27. Ben asked to add both functions, then to design the combination and compare it with scratchpad-only. This document answers that design request. It does not register a measured winner or start Step 2. The resized baseline must first meet the existing 0.95 four-number practice exactness gate. No candidate has been implemented or trained.

## Recommendation and evidence status

SUGGESTED: scratchpad-only is the lower-risk first experiment under the unchanged answer and halt losses. The combined design is a feasible, inexpensive way to test Ben's two-function idea, but it introduces another learned decision and can undo useful state. More expressiveness does not establish better optimization or generalization. UNTESTED: which architecture performs better on new hands.

Sol reviewers agreed the design below is feasible and the algebra and parameter budget are consistent. The bookmark designer favored scratchpad-only as a first experiment; the protocol reviewer favored testing the combination given Ben's request. These are recommendations, not measured votes about accuracy.

## One bank, two uses

Keep the inherited 256-wide recurrent core and all losses, puzzle data, fixed env=0, and stopping rules. Treat each token's existing hidden state as h_t=[c_t,z_t], with c having 240 coordinates and z having 16. The shared core learns all 256 features. The 16-coordinate interface has no arithmetic meaning supplied by code. Preserving c means restoration need not erase all current context; it does not guarantee that c represents failed attempts.

Eight episode-local slots hold dynamic keys K_i of width 16, tokenwise unnormalized payloads Z_i of shape [T,16], and occupancy masses m_i. All start at zero. Eight learned static address vectors E_i distinguish slots. T is the current puzzle's number of grid tokens, fixed within an episode/batch and allowed to vary between puzzle sizes.

Learned components:

- Biasless query and key maps Wq,Wk: 256 to 16.
- Biasless scratch decoder U: 16 to 256.
- Scalar sigmoid gates g_s, g_b, g_w: scratch use, bookmark use, and writing, each from 256 features plus a bias.
- Learned slot address vectors E: 8 by 16.

At each round, read before the inherited core step:

1. Form q=Wq mean_t(h_t) and beta=softmax_i(q dot (K_i+E_i)/sqrt(16)). Both memory uses share this learned selection.
2. Read v_t=sum_i beta_i Z_i,t and mu=sum_i beta_i m_i.
3. Scratchpad: h_s,t=h_t+g_s U(v_t). Use U tokenwise, preserving positional information. This differs from the earlier pooled-summary sketch; no version of that sketch was trained.
4. Partial bookmark: keep the first 240 coordinates c_s,t. Replace the final 16 by z_out,t=(1-g_b*mu) z_s,t+g_b v_t.
5. Run the unchanged recurrent core on that combined state and the original puzzle embedding.

The bookmark equation is a convex move toward the occupied stored payload. No inverse of a learned projection is assumed. At full occupancy and unit gate it restores the represented 16-coordinate payload. Soft writing and reading can blend several earlier states, so it is a **soft partial bookmark**, not guaranteed restoration of one complete previous round. Current c and older z can also be inconsistent, which is a substantive design risk.

After the core step, form k=Wk mean_t(h_new,t), learned write gate g_w, and a=softmax_i(k dot (K_i+E_i)/sqrt(16)). For w_i=g_w*a_i:

- K_i <- (1-w_i) K_i + w_i k
- Z_i,t <- (1-w_i) Z_i,t + w_i z_new,t
- m_i <- (1-w_i) m_i + w_i

Occupancy tracks the mass of the same learned writes; it is bookkeeping, not a puzzle-dependent addressing or reasoning rule. Z already contains write mass, so do not multiply it by m again at read time. These operations require no solver labels, external validity signal, search code, or arithmetic matching rules.

Advance h,K,Z,m during free rounds under no_grad; detach all dynamic state at the inherited boundary. Retain the existing maximum six graded rounds. Reset the bank on every new puzzle. Initial core weights and training streams remain paired across variants.

## Calculated cost, pending implementation measurement

| Component | Learned parameters |
|---|---:|
| Wq and Wk | 8,192 |
| Biasless U | 4,096 |
| Three scalar gates, including biases | 771 |
| Eight address vectors | 128 |
| Combined addition | 13,187 |
| Baseline plus combined addition | 1,659,681 |

The combined addition is 0.8009% of the 1,646,494-parameter baseline. The matched scratchpad-only design omits the bookmark gate and overwrite, adding 12,930 weights (0.7853%). Both fit the 1% rule. Dynamic storage is larger than the earlier pooled sketch: eight tokenwise payloads plus keys and occupancy. Runtime and peak MPS memory are UNTESTED and must be measured; matched parameter count alone does not match computation.

## Wiping and fair comparison

Wipe **all dynamic card state K,Z,m before every read**, beginning at round 0. Keep static address vectors, gates, decoder, core, and stop rule. Then v=mu=0, the biasless scratch decoder contributes zero, and bookmark interpolation leaves z unchanged. Both modes have exactly no card effect. Verify this against the inherited core using the candidate's own core weights before evaluating results.

The proposed N5 thresholds are unchanged. A joint wipe penalty shows useful dependence on card contents under that intervention, not that both modes separately helped or that backtracking occurred. Wiping can also shift internal activation distributions.

For a trained-model comparison, A must be trained as scratchpad-only and B as combined, using this same bank, state interface, initialization for shared weights, seeds, data stream, steps, and scoring. Comparing B with its bookmark gate disabled is a useful dependence test but is **not** a substitute for training A. Compare own-stop dev validity, paired differences, intact-versus-wiped differences, compute, and effects on sums/grids. Do not pick a winner from training exactness alone. Any empirical comparison requires a separately frozen plan before running; this design document does not silently add a registered arm or authorize adaptive sealed-panel use.

Descriptive, predeclared development conditions for a frozen B checkpoint can include intact, scratch-only, bookmark-only, and all cards wiped. Keep sealed evaluation to the registered fixed conditions. No adaptive tuning or selectively suppressing registered results.

## Design comparison

| Question | Scratchpad-only | Combined |
|---|---|---|
| Primary learned behavior | Save and reuse useful features | Also choose when to replace part of current state |
| Short-range learning signal | A write can help a later answer | Same path, plus feedback for restoration decisions |
| Main extra risk | Ignored or blurred cards | Those risks plus overwriting progress or mixing incompatible states |
| Can revisit old information? | Yes, by adding retrieved features | Yes, with an explicit partial-state replacement operation |
| Guarantees different continuation? | No | No |
| Likely ease of training, hypothesis | Better | Harder |
| Measured winner | Unknown | Unknown |

SUGGESTED conclusion: retain the combined design as a concrete candidate, but prefer scratchpad-only on expected trainability until a matched experiment supplies evidence for the bookmark mode. The current user request is a design comparison; baseline training continues, and the prerequisite remains in force.
