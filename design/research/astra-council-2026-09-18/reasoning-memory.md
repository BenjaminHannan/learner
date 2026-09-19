# Premonition: reusable reasoning and reliable memory

Research-only specialist report, 2026-09-18. I inspected the council brief and lead evaluation, the current mini spec, the deep-research report, the older novel-mechanisms memo, the answer-path handoff, and the council coordination record. I did not run training/tests or edit implementation files. The current milestone-2 numbers below are provisional saved-artifact observations from one development seed, not independent reproductions.

## Plain-language conclusion

The strongest next architectural idea is to **keep facts readable and change only a small reasoning workspace**. Premonition's provisional answer-path result is unusually clear: original D scored 73/512 on the supplied-fact toy, while whole-Think gating and the separate pre-Think card bypass each reached 512/512 on the same stated seed. A second baseline seed was also poor. This does not prove why D failed, and it says nothing yet about autonomous retrieval or multi-step reasoning, but it makes one design principle worth testing: facts should remain stable while reasoning changes a separate state.

The second useful idea is narrower: **make the binding between an identity and its role easier to preserve**. Pointerizing names already removes spelling as the identity problem, but a 128-dimensional pooled card can still entangle “Mira gave to Oren” with “Oren gave to Mira.” The model should be tested on role reversals and correlation-violating fresh identities before we assume its card representation is systematic.

Neither proposal is claimed as global novelty. Both borrow known ideas. What is new to this project is the specific combination with Premonition's pointerized identities, protected card store, repeated Think block, and causal village tests.

Before either architectural change, run the lead's simpler control: **train the existing repaired model with answer loss only at the final Think loop**. Current training predicts the final answer after every loop, which can reward unfinished states for guessing the answer. A March 2026 depth-recurrent preprint independently reports that final-step-only supervision plus identity-biased recurrence helped its recurrent models and that intermediate supervision hurt graph-depth extrapolation. That is supporting evidence for the control, not proof it will help Premonition.

## Candidate 1: latent role-bound cards

### Idea

Suppose the line is “Mira handed the key to Oren.” A useful memory should preserve at least three separable things: the event/relation, Mira's role, and Oren's role. If the names are swapped, the relation can stay similar while the bindings change. Today the card writer pools a line into a single value vector, while the pointerizer tells us which entities were mentioned. That representation may already learn roles; this proposal tests whether giving it a small explicit binding channel improves systematicity.

Catherine Chen et al. define role-filler binding exactly this way: a model should retrieve the correct arbitrary filler for a role even when the filler was unseen or violates training correlations. Their external-memory models could learn this under sufficiently diverse training, but their limited-filler regime failed completely on unseen fillers, and large schema changes also broke generalization. That is directly relevant: architecture alone is not enough; Premonition must train on aggressively randomized identities and role assignments. [Chen et al. 2019](https://arxiv.org/abs/1902.09006)

Altabaa et al.'s Abstractor similarly tries to separate relations from object features using relational cross-attention, improving sample efficiency on controlled relational and mathematical tasks. It is good precedent for a relation/object separation, but its tasks and architecture are different enough that it should motivate a small screen rather than a redesign. [Altabaa et al. 2024](https://arxiv.org/abs/2304.00195)

### Exact mechanism

Keep the existing raw card value `v_i` unchanged. For each entity mention `m` on line `i`, use the already available pointer identity `e_m` and the mention/line hidden states to predict a small latent role distribution:

`rho_im = softmax(W_r [h_m ; mean(h_line)])`, over perhaps 4 role slots.

Do **not** provide gold role labels. Store the entity pointer IDs plus these small role weights beside the ordinary card. When the question queries a card, form role-specific binding summaries from the existing entity embeddings:

`b_ir = sum_m rho_im[r] * E[e_m]`.

The memory key remains responsible for locating the relevant event; the value path returns `[v_i, b_i1, ..., b_iR]`. This follows the useful distinction in Key-Value Memory Networks: the representation used for addressing a memory need not equal the representation used to answer from it. Their paper demonstrated this on document/KB QA with task-specific encodings, so it does not establish that Premonition needs this factorization. [Miller et al. 2016](https://aclanthology.org/D16-1147/)

This is **new to Premonition**, not an unproved claim of global novelty. It adds one learned role projection and a small amount of per-card working state. With `R=4`, the extra arithmetic is roughly linear in entity mentions per line rather than in vocabulary size or number of card pairs. Exact wall time and bytes should be measured; do not reuse the existing FLOP formula by assumption.

### Smallest decisive experiment

Use a tiny subset where answers are entity pointers and construct paired worlds with identical vocabulary and event type but reversed roles. Train with fresh randomized names and deliberately break name-role correlations at test. Compare:

1. current repaired D with raw pre-Think card access;
2. the same model plus simple role-reversal data augmentation;
3. latent role-bound cards.

Keep total examples, loops, answer supervision, retrieval information and compute as matched as practical. Score both members of each reversal pair, consistent renaming, and irrelevant-fact invariance. A win must survive fresh bindings, not merely the training names.

**Kill criterion:** if augmentation or a cheap mention-position feature matches the role-bound variant, prefer the simpler method. Also kill/postpone it if learned roles do not remain stable under fresh identities or if they improve reversal tests while hurting ordinary questions. The main objection is real: pointer IDs plus contextual card vectors may already contain all necessary role information, making this redundant machinery.

## Candidate 2: protected facts + recurrent scratch transition

### Idea

Treat memory like a reference sheet and Think like scratch paper. A fact row is written once for the episode and stays unchanged. Each loop reads from those protected facts and updates only a small mutable reasoning state. This directly follows the current provisional observation that preserving access to pre-Think cards repairs the supplied-fact toy.

The structure also resembles earlier memory networks: a query state is repeatedly updated after reading external memory, rather than repeatedly rewriting the memory itself. The stronger claim we want to test is whether one shared transition can become a reusable operation across new identities and new combinations of familiar rules.

Recent evidence is suggestive but mixed. Chen's 2026 depth-recurrent Transformer uses a shared block, final-step-only supervision, LayerScale, and an identity-biased gate; it reports 20+ stable recurrent steps and extrapolation on controlled graph, logic, and relational-text tasks. However it is a recent preprint, graph reachability uses strong structural masking, and the unstructured-text task reaches a lower plateau. [Chen 2026](https://arxiv.org/abs/2603.21676)

Ramesh et al. show that Transformers can generalize compositions of synthetic functions, and that emitting intermediate results can help unseen compositions, but composition order in training can create sharp failures. Their functions have explicit identifiers and their setting is far cleaner than village text. This argues for held-out operator order/combinations, not for importing their intermediate-output recipe uncritically. [Ramesh et al. 2024](https://arxiv.org/abs/2311.12997)

### Exact mechanism

Let `E` be the fetched **pre-Think** card rows. They are immutable during reasoning. Let `z_t` contain the four registers plus the entity/question working rows that we choose to make mutable. Each loop does:

`a_t = CrossAttention(Q(z_t), K(E), V(E))`

`delta_t = F_theta(z_t, a_t, q_original)`

`z_(t+1) = z_t + g_t * delta_t`

where `F_theta` is the shared two-layer transition and `g_t` starts biased toward identity/preservation. Reinject the original question representation each loop. The decoder receives final `z_T` and protected `E`, so exact factual content remains available for copying while the scratch state can encode the operation/composition.

This differs from the current whole-Think gate: the proposal changes **what is recurrently transformed**. Facts are protected by construction; only scratch evolves. It adds cross-attention from scratch to the existing fetched rows each loop but does not enlarge the permanent store. Inference cost grows linearly with loop count; memory for protected cards is already paid, while mutable-state memory stays roughly constant with loops if intermediate activations are not retained at inference.

### Supervision and decisive experiment

First compare current all-loop answer loss against **final-loop-only** answer loss on the repaired architecture, fixed loop budget, same seed/data. If that simpler control solves the intended composition test, do not credit a new executor.

Only then compare protected-scratch recurrence against that final-only control. Use familiar primitive rules but unseen compositions and fresh entities. Vary allowed loops while keeping available facts fixed, so “more thinking” is not secretly “more retrieval.” Train a genuine no-Think control. Score familiar single operations, unseen compositions, role reversals, and whether extra loops turn correct answers wrong.

Do not use `oracle.Deriv.steps` as a target for recurrence depth: it sums premise work and is not sequential depth. The saved traces also lack a full operand/state dependency graph. If future work instruments intermediate states, any trace supervision is privileged and must be supplied to matched competitors. For this first screen, answer-only final-step supervision avoids that privilege.

**Kill criterion:** reject the reasoning claim if a trained no-Think model with the same protected cards matches it; if extra loops do not help on controlled additional operations; or if gains disappear on unseen operator order/compositions. Zhou et al. show how fragile apparent length generalization can be to initialization and training order, even on addition, and their headline curve used best-of-10 trials. Every seed matters here. [Zhou et al. 2024](https://arxiv.org/abs/2402.09371)

## Recommendation and largest doubt

The best sequence is: **(1) final-loop-only supervision control, (2) protected-facts/scratch-only recurrence, (3) role-bound cards only if role-reversal diagnostics remain weak.** The protected-scratch proposal is the strongest candidate because it follows directly from the provisional gating/bypass result and preserves the project's reasoner/store separation. Role binding is a targeted second mechanism for a distinct failure mode.

The largest doubt is that the supplied-fact toy may be too easy. Both 512/512 repairs could merely restore one-fact copying. The decoder may solve shallow multi-fact questions directly from protected cards, leaving the recurrent transition unnecessary. That is why an actually trained no-Think control and held-out familiar-operation compositions are essential. Until those separate reading a fact from applying a reusable procedure, these mechanisms remain hypotheses rather than evidence of reasoning.

### Primary sources checked

- Chen et al., *Learning to Perform Role-Filler Binding with Schematic Knowledge*: https://arxiv.org/abs/1902.09006
- Altabaa et al., *Abstractors and relational cross-attention*: https://arxiv.org/abs/2304.00195
- Miller et al., *Key-Value Memory Networks for Directly Reading Documents*: https://aclanthology.org/D16-1147/
- Chen, *Thinking Deeper, Not Longer: Depth-Recurrent Transformers for Compositional Generalization*: https://arxiv.org/abs/2603.21676
- Ramesh et al., *Compositional Capabilities of Autoregressive Transformers*: https://arxiv.org/abs/2311.12997
- Zhou et al., *Transformers Can Achieve Length Generalization But Not Robustly*: https://arxiv.org/abs/2402.09371
