# GPT-6 Pro reply: brain-inspired reasoner contenders (saved by the Thread manager, 2026-09-27T20:16:39Z)

Ben pasted this reply in the Thread manager thread at 20:13:02 UTC. The prompt was reviews/gpt6pro-brain-reasoner-contenders-2026-09-27.md. The text below is the reply as pasted; only the ":chatgpt-content-reference" citation markers were removed (GPT's own link placeholders, no content).

Thread manager checks (20:14 UTC), before anyone acts on it:
- **Correct catch:** the prompt's "sums 200" for dense + replay was sums4 after phase B. T uses sums4 after phase C, which was about 191.84 (470.17 - 128.00 - 150.33, from artifacts/claude-rsn358e4-20260927/RESULTS.md:24). The prompt was wrong, T 470.17 is right.
- **Likely floor effect (inferred):** the proposed gate "64-example maze accuracy >= 50%" is far above current evidence. The best small loop in xfer-1 solved 0.5-1.5% of 9x9 mazes after 1,000 examples (artifacts/claude-xfer1-20260927/RESULTS.md:35-38). Ben chose (20:15) to race designs 3, 1 and 2 with the ladder extended up to 64k examples and the 50% bar report-only.
- The cited papers are real, recognisable works; every design and test below is untested, as the reply says.

---

## Recommendation

**Suggested:** I would race **feedback-written method patches**, **hypothesis-gated dendritic units**, and **persistent relation-state networks** first—in that order for your priorities. The first two are modifications of your looped transformer. **The third is my leading contender for replacing the transformer itself.**

**Untested:** None has demonstrated superiority on your puzzles. Their proposed contributions are specific changes to existing ideas, not eight architectures I can honestly certify as never previously proposed.

I use **shown** for results reported in your prompt, published findings within their tested scope, or explicit arithmetic; **suggested** for an interpretation or prediction; and **untested** for proposed designs and experiments. A label applies to its paragraph or clearly marked block.

## What your current evidence supports

**Shown—your report:** Recurrence substantially improves larger-instance performance against the specified same-size plain transformer. Dense learning with replay also beats the tested expert arrangements on the combined sequential-learning score. There is no reliable few-example result yet.

**Suggested:** Your frozen-expert result points toward an important failure mode: **protecting a component's weights does not protect its behavior when the components feeding it change.** For example, a frozen expert that learned what hidden coordinate 17 means can become useless when shared layers change that meaning. Your results are consistent with this explanation, but do not isolate it experimentally.

**Shown—comparison limits:** Equal parameters, examples, and optimizer steps do not imply equal computation when one network repeatedly applies its blocks. Also, the component scores quoted for the dense replay model sum to \(128+200+150=478\), not the stated \(470.17\). They may summarize different measurements, but the prompt does not specify that. I therefore use paired experimental thresholds below rather than reconstructing precise forgetting rates from those components.

**Suggested:** The best next invention should change **how experience modifies later reasoning**, not merely make an individual forward pass more elaborate.

---

# 1. Shared design and accounting rules

### What "learning a method" means here

**Untested—operational definition:** After receiving a solved example, a model has learned something reusable only if that experience improves its performance on **different puzzles**. Improving on the same example is insufficient. The central training structure should therefore be:

\[
\text{observe example and correction}
\;\rightarrow\;
\text{change the reasoner}
\;\rightarrow\;
\text{evaluate different examples}.
\]

Include both new-family and previously learned examples in the final evaluation of that change.

**Shown—relevant distinction:** Rapid assimilation into an existing framework has biological support: Tse and colleagues found rapid learning of new flavor–place associations after rats had acquired a relevant associative schema. That does **not** establish one-example learning of an entirely new reasoning algorithm.

### Parameter budgets

**Shown—arithmetic under your stated block structure:** Ignoring embeddings, biases, norms, and heads, the two-block transformer contains approximately

\[
2\bigl(4d^2+8d^2\bigr)=24d^2
\]

matrix weights.

| Width | \(24d^2\) | Remaining to nominal target |
|---|---:|---:|
| 256 | 1,572,864 | 77,136 to 1.65M |
| 512 | 6,291,456 | 108,544 to 6.4M |

**Untested—construction rule:** The designs below reallocate roughly this \(24d^2\) core budget. Their final feed-forward widths must be adjusted after counting the actual vocabulary, positional embeddings, biases, norms, routing, and stop heads. These are buildable sizing recipes, not audited counts of an implementation I have not seen.

**Untested—fairness rule:** Count every expert, writer, controller, and inference-accessible persistent coefficient—not just active weights. Report separately:

- learned model parameters and persistent fast-weight coefficients;
- raw example-memory bytes;
- temporary per-puzzle state and training memory.

Match the first category strictly, give rivals the same raw-example storage allowance, and disclose the third. A giant temporary state is not a giant parameter count, but neither is it free computation.

### Learned stopping

**Shown—prior work:** Learned variable computation is already established territory, including Adaptive Computation Time and PonderNet. Adding a stop head is not itself the novel contribution.

**Untested—common implementation:** For the first three contenders, keep your existing stop-head training procedure unchanged. Each supplies a pooled reasoning state to a head such as

\[
p_{\mathrm{stop},t}
=
\sigma\!\left(w^\top\operatorname{pool}(h_t)+b\right).
\]

Keep the same 48-round safeguard and report learned-stop performance alongside forced-depth performance.

**Suggested:** Do not equate "the state stopped changing" with "the puzzle is solved." A wrong answer can be stable. Any later improvement to halt training should be a separate experiment, using training-time correctness and continuation outcomes—not a rule checker available during inference.

---

# 2. Eight ranked contenders

## 1. Feedback-written method patches

**Suggested—why first:** This most directly targets your main measure: turning a small number of corrected examples into a useful change in the reasoning procedure.

### Brain connection and existing work

**Shown—biology:** Yagishita and colleagues demonstrated that dopamine could promote structural changes at recently activated dendritic spines within a restricted timing window. This supports feedback-modulated plasticity, not the particular learning rule proposed below.

**Shown—closest machine-learning work:** Meta Networks already learn rapid parameter changes from experience, and differentiable neuromodulated plasticity already learns how feedback controls changes in connections. Neither fast weights nor a learned writer is new.

### Proposed mechanism

**Untested:** Keep the looped core, but give it a small, feedback-written modification to its repeated computation.

In plain words: after a corrected puzzle, the writer changes a few adjustable connections that the reasoner can reuse on later puzzles. It does **not** store a written explanation or merely cache the answer.

Let \(A_s\in\mathbb R^{r\times d}\) and \(B_s\in\mathbb R^{d\times r}\) be the patch after support example \(s\). Then:

\[
h_{t+1}
=
F_\theta(h_t,x)
+
g_\theta(x,h_t)\,B_sA_sh_t .
\]

Here, \(g_\theta\) is a learned applicability gate. It receives puzzle content and current state, not a puzzle-kind label.

After feedback:

\[
(\widehat A_s,\widehat B_s)
=
W_\psi\!\left(
\text{support activations},
\text{corrected output}-\text{predicted output}
\right),
\]

\[
A_{s+1}=\rho A_s+(1-\rho)\widehat A_s,
\qquad
B_{s+1}=\rho B_s+(1-\rho)\widehat B_s.
\]

Use bounded outputs and a bounded residual scale. Hold the ordinary weights fixed during immediate support adaptation; update them during sleep.

**Untested—critical training objective:**

\[
\mathcal L
=
\mathcal L_{\text{different new examples}}
+
\lambda\mathcal L_{\text{old examples}}.
\]

The writer earns credit for improving future examples without damaging old ones—not for reproducing its support answer. Query answers never enter the writer at evaluation.

### Contribution, stopping, and size

**Untested—specific proposed contribution:** A bounded, low-rank, feedback-written change **inside the shared recurrent transition**, with content-dependent reuse and an old/new future-example objective. Cross-example training and fast parameter generation are prior art; this exact combination and its puzzle-transfer claim are the proposed contribution.

This improves on generic working-memory fast weights by changing the reasoning dynamics **across puzzles**. The queued implementation's write rule is unspecified, so I cannot certify that it does not already overlap.

**Untested—size:** Use \(r=8\) at \(d=256\), and \(r=16\) at \(d=512\). Reduce each transformer MLP from hidden width \(4d\) to approximately \(3.5d\):

\[
8d^2\text{ attention}+14d^2\text{ MLPs}+2d^2\text{ writer}
\approx24d^2.
\]

A shared writer \(2d\rightarrow d/2\rightarrow2d\), invoked for each rank slot, costs approximately \(2d^2\). The persistent \(A,B\) values add 4,096 or 16,384 coefficients; subtract their allowance and the small gates from the remaining MLP budget. Use the common learned stop head.

### Expected strengths and losses

**Suggested:** Few-example learning is the strongest opportunity: the writer could learn how to make useful changes before encountering the held-out family. Retention may improve because immediate adaptation leaves the backbone untouched, but sleep still needs replay and regeneration of patches in the updated representation. Larger-instance benefits would come from repeatedly applying the learned change, not from an additional scaling guarantee. It matches total size, but the writer consumes capacity that the original solver used directly.

**Suggested—likely failure:** With only a few source families, the writer may learn family-specific tricks rather than a broadly useful update rule. A rank-8 patch may also be incapable of expressing the required new algorithm, or may destabilize repeated computation.

---

## 2. Hypothesis-gated dendritic units

**Suggested—why second:** This is a relatively contained architectural change aimed at reusing old computations without freezing an entire expert.

### Brain connection and existing work

**Shown—biology:** Cortical feedback can engage active dendrites. More recent experiments also found neuron-specific, error-related dendritic signals during learning; these findings do not prove that cortex implements ordinary backpropagation.

**Shown—closest work:** Iyer and colleagues' active-dendrite networks use context-dependent gating and sparse representations for multitask and continual learning. Importantly, their work includes context inference without supplied task IDs. "Remove the task label" would therefore not be a new contribution.

### Proposed mechanism

**Untested:** Replace each ordinary MLP with several gated branches.

In plain words: each cell has a few reusable calculation routes. Which routes are active depends on what the model currently believes, and can change as it thinks—not just when a new puzzle arrives.

For cell \(i\):

\[
u_i^t
=
\sum_{b=1}^{4}
D_b
\left[
\phi(A_bh_i^t)
\odot
\sigma(B_bh_i^t+C_bc_t)
\right].
\]

A simple initial context is

\[
c_t=\operatorname{mean}_i(h_i^t-x_i).
\]

Thus \(c_t\) reflects the developing computation relative to the input. It contains no true query answer.

**Untested:** Use soft gates initially, ordinary gradient learning, and the same replay as the dense baseline. Do not simultaneously add frozen branches, growth, a new optimizer, and a new replay strategy.

### Contribution, stopping, and size

**Untested—specific proposed contribution:** The proposed distinction is **recomputing branch context from the evolving hypothesis during each reasoning round**, rather than selecting a largely fixed task-context subnetwork. Its novelty would need a closer comparison against recurrent contextual-gating models before a publication claim.

**Shown—conditional size arithmetic:** With four branches and branch width \(m=d/2\), each branch uses four matrices costing approximately \(4dm\). Therefore:

\[
4\text{ branches}\times4d(d/2)=8d^2,
\]

matching one original MLP's matrix budget. Branch width is approximately 128 or 256 at the two target scales. Adjust slightly for extra biases. Attention, the outer recurrence, and learned stopping remain unchanged.

### Expected strengths and losses

**Suggested:** Few-example learning could improve through recombining existing branches. Retention could improve if different problems change partially different pathways. Longer thinking remains available, but there is no clear additional size-generalization advantage over the loop itself. Total parameters are well controlled, although gating adds operations.

**Suggested—likely failure:** This can collapse into another weak expert system. Gates may saturate, branches may receive little useful training, or changing shared attention and embeddings may still disrupt every branch. **It does not solve the frozen-interface problem by construction.**

---

## 3. Persistent relation-state network

**Suggested—why third:** This is the strongest first-race candidate whose core computation is genuinely different from a transformer: the network carries evolving beliefs about **relationships**, not only about cells.

### Brain connection and existing work

**Suggested—brain connection:** Borrow the distinction between reusable relational structure and the particular objects occupying that structure. This is a computational interpretation of hippocampal–entorhinal organization, not evidence that the brain stores the matrix below.

**Shown—closest work:** Whittington and colleagues developed a structural-memory model separating environmental structure from particular sensory entities. Recurrent Relational Networks already perform iterative relational reasoning, including Sudoku; Neural Relational Inference already learns interaction structure. None of those broad ingredients is new.

### Proposed mechanism

**Untested:** Keep a state \(h_i\) for each cell and an additional state \(r_{ij}\) for each directed pair of cells.

In plain words: besides asking "what belongs in this cell?", the model keeps revisable working beliefs about "how does this cell relate to that one?"

Let \(v_i\) be the unchanged input-symbol representation and \(p_{ij}\) generic relative geometry:

\[
r_{ij}^{t+1}
=
\operatorname{GRU}_e
\left(
r_{ij}^{t},
[P_hh_i^t,P_hh_j^t,P_v(v_i-v_j),p_{ij}]
\right),
\]

\[
m_i^t
=
\frac1N\sum_j
(Ur_{ij}^{t+1})\odot(Vh_j^t),
\]

\[
\widetilde h_i^{t+1}
=
\operatorname{GRU}_n(h_i^t,[x_i,m_i^t]),
\]

\[
h_i^{t+1}
=
\widetilde h_i^{t+1}
+
\operatorname{MLP}(\widetilde h_i^{t+1}).
\]

A GRU is simply a recurrent update with learned controls over what to retain and replace.

**Untested:** Start with all pairs. Do not supply a Sudoku constraint graph, a maze solver's adjacency decisions, or digit-carry rules. Geometry and cell contents are inputs; their relevance must be learned. Relation states reset between puzzles, not between reasoning rounds.

### Contribution, stopping, and size

**Untested—specific proposed contribution:** Persistent directed relation states, coupled to evolving cell hypotheses while preserving access to original symbols, evaluated for held-out-family adaptation. This is not merely attention with a biological name, although it remains close to recurrent graph-network research.

**Shown—conditional size arithmetic:** Set relation width \(q=d/4\), giving 64 or 128. The displayed GRUs and projections cost approximately \(11.6875d^2\). A residual MLP with hidden width \(6.15625d\)—1,576 or 3,152—adds \(12.3125d^2\), bringing the matrix core to \(24d^2\). Adjust for heads and biases. Use the common learned stop head on cell states.

**Shown—working-state cost:** For 121 cells and \(q=64\),

\[
N^2q=121^2\times64=937{,}024
\]

relation-state values, approximately 3.75 MB in float32 **per example for one state snapshot**. Training needs additional activations and retained rounds.

### Expected strengths and losses

**Suggested:** Few-example gains would come from learning reusable relational updates rather than family-specific global patterns. Shared pairwise operations may also transfer to more cells. There is **no dedicated long-term retention mechanism**; replay remains necessary. Stopping is learned, and parameters match, but all-pairs recurrent state may make this the slowest of the first three.

**Suggested—likely failure:** It may spend most of its capacity maintaining irrelevant relations. Preserving input symbols does not automatically produce symbol-independent reasoning, and there may be too little source-task diversity to learn useful relational primitives.

---

## 4. A thalamus-inspired microstep scheduler

**Suggested—main bet:** Learn how to compose small operations into a new procedure, instead of assigning an entire puzzle to an expert.

### Brain connection and existing work

**Shown—biology:** Schmitt and colleagues' work links thalamic amplification of cortical connectivity with attentional control. Treating this as a literal software scheduler would go beyond the evidence.

**Shown—closest work:** Recurrent Independent Mechanisms already selectively update communicating recurrent modules. Neural Production Systems already learn reusable, selectively applied operations. Modular routing and learned rules are therefore prior art.

### Proposed mechanism

**Untested:** Give four small recurrent modules a shared cell workspace. A controller chooses a module and where it reads and writes; a fifth action is STOP.

\[
c_{t+1}=\operatorname{GRU}_c(c_t,\operatorname{pool}(h_t)),
\]

\[
a_t\sim\pi_\theta(\,\cdot\mid c_{t+1}),
\qquad
a_t\in\{1,2,3,4,\mathrm{STOP}\},
\]

\[
\alpha_i=\operatorname{softmax}_i((Wc_{t+1})^\top h_i),
\]

\[
s_{a_t}'=\operatorname{GRU}_{a_t}
\left(s_{a_t},\sum_i\alpha_i h_i\right),
\]

\[
h_i'=h_i+\alpha_iD_{a_t}(s_{a_t}'-s_{a_t}).
\]

In plain words: the model chooses its next small mental operation and which information that operation should affect. No module is named "carry," "check row," or "find path."

**Untested—proposed distinction:** Persistent module states plus a controller that revisits unresolved parts of its workspace, trained on future-example improvement after support feedback. This is a specific compositional-learning hypothesis, not a claim that learned neural production systems are new.

**Untested—size:** At \(d=256/512\), use four modules of width \(d/2=128/256\). Four GRUs receiving \(d\)-wide inputs cost about \(9d^2\); the controller costs \(6d^2\); read/write projections about \(3d^2\). Allocate the remaining \(6d^2\) to workspace processing. Count all four modules even when only one runs.

**Suggested—trade-offs:** Few-example learning could benefit from recombining operations; selective use might reduce interference; longer schedules could solve larger puzzles. STOP is an explicit learned action. Against those advantages, the controller and routing consume a substantial fraction of 1.65M weights, and module starvation could reproduce your expert failures. I would test this after the first three, not alongside several routing changes.

---

## 5. Feedback-gated, multi-timescale synapses

**Suggested—main bet:** Let new changes happen quickly, but require stronger evidence before they influence slower, more persistent connection values.

### Brain connection and existing work

**Suggested—biology:** Borrow the idea that memory-related changes can occupy interacting processes with different persistence times. The equations below are a computational model, not a measured complete description of a biological synapse.

**Shown—closest work:** Kaplanis and colleagues applied complex, multi-timescale synapses to continual reinforcement learning. More recent Nested Learning work also explicitly treats interacting learning processes and memory at different timescales. "Add fast and slow weights" is not novel.

### Proposed mechanism

**Untested:** Give a restricted subset of connections three values: fast \(a\), medium \(b\), and slow \(c\). Only \(a\) participates directly in the forward pass.

\[
a' = a-\eta g+\kappa_1(b-a),
\]

\[
b' = b+\lambda_t\kappa_1(a-b)+\kappa_2(c-b),
\]

\[
c' = c+\kappa_2(b-c).
\]

Use simultaneous updates with bounded coefficients.

The proposed addition is a learned promotion gate:

\[
\lambda_t
=
\sigma\!\left(
w^\top[
\|g_{\rm recent}\|,
\|g_{\rm replay}\|,
\langle g_{\rm recent},g_{\rm replay}\rangle,
\text{usage statistics}
]+b_0
\right).
\]

**Untested:** Train that gate on later new and old examples. In plain words: it learns when a recent change looks useful enough to affect longer-lived memory. It is not handed a task boundary or a hand-coded rule that conflicting gradients must always be rejected.

**Untested—specific contribution:** Future-example-trained promotion between timescales, conditioned on recent/replay agreement, within a strictly budgeted subset of connections. This is a narrow extension of existing consolidation methods.

**Shown—size arithmetic:** Triplicating one-eighth of a base network adds two extra copies of that eighth:

\[
P_{\rm total}=P_{\rm base}(1+2/8)=1.25P_{\rm base}.
\]

Thus the base network can use approximately 1.32M or 5.12M coefficients before small gate adjustments. Do not present a 1.65M backbone plus uncounted slow copies as a 1.65M model. Keep the ordinary learned stop head.

**Suggested—trade-offs:** This targets retention more directly than new-family learning. Fast values permit immediate adaptation; slower values may resist forgetting. It provides no independent advantage for larger puzzles, and matched size means less forward-pass capacity. A conservative gate can preserve ignorance just as effectively as knowledge. Limited replay and changing shared representations can still defeat it.

---

## 6. Episodic repair memory with current-state re-encoding

**Suggested—main bet:** Reuse a past correction without depending on an old hidden representation retaining its meaning forever.

### Brain connection and existing work

**Shown—biology:** Suppressing hippocampal sharp-wave ripples impaired spatial memory in Girardeau and colleagues' experiments, supporting a role for these events in consolidation. That does not show that sleep performs the exact replay algorithm proposed here.

**Shown—closest work:** Fast experience-dependent memory and slower learned knowledge are already central to complementary-learning approaches; Meta Networks also combine rapid adaptation with learned cross-task knowledge.

### Proposed mechanism

**Untested:** Store a bounded number of raw correction episodes:

\[
e_j=(x_j,\widehat y_j,y_j).
\]

Whenever memory is read, encode the episode using the **current** network:

\[
z_j=E_\theta(x_j,\widehat y_j,y_j),
\]

\[
r_t=\sum_j
\operatorname{softmax}_j(q_t^\top z_j)\,z_j,
\qquad
h_{t+1}=F_\theta(h_t,x,r_t).
\]

In plain words: retain "what I saw, what I answered, and the correction," then interpret that experience afresh when needed. Do not assume a hidden vector saved before sleep still means the same thing afterward.

**Untested—specific contribution:** Retrieval of correction relationships, re-encoded in current coordinates, with success measured on different puzzles rather than on stored-answer retrieval. This is a relatively modest architectural novelty claim.

**Untested—size:** Reduce the loop core to about \(20d^2\). Use approximately \(4d^2\) for an episode encoder—for example, a shared \(3d\rightarrow d\rightarrow d\) mapping over aligned input, prediction, and correction representations. This fits both widths after final accounting. Start with 128 raw episodes and give controls an equal byte allowance. Use the common stop head.

**Suggested—trade-offs:** It could adapt quickly when a new puzzle resembles a past failure and help retention through replay. Re-encoding addresses one kind of stale-memory problem, not all forgetting. Larger-puzzle transfer depends on learning an abstract correction rather than retrieving a similar-looking answer. Retrieval also adds compute, and a 1.65M model may be too weak to extract transferable methods from these records.

---

## 7. A cerebellum-inspired internal repair predictor

**Suggested—main bet:** Learn to predict which small change to the current attempted solution will help before committing to it.

### Brain connection and existing work

**Shown—biology:** Tseng and colleagues found evidence that sensory prediction errors drive cerebellum-dependent adaptation of reaching. Extending that mechanism to abstract puzzle reasoning is **suggested**, not shown.

**Shown—closest work:** Imagination-Augmented Agents already combine learned predictions with decisions. The general idea of a model helping evaluate candidate actions is established.

### Proposed mechanism

**Untested:** Produce two candidate changes to the internal state:

\[
\widetilde h=F_\theta(h_t,x),
\qquad
h^{(k)}=\widetilde h+G_\phi(\widetilde h,e_k),
\quad k=1,2.
\]

Include the unchanged state \(h^{(0)}=h_t\). A learned evaluator scores them:

\[
k^*=\arg\max_{k\in\{0,1,2\}}V_\psi(x,h^{(k)}).
\]

Choosing \(k=0\) means STOP; otherwise continue with the chosen candidate.

**Untested:** During training, supervise the evaluator using actual outcomes of its proposed edits, including whether a further rollout improved the answer. At inference, it receives no correctness oracle. Neither proposal is generated by a hand-written legal-move rule.

**Untested—specific contribution:** Predicting the effects of edits to a **reasoning state**, rather than actions in a physical environment, with the proposer and evaluator trained jointly from generated puzzles and corrections.

**Untested—size:** Allocate approximately \(18d^2\) to the recurrent core, \(3d^2\) to a shared two-proposal generator, and \(3d^2\) to the evaluator. For example, a \(d\rightarrow1.5d\rightarrow d\) MLP costs \(3d^2\). Use action embeddings to distinguish proposals rather than two separate generators.

**Suggested—trade-offs:** Useful repair directions could accelerate few-example adaptation, and repeated repairs could extend to harder puzzles. There is no independent retention protection beyond replay. It has explicit learned stopping, but candidate generation and evaluation cost extra computation. At tiny scale, the evaluator may be too inaccurate to justify taking weights away from the solver; it can also reward misleading internal states. I would not assume this fixes the number puzzles.

---

## 8. A coarse-to-fine recurrent energy circuit

**Suggested—main bet:** Let distant parts of a large puzzle influence one another through a small coarse representation, while retaining detailed cell states.

### Brain connection and existing work

**Shown—biology:** Feedback interactions with active dendrites provide evidence for bidirectional cortical processing. The claim that cortex literally runs a multigrid solver remains **suggested**, not shown.

**Shown—closest work:** MgNet explicitly connects multigrid computation and neural networks. Hierarchical iterative correction is therefore not new, and neither is generic energy settling.

### Proposed mechanism

**Untested:** Maintain fine cell states \(h\) and a smaller coarse workspace \(z\). Learn an energy such as

\[
E_\theta(h,z;x)
=
\sum_i
\left\|
h_i-f_\theta(h_i,x_i,[Uz]_i)
\right\|^2
+
\sum_a
\left\|
z_a-g_\theta(z_a,[Rh]_a)
\right\|^2.
\]

Alternate updates:

\[
h\leftarrow h-\alpha\nabla_hE,
\qquad
z\leftarrow z-\beta\nabla_zE.
\]

In plain words: detailed cells and a rough overview repeatedly correct one another. The energy contains **learned** consistency tests, not programmed Sudoku constraints or arithmetic laws.

**Untested—specific contribution:** Add learned coarse/fine correction to the queued settling contender, with shared mappings usable on larger layouts. That is a concrete improvement over local-only settling, not a replacement name for it.

**Untested—size:** A fine network \(3d\rightarrow4d\rightarrow d\) costs \(16d^2\); a coarse network \(2d\rightarrow2d\rightarrow d\) costs \(6d^2\); two \(d\)-wide transfer projections cost \(2d^2\). Their total is \(24d^2\), before final small-parameter adjustments, at either width. Use a learned stop head—not an energy threshold.

**Suggested—trade-offs:** This has a clearer argument for larger-puzzle communication than for few-example learning or retention. Those latter goals still require suitable training and replay. It is parameter-efficient across levels, but differentiating through energy gradients can be computationally expensive. Coarse summaries may also erase precisely the distinctions needed for an exact symbolic answer. I would rank it below the learning-focused contenders.

---

# 3. The first three sealed experiments

## Common protocol

**Untested—proposed registration:** These are promotion thresholds for a small pilot, not predictions of achievable scores or a statistical guarantee of superiority.

### Train without the target family

**Untested:** Pretrain on **grids and sums only**. Exclude every maze example from ordinary training, adaptation training, validation, and curriculum construction. Merely withholding larger mazes would test size transfer, not learning a new kind.

Train each pretrained architecture on the same source examples and the same support-then-query episode schedule. The source generator may form related episodes, but the model receives no family IDs.

**Untested:** For the learning-to-learn portion, apply an identical outer objective: performance on different examples after support feedback, including retained old examples. Differentiate through the last two adaptation steps and detach earlier adaptation history. Keep the reasoning-round truncation policy matched separately. A control must not be denied this training structure while only the new writer receives it.

### Measure support efficiency

**Untested:** Use support sizes

\[
k\in\{1,4,16,64\},
\]

with nested, sealed support sets. Permit eight shuffled passes over each support set for every arm; repeated presentation does not increase the stated number of unique examples.

For each \(k\), start from a clean copy of the source-trained model and evaluate 300 unseen mazes, stratified across 5×5 and 7×7. Record zero-support accuracy separately.

Define the primary score, in percentage points:

\[
F=\frac{A_1+A_4+A_{16}+A_{64}}4.
\]

Also report \(F-A_0\), because strong zero-shot performance and rapid learning are different achievements.

**Untested—controls:** Each contender faces a source-trained dense loop, a source-trained plain transformer, and a fresh network of its own architecture. **The fresh network may learn by ordinary supervised gradient updates.** Do not freeze a randomly initialized writer and present its inability to adapt as a meaningful fresh-network comparison.

**Untested:** Evaluate old and new queries in mixed order, with no task-triggered memory reset. A puzzle's temporary working state may reset between puzzles; persistent learned memory may not reset merely because the evaluator knows the family changed.

### Test sleep without granting more new evidence

**Untested:** After the 64-example adaptation branch, run a fixed sleep phase:

\[
512\text{ updates}\times16\text{ examples/update},
\]

with eight old examples and eight examples drawn from those same 64 maze supports per update. Use the same raw replay allowance across arms—for example, 128 stored grids and 128 stored sums. Do not silently add thousands of new maze examples during this phase.

Record old accuracy before maze adaptation, after adaptation, and after sleep. Let \(R_{\rm before}\) and \(R_{\rm after}\) be mean old-family accuracy before adaptation and after sleep, and define

\[
D=R_{\rm before}-R_{\rm after}.
\]

Report grids and sums separately as well; an average can hide complete loss of one kind.

### Common eligibility gates

**Untested:** Use two paired model seeds, matching support draws and query sets across arms. Require the stated gains in **both seeds**, not merely in their mean. Before considering a contender successful:

- its source-task performance must be within three percentage points of the loop on each old family;
- its 64-example maze accuracy must reach 50%;
- its \(F\) must exceed both the pretrained plain model and its fresh counterpart by at least five percentage points.

The 50% floor is an intentionally demanding engineering target. Missing it rejects promotion at this budget; it does not disprove the mechanism universally.

**Untested:** For recurrent models, retain the existing learned halt procedure. Report a stop failure when learned stopping loses more than two percentage points relative to the model's fixed-depth setting selected on source validation. Report mean rounds and cap-hit rate. Run the larger-maze evaluation at 9×9 and 11×11 as a secondary test, not a substitute for the few-example endpoint.

---

## Test A: Does the learned patch transfer useful changes?

**Untested—single experimental change:** Replace ordinary immediate adaptation with the feedback-written recurrent patch, including the required parameter reallocation. Do not add dendritic branches, growth, or new stopping logic.

**Untested—pass marks:** In both seeds:

\[
F_{\rm patch}-F_{\rm loop}\ge10\text{ percentage points},
\]

while satisfying the common eligibility gates and ending sleep no more than three points below the loop on either old family.

**Untested—registered negative result:** Reject this implementation at this budget if it improves support answers but has \(F\le F_{\rm loop}\) in both seeds, or if it gains new-family accuracy only by exceeding the allowed old-family damage.

**Suggested—interpretation:** This distinguishes a writer that learned useful adaptation from one that merely found a compact way to fit its examples. The first-race result would not establish that its stored changes correspond to human-readable "methods."

---

## Test B: Do evolving dendritic gates reduce interference without blocking learning?

**Untested—single experimental change:** Replace the MLPs with the hypothesis-gated branches. Keep the optimizer, replay, adaptation schedule, and stopping procedure matched.

**Untested—pass marks:** In both seeds, require

\[
F_{\rm dendritic}-F_{\rm loop}\ge5\text{ points},
\]

plus the common gates, and a reduction in forgetting satisfying

\[
D_{\rm loop}-D_{\rm dendritic}
\ge
\max(3\text{ points},\,0.5D_{\rm loop}).
\]

Post-sleep maze accuracy must be no more than three points below the loop.

**Untested—registered negative result:** Reject the proposed learning-and-retention claim if the network preserves old performance by failing to acquire mazes, or if both seeds show no improvement in either \(F\) or forgetting.

**Suggested—important boundary:** If the loop scarcely forgets under this sleep schedule, the retention comparison has insufficient headroom. Report that endpoint as inconclusive rather than declaring the biological idea refuted or changing the replay difficulty after seeing results.

---

## Test C: Do persistent relations support faster acquisition of a new kind?

**Untested—single experimental change:** Replace the transformer reasoning cell with the relation-state circuit. Keep the data, objective, adaptation budget, and replay fixed.

**Untested—pass marks:** In both seeds:

\[
F_{\rm relation}-F_{\rm loop}\ge10\text{ points},
\]

with the common gates and no greater than three-point post-sleep deficit on either old family.

**Untested—registered negative result:** Reject its proposed few-example advantage if \(F\le F_{\rm loop}\) in both seeds, even if it performs better on 11×11 mazes after extensive adaptation. That would support a different claim—larger-instance solving—not your primary one.

**Suggested—interpretation:** A win would support this entire recurrent-cell replacement. It would not yet identify whether persistent edges, the symbol path, or the changed computation distribution caused the gain. Those are subsequent single-factor ablations, not conclusions available from this first race.

---

## CPU-run accounting

**Shown—run arithmetic for the proposed protocol:** One independently controlled race requires two seeds each of the contender, pretrained loop, and pretrained plain model: **six source-training runs**, plus **two fresh-model support-only jobs**.

Identical loop and plain controls can be shared across the three races:

| Work across all three races | Count |
|---|---:|
| Source-trained contenders: 3 designs × 2 seeds | 6 |
| Shared source-trained loop and plain controls: 2 × 2 | 4 |
| Fresh contender controls: 3 × 2 | 6 |
| **Total** | **10 source-training runs + 6 support-only jobs** |

**Shown—conditional arithmetic:** Ten runs at your existing baseline's 1.5-hour cost would equal 15 baseline-reference CPU-hours. That is **not** an estimate of this protocol's actual runtime: adaptation training, evaluation branches, sleep, and the more expensive relation circuit add work.

**Suggested:** The defensible cost commitment is the run count. Exact CPU time needs the missing source-update budget and measured per-step costs. No evidence supplied supports promising that every proposed GPU run fits $4.

**Untested—compute check:** Keep parameter-matched results primary, as requested, but also report training operations and inference time. Add a secondary evaluation at matched inference computation. A relational circuit should not receive credit for "better reasoning per computation" merely because its nominal round performs much more work.

---

# 4. Honest architectural and novelty audit

**Shown—by construction:** Designs 1 and 2 remain looped transformers. Designs 5 and 6 also remain transformer-based when attached to the proposed backbone, and design 7 is a transformer-centered planning hybrid. Those can constitute meaningful architecture research, but they are not replacements for the transformer family.

**Shown—by construction:** Design 3 is a recurrent relation-state network; design 4 is a modular recurrent controller; design 8 is an iterative energy system. Those are more substantial departures. Their constituent ideas still have clear published predecessors.

**Suggested:** The highest risk at 1.65M is spending too much capacity on managing reasoning instead of performing it. The scheduler needs competent modules *and* a competent controller. The repair predictor needs useful proposals *and* a trustworthy evaluator. The energy circuit needs a useful landscape *and* stable optimization. A larger model might absorb those overheads; your tiny model may not.

**Suggested:** Dendritic gating and method patches deserve earlier tests because they make smaller reallocations around an already functional solver. The relation-state model deserves a place because it tests a meaningfully different representation of the problem.

**Untested—novelty standard:** I would make the eventual research claim something like:

> "At a fixed total-weight budget, this particular feedback-driven change to recurrent computation improves acquisition of a held-out puzzle family while preserving previous families."

That is sharper and more defensible than "we copied the brain" or "we invented a new kind of neuron."

**Suggested—missing facts that matter:** The exact queued fast-weight update determines whether design 1 is genuinely distinct from that queue. Vocabulary and positional-embedding sizes determine exact widths. Source-task diversity determines how much reusable adaptation can plausibly be learned. The validity and canonicalization rules for mazes and number puzzles determine whether exact-answer scoring unfairly rejects alternative correct solutions. None of these unknowns justifies borrowing results from your other project components.

---

# Plain-language summary

**Shown:** Your repeated-thinking model solves bigger puzzles better than the plain model in the tests you reported.
**Suggested:** The next improvement should help it learn from corrections, not just think for longer.
**Untested:** First, I would try a model that turns a correction into a small change in how it works, rather than saving a written guide.
**Untested:** Second, I would try several small calculation routes that it can switch between as its understanding changes.
**Untested:** Third, I would try a model that keeps track of relationships between cells as well as the cells themselves.
**Suggested:** These borrow the brain-inspired ideas of changing connections after feedback, choosing useful pathways, and reusing relationships.
**Untested:** I would keep a design only if a few solved examples help it solve different puzzles without sacrificing the old kinds.
**Suggested:** The relationship model is the clearest break from your transformer, while the first two are the more cautious first experiments.
