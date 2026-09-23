# PASSMARKS — own-O0d ear model code + trainer (sealed BEFORE the tests)

Task: builder for own-O0d (plan §2.1, §7.1). CPU only, plain torch.
Sealed files: scripts/claude_own_o0d_model.py, scripts/claude_own_o0d_train.py,
scripts/claude_own_o0d_test.py, this file. Seal: artifacts/claude-own-o0d-20260923/SEAL.sha256.txt.
Predictions appended to artifacts/fable-predictions-ledger.md as Pown0d.1–4.

- Pown0d.1 — all unit tests pass (BPE round-trip + word ids; whole-word mask blocks
  word-cutting spans; hungarian matcher optimal on a brute-force check; forward shapes;
  toy relation-table read: 153 relations + OTHER = 154 classes). Bar: every unit test passes.
- Pown0d.2 — audited ear count within 0.5% of 32,850,051 (exact number reported per part
  next to the plan §7.1 table). Predicted: exact match 32,850,051 (0 difference).
- Pown0d.3 — kill test: kill -9 at step N=30, resume from newest checkpoint, parameters at
  step 60 byte-identical to an uninterrupted 60-step run. Bar: identical (sha256 equal).
- Pown0d.4 — 0 non-whole-word spans decodable over a 10,000-sample fuzz of random logits
  across random word layouts. Bar: 0.

Smoke (not a mark, reported): ≤10-minute CPU frame run on an in-task toy set shows falling
loss (mean of last 10% steps < mean of first 10% steps); MLM pilot runs a few steps.
Toy relation ids in the smoke are indices into an in-task list, not the 153-class table.
