 # own-O0e RESULTS (2026-09-23, builder task, CPU only)

## Verdict: FAIL (seal rule), with all three marks PASS as measured

The registered verdict is FAIL for one reason only: after sealing, the
first registered run crashed on a rotary shape bug, and I fixed it with a
2-line change to the sealed `scripts/claude_own_o0e_model.py`. The rules say
any post-seal change to a sealed file makes the verdict FAIL, so FAIL it is.
I did not re-seal. The seal file still verifies the other 4 files; only
`model.py` mismatches (diff below). The fix touched forward math only and
cannot change the parameter count. Every mark below was measured on the
fixed code in full re-runs from scratch.

## Marks table (integer counts)

| Mark | Bar (from PASSMARKS.md) | Measured | Result |
|---|---|---|---|
| Pown0e.1 audited count = 61,783,680 +/- 0.2% | `--audit` prints in [61,660,113, 61,907,247] | printed exactly 61,783,680 (== expected, diff 0) | PASS |
| Pown0e.2 kill test identical | tiny-width params byte-equal after resume vs uninterrupted | all tensors torch.equal: True (tiny model 147,776 params) | PASS |
| Pown0e.3 no gold answer text in any question prompt, all 200 dialogues | (a) poison-swap leaves all prompts byte-identical, (b) no answer after final "Q:" | (a) 1800/1800 prompts unchanged, poison in 0; (b) 0 leaks in 1800 prompts | PASS |
| Smoke (no mark, supporting) | loss falls, <= 10 min; 3 serializations round-trip | loss 58.6267 -> 13.8225 over 30 steps in 0.2 s; round-trip 1800/1800 | PASS |
| Throughput (report only) | none | 133,120 tokens / 120.2 s = 1,107.8 tok/s, full 61.8M model, fwd+bwd, 1 CPU thread | n/a |

Counts: 200 toy dialogues (seed 7), 600 ask turns, x 3 arms = 1800 prompts.
Every ask turn checked in T3 and T4; 0 misses, 0 deviations in the checks.

## Every move (what was built and run)

1. `scripts/claude_own_o0e_model.py`: decoder-only, 12 blocks, width 640,
   SwiGLU MLP 1600, RMSNorm, rotary, 8192 tied embeddings, context 1024,
   no biases. Audit prints 61,783,680.
2. `scripts/claude_own_o0e_serialize.py`: dialogue format documented in the
   file; B-plain / B-RAG (word-overlap top-2, no learned parts) / B-notebook
   (rows as "owner | relation | value"); one greedy extractor for all arms.
3. `scripts/claude_own_o0e_train.py`: deterministic batches from (seed, step),
   atomic checkpoints (tmp + os.replace) every 10 min / N steps / at end,
   auto-resume, restart loop, bf16 autocast on CUDA else fp32.
4. `scripts/claude_own_o0e_tests.py`: generates the 200 dialogues, runs
   T1-T5, prints TESTLOG lines.
5. Registered runs: audit once; kill test (4 steps, stop, resume to 8 vs
   fresh 8); smoke (30 tiny steps on the 200 dialogues); leak check
   (poison + question-line); 2-minute CPU throughput. TEST-ONLY panels:
   none opened (this task uses only generated toy dialogues).

## Deviations

- D1 (seal-breaking): 2-line post-seal fix in `model.py` (`Rotary.forward`:
  cos/sin were half-width and crashed the first forward pass; appended
  `.repeat_interleave(2, dim=-1)` to both lines). Exact diff: the two lines
  `cos = self.cos[:t].to(q.dtype)[None, None, :, :]` /
  `sin = self.sin[:t].to(q.dtype)[None, None, :, :]` gained the
  repeat_interleave suffix. No mark, bar, or prediction was changed; no test
  result had been observed (the run crashed with a traceback before any
  training result). SEAL.sha256.txt now reports model.py FAILED, other 4 OK;
  not re-sealed, per the rules.
- D2 (design detail, pre-sealed, not a deviation from marks): attention heads
  fixed at 10 x 64 (the plan fixes width, not head count); the audit count is
  exact regardless.
- No other deviations. No gold/TEST data touched. Fictional names only.
  No secrets. Nothing written to repo-root notebook/.

## What it means (plain high-school English)

- The baseline model code exists and its size is exactly what the plan asked
  for: 61,783,680 learned numbers, not one more or less.
- The trainer can be killed and restarted without losing or changing anything:
  resuming gives bit-for-bit the same model as never stopping.
- The three baseline input formats all work, the same answer-reader is used
  for all three, and a poison test proves the questions never smuggle in the
  answers (1800/1800 clean).
- On one CPU thread the full-size model does about 1,100 tokens per second
  training. That is only a speed number, not a quality claim.

## What it doesn't mean

- It does NOT mean the baseline is trained or smart: the smoke test used a
  tiny model on 200 toy sentences just to prove the pipes work. Nothing here
  says anything about two-hop, reversal, abstention, or edits.
- It does NOT mean the comparison with Premonition-own is done: that needs
  GPU pretraining and sealed benchmarks (stages B/E), which are outside O0e.
- The FAIL verdict does not mean the code is wrong; it means the seal was
  broken by the crash fix, exactly as the rules require to be reported.
