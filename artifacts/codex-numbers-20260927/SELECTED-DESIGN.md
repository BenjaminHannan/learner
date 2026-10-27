# Selected candidate: learned scratchpad only

Ben's latest decision: "ok, do scratchpad only". This supersedes the combined architecture proposal. No restore operation, bookmark mode, extra supervision, or second trained candidate is included.

The candidate is the inherited fixed-env recurrent loop plus eight episode-local learned scratch slots. Each has a dynamic16-dimensional key and a position-aware payload [T,16], where T is the number of grid tokens. Learned components: biasless Wq,Wk,Wv maps256→16, two scalar read/write sigmoid gates with biases, and eight learned16-dimensional slot address vectors E. The biasless read decoder is Wv transpose. Calculated extra parameters12,930 (0.7853%); baseline1,646,494; candidate1,659,424. Implementation must verify these counts.

Before each inherited core step: compute q=Wq mean_tokens(h), beta=softmax(q dot(K+E)/sqrt16), read v_t=sum_i beta_i V_i,t, then add sigmoid(g_read(mean h))*Wv^T v_t to h_t. After the core step: k=Wk mean_tokens(h_new), write address alpha=softmax(k dot(K+E)/sqrt16), payload vnew_t=Wv h_new,t, and mass w_i=sigmoid(g_write(mean h_new))*alpha_i. Blend K_i and V_i toward k and vnew by w_i. All what/when/which choices are learned through the unchanged task losses. Generic position-aligned storage is not an arithmetic matching rule.

Per-token values retain positional roles, addressing the information-loss concern raised during design discussion. This replaces the earliest pooled-value sketch. It does not reserve hidden-state coordinates or restore an earlier state. Query/write decisions still use pooled hidden state. Soft-address collapse and weak delayed gradients remain risks, not resolved facts.

Start K,V at zero for each puzzle/batch. Advance through free rounds under no_grad and detach both alongside h before graded rounds. Use the same state-machine path for training, evaluation and hidden-field poison checks. At most six graded rounds, 1–16 training rounds and48 evaluation rounds remain unchanged. No card tensors persist between puzzles.

Required ablation: wipe K,V before EVERY read, beginning at round0. Keep all learned weights/address vectors, recurrent core and own-stop rules. Biasless value/read maps make an empty read exactly zero. Verify wiped full logits/halts equal those of the same checkpoint's inherited core. This test must actually traverse the candidate code rather than bypassing it through base.step.

Verify nonzero card gradients on a deliberately multi-graded-round CPU smoke, core gradients during training, per-call reset, checkpoint reload, batch independence, the exact parameter count and paired initial core tensors. One-graded-round writes cannot receive subsequent read gradients and are not falsely treated as a failure. Parameter-specific accumulated card gradient diagnostics must distinguish expected one-round cases from unused modules.

Candidate and baseline share the same complete training stream and core initialization per paired seed; extra card initialization is tracked separately. Base-init hash excludes scratch parameters; full-init hash includes all parameters. Registration, source hashes, checkpoint hashes, checks of fixed env0 and strict panel controls remain required.

Ben's proposed N5 is unchanged: intact-minus-wiped mean>=10/300 on numbers4 and>=5/300 on fresh numbers5, positive on at least3/4 seeds for each. Passing establishes useful dependence on card contents under the intervention, not proof of arithmetic representations or backtracking. Combined-design notes are historical brainstorming, not active specifications.
