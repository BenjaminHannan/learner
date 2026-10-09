---
name: blocker-ideas-opus
description: Opus paper-to-ideas pass on the learning blocker (00:20 UTC 10-05): ranked fixes in papers/blocker-ideas.md, key diagnosis = front prefix can't steer attention
metadata:
  type: project
  modified: 2026-10-05T00:17:09.368Z
---

Thread cmsg_01GSLCHTCnZxn7DhV19qcDvMHDNWSFWXEaN2NxuaavcX87 wrote /mnt/project-files/papers/blocker-ideas.md, sent to the plateau session (session_01UVRuQP7opzxjBaPoUr5JcC). No training run.

Shown in code: the LM input is [8 core vectors][prompt embeddings][BOS][answer], so the core's vectors sit BEFORE the question. LFM2.5-1.2B has 16 layers but only 6 attention layers (2,5,8,10,12,14); the rest are kernel-3 convs.
Diagnosis (suggested): per Petrov et al. 2310.19698, a front prefix can't change attention within the question, so it can only elicit skills the LM has. That fits chain families at ~15% and easy families at ~100%.

Ranked ideas, written around fix screen v3 (LoRA everywhere + shuffle lesion):
1. A second exit copy that writes 8 vectors AFTER the question (LRT 2609.01117 places latents there).
2. Two-path loss: an extra CE with the LM seeing only the core vectors.
3. If v3's LoRA helps, shrink it to 2609.36585's one-layer residual edit, then run the shuffle check on it.
4. Random round counts plus an operator-first curriculum.
5. Batch 16.
Free checks: C1 per-round answer probe; C2 whether v3's S swap is same-family; C3 an English check before keeping any LM LoRA.

**Why:** Ben's rule is that Sonnet finds papers and Opus turns them into ideas ([[director-role-and-rules]]).
**How to apply:** when v3 results land, use the decision table in the file to pick the next screen.

Update 00:16 UTC 10-05: the plateau thread adopted C2 and C3 into the v3 spec (a1300fa4c). dev in_dist is grouped by family (1,326 of 1,359 neighbours share a family), so v3's S is a same-family swap. If v3's A fails, ideas 1 (exit after question) and 2 (two-path loss) are its next candidates.
