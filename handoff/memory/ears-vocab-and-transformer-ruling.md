---
name: ears-vocab-and-transformer-ruling
description: 2026-09-21 Ben — transformer ears are fine "if it turns English into thought"; wants varied vocabulary (read research papers); use sentences from online; WebRED downloaded, WikiFact sentence set dead link
metadata:
  type: feedback
---

Ben's rulings 2026-09-21: (1) a transformer for the ears is acceptable if it turns English into "thought" (the form the reasoner reads) — the tape-ears design is no longer required for the ears, it competes on the same marks; (2) "just get sentences from online" — open web/text datasets for training the ears are approved (download approved, done); (3) he wants a VARIED vocabulary: eventually the model should read research papers and understand what the words mean — the 3,000-word lexicon + opaque tags is a v1 stopgap, not the goal.

**Why:** the notebook-writing ears (closed form, safety first) and the reading goal (open vocabulary) are different jobs; Ben cares about the second.

**How to apply:** bring rung 4's masked-word pretraining forward as its own track: a token-level transformer pretrained on open English on the 5070 Ti ([[pretraining-english-only]]: notebook stays empty, facts never enter weights as truth), reused as the word-meaning front end for both the notebook ears and reading. Keep the closed-form output + brakes for notebook writes. Data on disk: data/open/webred/ (CC BY 4.0, 53 MB + 1.9 MB TFRecord; parse without TensorFlow). WikiFact sentence-extraction links are 404; its 13 GB classification set exists (1.35 GB dev file) — not pulled. See [[ears-decisions-20260921]].
