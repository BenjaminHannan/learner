---
name: focused-priorities-and-claims
description: "Ben's 2026-09-19 review of the broad sweep — wants a short focused experiment sequence, claims no stronger than the evidence, toy-card vs village results kept separate; next milestone = dependable two-hop in fresh worlds"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: aa82fa83-15ca-4df2-9694-910b4cc9284b
  modified: 2026-09-19T13:52:53.243Z
---

On 2026-09-19 Ben reviewed the 100-idea broad sweep (design/research/broad-sweep-2026-09-19/README.md): liked the direction, but said 40 "try soon" items is too many to guide a decision and several descriptions promised more than their experiments establish.

**Why:** a long ranked list doesn't tell him what to do next, and overclaiming (e.g. "proves the loop does nothing", "14 epochs = memorising") misleads later decisions.

**How to apply:**
- Give a short prioritised sequence tied to identified failures, not a catalogue. His four priorities: (1) dependable comparisons (seeds, LR schedule, best-val checkpoint, shortcut baselines, fair competitors; report every seed + fraction succeeding; 5 seeds = screen only); (2) locate the failing operation, then change ONE thing (own retrieval vs first gold card vs both gold cards; log whose card / which relation the 2nd lookup asks for); (3) bounded fair trial for the Think loop, judged by accuracy gain vs added compute; (4) move the retention experiment (#39) early, stating whether knowledge lives in weights or cards, under explicit storage/replay budgets.
- State what an experiment would establish, no more. Detectable-in-a-representation ≠ used-in-behaviour (he cited Amnesic Probing); use valid factual swaps with irrelevant-change controls, not arbitrary vector swaps.
- Keep small card-ladder experiments and village-model (Core) results explicitly separate.
- Next milestone he named: dependable two-hop reasoning in fresh worlds — correct across seeds, changes with relevant fact changes, resists irrelevant ones.
- Before any sweep, check reviews/ for Opus milestone reports newer than the inputs: on 2026-09-19 the sweep missed m03 continuations (swap tests + address-keyed selector already run). See [[gpu-budget-cap]] for Astra/Opus ownership.
