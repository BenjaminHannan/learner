# A model that discovers new quantities it can reason with

20 September 2026. Research proposal, not an implementation or result. No model training or evaluation was run for this proposal.

Ben's target is a model that independently acquires useful new concepts and uses them to make discoveries, with a measured advantage over competing AI systems. A previously unseen sentence, a longer lookup chain, or a newly named macro does not establish that capability.

**Recommendation:** investigate learning new state variables and their rules from experience, then making those variables persistent, callable parts of the reasoner's working vocabulary. The initial experiment should test whether this makes discovery and subsequent learning more efficient than equally equipped transformers and existing latent-variable discovery methods. This is an established research direction with an untested application to Premonition; it is not a claim to have invented a new algorithm or solved general creativity.

**Plain-language example.** Objects sometimes activate a device, sometimes fail, and change one another when brought into contact. The model is never told that the objects contain a transferable hidden quantity. From observations and experiments, it learns a quantity that explains these changes, learns how actions change that quantity, and uses it to predict unfamiliar situations. We might call the result “stored charge.” The model does not need that word. Its invention is the usable explanatory representation.

This establishes a concept that is new to the learner. It would not establish a discovery new to humanity: the simulator designer already knows the hidden mechanism. A later scientific task with independently verified unknown results would be needed for that stronger claim.

**What the mechanism would actually do — all untested here.**

1. Learn to predict observations following actions using its current representation. Record systematic prediction failures on fresh episodes. Prediction error is evidence of model inadequacy, not proof that a particular missing concept exists; noise, poor optimization and missing observations can also cause it.
2. Fit a small additional state variable from observation/action history. Learn its initializer, its update under actions, and the way it affects predicted observations. These are learned functions, not a human-provided definition of charge, conservation, or another target concept. A first implementation can use a gated pool of scalar state modules with a fixed upper bound, learning how many to activate.
3. Train the variable and its update jointly with predictions over several future steps. Prefer compact explanations using a declared complexity penalty. A tiny neural update function is a practical first choice. A sparse symbolic update can be a separate implementation, with every allowed primitive disclosed. Adding a module does not create semantics by itself; the predictive training and transfer tests must establish its usefulness.
4. Select candidates using a separate discovery-validation stream. Retain a variable only when it improves predictions enough to pay for its extra storage and computation. Shared prediction failures across different objects or settings favor a reusable explanation. Do not give the learner labels identifying the hidden quantity, its count, its conservation law, or the simulator's latent state.
5. Persist the learned estimator and update rule with an arbitrary identifier. Expose calls that initialize the state from observations, update it after an action, and predict observations from it. The reasoner can then use the discovered quantity in later predictions and planning. Human-readable naming is optional and does not earn discovery credit.

An illustrative fitting objective is

`prediction loss on action-conditioned trajectories + lambda * active-state cost + mu * update-function complexity`.

This is a predictive bottleneck with model selection, not a novel objective. Estimate the complexity cost using an explicit coding or parameter-count convention; do not describe an arbitrary regularizer as exact minimum description length. Candidate optimization uses discovery-training data, model selection uses discovery-validation data, and final scoring uses untouched test episodes. All fitting and rejected candidates count toward the compute budget.

**Why this is separate from the excluded proposals.** The changed object is the model's explanatory state: what quantities it represents and how those quantities evolve. Replaying or splicing lookup programs leaves those quantities supplied by the designer. Here the learner must infer them. There is no dream phase, macro extraction, analogy curriculum, role/filler split, halting repair, progress critic, or random replacement of controller units in the proposed first experiment. A generic generate-and-evaluate loop alone would not be the contribution; prediction learning must construct the previously unspecified state variables and update rules.

There is nevertheless overlap with older work and with the repository's earlier idea inventory. `reviews/newidea-reply-gpt-summary-2026-09-19.md` already lists counterexample state splitting and bottleneck growth among rejected novelty candidates. Allocating state after prediction failures is closely related. Calling it a new name would not resolve that overlap. The reason to consider this route is its fit to the capability Ben wants, not an assertion that its ingredients have never been proposed.

All computational concepts are implemented using an existing substrate. A learned quantity can be a useful new concept even though its estimator uses ordinary arithmetic. This experiment cannot show creation outside every human-specified hypothesis class, and should not claim that standard neural networks cannot learn the same representation.

**What the literature establishes.**

| Primary source | Relevant finding and limit |
| --- | --- |
| [Iten et al., Discovering Physical Concepts with Neural Networks, 2020](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.124.010508) | SciNet learns representations related to physical parameters in selected toy problems. Learning physical concepts through a bottleneck is already demonstrated in restricted settings. It does not establish general autonomous invention. |
| [Champion et al., Data-driven discovery of coordinates and governing equations, 2019](https://arxiv.org/abs/1904.02107) | Jointly learning coordinates and sparse dynamics is close prior art. A sparse latent dynamics implementation must be compared against this family, not presented as an unprecedented mechanism. |
| [Chen et al., Automated discovery of fundamental variables hidden in experimental data, 2022](https://pubmed.ncbi.nlm.nih.gov/38177869/) | Discovers candidate state variables and estimates intrinsic dimension from videos of physical systems. This supports the feasibility of finding variables without their labels; it does not make every learned variable an identifiable causal concept. |
| [Wu and Tegmark, AI Physicist, author implementation](https://github.com/tailintalent/AI_physicist) | Includes theory simplification, unification and lifelong reuse. Saving and reusing discovered theories is also prior art. |
| [Bing et al., Identifying Linearly-Mixed Causal Representations from Multi-Node Interventions, 2024](https://proceedings.mlr.press/v236/bing24a.html) | Causal-variable recovery depends on assumptions about mixing and the interventions available. Observational prediction alone does not identify a unique hidden explanation. |
| [Courellis et al., Abstract representations emerge in human hippocampal neurons during inference, 2024](https://www.nature.com/articles/s41586-024-07799-x) | Human recordings associate successful inference with abstract representations of observed and latent task variables. This is motivation for studying useful latent representations, not a demonstrated neural algorithm for creating concepts or an explanation of all creativity. |
| [Novikov et al., AlphaEvolve, 2025](https://arxiv.org/abs/2506.13131) | Reports verified algorithmic discoveries using LLMs and evolutionary evaluation. Existing AI can contribute novel results. This is relevant to the comparison standard, not a proposal to reuse Ben's excluded generate-and-evaluate approach. |

Source inspection was a targeted prior-art check, not an exhaustive novelty audit. The hypothesis of superior discovery efficiency remains untested.

**A bounded first experiment.** Build a separate interactive simulator; the current lookup task cannot establish this capability. Keep it separate from the card controller and village-language tracks. Existing lookup results neither support nor refute success here.

Use anonymous objects with observable readouts and generic action identifiers. In the main family, a hidden quantity can change within an object, move between objects, and affect a device's output. Randomize identities, initial states, coefficients and irrelevant appearance. Add control worlds in which apparent regularities come from noise or directly observable properties. The learner must decide whether an additional persistent variable is useful. The interface must not expose hidden-state values, simulator source, privileged resets, or names such as “charge.”

For an initial feasibility screen, all systems receive the same fixed intervention traces. This separates representation learning from the separate difficulty of choosing experiments. Later, let all systems choose actions under the same observation and reset budget; do not give only the proposed model active experimentation.

Keep complete world instances separate across development and final evaluation. Within each evaluated world, split discovery-training, discovery-validation and final query episodes. Final tests should include unseen action sequences, new objects, changed distractors, and observations that separate competing explanations. Merely changing random seeds tests new instances, not a new class of concepts. A later claim of general concept invention needs held-out mechanism families and more than one kind of discovered variable.

For every system, measure future-outcome error after fixed discovery budgets such as 32, 64, 128, 256 and 512 transitions. Also measure how much data is needed to reach a fixed prediction threshold. Use a common normalization of squared error by the outcome variance over each benchmark family. Publish raw errors too. Test persistent reuse by presenting a second task using the same hidden dynamics, allowing the same small downstream learning budget, and comparing retained learned state machinery against relearning it.

Never score the word “charge” or require an exact match to the simulator's coordinate system. Equivalent changes of units or coordinate transformations can represent the same discovery. Require correct unseen predictions, useful interventions when supported, and transfer. Removing or permuting the proposed concept state should selectively impair the predictions it supposedly supports, but an ablation alone is insufficient: compare against ablations of ordinary learned features too.

**Comparisons needed to claim an advantage.**

| Comparison | What it rules out |
| --- | --- |
| Transformer predicting the same action-conditioned trajectories, with history and persistent storage | An advantage caused solely by giving one system observations or memory the other lacks. |
| Transformer allowed online fitting, the same extra latent-state capacity and the same training objective | An advantage caused solely by adaptation or the objective, rather than the proposed structure. |
| Transformer using the complete proposed concept mechanism | Whether the improvement belongs to a general method that also helps transformers. A tie would defeat a claim that Premonition's backbone is necessary. |
| Recurrent latent-state model and an applicable coordinate/dynamics discovery baseline | Whether ordinary system identification already explains the gain. Adaptations of published methods must be disclosed. |
| Proposed model with fixed latent dimension, then separately without persistent reuse | Whether selecting concepts or retaining them contributes beyond ordinary representation learning. |

Match information, tool access, tuning effort and total discovery compute. Include all rejected candidates, representation updates, persistent state and inference cost. Report parameter/storage matching and compute matching separately when both cannot be satisfied simultaneously. Larger pretrained systems can be useful practical benchmarks, but their hidden pretraining cost prevents a clean equal-training comparison.

Suggested advancement threshold, to freeze before evaluation: at a fixed total-compute budget, at least 20% lower mean normalized prediction error than the strongest preregistered applicable baseline, with a paired interval excluding zero, plus improved data efficiency on a subsequent task using the discovered concept. This threshold is a proposed engineering decision, not an expected result or a statistical power claim. Choose independent world and training-seed counts using development-set variance; do not treat correlated steps from one world as independent samples. If uncertainty remains wide, the outcome is inconclusive.

Reject the proposed advantage if equally equipped transformers or ordinary latent-state discovery match it; if the gain disappears after full compute accounting; if the concept works only on seen trajectories; or if success requires supplying the target variable or law. If the transformer benefits equally from the mechanism, report a potentially useful learning method, not a superior non-transformer architecture.

**What a pass would mean.** Evidence that this system can construct and reuse a previously unspecified representation in a bounded family of environments, more efficiently than the tested alternatives. It would not establish human-level creativity, a universally superior model, or ideas new to science. Those are separate research steps.
