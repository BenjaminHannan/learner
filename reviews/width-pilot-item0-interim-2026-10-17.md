# Width pilot v2: Item 0 interim (facts audit), 2026-10-17

From the size-versus-stall session, after the coordinator delivered file 1 of 2 (`deep3-stage3-pilot-v2.md`). Item 0 costs $0 and gates everything. This note is not a closed Item 0: the playbook (`deep2-blocker-2-stall.md`), which defines Frozen-F, Logged-L and the Item 0 sub-items, has not been delivered. Labels: **shown** = read in code or result files; **suggested**; **open**.

## 0. Correction to my earlier documents

My solve report (10-16) and bid (10-17) inferred v2's host to be the Gemma-fronted B2/B3G2 class (the "V6" inference). **That was wrong.** The spec hosts the pilot on the far-join HO cell (420 items) under the L13 guard recipe, with Arm A at 1x and Arm B at 2x non-embedding parameters, trained from scratch.

So v2 already tests a stalled line. **Bid B is withdrawn.** The pilot follows v2.

## 1. Blocking finding for Item 0: "from scratch" and "the L13 guard" don't fit together in the record

**What the record has (shown):**
- **Trainer.** Every far-join trainer in the record is `domain/far/learn_probe.py train` (branches `claude/project-thread-94a956` and `claude/forgetting-replay-arm`, and the L13 command line). It always loads a **parent checkpoint**: `--parent`, default the T1SDR s200 parent, `load_model(PARENT)`. It has no from-scratch path and no width option.
- **The L13 recipe** (`domain/far/MARKS-L13-NKsoft10-2026-10-13.md`): parent T1SDR s200; every weight; lr 1e-4; 4,000 updates; batch 64; L5 join rows; guard refresh every 500. Each update adds 32 diary rows, and the loss is the join loss plus 10 × the mean KL **to the frozen parent** over those rows. The K-FAC graded mask is computed from **parent** statistics, `kf.factors(stats, 0.99, soft=10)`. It ran at 4.6 s/update on free cloud CPU, with replay KL mean 0.0110 and HO 14.1 at 4,000 updates.
- **Consequence.** Both halves of the L13 guard, the mask and the KL replay, are defined relative to a trained parent. "From scratch at every size", read literally, has no parent to take a mask from or a KL to.

**Two readings of v2.** The coordinator must choose one, in writing, before Item 1 can calibrate anything:

| Reading | What a run is | What it implies |
|---|---|---|
| **(a) Per-size parent, then the L13 join phase** | Train a T1SDR-recipe parent from scratch at width w (24k updates, the 200k-row build), then run the L13 join phase for 4,000 updates from **that width's own parent**. | The parent stage is unpriced in §7. A 3M T1SDR parent takes 35–130 min; at 2× width the 4090 time is unmeasured. It needs a width option in `custom_io` (shown: the `tool` model takes `d`, so no model code change is needed) and parent-agnostic sha checks in the far trainer. G0's "from scratch" note would then mean "a fresh parent per size", not "no parent". |
| **(b) A single from-scratch run with a guard** | Random init, trained on the join rows plus replay, for 4,000 updates. | The KL target and the mask source must be defined: KL to what? Mask from what statistics? No code for this exists. The spec's 7.2 s/update for a base run on a 4090, against 4.6 s/update for L13 on CPU, suggests a heavier step than L13's, consistent with a different trainer (suggested). |

Until this is settled:
- Item 1 has no trainer to calibrate;
- C8 has no confirmed host loop. My C8 draft sits in `custom_io/train.py`, which is the parent trainer under reading (a). The pilot's own runs train in `learn_probe.py`, which would need the same logging.

## 2. Item 0 sub-items named in the spec, and what the record shows so far

| Sub-item (as the spec names it) | Status |
|---|---|
| Base layer count (axis gate condition 1) | **Shown for T1SDR:** `tool` model, d256, 4 heads, **2 blocks** with 8 loops (`n_loops` 8), reader layers 2. The **axis gate** compares base depth with the saturation band of about 4–6 layers. 2 blocks (looped 8×) is below that band if blocks count as layers, or arguably 16 if loops count. **Open: how the spec counts looped blocks.** That choice decides gate condition 2 and the **redirect rule** ("if base depth is 2 or 3 layers … redirects … to depth-first"). |
| 0(b) embedding treatment at 2× | Spec: d_model scales, FFN scales proportionally, heads multiply at fixed d_head, embedding matrix scales with d_model. **Shown:** the `tool` model at d448 / 7 heads has 9,854,600 params (2.97× total). 2× non-embedding needs its own count. **Open:** the exact d that gives 2.0× non-embedding (about d362 / 5.66 heads is not integral at d_head 64, so a head-size rule is needed). |
| 0(e) masking per family; answer-only vs intermediates | **Open.** Needs the L5 / L9 row format per family. |
| 0(f) replay selection type (model-state-dependent or not) | **Shown for L13:** "32 diary rows per update … seeded draw" (`--kl-replay-rows`, KL_REPLAY_SEED), which looks state-independent. **Open** under reading (b). |
| 0(j) shortcut identification attempt | **Open.** |
| 0(k) batching feasibility at 2× | **Open.** It needs the trainer. |
| Seeds, manifest hash per arm, HO cell plus a disjoint second HO cell plus validation slice, hashed | **Open.** The 420-item HO cell is the L5 / L13 HO (14.05% = 59/420, re-scored 10-16). A second disjoint cell must be generated and hashed. |
| Unique-problem and unique-combination counts per family (dose currency) | **Open.** L5 join data: 6,000 joined plus 6,000 not-joined rows (L8/L9/L12 builds). |

## 3. What I need from the coordinator

1. **File 2 of 2, and the playbook** (`deep2-blocker-2-stall.md`, sections 0 and Items 0–8: Frozen-F, Logged-L, the full Item 0 list).
2. **A written choice between reading (a) and reading (b)** for "from scratch under the L13 guard". Under (b), also the KL target and the mask source.
3. **How looped blocks count** for the axis gate's "layers".

Nothing is booked. Item 1 ($0.74) will be bid only once a trainer to calibrate exists.
