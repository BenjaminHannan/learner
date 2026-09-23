---
name: teachable-assistant-goal
description: "2026-09-20 Ben's end goal — an assistant that starts knowing nothing, reasons well, and learns facts as he teaches it in English over time"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-20T22:35:45.571Z
---

Ben's stated end goal (2026-09-20): he does not care that the model knows nothing at first. He wants to teach it as it grows, as an assistant. Basic requirements, in his order: (1) it reasons well; (2) it can learn facts as it grows (taught by him, in English, persistently). An English encoder → reasoner+memory → decoder was the original plan (reviews/2026-09-17-contract, Contract A: single English sentences teach a fictional world; paraphrased queries; corrections propagate; "unknown" answers) and is parked, not cancelled.

**Why:** this is what "original thinking / genuinely learning model" means to him in practice ([[human-learning-redesign]]); world knowledge is explicitly not a requirement, so pretraining on the internet is not needed and a tiny-vocabulary English interface is acceptable.
**How to apply:** frame milestones as steps toward a teachable assistant — dependable multi-step reasoning first ([[canonical-operator-roadmap]], [[exp19-replay-result]]), then one-shot fact learning that persists and can be corrected, then the English sentence interface. Keep claims ≤ evidence ([[focused-priorities-and-claims]]); don't bolt on a pretrained chatbot and call it his model.
