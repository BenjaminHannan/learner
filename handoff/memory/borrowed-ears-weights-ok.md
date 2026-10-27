---
name: borrowed-ears-weights-ok
description: "2026-09-21 ruling — ears may use a fine-tuned open-weight encoder (someone else's weights) for now; own pretrained encoder swapped in later on the same marks"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-22T00:32:12.714Z
---

Ben (2026-09-21): "for now it's fine to have ears' weights that would be someone else's. My biggest concern was mostly just that it wouldn't be as good for our model."

**Why:** Ben wants the ears to read research papers (open vocabulary). A from-scratch 3,000-word tape/BiGRU can't; pretraining our own encoder first would delay testing the thought format by weeks. Borrowed-now/own-later was my recommendation and he accepted it.

**How to apply:** Rung 2 ears = tape vs BiGRU vs fine-tuned open encoder (permissive licence, ~100M–500M, frozen body + our frame head + five brakes), all on the same safety-first marks. Own pretrained encoder replaces it later, compared on identical marks. Quality-for-our-model is his concern, so report fit (coverage/safety marks) not just English ability. Related: [[ears-vocab-and-transformer-ruling]], [[placeholder-english-ok]], [[pretraining-english-only]].
