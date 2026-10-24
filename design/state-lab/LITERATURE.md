# Literature on looped latent state (summary of a Sonnet research pass, 2026-10-23)

Claims are the research agent's; abstracts were opened for every arXiv paper, full text only for Geiping and TRM.
Check against the papers before relying on exact numbers.

- Geiping et al. 2025 (arXiv 2502.05171), recurrent depth: input re-injected every iteration (concat + adapter beat add),
  random initial state, iteration count sampled per sequence (log-normal Poisson, mean 32), backprop through last 8 only,
  exit when successive-step KL < 5e-4. ARC-Easy 49.1 (r=4) -> 65.1 (8) -> 69.5 (16); GSM8K 0 (r=1) -> 34.8 (r=32). [shown, 3.5B]
- TRM (arXiv 2510.04871), 5-7M params: latent z + answer y, T=3 n=6 recursions, only the last recursion backpropagated,
  deep supervision, weight EMA. Sudoku-Extreme 87.4 vs HRM 55.0; 1-step-gradient ablation 56.5. [shown, one task, one seed]
- HRM (arXiv 2506.21734) + ARC Prize reproduction: the outer refinement loop with carried state drove most of the gain;
  the two-level hierarchy mattered little. [shown by the ARC Prize analysis]
- Saunshi et al. 2025 (2502.17416): k layers looped L times ~ kL layers on reasoning tasks; looping helps reasoning more than
  memorisation. [shown on synthetic tasks]
- Fan et al. ICLR 2025 (2409.15647): adaptive loop counts give length generalisation. [shown, algorithmic tasks]
- PonderNet (2107.05407): halting as a distribution with a prior, instead of a greedy stop. [shown on its tasks]
- Registers (Darcet 2023), Memory Transformer, RMT, Slot Attention: extra or competing state tokens; evidence for reasoning
  use is indirect. [recalled]

Mapping to D (village model): D already has the shared block + step embedding (Universal-Transformer style). It does NOT
re-inject inputs (rows are overwritten each loop), its HALT target is "answer already right at this loop" while the answer
loss is applied at every loop, which rewards answering early. These motivate the `inject` and `lastloss` arms.

Agent suggestion checked against code and found wrong: "the puzzle controller's second step doesn't get the first step's
result". In custom_io/models/ledger.py the written result slots Rs are concatenated into S, which the controller
cross-attends to every iteration and which the operand pointers can select (`ks_ = k_slot(... cat([S0, Rs]))`). So the
intermediate result IS available; the two-step failure is more likely training data (no fitting two-step tries for sleep
to learn from), as the earlier v2 research said.
