---
name: ben-moe-separate-experts
description: Ben 09-26 19:15-19:21 UTC: fix sleep forgetting by separating parts (mixture of experts, learned router; reasoner = MoE); two $0 tests started, and his frustration that nobody had tested it
metadata:
  type: project
  modified: 2026-09-27T00:27:00.000Z
---
Ben's words, Thread manager thread, 2026-09-26:
- 19:15 "What if we separated parts of the brain?"; "like we did a mixture of expert style thing."
- 19:20 "why the hell has no one tested this on the model yet? ... If it's overriding old skills, just put the old skills somewhere where they don't get overridden."
- 19:21 "a mixture of experts where ... it has the learned router and then the reasoner is just the mixture of experts."

Facts checked by the Thread manager:
- Every dl sleep run already freezes the base 1B. add_lora freezes the model (scripts/claude_blurt2.py:244, :264; dl1 :182), and one growing LoRA r16 stays on for every question.
- dl-5 CARRY.md:14-16: 299-300 of 300 panel replies take the grid shape. bm-398r: an always-on adapter drops GSM8K from 191 to 20 of 300.
- 0.2d's sleep slot is an adapter on the talker's 1B. It is still empty (claude_e2e02d.py:23-25, :69).
- Before today, no test on the 1B had tried a learned router. Toy card experiments exp 44 and 43I had passed learned skill routers. One-adapter-per-night (O-LoRA) was a parked idea at sleep-research-2026-09-24.md:159.

Started 19:22-19:25 UTC, both $0 (CPU or BensPC), marks sealed first:
1. Fix sleep: a learned on/off switch for the 1B sleep add-on. First a quick finding on dl-5's saved S adapters (Claude prefix, so finding only), then a clean registered run with GLM frames and bare-number targets.
2. Sleep research: the 358 loop reasoner as a mixture of experts with a learned router, vs the same-size loop net. Learn kind A, then kind B; measure A kept and B learned, plus a carry-over row.

Nothing joins 0.2d without Ben's yes on the results.

**Why:** Ben sees this as the obvious fix and was angry that it had waited. The Thread manager owned the miss: every fix before this tried to make one always-on add-on do less damage.

**How to apply:** treat both tests as top of the sleep and reasoner queue. Before proposing more one-adapter fixes (replay, anchors, lighter nights), ask whether separating parts solves the problem. Related: [[fix-sleep-0926]], [[brain-emulation-goal]], [[question-failures-critically]].

**Sleep research results on the loop reasoner** (small nets, CPU, dev /200, seeds 1/2):
- rsn-358e FAIL (91ac1343a). Learning sums after grids: dense grids5 199/198 -> 0/0; 4-expert moe -> 0/0. Freeze-old-plus-new-experts (moe-grow, 1.64x size) -> 40/70, but sums4 only 139/124 and mazes 3/3.
- Diag (4aedbf9ea): the old weights were byte-identical, and old-only routing restores 187/188. The router, trained on sums only, moved grids away.
- rsn-358e3 FAIL (0fe86b700): moe-grow + 1-in-10 grids replay keeps grids5 191/188 but sums4 136/67.
- Report only: dense + the same replay keeps 184/172 AND sums 200/200, mazes 150/136.
- Reading (suggested): replay does the protecting, not the experts. The experts cost new learning.
- 09-27: equal-size freeze-and-grow (eq arms, 12 narrow experts, 352,944 trainable) learns new kinds far worse. In 7 of 8 runs the new group got at least half of the new kind and still learned little; one run (358e4 s4) had a dead new group (DIAG at 33b38420b). So capacity is suggested as the limit, with routing secondary.
- 358e4 (graded, seeds 3-8, running on CPU): verdict wording fixed in ADDENDUM-3 ("this recipe", never "experts are wrong"). Follow-ups sealed 9b827b22d: 358e6 (shared attention and norms train) and 358e5 (warm routing, with a hand-given kind label disclosed). Queue in scratchpad queue358.txt via go4.sh; pusher.sh commits each run.
- An outside agent (GPT-6 Sol, on Ben's Mac, from 03:45 UTC 09-27) may push small-net forgetting experiments. Don't duplicate them. Sleep research reviews them as owner, and they count only once verified.
- 09-27 05:49 UTC: rsn-358e4 PROVED WRONG for this freeze-and-grow recipe (d05fb81ce, blind recount agrees). Mean T eq 239.83 vs dense 470.17, lower on 6/6; mazes 3.33 vs 150.33. Frozen eq keeps grids better (164 vs 128, report only). Only 3 of 6 seeds tested the routing, so it "says little about separate experts themselves". Ben's architecture question is held until 358e6 lands (recommend: plain loop + sleep replay).
- 09-27 07:46 UTC: rsn-358e6 PASS (93ea1c215): with shared attention and norms training, the frozen-expert net learns new kinds (N 298 vs 80). But T is still 321 vs dense 470, and old grids collapse to 42. So neither experts layout beats the dense loop plus replay. The architecture question went to the Thread manager for Ben: recommend a plain loop plus sleep replay. 358e5 is still running.
