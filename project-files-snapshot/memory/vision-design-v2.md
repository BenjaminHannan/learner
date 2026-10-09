---
name: vision-design-v2
description: Vision input design (Opus thread, 10-03): PR #26 supersedes #22; SigLIP2 probe results; E5 lesion trap; run order
metadata:
  type: project
  modified: 2026-10-03T14:15:04.578Z
---

Thread cmsg_01GSLCHTCnZxn7DhV19qcDvMTBiRP2VKKyQBM8hFtQbUEB owns vision. PR #26 (branch claude/project-thread-72y079) supersedes PR #22. Files: design/next-parts/vision/ (DESIGN.md v2, REVIEW-opus-2026-10-03.md, cpu_probes/). Explainer: https://claude.ai/artifact/PcgthZYe9QWnUAEZagKUDF

- Shown (CPU, frozen google/siglip2-base-patch16-256, ridge probes, marks pre-fixed): 8x8 pooling = 16x16 on count/relation/more/digit, and 9-digit hotbar 99.8% vs 100%. Last layer >= penultimate. PCA-32 costs ~4.5 pts mean.
- Shown: with image in the notebook, read_latent returns only question positions, so a loop-vs-identity lesion is rigged; E5 is now a round curve (1..16) + MLP-probe ceiling.
- Defaults: h=32 adapter, zero-init tags, pos2d x learned 0.1, guides via the text path, NaFlex at screen stage. Glimpse (E4b) only if real Minecraft screenshots fail (P3-MC/P4-MC need ~20 screenshots from Ben).
- Run order: wait for English pilot + reasoner C1/C2, then E1, E2, E4a, S2+E5, E6, E7.

**Why:** Ben moved vision design to Opus (13:42 UTC 10-03).
**How to apply:** route vision GPU work in this order; see [[critical-thinking-reasoner-design]].

- PAUSED (Ben, 15:07 UTC 10-03, cmsg_01GSLCHTCnZxn7DhV19qcDvMAHzsVZ9uKbcBNTDxVh56Ke): "Don't worry abt vision and audio yet." All vision work is saved on PR #26. Resume only when Ben or the coordinator restarts it.
