**Fairness**
- **$k=1$ ($E_1/B_1 \le 0.80$, shuffle $\ge 1.25\times$):** Fair, slightly generous on MSE; directional moves dominate pixel error on 16×16 frames, so a working 1-step model should clear 0.80 easily.
- **$k=3,5$ ($0.90/0.95$, $k=5$ shuffle $\ge 1.10\times$ in $\ge 12/16$ worlds):** Steep for $k=1$-only training. Open-loop rollouts into a frozen linear readout typically drift off-manifold by $k=5$, and random-walk action shuffles can partially cancel, making $1.10\times$ across 12/16 worlds tough.
- **Per-action std ($0.25\text{--}2\times$):** Both loose and fragile. A $0.25\times$ floor allows heavy smoothing, while rare or near-no-op actions among 17 choices can fail from small-sample noise. Restrict to frequent actions (or take the median) and raise the floor to $\sim 0.4\times$.

**Cheats the marks miss**
- **Blind action-shift:** Pure copy fails $E_1/B_1 \le 0.80$, and the frozen readout blocks readout gaming. Still, because $B_k$ is action-blind, a stateless rigid shift per move action (ignoring walls, collisions, and interactions) can beat shrink-to-mean, trigger large shuffle penalties, and match per-action std without modeling world state.
- **Step-1-then-shrink:** Predicting $k=1$ well and decaying toward the mean on $k=2\text{--}5$ starts one frame ahead of $B_5$, potentially clearing $E_5/B_5 \le 0.95$ and $k=5$ shuffle purely via $a_t$.

**One extra control**
Add a **stateless per-action baseline** $B_k^{\text{act}}$: closed-form ridge (or optimal rigid shift + shrink) fit on train from $(x_t, a_t) \to x_{t+1}$ and rolled out $k$ steps. Beating $B_k^{\text{act}}$ closes the blind-shift shortcut.

**Odds (current marks)**
- **PASS: 20%** — $k=5$ open-loop drift without $k>1$ training is the bottleneck.
- **PARTIAL: 55%** — $k=1$ accuracy and shuffle should clear cleanly.
- **FAIL: 25%** — unweighted latent MSE misaligning with the frozen readout, or rare-action std variance.
