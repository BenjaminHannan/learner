# [Superseded by DESIGN.md v2] Images into the Premonition reasoner: design memo v1 (2026-10-03)

Labels: **[shown]** = read in this repo's code; **[suggested]** = my reasoning, not tested; **[untested]** = outside fact I'm recalling and haven't checked. This memo covers only the village-model pipeline (frozen LFM2.5-1.2B, reader, ~9M looped core, 8 prefix vectors). The small card experiments are mentioned only as a later source of tasks.

## 0. What the code does now
- `HumanInputProjection`: LN(lm_width) -> Linear(lm_width,32) -> GELU -> Linear(32,256), output `[B,1,T,256]`. Text arrives as a 1xT grid **[shown]**.
- `begin_latent(latent [B,H,W,256], notebook [B,M,256])` concatenates the notebook after the grid. Notebook rows get offset index `CLIP` in both dr and dc, which means relative offset 0. So every notebook slot looks like "same cell" to every query, and the narrow heads (half the heads, which mask |dc|>1) can still see them **[shown]**. As a result **the notebook has no geometry**, and `begin_latent` takes **no padding mask** **[shown]**.
- `read_latent` returns only the first `query_n` = HxW positions to the output translator **[shown]**.
- CLIP=4, so relative offsets saturate past ±4 **[shown]**. Core = 2 blocks at d=256 with 8-expert upcycled MLPs, about 9M **[suggested, from the shapes]**.

## 1. Candidate frozen encoders (vision tower only)
| Encoder | ~Params | Width / grid | Notes |
|---|---|---|---|
| SigLIP2-B/16 @256px | ~86-93M | 768, 16x16 | Aligned with language. A SigLIP2 base tower is reportedly the encoder in LFM2-VL-450M, the same family as our LM **[untested]** |
| SigLIP-B/16 (v1) | ~86M | 768, 14x14@224 or 16x16@256 | Older, well supported **[untested]** |
| DINOv2-S/14 | ~21-22M | 384, 16x16@224 | Strong spatial features, no language alignment **[untested]** |
| TinyCLIP ViT-8M/16 | ~8M image side | ~256, 14x14 | **Unsure** of exact count and quality |
| MobileCLIP-S0 | ~11M image side | conv/hybrid | **Unsure**. Its grid output is not a plain ViT grid |
| MobileViT-S | ~5.6M | ImageNet classifier | **Unsure** and weak as a general feature source |
| SigLIP So400m | ~400M | 1152 | Too big for stage 1 |

**Stage-1 pick: SigLIP2-B/16 at 256px, frozen, features cached once.** It gives a native 16x16 grid, its features are aligned with text (which helps the frozen LM read our prefixes), and the most likely LFM pairing is with this family **[suggested]**. Use DINOv2-S as the single swap test (E7).

## 2. Modality-agnostic interface contract
Every translator (text, image, audio) emits one `Percept` **[suggested]**:
```
tokens  [B, N, 256]   float, same dtype/device as core
layout  "grid" (H,W with N=H*W) | "seq" (N=T, treated as H=1) | "set"
coords  [B, N, 2] int (row, col) or None   # for a future reasoner that takes coords
valid   [B, N] bool                         # needed once padding exists
modality int  -> nn.Embedding(n_mod, 256), ZERO-INIT, added to tokens
role    "query" | "context"
```
- **Shim to today's core**: the `query` Percept is reshaped to `[B,H,W,256]` as the latent, and `context` Percepts are flattened and concatenated into the notebook. The contract is defined at the translator output, not at `begin_latent`, so the sibling reasoner redesign can take `coords` and `valid` directly **[suggested]**.
- **Stage-1 placement**: the text question stays the query (1xT), so the output translator keeps seeing the input type it was trained on. **The image is notebook context.** Its notebook slots have no relative geometry, so the image adapter adds a fixed 2D sin-cos position (row half, col half, 0 params) before the tag **[suggested]**. Putting the image in the latent grid instead is experiment E4.
- **Fixed grid**: resize to 256x256 (squash, no crop), take 16x16 SigLIP patches, then 2x2 average pool to **8x8 = 64 slots** (default; 16x16 = 256 is the E-later option). A fixed N means no padding, which matters because the notebook has no mask **[shown, for the missing mask]**. On 8x8, offsets up to ±4 stay distinct under CLIP. On 16x16 many offsets merge **[shown, for CLIP]**.
- With a zero-init modality tag, the text path stays exactly as it is at initialisation (test T1) **[suggested]**.

## 3. Adapter
`LN(768) -> Linear(768,h) -> GELU -> Linear(h,256) + pos2d + tag[image]`. This mirrors `HumanInputProjection` and is the same thin translator with no attention **[suggested]**.
- h=32 (matches the text pipe): about 1.5k + 24.6k + 8.4k ≈ **35k trainable**.
- h=128: about **132k**. The tag adds 256 per modality.
- **Start at h=32** so that "image vs text" is the only difference from the text path. The width is tested alone in E2. A frozen ViT feature is already contextual, so 32 may hold up better here than it does for single token embeddings, but this is **[untested]**.

## 4. Training stages
| Stage | Trainable | Frozen | Data |
|---|---|---|---|
| S0 CPU | nothing | all | contract tests, feature cache |
| S1 align | image adapter (+tag) | SigLIP2, LM, core, text reader, output adapter | human captions (e.g. COCO). Query = fixed text "What is in the picture?". Loss = existing `human_loss` on the caption |
| S2 skills | core (low LR) + image adapter | SigLIP2, LM, text reader | synthetic images: count, compare, left/right/above, count-then-compare |
| S3 retention | same as S2 | same | S2 mixed with text replay |

**Cheap tests with no GPU** **[suggested]**:
- T1: with a zero tag and an empty notebook, text outputs are bitwise equal to the current pipeline (CPU, a few rows).
- T2: shape and dtype guards. N=64, the notebook concat path runs, and `query_n` is unchanged.
- T3: feature cache is deterministic. Same image gives the same sha256 of features.
- T4: bottleneck rank. PCA on about 2k cached SigLIP patch vectors, measuring the variance kept at 32 vs 128 dims. Also a closed-form ridge probe for color/shape/position on synthetic images through a random 32- vs 128-dim projection (CPU, minutes).
- T5: position sanity. Check that pos2d sin-cos values differ for all 64 slots.
- T6: parameter count printout matches §3.

## 5. GPU experiments (one change each; set noise from 2 seeds first)
| # | Single change | Pass mark (fixed now) | Proves it wrong |
|---|---|---|---|
| E1 | S1 adapter on vs **shuffled image** (features from another image) | held-out caption loss ≥0.15 nats/token below shuffled; 8-way caption pick by LM loss ≥50% (chance 12.5%) | real within 0.05 nats of shuffled → image info isn't getting through |
| E2 | h=32 → h=128 | ≥10 pts better 8-way pick on both seeds = 32 is a cap | <3 pts gain → 32 is not the limit here |
| E3 | pos2d on vs off (left/right/above task) | on ≥85%, off ≤60% (chance 50%) | off also ≥85% → SigLIP already carries position, so pos2d isn't needed |
| E4 | image as notebook+pos2d vs image as **latent grid 8x8** (question → notebook) | grid ≥5 pts better on relation+count, both seeds | gap <2 pts → keep the notebook |
| E5 | core lesion: identity in place of 4 loops | loops beat lesion by ≥15 pts on count-then-compare | gap <5 pts → encoder/LM is doing the thinking, against Ben's rule |
| E6 | S3 text replay on vs off | with replay, text eval within 1 pt of pre-vision | drop >3 pts even with replay → shared core is being overwritten |
| E7 | SigLIP2-B → DINOv2-S | report only. Neither wins unless ≥5 pts | — |

## 6. Risks
- **No geometry in the notebook** **[shown]**. Fixing it with absolute pos2d is a workaround. The proper fix is to pass `coords` into the reasoner's bias, which is the sibling thread's call.
- **No notebook mask** **[shown]**. Variable grids or multiple images need `valid` before they can be used.
- **The encoder or the LM does the reasoning.** SigLIP features already hold some count and relation information **[untested]**, and the LM may answer from priors. E5 and a no-image baseline guard against this.
- **Narrow heads** mask |dc|>1. In grid placement (E4), half the heads see 3-column stripes **[shown]**. This suits puzzles but is unknown for images.
- **Capacity of 8 prefix vectors** may limit long captions. S1 judges on retrieval, not caption fluency **[suggested]**.
- **Captions vs skills**: S1 captioning is only alignment. Skills come from S2 synthetic tasks, which keeps the "skills first, facts later" order.
- **Provenance rules**: the human-origin checks in `human_rows` are text-specific. Caption data needs its own registry **[shown, for text-only checks]**.
- **Licences**: SigLIP2 and DINOv2 are, I believe, Apache-2.0 **[untested]**.
- **Hard choice worth an outside opinion**: E4, grid vs notebook. Either Astra or GPT could review it before GPU time.

## Plain-language summary for Ben
We borrow a ready-made image reader (SigLIP2) that turns a picture into a 16x16 grid of feature vectors. We average that down to 8x8 and squeeze each square through a tiny ~35k-parameter adapter into the same 256-number format the reasoner already uses for text. We also stamp each square with "this is an image" and "this square is at row r, column c". The question stays as text. The picture goes into the reasoner's "notebook". The current notebook has no sense of where things are, which is why we add the position stamps. First we train only the tiny adapter, then the reasoner on picture puzzles. Each later test changes one thing and has a pass mark written down in advance.

## Roadmap (added by the thread, after Ben's Minecraft answer; all [suggested])
1. **Now (CPU, this PR):** contract, adapter prototype, 7 tests with a stand-in frozen encoder. Real SigLIP2 not loaded here.
2. **Pilot (GPU, after the English pilot frees the PC):** S1 then E1-E3. Hand to the execution owner via the coordinator.
3. **Skills:** S2 synthetic puzzles, E4-E6.
4. **Video:** frames at a few per second go through the same adapter; older frames become notebook slots with a time tag. Needs the reasoner's coords/mask (sibling thread).
5. **Screen agent:** the reasoner output goes to a small action head (keys, mouse dx/dy, click) in a closed loop. Ben: play Minecraft like a person from the screen, with keyboard and mouse. Action head, latency and safety of a real game loop are untested.
6. **Reading guides online:** web pages as screenshots go through the same image path (OCR-like reading by SigLIP2 is untested), or as text through the text path. Browser access is a separate design.

Prototype notes: `vision_adapter.py` (GridAdapter, pos2d, FrozenPatchEncoder stand-in) and `test_vision_adapter.py`. Shown by test: the adapter output feeds the real AttentionReasoner both as latent grid and as notebook, the encoder gets no gradients, and a toy quadrant task is learnable through the adapter. This says nothing about real images or reasoning.

## Reconciliation with PR #23 (shared Workspace contract)
PR #23 (critical-thinking reasoner, section 6) defines `Workspace`: `tokens [B,N,256]`, `segment [B,N]`, `coords [B,N,<=3]`, `valid [B,N]`. This design adopts it and drops its own format. Changes to the first draft above:
- **Modality tag + role -> segment.** One learned zero-init embedding per role (question, notebook, example, tool_result, register) and per modality (text, image, audio), summed. Segment shape here is `[B,N,2]` (role, modality) so one vector can carry both. PR #23 uses a single id per vector; if it keeps one id, the pair can be folded into one table with a product vocabulary. Both are cheap; decide when the reasoner thread freezes the table.
- **Layout tag (grid/seq/set) dropped.** Coordinates carry it: images get (row, col, 0), audio will get (0, 0, time), text may get none.
- **Position code.** My fixed sin-cos code was a workaround for the notebook having no geometry. If the core uses `coords` for its bias with a new neutral index (as PR #23 proposes), the workaround is unnecessary and E3 changes to coords-on vs coords-off.
- **Mask.** `valid` is in the contract, so variable grids and several images become possible (they were blocked before).
- Prototype: `workspace.py` (`Workspace`, `SegmentEmbedding`, `image_to_workspace`) and one test. The real core does not yet read `segment`, `coords` or `valid`; that is the reasoner thread's change. Audio thread should emit the same record.
