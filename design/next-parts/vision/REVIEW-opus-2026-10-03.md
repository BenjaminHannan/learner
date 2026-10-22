# Independent review: vision path for the Premonition village model (2026-10-03)

Labels: **shown** = read in repo code, computed by me on CPU, or read in a source I opened (cited). **suggested** = my reasoning. **untested** = a guess or a recalled fact I did not check. Small card experiments are out of scope. No repo files were edited; nothing was trained.

## 0. Things the earlier memo got wrong or missed (code-level)

1. **The planned loop lesion (E5) is broken in notebook mode.** `read_latent` returns only `h[:, :query_n]`, the text-question positions (`sol_spatial_attention_core.py`, `read_latent`) **shown**. The image sits in the notebook and reaches the question positions only through attention inside `step`. If the loop is replaced by identity, the read-out never sees the image, so "loops beat the lesion" is guaranteed and proves nothing about thinking **suggested (follows from the code)**. Fix: compare 1 round against N rounds, both trained with random depth, plus a probe baseline (see §4).
2. **pos2d swamps the image content at init.** CPU check with `vision_adapter.py`: the pos2d vector has a norm of 11.3 per slot, and 10.3 of that is a vector shared by all 64 slots (low-frequency `cos≈1` dims). The adapter's content norm is about 3.3-3.5 (h=32 or 256). The smallest distance between two slots' codes is 2.2 **shown (computed)**. So image tokens arrive as "one big shared constant + small content". That can flatten attention onto the image block (untested). Cheap fix: drop pos2d once the coords bias exists, or scale it by a learned scalar that starts at about 0.1 **suggested**.
3. **Code and memo disagree.** `GridAdapter` defaults to `hidden=256`, and its modality embedding is `normal(0.02)` rather than zero-init. DESIGN.md says h=32 and "ZERO-INIT" **shown**. `SegmentEmbedding` in `workspace.py` is zero-init **shown**. Pick one before any GPU run.
4. **CLIP=4 already merges offsets on 8x8.** An 8x8 grid spans offsets of ±7, so 5, 6 and 7 all collapse into the ±4 bucket (`claude_fewex_net.py: CLIP, WINDOW = 4, 1`; `offsets` clamps) **shown**. Saying "8x8 is safe, 16x16 is not" overstates the difference.
5. **The encoder pairing claim is now checked.** LFM2-VL-450M uses "SigLIP2 NaFlex base (86M)" and tiles images at 512×512 ([HF card](https://huggingface.co/LiquidAI/LFM2-VL-450M)) **shown**. That is the NaFlex variant, not the 256px FixRes model the design picked.
6. **Ordering conflict with the reasoner redesign.** Stage S1 trains the adapter to make the LM produce a caption through the current output path: question positions are average-pooled into 8 prefix vectors **shown (reasoner doc §2)**. The reasoner thread's C1 asks whether that path can carry even "The answer is 4827". If C1 fails, an S1 failure cannot be blamed on vision. **Run vision S1 only after C1/C2 settle the output path** **suggested**.

## 1. Encoder choice

Facts I checked:
- SigLIP 2 comes in B 86M, L 303M, So400m 400M and g 1B. NaFlex variants keep the native aspect ratio ([arXiv 2502.14786](https://arxiv.org/abs/2502.14786)) **shown**.
- NaFlex resizes an image to at most `max_num_patches` (default 256), keeps the aspect ratio, and pads with a mask ([HF docs](https://huggingface.co/docs/transformers/model_doc/siglip2)) **shown**.
- SigLIP2 base NaFlex is Apache-2.0 ([HF card](https://huggingface.co/google/siglip2-base-patch16-naflex)) **shown**.
- DINOv2 code and weights are Apache-2.0, and ViT-S/14 has 21M parameters ([GitHub](https://github.com/facebookresearch/dinov2)) **shown**.
- DINOv3 ViT-S/16 has 21M parameters but uses the custom "DINOv3 License" and its download is gated ([HF](https://huggingface.co/facebook/dinov3-vits16-pretrain-lvd1689m)) **shown**. That is a reason to prefer DINOv2 as the swap test.

My judgment:
- **Stage 1 (synthetic square images): keep frozen SigLIP2-B/16, FixRes 256** **suggested**. Language alignment and a 16x16 grid are good enough for a proof of concept.
- **Screen stage: switch to SigLIP2-B/16 NaFlex.** Squashing 16:9 onto 256×256 stretches every glyph by 1.78× horizontally. NaFlex at 256 patches on 16:9 gives roughly a 12×21 grid (252 patches, my arithmetic) with no distortion **suggested**. It needs `valid` and `coords`, which the Workspace contract now has **shown**.
- **Penultimate vs last layer.** SigLIP's training loss reaches patch tokens only through the pooled (MAP) head, so last-layer patch tokens may be less spatial. Many VLMs read layer −2 **untested**. Settle it with the CPU probe P1 below rather than by belief.
- **Small trainable CNN at 64-128px (Dreamer/VPT style).**
  - DreamerV3 sees 64×64×3 in Minecraft (paper appendix) **shown**.
  - VPT uses 128×128, and says this was "the smallest resolution for which in-game GUI elements are still discernible" ([VPT, arXiv 2206.11795](https://arxiv.org/abs/2206.11795), App.) **shown**.
  - Both learned their pixels from millions of frames with in-game reward or labels. We have no such budget at stage 1, and a CNN gives no language alignment.
  - So: no CNN as the main encoder now. Keep it as a later fast path for motion and low-level control **suggested**.
- **Out-of-distribution textures.** Whether SigLIP2 represents Minecraft blocks well is **untested**. Probe P3 checks it.
- **MineCLIP alternative.** MineCLIP is a 150M video-text model trained on 640K Minecraft clip/transcript pairs at 160×256, and it is used as a reward ([MineDojo](https://arxiv.org/html/2206.08853)) **shown**. It is a candidate swap for the Minecraft stage. Its weight licence is **untested**.
- **Real-time cost.** SigLIP2-B at 256 tokens is about 2·86M·256 ≈ 44 GFLOP per frame. The core costs about 2·2.6M active·300 tokens·4 rounds ≈ 6 GFLOP per frame. That is plausible at 10-20 Hz on a 5070 Ti, but the latency is **untested**. The 1.2B LM must not be inside the per-frame loop **suggested**.

## 2. The 8x8 pooling and the alternatives

What pooling throws away (arithmetic, **suggested**; Minecraft GUI sizes **untested**):
- At 1080p with GUI scale 4, a hotbar digit is about 28-32 px tall. After squashing to 256 px it is about 7 px, under half of one 16-px patch.
- After 2×2 pooling, the whole 9-slot hotbar falls into about 3 pooled cells. Item counts and crafting-grid contents are then unreadable whatever the encoder.
- Counting small objects suffers in the same way: two objects in one 32-px cell average into one vector.

Options, best long-term first:
1. **Global view plus a foveated glimpse chosen by the reasoner.**
   - Use 64 global tokens (8x8) plus a 16x16 patch grid from a crop at native resolution, centred where the registers point.
   - The glimpse is the first *action* the model learns. It is low-risk, it is graded by task success, and it trains the same register→action head that will later move the mouse.
   - Training the choice of location needs either RL/REINFORCE or a differentiable soft-attention variant **suggested**.
   - This is my preferred direction **suggested**.
2. **16x16 with the coords bias.** This needs CLIP raised (say to 8 or 16) or a log-bucketed bias, which is a reasoner-thread change. It costs 4× the tokens, and attention cost grows with the square of the token count. It is fine for stage 1 **suggested**.
3. **Fixed UI crops** (hotbar and inventory at known screen positions as extra tokens). This is cheap and Minecraft-specific. It is good as a scaffold, but it hard-codes the game **suggested**.

## 3. Is E4 (notebook vs main grid) still the right question?

**No** **suggested**. In the redesign, output is read from 8 draft registers, the role/modality ids say what each token is, and coords drive a relative bias (reasoner doc §3, §6) **shown**. "Query grid vs notebook" then reduces to two smaller questions:
- **E4a. How position enters:** coords relative bias vs absolute pos2d vs none, on left/right/above and on "which object is nearest X". This replaces E3+E4.
- **E4b. Token budget:** 64 pooled vs 256 full vs 64 global + 64 glimpse, with tokens held equal where possible, on small-object counting and digit reading.

Until the redesign lands, keep the image in the notebook and change nothing else.

## 4. E1-E7: controls, marks, gaps, order

- **E1 (shuffled image).** Good. Add a **blind arm** (empty or zeroed image tokens) and evaluate the trained model with shuffled images at test time, not only as a separately trained arm. The 8-way caption pick needs distractors from the same scene type, or it rewards coarse gist only. Pass marks stand.
- **E2, E6, E7.** Fine as written.
- **E3.** Expect its falsifier to fire, because SigLIP patches carry learned absolute positions (**untested**). Fold it into E4a.
- **E5. Replace it with a round curve plus a probe ceiling.**
  - (a) A frozen-feature probe: a linear head and a 2-layer MLP on the pooled SigLIP features plus the question id. This is the "the encoder does the thinking" bar.
  - (b) The core trained with random depth (1..16, as `claude_fewex_net.py` `train_loss` does for puzzles **shown**), scored at 1, 2, 4, 8 and 16 rounds.
  - Pass: on count-then-compare, the core at 8 rounds beats the MLP probe by ≥15 points and beats its own 1-round score by ≥10 points, on both seeds.
  - Proves it wrong: the probe comes within 5 points of the core, or 8 rounds is ≤ 1 round + 3 points.
- **Missing pieces.**
  - A blind or text-prior baseline on S2 tasks (answer balance per question template).
  - Compositional held-out splits (unseen colour×shape pairs, larger counts than seen in training).
  - A small-object/digit task that measures what pooling costs.
  - A check that the pos2d scale is not dominating (§0.2).
- **Order.** CPU probes P1-P5 → (wait for reasoner C1/C2) → E1 + blind → E2 → E4a → E4b → S2 skills with the E5 replacement → E6 → E7.

## 5. Roadmap to real-time closed-loop play (all **suggested** unless cited)

1. **Stage 1, synthetic stills.** As above.
2. **Crafter or a 2D grid game before Minecraft.** It is a cheap, CPU-speed Minecraft-like test (Crafter facts **untested**).
3. **Frames and memory.**
   - Run a *fast loop* at 10-20 Hz: encoder plus 1-4 core rounds per frame, warm-starting the core state `h` from the previous frame. The looped design suits this, because extra rounds can be spread across frames.
   - Older frames enter as compressed register snapshots in the notebook with a time coordinate, not as raw patches.
   - The LM talker is a *slow loop*, called only to speak or read.
4. **Action head on the registers:** multi-binary keys, binned mouse dx/dy, click. Note what VPT's interface is: 20 Hz keyboard and mouse (VPT abstract) **shown**.
5. **Learning from unlabeled video (VPT recipe).**
   - VPT trained a non-causal inverse-dynamics model on 1,962 hours of contractor data (90.6% keypress accuracy, mouse R² 0.97) and pseudo-labelled about 70k hours of clean web video **shown**.
   - The IDM has about 0.5B weights, and the RL runs used a 248M model **shown**.
   - The diamond pickaxe needed BC pretraining, then BC fine-tuning on early-game video, then RL, and succeeded in 2.5% of episodes **shown** (VPT §4-5).
   - Our budget cannot repeat any of that. The realistic version: Ben records a few hours of his own play with key logging, and we train a small IDM on our frozen features, *or* reuse VPT's released models and data (availability and licence **untested**).
6. **World models.** DreamerV3 found diamonds from scratch in 100M environment steps, using 64×64 input, an abstract MineRL action space with "block breaking" eased, and 1 GPU for 9 days (Nature version, arXiv 2301.04104) **shown**. That is outside a $15-40 budget. Use a *cheap* world-model signal instead: an auxiliary loss that predicts the next frame's SigLIP features from current registers plus the action **suggested**.
7. **Reading guides.** Use the text path: fetched text goes into the notebook as a tool_result segment. Screenshots of guides would demand small-text OCR that a 256-px SigLIP-B is unlikely to give (**untested**). Screenshots are only for in-game reading, through the glimpse.

## 6. One change at a time (pass marks fixed now)

| # | Change | Pass | Proves it wrong |
|---|---|---|---|
| R1 | pos2d × learned scalar (init 0.1) vs raw pos2d, before S1 | spatial-relation accuracy ≥5 pts better, or S1 caption loss ≥0.05 nats lower, both seeds | both gaps within noise (<2 pts / <0.02 nats) → scale is harmless |
| R2 | E5 → round curve + MLP-probe ceiling (protocol, not a model change) | see §4 | see §4 |
| R3 | 8x8 pooled → 64 global + 64-token glimpse at a *given* (oracle) location, on synthetic digit/count-of-small-objects | ≥20 pts better than 8x8, both seeds | <5 pts → pooling isn't the bottleneck, drop glimpse |
| R4 | (only if R3 passes) oracle location → location chosen by the registers | recovers ≥70% of the oracle gain | <30% → location learning needs a different training signal; ask for an outside opinion |
| R5 | FixRes squash → NaFlex at the screen stage | ≥5 pts on a UI-reading task | <2 pts → keep FixRes |

## 7. CPU-only checks before any GPU time

- **P0 (done, shown above).** pos2d norm 11.3 vs content 3.3-3.5. Pass for "harmless": ratio <1.5. **Failed.**
- **P1. Layer choice and pooling cost.**
  - Load real SigLIP2-B on CPU (~86M, fine). Render about 2k synthetic 256-px images: small squares of 4/8/16 px, counts 1-9; left/right pairs; two-digit numbers in a pixel font at 6-10 px.
  - Fit closed-form ridge probes on features from {last, penultimate} × {16x16, 8x8 pooled}.
  - Marks, fixed now:
    - Penultimate beats last by ≥5 pts on count/position → use −2. Within 2 → keep last.
    - 8x8 loses ≥10 pts vs 16x16 on 8-px counting or digits → pooling matters, and R3 is justified. <3 → keep 8x8.
- **P2. The lesion trap, shown with a unit test.** At 0 rounds, the gradient of `read_latent` output with respect to the notebook is exactly zero, and after 1 round it is non-zero. This confirms §0.1 cheaply.
- **P3. Minecraft out-of-distribution check.**
  - 200 labelled crops from Ben's screenshots (20 block/item classes).
  - SigLIP2 zero-shot text matching and a ridge probe.
  - Marks: probe ≥70% top-1 → features carry block identity. <40% → plan a fine-tuned or Minecraft-specific encoder (MineCLIP swap).
- **P4. UI size arithmetic on real screenshots.** Measure the digit height in pixels after the planned resize, at Ben's real resolution and GUI scale. Mark: under 12 px (under one patch) → UI reading needs the glimpse or crops.
- **P5. NaFlex grid shapes for 16:9 and 4:3.** Confirm the valid-mask and coords path end to end with `workspace.py`.

## Plain-language summary for Ben

The plan to borrow Google's SigLIP2 picture reader is fine for the first step. I found four problems. First, the planned test of "is the reasoner really thinking?" was rigged to pass: if you switch the reasoner off, the picture has no path to the answer at all, so of course it does worse. Better tests: compare 1 thinking round against 8, and compare against a simple guesser that reads the picture features directly. Second, the "where is this square" stamps are about three times louder than the picture information itself, and most of the stamp is the same for every square. Turn it down. Third, shrinking the picture to an 8x8 grid makes Minecraft's small numbers (hotbar counts, crafting slots) impossible to read. The best fix is to let the model choose where to look closely, like your eyes do. That "where to look" choice is also the first step toward moving a mouse. Fourth, the picture training should wait until the other thread fixes how answers come out, or we won't know which part failed. For Minecraft, the big results (OpenAI's VPT, DreamerV3) used thousands of hours of video or nine days on a big GPU, so we copy their ideas small: learn from recordings of your own play, and keep the big language model out of the fast 20-times-a-second loop. Most of these questions can be checked on a normal CPU first, for free.
