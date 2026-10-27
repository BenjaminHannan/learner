---
name: gpu-only-5070ti
description: "2026-09-21 — only GPU = BensPC RTX 5070 Ti (no rentals); 23:40 Ben: it is mine to use whenever, no permission needed per job; talker first run approved"
metadata:
  type: feedback
---

Ben (2026-09-21 22:20): "You can use only 5070-ti gpu."

**Why:** no more cloud spend; the PC is free and sufficient for borrowed-encoder fine-tunes (~110–150M params, bf16).

**How to apply:** never propose or prepare a vast.ai rental (supersedes [[compute-availability]], [[gpu-budget-cap]], [[rented-cpu-standing-ok]] for GPU work). Schedule GPU jobs on BensPC one at a time (16 GB); Qwen llama-server must stay down while training (it holds ~15 GB). Mac CPU for everything else. Related: [[director-role]], [[benspc-gpu-ops]].

**Update 2026-09-21 23:40:** Ben: "Go ahead. The gpu is yours to use whenever you want, I don't have rules for whether you can or can't use it" — answering my question about starting the talker's first run (doc 87) when the GPU is idle. So: use the 5070 Ti freely (still one job at a time), and the talker first run is approved.
