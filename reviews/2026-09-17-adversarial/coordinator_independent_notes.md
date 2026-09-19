# Coordinator's independent notes (written BEFORE reading any reviewer report)

## Code-level findings (memorylab/model.py, tasks.py, run.py)
C1. Cue and routing come from x only (MainNetwork.step). m is identical at every step of a query, so the loop iterates F on a constant (x, m). Multi-hop retrieval and composition are impossible by construction until z-dependent cues exist.
C2. HaltingController: head on detached state; decision = confidence >= 0.8 -> stop, else "stuck"; sigmoid >= 0.5 -> continue. No training code exists. At deployment there is no oracle; the head must predict improvement from state (a value function). Confidence is uncalibrated.
C3. Writer.propose receives `targets` and embeds them (nn.Embedding(MOD, width)); content v = MLP(x, trace slice, target_embed). The writer has the label directly. For method items the label is the answer for one operand; storing the rule requires computing (target - operand) mod 8 from x and target.
C4. Write key = read key = model.key_route(x). Teaching input can be the same string as the query. Memory becomes a lookup keyed by the (encoded) query string; "paraphrase generalization" is two templates mapping to one key.
C5. World.rules[entity] is one number that is both the "mark" (fact) and the machine's shift (method). Ideal memory is entity -> number; the "method" family is decoder arithmetic (number + operand) mod 8. No method is acquired; parameters of one pre-built family are identified. Fact-to-method "transfer" is the same number.
C6. Family is in the surface form ("mark" vs "start at"/"move with"); hints also name the family. Type inference is trivial here.
C7. World.feedback always returns accepted=True with the true target regardless of the response. The "checker" is an oracle; practice = supervised learning with labels. There is no pass/fail-only or noisy regime.
C8. Vocabulary 42 tokens, MAX_TOKENS 12, output 8 classes. "English" is nominal; no generation.
C9. Memory 4 x (48 x 48). <= 48 exact associations per bank; 24 entities fit only if learned keys are near-orthogonal. Nothing enforces orthogonality. RMS overlap of random unit keys is 1/sqrt(48) = 0.144; after ~23 other one-shot writes at eta = 1 the accumulated perturbation on a stored read is O(sqrt(23) * 0.144) ~ 0.7 of a typical error norm unless keys are learned to be orthogonal or replay re-writes.
C10. No decay/forgetting gate; corrections at the same key overwrite exactly (eta = 1, unit key) but cycle for conflicting targets at overlapping keys.
C11. Warmup mode writes the same content to all banks with eta = 1 -> banks start identical; router symmetry breaking is not obviously driven by anything.
C12. Learned mode sums log-probs of all four heads even when write = 0, so bank/trace/strength heads receive credit for no-ops (variance without effect).
C13. run.py passes hard = 10 GB, steady = 8 GB by default (runtime.local.json omits them); storage.py constants are 100/80 GB. Config mismatch.
C14. memorylab/experiment.py and tests/ do not exist. Nothing trains yet. The storage guard is larger than the science code.

## Review-document corrections (my own)
R1. Nested Learning link: abehrouz.github.io/files/NL.pdf 301-redirects to alibehrouz.com/files/NL.pdf; the paper is also arXiv:2512.24695 (NeurIPS 2025). "Sections 9-10" attribution is consistent; Sec. 9.1 uses Llama3-8B / Llama-3B with 15B tokens continual pre-training; Sec. 10 has the "not solved in general" sentence. Correct in substance.
R2. ACT/PonderNet row: "Their training objectives cannot be imported without reconciling our initial absence of a compute-cost penalty" conflates the two. ACT has an explicit tau penalty and is documented as sensitive to it. PonderNet's authors state they do NOT regularize to minimize steps; the KL-to-geometric prior is framed as exploration and a prior over halting (it still biases toward ~1/lambda_p steps). The deeper import problem is that the proposal has no halting distribution over steps at all, only a pairwise now-vs-continue comparison.
R3. TRM row could add the verified cost: ~3 days on 4 x H100 for ARC-AGI, 2-layer 7M model, ~1000 examples with ~1000 augmentations each, deep supervision, no natural language. Supports the review's caution.
R4. Novelty claim should be narrowed further. Uncited close precedents: CaMeLS (meta-learned writer for gradient updates trained via later QA), Backpropamine (network-generated gate on plastic weight updates), Metalearned Neural Memory, MANN episodic teach-then-query, Larimar/Kanerva Machine (least-squares matrix memory + LM decoder, sequential editing, forgetting), Gated DeltaNet (decay gate for corrections), sparse memory finetuning (weight-based fact learning with 11% vs 89% forgetting), MemoryLLM, Physics of LMs 3.1 and Reversal Curse (one-exposure facts are not extractable / directional).
R5. The review's method example ("double vs add two") is more ambitious than the implemented world (a one-parameter cyclic shift family). The document should say the current world tests parameter identification, not method acquisition.
R6. Evidence map "Can a learned network generate fast weight writes?" Schlag et al. is correct as cited, but the better precedent for a LEARNED, GATED writer is Backpropamine / MNM.
R7. Titans' "persistent memory" term means input-independent learnable parameters (Sec. 3.3), not persistence across deployments; the review does not misuse it, but readers may.
R8. Math checks all pass (SGD step, interference, eta = 1 exactness, V K+, 16 B/param, 8.39 MB, E[max(0, eps)] > 0).

## My ranked objections (independent)
O1. The evaluation world cannot separate the four capabilities (fact recall, procedure selection, composition, new-method acquisition) or test type inference: one latent per entity, family in surface form, oracle checker. Any success = "store 24 numbers + decoder arithmetic." Fix the world before any architecture decision.
O2. Addressing: input-only, shared write/read cue -> string-keyed lookup; loop cannot re-query; composition impossible by construction. Fix: z-dependent cues, teach/query surface separation, held-out templates.
O3. Linear delta banks: rank-d capacity, interference with learned keys, no decay gate. One-shot writes without replay accumulate interference. Slot/softmax memory (GRACE-, Larimar-, Hopfield-style) likely dominates on capacity and locality and is still "weights". At minimum add a gate and an orthogonality pressure; run known-good-key positive control.
O4. Writer training: with an oracle checker, "write the label" is optimal -> always-write attractor; skip is never valuable; R = B - lambda D via RL with four heads is delayed, noisy, biased (max(0,.)); the differentiable content/cue path will carry the value. Make skip valuable (noisy/false teachings) or drop the RL heads initially.
O5. Depth/stopping: on constant (x, m) extra depth is fixed-point iteration; expect flat/degrading quality by depth; no compute penalty + noise -> "continue" drift; deployment has no oracle and the confidence threshold is uncalibrated. Baselines: fixed depth, KL-exit, self-consistency.
O6. Experimental design: "no persistent writes" has zero capacity so it is not an equal-capacity control (use random/shuffled-content writes); power is feasible at this scale IF training converges within 10 min, which is the real risk; positive controls: one-hot keys + oracle content, then learned cue + oracle content, then both learned.
O7. Resources: bytes are a non-issue for the prototype; config mismatch (10 vs 100 GB); the binding constraint is the 10-minute wall clock for joint from-scratch training of encoder, cue, reader, writer under RL + functional writes.

## Strongest case FOR
Delta-rule writes are one-step regression with known theory; meta-learned writers (CaMeLS, Backpropamine, MNM) and episodic teach-then-query training (MANN) exist; functional writes allow end-to-end training of cue/content; W separate from theta gives an auditable, reversible learning channel; B/D is the right shape of metric; the tiny scale makes causal interventions (zero W, swap worlds) cheap. No verified source shows the combination fails.

## Simpler competing designs
A. Slot memory with softmax retrieval + learned gate (GRACE/Larimar-like), slots as parameters.
B. Sparse memory finetuning on a product-key memory layer (verified low-forgetting numbers; needs a base LM).
C. CaMeLS-style learned token weighting on ordinary gradient updates + replay.
D. Two-timescale plastic weights inside the recurrent net (differentiable plasticity / Backpropamine).
E. Keep delta banks; drop RL heads; checker-gated writes with differentiable cue/content (fixed-rule + learned representations).

## Most consequential next decision
Define the evaluation world and evidence standard so the four capabilities and type inference are separable and not present in surface form; only then choose linear banks vs slot memory.
