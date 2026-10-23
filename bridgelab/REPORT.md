# Bridge between the halves: first results (2026-10-23)

Labels: **shown** = measured here; **suggested** = reading; **untested**. Card experiments and the real (village) model are kept separate.

## 1. Old bridge on the real v1 weights (bridgelab/r0, shown)
v1full-pc weights, 3,399 dev / 1,307 validation questions regenerated with the v1 generator.
D dev: real 81.3%, off 22.5%, fresh creative summaries 46-55%, output vector x0.5 55.6%, random summary 21-26%, frozen constant = real (bit-identical).
Fresh summaries point the same way as the saved one (cos 0.99 after projection) at about half the norm. Suggested: the bridge is a learned constant D is tuned to; untested: rescaling the fresh summaries to the saved norm.

## 2. Card experiment (bridgelab/, PREREG.md + amendments; 3 seeds, results/SUMMARY.md)
Split-information lookup game, chance 12.5%.
- B->A (sender already holds the fact): pooled, xattn, slots all 100%; off/shuffle/mean 12-13%; probe 1.0. ema_const and none at chance. **Passes the pre-registered marks** (shown, 3 seeds).
- A->B (sender must look up then send): pooled 40.8±0.2%, xattn 23.7±9.5%, slots 20.4±4.5%; shuffle/mean at chance; probe ~0.41 in every per-item arm. **Fails the 90% mark**: information flows (shuffle collapses it) but the channel is only partly learned (shown). Suggested: needs longer training.

## 3. Real-model count handoff (bridgelab/real, shown)
Frozen D on 1,000 dev count questions (q.count_at / q.count_held): D answers only 0 or 3; right 42.5% vs 43.7% for always-majority. Linear probes on D's final-loop registers predict c at prior level (0.42-0.43 dev; shuffled-label control 0.40). So D's state carries no count to hand over, and the handoff test cannot pass with this D whatever the bridge. Harness, tests and GPU commands are ready (bridgelab/real/README.md); not run at scale.

## Next (one change each)
1. Make D count (or pick a handoff D already does well) and re-run probe_d: pass = probe >= prior + 30.
2. Run bridgelab/real with pooled vs ema_const vs d_text on GPU, shuffle ablation as the decisive test.
3. Card A->B: longer training / curriculum to see if pooled reaches 90%.
