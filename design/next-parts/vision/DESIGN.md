# Images into the Premonition reasoner: design v2 (2026-10-03, Opus thread)

Supersedes `DESIGN-v1.md` (kept for history). Sources for this version: a fresh look at the code, an independent
Opus review (`REVIEW-opus-2026-10-03.md`), CPU probes on the real frozen SigLIP2 encoder (`cpu_probes/`), and the
Workspace contract v1 settled on PR #23.

Labels: **shown** = read in code, measured here, or read in a cited source. **suggested** = reasoning, not tested.
**untested** = a guess or a recalled fact. This file is about the village model only (frozen LFM2.5-1.2B talker,
reader, ~9M looped core). The small card experiments are not part of it.

## 1. What changed from v1, and why

| v1 | v2 | Why |
|---|---|---|
| E5: loops vs an identity lesion | E5 is a **round curve** (1/2/4/8/16 rounds, trained with random depth) plus a **frozen-feature probe ceiling** | With the image in the notebook, `read_latent` returns only question positions, so the image reaches the answer only through rounds. Removing the loop cuts the image off and the test passes by construction. **shown** (code + unit test `test_lesion_trap...`) |
| pos2d added at full size | pos2d times a learned scalar starting at 0.1 | Raw pos2d norm is 11.3 per slot, and 10.3 of that is the same for all 64 slots; adapter content is ~3.4. Position would drown the picture. **shown** (computed) |
| Code: hidden=256, random modality tag | Code now matches the memo: hidden=32, zero-init tag (~35k params) | Code and memo disagreed. **shown**, fixed, tested |
| E3 position on/off, E4 notebook vs grid | **E4a** how position enters (coords bias vs scaled pos2d vs none). **E4b** token budget (64 pooled vs 256 vs 64 global + 64 glimpse) | Under PR #23 the talker reads registers and coords drive the bias, so "query grid vs notebook" stops being a real choice. **suggested** |
| S1 caption alignment first | S1 waits for the reasoner thread's C1/C2 (output path check) | S1 trains through the same average-pooled 8-vector output that C1 tests. If that path is the bottleneck, a vision failure would be misread. **suggested** |
| E1 shuffled image only | E1 adds a **blind arm** (no image tokens) and a test-time shuffle of the trained model; distractor captions from the same scene type | Separates "uses the image" from "LM prior" and "learned gist only". **suggested** |
| Own segment/position format | Workspace v1: `role`, `modality`, `coords [B,N,3]` (row, col, time), `coord_valid [B,N,3]`, `valid` | Shared with reasoner and audio. A still image has time absent; a video frame carries its own time (seconds, <= 0). **shown** in `workspace.py` + test |
| Screen: squash to 256x256 | Screen stage: SigLIP2-B **NaFlex** (keeps 16:9, ~12x21 grid, uses `valid`) | Squashing stretches glyphs 1.78x. LFM2-VL-450M itself uses SigLIP2 NaFlex base (model card). **shown** (card), benefit **untested** |
| Guides as screenshots or text | Guides through the **text path** as `tool_result` tokens | A 256-px encoder is a poor reader of page text. In-game text goes through the image path. **suggested** |

Kept: frozen SigLIP2-B/16 at 256 px for stage 1; thin adapter with no attention; image in the notebook until the core
reads `coords`; DINOv2-S as the one swap test (DINOv3 has a custom licence and gated weights, **shown**).

## 2. CPU probes on real SigLIP2 features (done, shown)

Frozen `google/siglip2-base-patch16-256` (vision tower 92.9M stored params, measured), 1,500 train / 500 test synthetic
images per task, different seeds, ridge linear probes. Marks were fixed in `cpu_probes/MARKS.md` before running.
A linear probe is a lower bound on what an adapter + core could get. These are encoder checks, not reasoning checks.

| Task (chance) | raw pixels 32x32 | last 16x16 | last 8x8 | last 4x4 | pen. 8x8 | last 8x8 PCA-32 |
|---|---|---|---|---|---|---|
| count 1-9 (11%) | 19.6 | 54.6 | 55.4 | 57.8 | 51.4 | 48.4 |
| red left of blue (50%) | 89.0 | 95.4 | 96.2 | 96.0 | 94.6 | 95.4 |
| more red than blue (50%) | 62.0 | 86.8 | 87.2 | 90.0 | 87.0 | 87.4 |
| one 9-px digit (10%) | 10.2 | 99.6 | 99.6 | 99.6 | 99.8 | 89.0 |
| hotbar, 9 digits at once (10%), mean per slot | 63.9 | 100.0 | 99.8 | 97.7 | not run | 94.7 |

Decisions by the fixed marks:
- **P1 pooling:** 8x8 vs 16x16 differs by <1 pt on count and digit. **Keep 8x8.** Even 4x4 loses nothing here.
- **P2 layer:** last beats penultimate by 1.9 pts on the mean. **Keep the last layer.** (The common "use layer -2" habit did not help here.)
- **P3 width:** PCA-32 loses 4.5 pts on the mean (7 on count, 10.6 on digit). Between the marks, so **keep h=32 as the start** and let E2 decide; the digit loss is a warning for UI reading.
- **P4 small text:** one isolated 9-px digit is read at 99.6%. A global view is enough *for one item*.
- **P5 too easy?** "More red than blue" is 87% for a linear probe, below the 90% bar, so it stays usable, but there is little headroom. Counting (55% linear) has the most room for the core to show reasoning. Raw pixels never beat SigLIP, so the encoder suits these tasks.
- **P6 hotbar** (marks added before running, `MARKS.md` addendum A): 8x8 reads all nine 9-px digits at 99.8% vs 100% at 16x16. Within 3 pts, so **keep 8x8 for UI too**. Even 4x4 gets 97.7%.
- Reading: the frozen ViT's patches are contextual, so a pooled 8x8 cell still carries what was inside it. On clean synthetic images, pooling to 8x8 costs nothing we could measure. Caveats (**untested**): Minecraft's pixel font sits on textured slots with shadows, and on a real 1080p screen squashed to 256 px a digit may be ~7 px, smaller than the 9 px tested. So the glimpse (E4b) is now **conditional**: run it only if P4-MC/P3-MC on real screenshots fail.

## 3. Path (stage 1)

`image 256x256 -> frozen SigLIP2-B/16, last layer, 16x16x768 -> 2x2 avg pool to 8x8 -> LN, Linear(768,32), GELU, Linear(32,256)
-> + 0.1*pos2d (learned scale, notebook mode only) -> Workspace(role=notebook, modality=image, coords=(row,col,-), time absent)`.
The question stays text. When the core reads `coords`, pos2d is dropped (E4a decides).

## 4. GPU experiments, one change each (none run; 2 seeds; marks fixed now)

Order: wait for reasoner C1/C2 -> E1 -> E2 -> E4a -> E4b -> S2 skills with E5 -> E6 -> E7.

| # | Single change | Pass | Proves it wrong |
|---|---|---|---|
| E1 | S1 adapter with real images vs shuffled images; plus blind arm and test-time shuffle (controls, not changes) | held-out caption loss >=0.15 nats/token below shuffled and blind; 8-way same-scene caption pick >=50% | real within 0.05 nats of shuffled or blind |
| E2 | adapter hidden 32 -> 128 | >=10 pts on 8-way pick, both seeds | <3 pts |
| E4a | position: scaled pos2d vs coords relative bias (needs the reasoner's coords bias) on left/right/above and nearest-to-X | coords >=5 pts better, both seeds | gap <2 -> keep pos2d until scale-up |
| E4b | (only if P3-MC/P4-MC fail on real screenshots) 64 pooled vs 64 global + 64 glimpse at a *given* location, on real hotbar reading and small-object count | glimpse >=20 pts better | <5 pts -> pooling is not the bottleneck; drop glimpse |
| E4c | (only if E4b passes) given glimpse location -> location chosen by the registers | recovers >=70% of E4b's gain | <30% -> needs another training signal; outside opinion |
| E5 | protocol: core trained with random depth, scored at 1/2/4/8/16 rounds, vs a 2-layer MLP probe on frozen features + question id | on count-then-compare, 8 rounds beats the MLP probe by >=15 pts and 1 round by >=10 pts, both seeds | probe within 5 pts of the core, or 8 rounds <= 1 round + 3 pts (encoder or LM is doing the thinking) |
| E6 | text replay on vs off during S2 | text eval within 1 pt of pre-vision | drop >3 pts even with replay |
| E7 | SigLIP2-B -> DINOv2-S/14 | report only; neither wins unless >=5 pts | - |

S2 data must include compositional held-out splits (unseen colour x shape, counts above the trained range) and a
per-template answer-balance check, so a blind guess scores at chance.

## 5. Roadmap to playing Minecraft from the screen (all suggested unless cited)

1. **Stills (stage 1).** Sections 3-4.
2. **A small 2D survival game first** (Crafter-like), run on CPU at high speed, before Minecraft.
3. **Frames.** A *fast loop* at 10-20 Hz: encoder + 1-4 core rounds per frame, carrying the core state from the last frame, so thinking spreads across frames. Older frames enter the notebook as compressed register snapshots with their time (Workspace time, log buckets). The 1.2B LM is a *slow loop*, called only to speak or to read guides. Cost estimate: SigLIP2-B ~44 GFLOP/frame, core ~6 GFLOP/frame, so 10-20 Hz looks feasible on the 5070 Ti; latency **untested**.
4. **Glimpse, if needed.** If real screenshots show the global 8x8 view misses UI detail, the registers pick where to look at full resolution (E4b/E4c), and that choice is the first trained action. CPU probes so far say a global view may be enough.
5. **Keyboard and mouse head** on the registers: multi-binary keys, binned mouse dx/dy, click. VPT used a 20 Hz keyboard-and-mouse interface at 128x128 (**shown**, arXiv 2206.11795).
6. **Learning from video.** VPT trained an inverse-dynamics model on 1,962 h of labelled play and labelled ~70k h of web video; the diamond pickaxe still needed fine-tuning plus RL and worked in 2.5% of episodes (**shown**). Our version is small: Ben records a few hours of his own play with key logging, and a small inverse-dynamics head on our frozen features labels more video.
7. **Cheap world model.** DreamerV3 found diamonds from 64x64 pixels in 100M steps on one GPU for 9 days (**shown**), beyond our budget. Instead, an auxiliary loss predicts the next frame's SigLIP features from the registers plus the action.
8. **Guides.** Fetched page text enters as `tool_result` tokens through the text path.
9. **Sound.** Audio slots share the time axis, so "creeper hiss 400 ms ago, behind" and the current frame can be ordered in one workspace (audio thread, PR #24/#25).

## 6. CPU checks still open
- **P3-MC:** does SigLIP2 tell Minecraft blocks apart? 200 labelled crops from Ben's screenshots, 20 classes. Probe >=70% -> fine; <40% -> plan a Minecraft-specific encoder (MineCLIP swap). Needs ~20 screenshots from Ben.
- **P4-MC:** measure hotbar digit height after the planned resize at Ben's resolution and GUI scale. Under 7 px (below what P6 tested) -> run E4b; also run the P6 probe on real hotbar crops.
- **P5-NaFlex:** grid shapes for 16:9 and 4:3 through `workspace.py`.

## Plain-language summary for Ben
We still borrow Google's SigLIP2 "eye" and squeeze its 16x16 grid to 8x8. We tested that on this computer with the real
eye and made-up pictures. Squeezing lost nothing we could measure, the eye's last layer was best, and even a row of
nine tiny digits (like a Minecraft hotbar) was read 99.8% right after squeezing. Real Minecraft screenshots are the
next check, because its font and textures are messier than our test pictures. We also fixed three things. The old "is the reasoner really
thinking?" test was rigged to pass, so now we compare 1 thinking round against 8 and against a simple guesser.
The "where is this square" stamps were three times louder than the picture, so they now start quiet. And the code
now matches the plan. For Minecraft, the model will think a little on every frame and keep thinking across frames,
the big language model stays out of the fast loop, and guides are read as text.
