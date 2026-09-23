# PASSMARKS — own-O0d2 diagnosis-driven follow-up (recorded BEFORE the run)

Task: builder for own-O0d2, the ONE diagnosis-driven follow-up to the
registered FAIL of own-O0d (ear code). CPU only, plain torch.
New files: scripts/claude_own_o0d2_model.py (o0d model + only the two-part
fix), scripts/claude_own_o0d2_train.py (shim: o0d trainer unchanged, o0d2
model aliased in), scripts/claude_own_o0d2_test.py (o0d tests pointed at the
o0d2 model), this file. Predictions appended to
artifacts/fable-predictions-ledger.md as Pown0d2.1–5 before the run. The run
is scripts/claude_own_o0d2_test.py, executed once.

- Pown0d2.1 — all 8 unit tests pass. Bar: every unit test passes (8/8).
  Predicted: PASS (the flipped word_start_end condition is corrected, so
  mask-blocks-cuts and decode-whole-word-only flip to pass; decode with word
  ids restores single spaces, so bpe-roundtrip flips to pass; the other 5
  already passed).
- Pown0d2.2 — audited ear count still exactly 32,850,051 (architecture
  untouched; only two method bodies changed, 0 parameters added/removed).
  Bar: diff <= 0.005 with the exact number reported per part. Predicted: PASS
  at exactly 32,850,051.
- Pown0d2.3 — kill test identical (trainer code path unchanged; tokenizer
  methods are not in checkpoints). Bar: sha256 equal at step 60. Predicted:
  PASS.
- Pown0d2.4 — fuzz 10,000 random-logit draws: 0 non-whole-word spans decoded
  (span + owner checks). Bar: 0. Predicted: PASS (mask now admits only
  whole-word spans; decode trusts the mask).
- Pown0d2.5 — the o0d smoke (toy frames, <= 10 min): loss still falls (mean
  of last 10% steps < mean of first 10% steps). Predicted: PASS (training
  loss path is untouched by the fix).

Smoke/MLM pilot are reported, not marks. Toy data only, fictional names.
No TEST-ONLY panel is touched.
