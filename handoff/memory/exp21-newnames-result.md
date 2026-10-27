---
name: exp21-newnames-result
description: "2026-09-20 experiment 21 / M1 new names: registered FAIL 0/3, control 3/3 perfect; model zeroed code_scale (switched names off) within 500 updates"
metadata:
  type: project
---

Experiment 21 (M1 "new names": random re-drawn name codes per world, tied input/output, reserved half never trained) ran once under freeze on 2026-09-20. Control (fixed name table) 512/512 on all ten cells, 3/3 seeds. Treatment FAIL 0/3: 25–149/512 on most cells, 0 on c4/c5, LINK at chance (1/16), reserved-minus-trained exactly +0 on all 30 cells. scale_trace: `code_scale` fell from 0.139 to ≈0 by update 500 in all seeds and stayed; entity_output_bias went to −1.1…−2.4. The model made names invisible, so it never tested new-name generalisation at all. Speed-limit flag did not fire. All three 3/3-pass forecasts (mine .25, reviewer .35, GPT-6 Pro .45) false; nobody forecast the collapse. Write-up: artifacts/fable-newnames21-20260920/RESULTS.md.

**Why:** M1 is the first milestone of [[teachable-roadmap-fable-review]]; the tied-random-code design has an "ignore the names" shortcut.
**How to apply:** don't run the pre-named 7× scalar-LR follow-up blindly — it targets the opposite problem. Follow-up design goes to a Fable reviewer ([[ask-fable-max-subagent]]); candidates: fixed/normalised code scale, token-pointer copy head (GPT-6 Pro Stage A/B as corrected in design/v3/25b). One change at a time.
