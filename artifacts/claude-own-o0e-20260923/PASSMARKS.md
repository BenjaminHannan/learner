 # own-O0e PASSMARKS (sealed before tests, 2026-09-23)

Task: builder for own-O0e, plain-transformer baseline code (plan sect 7, 7.1).
CPU only, plain torch. 200 toy dialogues generated in-test (seed 7,
fictional names only). No TEST-ONLY panel is read anywhere in this task.

## Marks

- Pown0e.1 audited count = 61,783,680 +/- 0.2%.
  Bar: `scripts/claude_own_o0e_model.py --audit` prints exactly 61,783,680.
  +/- 0.2% = [61,660,113, 61,907,247]. PASS iff printed count in range.
  Predicted: exact 61,783,680 (embeddings 5,242,880 + 12 x 4,711,680 +
  final norm 640, tied head counted once).
- Pown0e.2 kill test identical.
  Bar: at tiny width (vocab 1024, width 64, 2 layers, mlp 128, 4 heads,
  ctx 64), train 4 steps, stop, resume to 8 steps == uninterrupted 8 steps,
  all parameters byte-equal (torch.equal on every tensor). PASS iff True.
  Predicted: PASS.
- Pown0e.3 serializations include no gold answer text in any question prompt
  (checked on all 200 toy dialogues).
  Operational meaning (fixed here before the run): for every ask turn in all
  200 dialogues x all 3 arms (plain/rag/notebook),
  (a) replacing every gold answer with ZZZPOISON9 leaves every prompt
      byte-identical and no prompt contains ZZZPOISON9 (builders never read
      answers; evidence/notebook context comes only from teach/correct text);
  (b) the gold answer string does not occur after the final "Q:" marker
      (prompts end with "Q: <question>\nA:").
  Note (not a leak): teach sentences and notebook/retrieved context state
  facts by design; that is the arm's defined memory, not answer leakage.
  Bar: (a) holds on all prompts AND (b) holds on all prompts. Predicted: PASS.

## Registered runs (order)

1. audit (T1). 2. kill test (T2). 3. smoke <= 10 min on 200 toy dialogues:
   loss falls over 30 tiny steps; all 3 serializations round-trip
   (extractor recovers each gold when appended). 4. leak check (T4).
   5. throughput: 2-minute CPU run on the full-size model (report only).
All bars above are PASS/FAIL as stated; throughput has no bar.
