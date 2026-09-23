# Proposal: two sequential learned lookups (not implemented, not trained)

2026-09-19. Author: Opus, for Astra's review. `full_verdict: false`; H1 OFF; defaults unchanged. Nothing here has
been built or run.

## Why

Address-keyed selection fixed one-step choosing and changed-fact binding. The fresh confirmation reproduced this on
both seeds and under renaming and reordering. It did **not** help two-hop questions, which take the form
"[question] P_e LINK R_r [answer]": combining is unchanged everywhere, with bounds spanning 0.
- The second fact, A(b, r), is keyed by b, the friend of e.
- b does not appear in the question, so a single address match against the question cannot reach it.
- The model needs a second lookup whose query comes from what the first lookup found.

## Mechanism

A default-off variant, for example `nothink+qread+addresskeys+chain2`, built on the address-key reader.

1. **Lookup 1 (learned).**
   - The decoder's question-conditioned query q1 is matched against the existing card address keys, giving
     attention α1 over the supplied cards.
   - The model reads r1 = Σ_k α1_k · E(object_k), where object_k is the embedding of line token 3. That is the friend
     on a link line, or the value word on an attribute line.
   - r1 is the model's own first result. It is a soft, differentiable read.
2. **Lookup 2 (learned, guided by r1).**
   - q2 = W₂ [r1; h_q], where h_q is the decoder's question state (it carries R_r).
   - q2 is matched against the same address keys, giving α2. The model then reads the card values as the address
     variant already does.
   - The answer is decoded from the lookup-2 read, together with the ordinary memory.
3. **Loss.** Only the ordinary answer cross-entropy. There is no intermediate supervision and no gold bridge label.

**Declared structural help.**
- The address parse already used: token 1 is the person, token 2 the relation or LINK.
- One addition: token 3 is the line's object.
- Both apply identically to every supplied line.

## Matched control: "two lookups, unchained"

- **What stays identical:** the architecture, parameter count, initialisation, data stream, steps, seeds, supplied
  cards, loss and evaluation.
- **The one difference:** lookup 2's query uses a second question-only vector in place of r1, with a matched-shape
  learned projection of h_q. So the only change is whether lookup 1's result feeds lookup 2.

This separates chaining from added capacity. The variant is also reported against the existing single-lookup
`answer-address-s{0,1}` and the pooled controls.

## Preventing gold intermediate answers from leaking into inference

- **Nothing oracle-derived in the forward pass.** Lookup 2's query is built only from lookup 1's own read and the
  question. No gold friend id, `gold_lines`, answer labels, triplet roles, intervention metadata or oracle bridge
  enters the forward pass. Inputs are label-free as now.
- **No teacher forcing of the intermediate in any training mode.** D's "teacher" mode inserts gold cards; this
  variant must not. The supplied card set is identical across arms, and lookup 1 chooses among it itself.
- **No bridge in the prefix.** No suffix or bridge is placed before or inside the question prefix. This follows the
  H2 lesson.
- **Readouts are diagnostics only.** Intermediate readouts (whether argmax α1 is the link card, and how close r1 is
  to E(b)) are computed afterwards under the read-only guard and never fed back.
- **Tests before any training:**
  - perturbing `answer`, `gold_lines` or metadata leaves outputs bit-identical;
  - replacing r1 with a zero or shuffled vector changes lookup 2;
  - no-card decode equals the baseline;
  - training and greedy decoding see the same memory.
- **Behavioural checks:** on the overnight paired 2-hop sets, an edit to the link card, an edit to the friend's
  fact, and a tempting edit must move, move and not move the answer respectively. Actual answers are saved.

## Predeclared evaluation (proposed)

- **Seeds:** 0 and 1 for the screen; 3 for a finalist.
- **Primary metric:** paired, visit-clustered one-sided 99% bounds on `combine:two_hop_trained_rel` and
  `combine:two_hop_heldout_rel`, chained minus unchained, validation only.
  - "Better" iff the lower bound is above 0 on both seeds.
  - The held-out relation is never trained as a two-hop question, so it is a composition test within the existing
    task family.
- **Non-inferiority on one-hop choosing:** the paired lower bound of (chained − single-lookup) must be at least −0.05.
- **Also reported:**
  - 2-hop causal-pair both-correct;
  - fresh-data confirmation, reusing the frozen fresh sets or a new predeclared set;
  - the unchanged gate. H1 stays OFF.

## Cost (to be re-estimated by a dry run before any training)

| Item | Seconds |
|---|---|
| Training, 2 arms × 2 seeds × about 190 | about 760 |
| Evaluation and comparison | about 60 |
| Reserve | 30 |
| **Total** | **about 850** |

This does not fit the 120.27 s left under the amended 2,100 s cap. It would need a new allowance.
