Read the shared brief FIRST and follow its required report structure exactly: /private/tmp/claude-502/-Users-ben-hannan-Desktop-projects-beautiful-model/a6cbbe20-5a16-4ad6-87ee-2f54ff4ef5c6/scratchpad/agents/brief.md
Then read the four files it lists. Write your whole report in ONE final message.

You are Reviewer 2 of 5: MEMORY AND WRITER. Your assigned research question: can a bank of delta-rule float32 matrices plus a learned writer serve as persistent, correctable, low-interference memory for facts and methods, and can the writer be trained at all under the proposed signals?

Challenge specifically:
- Capacity and interference: banks are d x d (draft: 4 banks, d = 48). Derive what one bank can store exactly, what happens with non-orthogonal keys, how interference scales with the number of writes, and whether bank routing changes the picture. Give the equations.
- Replay convergence: sequential delta updates are Kaczmarz projections. When do they converge, when do they cycle (conflicting targets, corrections), and what does the absence of any decay or forgetting gate in W_new = W + eta (v - W k) k^T imply for corrections? Compare Gated DeltaNet's decay gate and Titans' forgetting gate.
- Addressing: the draft computes the write key and the read key with the same cue network from the input encoding. What does paraphrase-invariant addressing require, and what does it mean that the teaching input and the query input can be the same string? How would workspace-dependent cues change addressing?
- Representation drift: if the encoder or cue network keeps training after writes, old keys become unreadable. Freezing theta and rho stops drift but also stops representation learning. Is there a middle path (e.g., key re-encoding, replay re-writes, slow/fast timescales as in Nested Learning) and what does it cost?
- Correction handling: superseding a fact, negation, and "unlearning" in a linear matrix; what is the minimal mechanism?
- RL credit assignment for the writer: four discrete actions (write/skip, bank, trace slice, strength) with reward R = B - lambda D measured by later queries. Analyze the noise, delay, and variance; the E[max(0, eps)] > 0 bias; and whether an always-write or never-write policy is a likely attractor. Which parts can be trained differentiably through the functional write instead?
- Separation of W from theta: does freezing theta actually protect old capabilities when every forward pass mixes in a memory read? What does a bypass/rollback guarantee and not guarantee?
- Compare against GRACE, SERAC, Larimar/Kanerva Machine, sparse memory finetuning, MemoryLLM, Metalearned Neural Memory, Backpropamine, and CaMeLS: which of Ben's goals does each already satisfy, and what is left for this design to add?
