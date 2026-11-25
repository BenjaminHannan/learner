**1. Top 3 causes Step 6 stays at "copy"**

1. **Frozen trunk drops/unmixes `a_t` × cross-row state (`suggested`)**: Crafter `Δframe` is a state×action shift, so averaging actions ≈ copy. Frozen from reading (0% action effect in Steps 3, 5), the trunk may drop `action_emb`, keep state/action additive (breaking the 1-layer probe), or omit neighbor info in `h_row`.
2. **Signal burial in `h_row` (`suggested`; board SNR shown, `h_row` untested)**: Real boards have 68× offset (1.36) and 10× start noise (0.2) vs 0.02 spread. Ridge whitens these; SGD on a frozen frame-less tick does not, or the trunk attenuates that 0.02 signal.
3. **Frozen tick gate + zero-init saddle (`untested`)**: Zero-init last layer gives `∇action_emb=0`, `∇W_in=0` at step 0; since `E[Δframe|b_t]≈0`, `W_out` stalls, starving `action_emb` (like Step 5's `α→0`). Also, reading gate `g` may close (`≈0`) without frames, crushing `g·spread·MLP(h)`.

**2. Cheapest checks (<2 min each)**

1. **Action/mixing probes (<1 min, no training)**: Check `std_a(h_row)/std_t(h_row)` across random `action_emb` (1×, 10×); `≈0` ⇒ trunk drops `a_t`. Fit ridge (~2k steps) to `Δframe`: (a) shared `W h(b_t,a_t)`, (b) per-action `W_a h(b_t)`, (c) per-action row-shared `Σ_r W_r(A_a h_r)`. (a) fails, (b) passes ⇒ missing state×action; (b) passes, (c) fails ⇒ missing cross-row info.
2. **`h_row` SNR & `frame_t` ridge (<1 min, no training)**: Log `h_row` offset RMS, start-noise std (two 0.2-sd seeds, same frames), frame spread; fit ridge `h(b_t)→frame_t`. Error `>>6%` ⇒ trunk loses state; `~6%` with high offset/noise ⇒ standardize `h_row`.
3. **Gate check + 32-step overfit (<2 min)**: Log imagine vs read `g` and `||W_ridge(g·spread·z)||/||Δframe||` (unit `z`). Overfit 32 transitions with `g=1`, last-layer init `1e-3`, `lr∈{1e-3,1e-2,1e-1}`; `img/copy<0.5` isolates gating/optimization.

**3. Next step if Step 6 fails**

- **One change**: Bypass the frozen trunk and gate: replace `gated MLP(h_row)` with a standalone cross-row delta head (1 attention/mixer block + `FiLM(a_t)`, tiny nonzero output init) on standardized `(board_t-μ_b)/σ_b`, adding `Δb·spread` before the frozen readout (reading trunk stays frozen).
- **Pass mark**: `k=1` E/B `≤0.80` and shuffled actions raise error `≥1.25×` in `≥12/16` held-out worlds (reading stays 6%).
- **Proves it wrong**: Staying near copy (`E/B≥0.95` or shuffle `<1.05×`) while a matched pixel `(frame_t,a_t)→frame_{t+1}` baseline passes. That falsifies the trunk/gate hypothesis and implicates `board_t`/readout geometry (e.g., 0.2 noise swamping 0.02 signal under SGD), requiring reading-board changes.
