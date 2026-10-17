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
- **Step-count census** (chain-length histogram, template mix and first-operation mix by step count, training vs eval): **open**, being computed on CPU now.

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

**Open**, being analysed now on L13 and L14 per-item outputs, from the repo checkpoints. YES requires one frozen heuristic meeting every TEST-11 condition (validity effect ≥ 25 points; depth effect < 10 points within the invalid row; invalid 1-step at about chance); otherwise NO.

## (k) Trainer lock and batching feasibility at 2× (shown in principle; Item 1 measures)

- **Trainers locked:**
  - parent stage: custom_io at the f6d724 pin;
  - join stage: `domain/far/learn_probe.py` at `claude/project-thread-94a956` head 4d294b665, plus the C8 draft (5ce1889, under review), plus one small change, a `--diary-data` flag (below).
- **Batching:**
  - **Parent stage (GPU):** batch 256, accum 1, d384. Activations scale with d (about 1.5×) and parameters about 2.2×. T1SDR 3M ran on 16 GB (5070 Ti) and on 5090s, so d384 is expected to fit a 24 GB 4090 without accumulation (suggested). Item 1 confirms peak memory.
  - **Join stage:** **`learn_probe.py` runs on CPU only.** It calls `torch.set_num_threads`, and batches go through `to_device(…, 'cpu')`. Batch 64 plus 32 diary rows fits RAM at any of these sizes.
  - So "fits the 4090 line" holds trivially for memory. **But the join stage's cost is set by the rented box's CPU, not its GPU.** The box's core count goes on every run card.
- **If Item 1 shows the parent stage won't fit at accum 1, the sweep stops** for a hardware decision (playbook (k)). It does not unfreeze batching.

## Code change still needed (small, a draft for review)

`DIARY_DATA` in `learn_probe.py` is hard-coded to another session's `/tmp` scratch path (`…/sk200k`). The fix is a `--diary-data` flag (default unchanged) pointing at the seed-1 200k build. With that flag, `--parent <run's parent>` and `--diary-compare none`, the join stage is parent-agnostic.

## Correction to the playbook's cost basis (shown; for Item 1)

The playbook prices the sweep trainer as the "B3G2 config class, 7.2 s/update on a 4090", citing the fleet's conflict C1. That is the wrong class:
- The L13 runs used **`learn_probe.py` on the T1SDR `tool` model** (3.3M; command line in `MARKS-L13-NKsoft10-2026-10-13.md`), at **4.6 s/update on 4 CPU threads**.
- B3G2 is the Gemma-fronted agent model; its 7.2 s/update is its own GPU rate.
- The join stage's real per-update cost is a CPU rate on the rented box. The parent stage (new under (a′)) is a GPU rate.

Item 1 must measure both. The playbook's plain-config sensitivity ("divide by about 9.4") is not the right correction either.
