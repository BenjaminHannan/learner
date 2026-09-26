# rsn-358e moe-grow diagnostic: the freeze held; the router moved grids off the old experts (report only; 2026-09-26 21:23 UTC)

Asked by the Thread manager at 20:25 UTC. Code: scripts/claude_rsn358e_diag.py (bcbbd3502), CPU, torch 2.14.0, 1 thread. Raw: runs/diag-s1/diag.json and runs/diag-s2/diag.json. No mark depends on this; the 358e verdict waits for dense and moe.

**REPRO (gate):** the rerun of phases A and B gives exactly the stage-1 after-B scores on both seeds: grids5 40 / 70, grids6 34 / 21, sums4 139 / 124. So the rows below describe the same nets.

**FREEZE:** on both seeds, all 67 weight tensors that existed after phase A are byte-identical after phase B (torch.equal), none has requires_grad, and all 36 new tensors are trainable. **Freezing happened** (shown).

**MASKS** (dev grids5 / grids6 out of 200; after-B net, router changed at test time only):

| row | what the router does at test | seed 1 | seed 2 |
|---|---|---|---|
| after A (before growing) | the 4 original experts | 187 / 160 | 188 / 167 |
| after B, as trained | route over 8, scale by the 8-way share | 40 / 34 | 70 / 21 |
| M0 old-only | route and scale over the old 4 | **187 / 160** | **188 / 167** |
| M1 no-rescale | route over 8; old experts scaled by the old-4 share | 54 / 29 | 97 / 35 |
| M2 old-routing | route over the old 4; scale by the 8-way share | 158 / 111 | 182 / 106 |

**What this shows:**
- M0 gives back the after-A score exactly on both seeds. The old experts and every other old weight still hold the whole grids skill. All of the forgetting is in how the grown router uses them. (Shown.)
- Removing only the routing shift (M2) recovers most of grids5 (158 / 182) and about two thirds of grids6. Removing only the rescale (M1) recovers little (54 / 97). So cells being sent to the new experts is the main cause, and the gate rescale is a smaller second one, larger on grids6. (Shown for these two seeds; the split between the two is not additive and is not claimed as exact shares.)
- Reading (suggested): the router's new rows learned from sums alone, and nothing in phase B asked them to leave grids cells on the old experts. This is the "the gate forgot" reading. It fits the replay follow-up (NEXT-replay-draft.md), which gives the router grids examples in phase B. It also means a router that knew which kind of puzzle it is on would keep grids fully, but that would be a hand-given task label, which the rules rule out as a build part.

**Checkpoints (scratchpad only, never pushed):** diag-s1 after_A 5c30564f..., after_B 93ee0b7a...; diag-s2 after_A 28ac79ec..., after_B 52517798... (full sha256 in the commit message).
