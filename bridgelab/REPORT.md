# Bridge between the halves: first results (2026-10-23)

Labels: **shown** = measured here; **suggested** = reading; **untested**. Card experiments and the real (village) model are kept separate.

## 1. Old bridge on the real v1 weights (bridgelab/r0, shown)
v1full-pc weights, 3,399 dev / 1,307 validation questions regenerated with the v1 generator.
D dev: real 81.3%, off 22.5%, fresh creative summaries 46-55%, output vector x0.5 55.6%, random summary 21-26%, frozen constant = real (bit-identical).
Fresh summaries point the same way as the saved one (cos 0.99 after projection) at about half the norm. Suggested: the bridge is a learned constant D is tuned to; untested: rescaling the fresh summaries to the saved norm.

## 2. Card experiment (bridgelab/, PREREG.md + amendments; 3 seeds, results/SUMMARY.md)
Split-information lookup game, chance 12.5%.
- B->A (sender already holds the fact): pooled, xattn, slots all 100%; off/shuffle/mean 12-13%; probe 1.0. ema_const and none at chance. **Passes the pre-registered marks** (shown, 3 seeds).
- A->B (sender must look up then send): pooled 40.8±0.2%, xattn 23.7±9.5%, slots 20.4±4.5%; shuffle/mean at chance; probe ~0.41 in every per-item arm. **Fails the 90% mark**: information flows (shuffle collapses it) the probe equals a bag-of-values control, so the bridge carries all A has; A never learns the lookup itself, even with direct supervision, 3x steps, more loops or a wider sender (shown, followup_ab/RESULT.md).

## 3. Real-model count handoff (bridgelab/real, bridgelab/dcount)
**Correction:** the first probe (D answers only 0/3, registers carry no count) was a harness bug: `dmsg.load_d` did not add the v1 bridge's frozen vector, so D ran in its bridge-off lesion (shown, bridgelab/dcount: harness answers match bridge-off 626/626). Fixed in `dmsg.load_d`; W2 likewise gets its frozen v1 vector (`bridge.base_in`). `results/probe_d.json` from before the fix is void (moved to `results/void_probe_d_bridge_off.json`).
With the bridge vector, official scorer on 1,000 dev visits: Q5 66.3% vs 44.4% majority (count_at 63.0, count_held 70.1). The count is fully decodable at the decoder (probe 67.9%) but only partly in the registers (53%); suggested bottleneck is retrieval (Q5 needs 4.55 evidence lines, gold recall 63.6%).
Handoff results (dev, 1,000 items, prior 43.7%, seed 0, CPU; count head trained on the true c, an auxiliary label):
| message source | steps | real | off | shuffle | mean | prior_inject | d_text (same run) | count head |
|---|---|---|---|---|---|---|---|---|
| D registers (run2) | 300 | 35.8 | 35.5 | 23.7 | 34.6 | 35.5 | 45.1 | - |
| D registers (run3, matched control) | 1200 | 47.4 | 42.2 | 22.3 | 43.5 | 42.2 | 61.1 | 47.8 |
| **D decoder state at the answer position (run3)** | 1200 | **66.9** | 12.3 | **11.9** | 43.6 | 42.7 | 61.8 | 67.1 |
**Shown (one seed):** a per-question bridge reading D's decoder state carries the count into the creative model: the amendment's marks all pass (bridgelab/real/PREREG.md, "msg-source decoder"); shuffling messages drops it from 66.9% to 11.9%, the batch-mean message gives the prior level (43.6%). It matches or slightly beats typing D's own answer into the prompt (61.8%), but is capped by D's own count accuracy (65.8%). Original mark (a) (prior + 30) is not met because D itself only reaches prior + 22. Validation: 52.8% vs prior_inject 44.1%.
**Shown:** reading D's think registers carries little (count head 47.8% vs prior 43.7%), matching the probes; where the bridge reads from matters more than its type.

## Next (one change each)
1. D retrieval for counts: list-wise ASK loss on gold lines for Q5 (pass: Q5 >= 73%, all-gold-fetched >= 55%, dev >= 80.2%; bridgelab/dcount/RESULT.md).
2. Run bridgelab/real with pooled vs ema_const vs d_text on GPU, shuffle ablation as the decisive test.
3. Card A->B: the bottleneck is A's own name lookup, not the bridge (followup_ab/RESULT.md); try a bigger reader or few-entity curriculum.
4. Real handoff: second seed; xattn on decoder rows; train D and bridge jointly so D learns to put the count where the bridge reads.
