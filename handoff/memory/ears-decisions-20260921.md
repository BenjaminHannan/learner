---
name: ears-decisions-20260921
description: 2026-09-21 Ben's rulings on the ears/mouth design (doc 43 section L) — Qwen may write practice sentences; fixed small-talk OK; BiGRU fallback OK; plain-software scaffolding OK
metadata:
  type: project
---

Ben's answers to the four open decisions in design/v3/30-modes/43-talker-ears-mouth-design-fable.md section L (2026-09-21):
1. YES — Qwen may write placeholder training/practice sentences (under the doc's four fences, E.5; footnote it in any claim).
3. YES — a fixed small-talk reply is fine in v1.
4. YES ("sure") — a same-size BiGRU is an acceptable fallback if the tape ears lose.
2. YES (2026-09-21, after explanation) — plain software around the learned network is fine: tokeniser/opaque tags, name copying, the five brakes, validator, mouth paste + locks. Honest claim wording: "every weight that listens or speaks was trained from scratch by Ben, with plain-software safety rails". Typos: v1 answers "please rephrase"; licensed later one-change tests = spell-fix toward the fixed lexicon (always echo) and near-name check against the notebook (always ask).

**Why:** unblocks rung 4 arm Q and the fallback path; consistent with [[placeholder-english-ok]] and [[talker-must-be-our-architecture]] (the BiGRU is a fallback, not the goal).

**How to apply:** rung 4's Qwen-written frames arm is licensed; label any claim with the training-data footnote. All four decisions are now settled.
