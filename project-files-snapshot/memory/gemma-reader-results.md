---
name: gemma-reader-results
description: EmbeddingGemma-in-B2 arms results 10-06/07 (EGE beats B2 but fails 2 marks; window was the cause) and the staged 6-seed confirm
metadata:
  type: project
  modified: 2026-10-07T05:37:42.584Z
---

Custom reader/talker thread (cmsg_01GSLCHTCnZxn7DhV19qcDvMVbDg7CgQkSgfNbyPrJL8Fu), branch claude/custom-reader-talker-4x309r, final analysis commit b3420dc7f, custom_io/results/RESULTS-EG2.md. All on rented 5090s, each arm vs plain B2 (B2V) of its seed; seeds 200/201.

- EGW, EGM, EGO, EGR: FAIL. All had reader_layers 0 (no +-4 window) and lost cipher_map (100 -> 2.5-10).
- Letter explanation ("Gemma hides letters") PROVED WRONG by the addendum 12 check (EGR cipher 5/2.5 with letters given back). Ben's replies were corrected with strike-through.
- R0 (window removed, no Gemma): "the window matters", B2-R0 +6.8/+6.3, cipher 12.5/2.5. Window check (addendum 13): the window is what cipher_map needs.
- EGE (Gemma added BEFORE the window, 274.5M whole, 3.5M trained): pooled-5 +1.59/+2.12, every split up (frame +3.6, vocab +2.7), cipher 97.5/95. FAILS addendum 4 marks 2 (variant +1.70 < 3) and 5 (loops:0 18.09 on s200 > 5; s201 4.49).
- EGK (eg_thinker: Gemma only into the controller cross-attn, addendum 14): FAIL, non-finite loss twice on s201; s200 +0.98 and loops:0 13.68, so the zero-round score does NOT come from the talker reading Gemma directly.
- Addendum 15: EGE 6-seed confirm on fresh seeds 202-207 (marks fixed: mean gain >= +1 and ahead on 5/6, no split < -2, chain-5 >= 99, loops:0 mean <= B2 mean + 1; wrong if mean < 0.5 or behind on 3+). Staged as PC queue 39 after q38 (Mac confirmed 1:37 AM ET: waiter q39_run.cmd, code C:\Users\benja\custom-io\src-eg2m, log work\q39.log; starts ~3:40 AM ET 10-07, Mac estimate 17-20 h, so ~9 PM-midnight ET 10-07). q35 finished 6/6 10:31 PM ET 10-06 (results not pushed yet); q38 EGT_s200 done 1:05 AM ET. Decision card to Ben (recommended PC); coordinator took the PC default overnight. No Vast spend on it without Ben. analyze_eg.confirm_ege judges it.
- q39 STARTED on PC 2:56 AM ET 10-07 (EGE_s202+s203 first). EGT (q38) FAIL: +0.18/+0.61, variant +2.54. PC plain B2 loops:0 is 0.00 (s200) and 10.81 (s201), so loops:0 is noisy even for B2.
- Test B1 students (q35) judged 4:05 AM ET 10-07 (e10ea0232, results/RESULTS-B1.md): B1-a PROVED WRONG (+0.78; short-answer +0.15), B1-c FAIL (-2.73), B1-b uninformative. Way B at ~10M dead; pre-written next = ~100M student (thinker-first thread's call; sent via coordinator). Replied to Ben.
- Vast boxes A-D all destroyed; credit $5.25 at 1:45 AM ET 10-07. Box B (offer 44614428, US) and box D ran EGE-type jobs slowly (~2.8-4 upd/s).

**Why:** Ben wants a Gemma version that beats B2 (pretrained encoders as the long-term path for Minecraft).
**How to apply:** when q39 lands, run analyze_eg with results 33 + 39 and report the addendum 15 verdict. Related: [[thinker-first-split]].
