# own-O0e2 PASSMARKS (sealed before tests, 2026-09-23)

Task: builder for own-O0e2, the ONE follow-up to own-O0e (baseline code),
which is a registered FAIL only because its sealed model file was changed
after sealing (a 2-line rotary fix, cos/sin .repeat_interleave(2, dim=-1)).
CPU only, plain torch. 200 toy dialogues generated in-test (seed 7,
fictional names only). No TEST-ONLY panel is read anywhere in this task.

The ONE change vs o0e: new file scripts/claude_own_o0e2_model.py is the
current scripts/claude_own_o0e_model.py (which already carries the fix)
copied unchanged, with the fix documented in its header; the diff against
the sealed o0e hash is shown in RESULTS.md. The o0e serialize and train
scripts are imported unchanged (not copied). Tests are the o0e tests
pointed at o0e2, plus one new rotary unit test.

## Marks

- Pown0e2.1 audited count exactly 61,783,680.
  Bar: `scripts/claude_own_o0e2_model.py --audit` prints exactly
  61,783,680. PASS iff printed count == 61,783,680.
  Predicted: exact 61,783,680 (embeddings 5,242,880 + 12 x 4,711,680 +
  final norm 640, tied head counted once; the fix touches forward math
  only and cannot change the count).
- Pown0e2.2 kill test identical at tiny width.
  Bar: at tiny width (vocab 1024, width 64, 2 layers, mlp 128, 4 heads,
  ctx 64), train 4 steps, stop, resume to 8 steps == uninterrupted 8 steps,
  all parameters byte-equal (torch.equal on every tensor). PASS iff True.
  Predicted: PASS.
- Pown0e2.3 no gold answer text in any question prompt, all 200 dialogues.
  Operational meaning (same as o0e, fixed here before the run): for every
  ask turn in all 200 dialogues x all 3 arms (plain/rag/notebook),
  (a) replacing every gold answer with ZZZPOISON9 leaves every prompt
      byte-identical and no prompt contains ZZZPOISON9;
  (b) the gold answer string does not occur after the final "Q:" marker
      (prompts end with "Q: <question>\nA:").
  Note (not a leak): teach sentences and notebook/retrieved context state
  facts by design; that is the arm's defined memory, not answer leakage.
  Bar: (a) holds on all 1800 prompts AND (b) holds on all 1800 prompts
  (0 leaks). Predicted: PASS (1800/1800 unchanged, 0 leaks).
- Pown0e2.4 rotary unit test (relative-position property).
  Bar: rotating q and k by the same position offset leaves q.k unchanged;
  max abs error over all positions/heads/batch <= 1e-5. Two checks:
  (a) per-position (R_t q).(R_t k) == q.k for t in 0..7;
  (b) cross-position (R_a q).(R_b k) depends only on b-a
  (pair (0,d) vs (m,m+d) equal for d=3, m=5).
  PASS iff both max abs errors <= 1e-5. Predicted: PASS
  (rotation is orthogonal; float32 rounding ~1e-6 or less).

## Registered runs (order)

1. audit (T1). 2. kill test (T2). 3. smoke <= 10 min on 200 toy dialogues:
   loss falls over 30 tiny steps; all 3 serializations round-trip
   (extractor recovers each gold when appended). 4. leak check (T4).
   5. throughput: 2-minute CPU run on the full-size model (report only).
   6. rotary unit test (T6, Pown0e2.4).
All bars above are PASS/FAIL as stated; throughput has no bar.
The suite runs ONCE after the seal; any post-seal change to a sealed file
makes the registered verdict FAIL (no re-seal).
