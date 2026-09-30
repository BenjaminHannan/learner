# Joint human grounding is a separate stage

Plan fixed before any optimization or language score. Seed 0 and seed 1, 500 updates, batch 2, 4 differentiable loop rounds; frozen pretrained LFM lexical/output weights; train only thin input projection, spatial loop and thin output prefix. Targets are literal HUMAN evidence sentences from SQuAD TRAIN. Learned halt uses expected human next-token loss plus .001 ponder cost, with no generated halt labels. This phase may update core; it is NOT the frozen decoder proof.

Completion marks: provenance/split/boundary tests pass; LM remains bit-identical; all visited rows and token/model-call/time/memory budgets recorded; no model-authored adaptation text; both parent checkpoints seal and freeze. Completion does not show English comprehension or general assistant quality. Any grammar/content claim needs autonomous generation on fresh training-partition dev, every required causal control, two parent seeds × two decoder seeds, and human scoring. Full proof remains noise-uncalibrated. A missing comparable plain human parent yields plain-control WAITING/NOT SHOWN, never a loop-win claim.

Reasoner training is allowed ONLY via the watcher in this separately labelled phase. Parent is frozen before output decoder proof. Notebook/sleep are external dependencies, not asserted from this job. No deadline guarantee or fabricated fluent replies.
