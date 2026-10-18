# Width pilot v2: Item 0 run card (draft for coordinator freeze), 2026-10-17

This is the playbook's Item 0, sub-items (a)–(k) (`deep2-blocker-2-stall.md`, delivered 10-17), under the coordinator's Item 0 ruling (reading (a′)). Labels: **shown** = read in code, data or result files; **open** = pending. It supersedes the interim note for every item it covers. The interim note stays as history.

**Pass condition (playbook):** (a), (b), (e), (g), (h), (i) and (k) recorded; (c) recorded or formally excluded; (d) run or its impossibility recorded; (f) answered; (j) answered YES or NO.

## (a) Model and sweep sizes (shown, CPU count of the `tool` model at the f6d724 pin; the pin differs from head only by a loss refactor)

| Arm | d_model | Heads | d_head | Blocks (distinct) | Loops | FFN (mlp 4.8) | Total params | Non-embedding | Embedding share |
|---|---|---|---|---|---|---|---|---|---|
| 0.5× (gated) | 192 | 3 | 64 | 2 | 8 | ≈922 | 1,907,694 | 1,830,894 (0.57×) | 4.0% |
| **1× base** | **256** | **4** | **64** | **2** | **8** | ≈1,229 | **3,314,132** | **3,213,268** | 3.0% |
| **2× wide** | **384** | **6** | **64** | **2** | **8** | ≈1,843 | **7,288,226** | **7,139,234 (2.22×)** | 2.0% |

- Reader layers 2 at every size. Depth counts distinct blocks: **base depth 2** (ruling Q48). n_loops 8, so 16 effective passes, recorded as a note only.
- **Ruled (Q53, coordinator, 10-17):** **d384 / 6 heads at fixed d_head 64**. The headline is the measured ratio, **2.22× non-embedding, 2.20× total**. Every SUCCESS / KILL / INTERMEDIATE wording uses the measured multiple, never "2×". Item 1 re-measures d384's seconds per step, and Bid A is re-priced on the measured numbers before anything books.

## (b) Embedding treatment (shown)

- d_model scales; FFN scales with it (mlp ratio fixed at 4.8); heads multiply at fixed d_head 64; every embedding table scales with d_model.
- The 12 `nn.Embedding` tables total 100,864 params at base: reader tok, pos, place; stype, ordinal, step_emb, src, ctrl, len_emb, tape_emb, e_s, e_e.
- **Tied/untied as found:** the GEN readout is **tied** to the char table, and the 9 register tokens are tied to the reader's place rows 0–8 (`ledger.py`, header and line 153).
- The rank-setting width is d_model, and the width axis widens it.

## (c) Historical WIDE: formally EXCLUDED

WIDE as found (shown):
- B2 (Gemma-fronted `eg_embed`), d448, 7 heads, 2 blocks, 12 loops, 10,173,509 trainable;
- lr 5.71e-4 = 1e-3 × 256/448, warmup 300, clip 1.0, **accum 1** (RESULT.json; the design planned 8);
- 24,000 updates on the **pooled-5 skills benchmark**, not the far-join cell;
- **no guard** (WIDE is not a continual-learning run);
- pool `p10-rung30-s400-a64`, manifest **8ee0b3ee**, against its 3M reference's **133e463e**;
- one seed (400); Modal A10G, 9.13 h, no resume events recorded.

It is a different model, task, guard regime and data pool, and its pool hash differs from its own reference. It is **excluded from evidence** on this run card and stays quarantined (playbook §0.1).

## (d) N1 manifest audit and step-count census

- **Join stage (shown):** the manifest is `train-rows-l5.jsonl` (sha 15cda9d3…).
  - 12,000 rows: 6,000 F4-two joins (1,200 per layout × 5 layouts: `K+J`, `K-J`, `K*J`, `(K)+(J)`, `(K)-(J)`) and 6,000 F0-near single-kind rows.
  - 131 skeletons; 131 of 140 ordered (kind, partner) × layout combinations; about 21.3 passes per joined prompt at 4,000 × 64.
- **Parent stage (shown):** the manifest is the seed-1 200k skills build, hash-checked against `FULL-BUILD-MANIFEST-200k-seed1.json`. That is the T1SDR recipe's own data, identical at every size.
- **Under reading (a′) the far items are 100% of the join stage, not ~5% of one mixed run.** The playbook's "historical share" field is therefore recorded as **not applicable**: the parent stage contains no far rows, and the join stage contains only far rows.
- **Step-count census (shown, measured on CPU; chain length = number of calculator calls in the tool's working; script `width-pilot-item0/census.py`):**

| Cell | n | 1 | 2 | 3 | 4 | 5 | 6 | 7 | Mean |
|---|---|---|---|---|---|---|---|---|---|
| Train F4-two (joined) | 6000 | 0 | 0 | 29.2% | 27.4% | 34.0% | 6.9% | 2.5% | 4.26 |
| Train F0-near (single) | 6000 | 33.7% | 33.3% | 33.1% | 0 | 0 | 0 | 0 | 1.99 |
| **Eval HO** | 420 | 0 | 0 | 30.7% | 33.1% | 30.5% | 4.0% | 1.7% | 4.13 |
| Eval HPO | 420 | 0 | 0 | 41.2% | 25.5% | 14.0% | 19.3% | 0 | 4.11 |
| Eval HP | 420 | 0 | 0 | 42.4% | 25.5% | 11.2% | 21.0% | 0 | 4.11 |
| Eval S | 420 | 0 | 0 | 26.0% | 35.0% | 30.0% | 7.1% | 1.9% | 4.24 |
| Eval S5 | 420 | 0 | 0 | 28.8% | 29.3% | 31.9% | 7.6% | 2.4% | 4.25 |

  - **HO's depth mix matches the training joins** (HO counts 3:129, 4:139, 5:128, 6:17, 7:7). HP and HPO lean toward 6 calls (19–21%).
  - **Template mix:** training F4-two is 20% of each of its five layouts; **HO and HPO are 100% `(K)*(J)`**, a layout absent from training (the intended far-join novelty). HP and S are 100% `K+J`; S5 matches training.
  - **First operation by step count** is set almost wholly by chain length, and HO mirrors training (3 calls: div 40% train / 33% HO; 4 calls: mul 63% / 57%; 5 calls: max 57% / 65%; 6 calls mixed). Full tables in the scratch `census.txt`, reproducible from the script.
  - So HO's novelty is the **layout**, not chain length or first-op mix. No step-count reweighting is needed.

- **Per-piece and join accuracy on L13 HO (shown):**
  - In context: K rounds fully right 34.5%, J 32.9%, both 15.2%; **join call right given both pieces right: 52/64 = 81.2%**; whole answer 14.0% (59/420). L14: K 31.2%, J 28.6%, both 11.2%, join given both 32/47 = 68.1%; whole 41/420.
  - Pieces asked alone on the same grid (join-gap audit): L13 HO K 62.4%, J 64.3%, both (P) 38.8%; HPO P 46.2%. **Pooled HO + HPO P = 42.5% (L13), 37.5% (L14).**
  - By pair type on L13 HO: range+range 40/130, range+cell 19/271, cell+cell 0/19.
  - **The playbook's "40–42% / 65–67%" bands could not be reproduced without their definition.** The nearest measured quantities are pooled P (42.5%) and single-piece accuracy (62–65%). The coordinator is asked for the bands' definition before they are used as a check.
  - Reading: the HO deficit sits mostly **in reading the pieces in the new layout** (in-context piece accuracy ~33–35% against ~63% alone), not in the join call (81% when both pieces are right).

## (e) Masking and target format per family (shown, `learn_probe.make_rows` → `mode.make_row`; `m.loss`)

- The prompt is **input only**: the reader encodes it, and there is no prompt-token LM loss.
- The trained targets are the **call sequence** (op plus operand strings, with results on the tape) and the **answer** through the mode, word and generation heads: `loss = lop + lcall + lmode + lword + lgen`.
- So targets are **not answer-only: they contain intermediates (calls)**.
- Joined rows have 3–7 calls; F0-near rows 1–3; HO rows 3–7.
- The same at every size.
- Under the L13 guard, each update adds 32 diary rows trained by KL to the frozen parent: `kl_replay_loss`, weight 1 + 10.

## (f) Replay mechanics (shown, code)

**Fixed buffer, state-independent selection.**
- The diary is built **once**, before the first update, from **this run's own parent** (`build_parent_diary(m, ck, …)`): the parent's own answers on the 200k-build training prompts, shuffled by `Random('200-diary')`, with size and check from the kf99n constants (diary 4,096, check 512).
- Each update draws 32 diary indices from `RandomState(SEED + 11)`, uniformly with replacement. This is independent of model state, loss and batch order.
- The guard refresh every 500 updates re-measures the K-FAC factors on the current weights. It does **not** rebuild the diary.
- So the "frozen mixture" holds for the index stream. The diary's targets are parent-mediated, which is the accepted pipeline-contrast scope.

## (g) Optimiser record (shown)

**Parent stage** (custom_io at the f6d724 pin):
- AdamW, betas (0.9, 0.95), weight decay 0.1 on matrices and 0 on biases, norms and embeddings;
- lr 1e-3; warmup 300, then cosine to 10%; clip 1.0; batch 256; 24,000 updates; bf16.

**Join stage** (`learn_probe.make_opt`):
- the same AdamW form (betas (0.9, 0.95), wd 0.1 on matrices);
- **constant** lr = the mode's night lr, **1e-4**, with no warmup and no schedule;
- clip 1.0; batch 64 (the mode constants); 4,000 updates.

**Weight decay:** frozen at 0.1 at every size, a width-independent convention. It is named as the second recipe qualifier, beside the L13 guard.

## (h) Validation slice (shown; draft for freeze)

- `reviews/width-pilot-item0/eval-rows-val.jsonl`: 420 rows of `(K)*(J)` on training pairs, seed **93704**, named before generation in commit f8c31af. **sha256 `0fcc4043efd5f2a6f18a87c56a19255e7b3be368fa24732278bdcec33b9d5c0e`**.
- Disjoint from HO, HO2 and every L5 row.
- It is the only permitted tuning target (Item 6). HO is never a tuning target.
- **Also frozen:**
  - **HO1** sha256 `3aba6de1…`;
  - **HO2** sha256 `eed9703a…` (seed 93703, ruling Q50; spec §4 confirmation cell).

## (i) Seed list (shown, filed in the amendment §B)

- Seed-indices 1–5, with run seed **P_i = 700 + i (701–705)**.
- The same P_i in both stages and at every width.
- Purchases use 706–710; calibration uses 700.
- The extension is pre-named on indices 1 and 2.

## (j) Shortcut identification

**Answer: NO (shown).** YES required one frozen heuristic meeting every TEST-11 condition (validity effect ≥ 25 points; depth effect < 10 points within the invalid row; invalid shallowest stratum at about chance, ≤ 5%). None does.

**Verification first.** The per-item outputs were regenerated on CPU from the repo checkpoints (L13 sha b10f7917…, L14 318ac36c…). L13 HO 59/420 and L14 41/420 match `scores.jsonl` cell by cell, and the L13 per-item file (sha e62bfd41…) is byte-identical to the record's.

**Heuristics frozen before scoring** (`width-pilot-item0/frozen_heuristics.py`, sha256 `8b2965917bd480fe533b2fce5bdc36a16a661d3922dd14443fb4ada8e1c32b41`): H1 J-only, H2 plus-join, H3 shared-cells. "1-step" = the shallowest HO stratum (3 calls); HO has no literal 1-call items.

**Freeze-order disclosure.** Before freezing, the analyst had seen the number of valid items for J-only (14), K+J (0) and a range-echo rule (51 of 130 applicable). No accuracy split by validity or depth had been seen. H3 was written after range-echo showed low capture of failures. The freeze is therefore clean on the outcome measures but not on item counts. This does not affect the NO answer, because no rule passes.

| Model / heuristic | Validity (valid vs invalid) | Effect | Invalid by calls (3 / 4 / 5 / 6+) | Depth effect | Invalid 3-call | Failures captured |
|---|---|---|---|---|---|---|
| L13 H1 | 1/14 vs 58/406 | −7.1 | 35.8 / 1.5 / 9.8 / 0.0 | 35.8 | 35.8% | 17/361 |
| L13 H2 | valid n = 0 | n/a | 34.9 / 1.4 / 9.4 / 0.0 | 34.9 | 34.9% | 8/361 |
| **L13 H3** | 28/70 vs 31/350 | **+31.1** | 22.0 / 1.6 / 9.0 / 0.0 | **22.0** | **22.0%** (CI 14.4–32.1) | 11/361 |
| L14 H1 | 1/14 vs 40/406 | −2.7 | 24.4 / 0.0 / 8.1 / 0.0 | 24.4 | 24.4% | 21/379 |
| L14 H2 | valid n = 0 | n/a | 24.0 / 0.0 / 7.8 / 0.0 | 24.0 | 24.0% | 8/379 |
| L14 H3 | 20/70 vs 21/350 | +22.6 | 14.6 / 0.0 / 7.4 / 0.0 | 14.6 | 14.6% | 6/379 |

- Only L13 H3 passes validity, and it fails depth (22.0 > 10) and the shallow-invalid condition (22% > 5%). L14 H3 fails all three.
- **H3's validity effect is item easiness, not a shortcut.** It sits entirely in the 3-call stratum (valid 27/47 vs invalid 18/82 on L13), and only 3% of failures equal H3's answer.
- About ten further candidate rules were screened (exploration scripts, not frozen); none captures more than 5.8% of failures.
- **What the failures are:** mostly first-piece operand reading. On L13, 271/361 failures go wrong first in K; 294/361 have the right op with wrong operands, and row ±1 is the commonest error. Cell-arithmetic pieces score 0/60 (L13) and 0/66 (L14).
- **TEST-11 as worded cannot be satisfied on HO**, because depth is confounded with piece type: L13 accuracy by (nK, nJ) is (1,1) 34.9%, (2,1) 2.2%, (1,2) 0%, (1,3) 21.4%. A depth effect under 10 points would need depth-matched, purpose-built items (suggested). The literal 1-step stratum exists only in F0-near, where the model scores 67.4% (L13) / 60.9% (L14), not chance.

**Consequences (per the playbook's NO branch):**
- factor (2), the shortcut share, is recorded **UNMEASURED**, not zero;
- Item 8 is reduced to **Phase A only**;
- confound **C4 stays OUT** of the pilot's readout.

## (k) Trainer lock and batching feasibility at 2× (shown in principle; Item 1 measures)

- **Trainers locked:**
  - parent stage: custom_io at the f6d724 pin;
  - join stage: `domain/far/learn_probe.py` at `claude/project-thread-94a956` head 4d294b665, plus the C8 draft (5ce1889, under review), plus one small change, a `--diary-data` flag (below).
- **Batching:**
  - **Parent stage (GPU):** batch 256, accum 1, d384. Activations scale with d (about 1.5×) and parameters about 2.2×. T1SDR 3M ran on 16 GB (5070 Ti) and on 5090s, so d384 is expected to fit a 24 GB 4090 without accumulation (suggested). Item 1 confirms peak memory.
  - **Join stage:** **`learn_probe.py` runs on CPU only.** It calls `torch.set_num_threads`, and batches go through `to_device(…, 'cpu')`. Batch 64 plus 32 diary rows fits RAM at any of these sizes.
  - So "fits the 4090 line" holds trivially for memory. **But the join stage's cost is set by the rented box's CPU, not its GPU.** The box's core count goes on every run card.
- **If Item 1 shows the parent stage won't fit at accum 1, the sweep stops** for a hardware decision (playbook (k)). It does not unfreeze batching.

## Code change (small; drafted, awaiting coordinator review)

`DIARY_DATA` in `learn_probe.py` is hard-coded to another session's `/tmp` scratch path (`…/sk200k`). The fix is a `--diary-data` flag (default unchanged) pointing at the seed-1 200k build, drafted in commit 6d8c8d3 with 3 tests (recorded in the run's output as `guard_diary_data`). With that flag, `--parent <run's parent>` and `--diary-compare none`, the join stage is parent-agnostic.

## Status

All of (a)–(k) are recorded against the pass condition: (c) formally excluded, (d) run, (f) answered, (j) answered NO. **Item 0 is ready for the coordinator's freeze.** Two questions ride with it: the definition of the playbook's 40–42% / 65–67% bands, and the axis gate 2(b) decision (base depth 2).

## Correction to the playbook's cost basis (shown; for Item 1)

The playbook prices the sweep trainer as the "B3G2 config class, 7.2 s/update on a 4090", citing the fleet's conflict C1. That is the wrong class:
- The L13 runs used **`learn_probe.py` on the T1SDR `tool` model** (3.3M; command line in `MARKS-L13-NKsoft10-2026-10-13.md`), at **4.6 s/update on 4 CPU threads**.
- B3G2 is the Gemma-fronted agent model; its 7.2 s/update is its own GPU rate.
- The join stage's real per-update cost is a CPU rate on the rented box. The parent stage (new under (a′)) is a GPU rate.

Item 1 must measure both. The playbook's plain-config sensitivity ("divide by about 9.4") is not the right correction either.
