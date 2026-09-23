---
name: ear235b-gate-result
description: 2026-09-22 — 235b write gate FAIL (5 confident wrong saves, recall 49%); 256 loop wiring stopped; 257 = ear v4 training data on blind earpanel257; 252b option B + 258 pure-denial guard
metadata:
  type: project
---

2026-09-22 17:18, verified by the director's own recount.
- The 235b gate is a margin over the top 4 beams plus a question guard, on the v3 ear. Registered FAIL:
  - arm A: recall 54/110, 5 wrong saves, 33% unsure, ASK 32/40;
  - brake only: 81/110 with 20 wrong;
  - rules: 16/110 with 1 wrong.
- The question guard works. The margin cannot catch confident errors: all 5 wrong saves had no rival reading in the top 4.
- Error classes, which the 257 training data targets:
  - R3 "teaches at" read as school;
  - compound relatives shortened;
  - pronoun attached to the wrong person;
  - invented frames in corrections;
  - relation-table gaps;
  - hop-1 family words.
- 256 (ear in the loop) stopped per its brief. It resumes only when an ear passes a fresh blind panel with ≤ 1 wrong save.
- 252b was ruled option B: the screen also catches apostrophe-less contractions, excluding real words. The remaining junk write ("That's wrong, that's old news.") goes to 258, which makes "that's Z" after a pure denial ask. 252b merges only together with 258.

**Why:** Ben wants no simple mistakes. A wrong save is a false memory.

**How to apply:**
- Don't wire the ear into the loop before the 257 panel passes.
- The Mac CPU ear with beams is slow (about 2.3 s median on a 12-turn pilot), so latency needs its own step before loop use.
- Related: [[learned-reader-decision]], [[decide-better-option]].
