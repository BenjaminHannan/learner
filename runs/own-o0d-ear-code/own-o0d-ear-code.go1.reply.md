Building your ear model and trainer — first reading the plan and constraints.
High load (69) but disk is fine (19GB). Checking ledger format and scipy, then building.
Cleaning up two rough spots in the model file:
Now the trainer:
Pilot syntax + forward + audit before sealing:
That error is in my pilot one-liner (`torch.ones` arg), not the file. Retrying:
Audit matches the plan exactly on every line. Writing PASSMARKS (sealed before tests), then the test script:
Fixing two glitches I left in the test script:
Quick pilot of the trainer (short runs) before sealing:
Gather-indexing bug in the matcher — fixing:
Trainer works. Quick MLM pilot, then seal and run the registered tests:
Both modes run. Sealing now, then ledger predictions:
Registered run finished in 12s with failures. Per protocol I won't touch sealed files — but I'll diagnose read-only:
Root cause found (read-only diagnosis — sealed files untouched). Verifying seal integrity, then writing RESULTS:
**Verdict: FAIL** (one diagnosed bug; fix reported, not applied; seal intact 4/4, no re-run).

**Marks table (integer counts)**

| Mark | Bar | Result |
|---|---|---|
| Pown0d.1 all unit tests pass | all pass | 5/8 pass → FAIL |
| Pown0d.2 audit within 0.5% of 32,850,051 | diff ≤ 0.005 | total 32,850,051, diff 0.000000, all 7 parts exact → PASS |
| Pown0d.3 kill test identical | sha256 equal | step-60 hashes equal (054dbec63839) → PASS |
| Pown0d.4 fuzz 10,000 draws | 0 bad | 11,418 bad → FAIL |

**Every move, every miss:** units — bpe-trains PASS (vocab 474), word-ids PASS, hungarian-optimal PASS (gap 0.00e+00, 20 seeds), forward-shapes PASS, relation-table-153 PASS (n=153); bpe-roundtrip FAIL, mask-blocks-cuts FAIL, decode-whole-word-only FAIL (bad=1703/2000). Audit PASS with every part matching plan §7.1 exactly (embeddings 4,194,304; encoder 25,174,528; slot_layer 1,052,672; pointers 1,572,864; question_pointers 524,288; classifiers 329,859; special_tokens 1,536). Kill test PASS (kill landed on ckpt 30, resumed, byte-identical at 60). Fuzz FAIL. Smoke (not a mark): frame loss 1.3347 → 0.3635 over 120 steps; MLM pilot ran.

**Deviations:** none from task order. No TEST-ONLY panels touched; toy data only, fictional names.

**Diagnosis (one note):** `ByteBPE.word_start_end` clears `end[i-1]` at word boundaries (where the token really is a word end) and never mid-word — exactly backwards. So `valid_span_mask` admits word-cutting spans (single-word "sister-in-law", 7 tokens: mask sum 7 instead of 1), and the decoder, which correctly trusts the mask, returns half-words. Separately, `decode` drops inter-word spaces. The independent `is_whole_word_span` checker is correct — that's what caught it. Fix diff is in RESULTS.md, NOT applied (sealed-model fix, needs director re-rule).

**What it means:** the size math is exactly right, kill-resume training works perfectly, the matcher is optimal — but the "only whole words" promise is broken by one flipped condition, so the ear can currently point at half-words.

**What it doesn't mean:** the pointer design isn't wrong, the plan counts aren't wrong, nothing leaked. It's one small bug with big effects, fixable in a follow-up.

PUSH paths: `artifacts/claude-own-o0d-20260923` `scripts/claude_own_o0d_model.py` `scripts/claude_own_o0d_train.py` `scripts/claude_own_o0d_test.py` `artifacts/fable-predictions-ledger.md`
