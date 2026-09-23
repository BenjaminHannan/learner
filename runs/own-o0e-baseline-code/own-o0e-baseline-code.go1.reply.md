Building the plain-transformer baseline — auditing specs and scaffolding the model.
Load is high (~66), disk fine (19 GB free). My files don't exist yet. Checking ledger format and toolchain before writing.
Toolchain works. Writing the three build files now.
Now the test driver (also under the allowed `claude_own_o0e_` name):
Quick pilot check (imports + demo) before sealing:
Serializer works. Creating the artifacts dir and sealing PASSMARKS before tests:
Sealed 5/5. Load 56, under the 60 bar — running the registered suite:
The registered run crashed — a rotary broadcast bug in my sealed `model.py` (no results observed, crash only). Reading what printed before the crash:
Fix verified. Re-running the full registered suite on the fixed code (seal left as-is, never re-sealed):
Verdict: FAIL (seal rule only) — all three marks PASS as measured.

The first registered run crashed on a rotary shape bug before any result was observed. I fixed it with a 2-line change to the sealed `model.py`, reported the diff, and never re-sealed. The rules say any post-seal change to a sealed file makes the verdict FAIL, so FAIL it is. Seal now: `model.py` FAILED, other 4 files OK.

Marks table (integer counts):

| Mark | Bar | Measured | Result |
|---|---|---|---|
| Pown0e.1 audited count = 61,783,680 ± 0.2% | print in [61,660,113, 61,907,247] | printed exactly 61,783,680, diff 0 | PASS |
| Pown0e.2 kill test identical | tiny-width params byte-equal after resume vs uninterrupted | all tensors `torch.equal`: True (147,776 params; 4 steps, stop, resume to 8 vs fresh 8) | PASS |
| Pown0e.3 no gold answer text in any question prompt, all 200 dialogues | poison-swap leaves all prompts identical; no answer after final "Q:" | 1800/1800 prompts unchanged (poison in 0); 0 leaks in 1800 prompts (200 dialogues, 600 asks × 3 arms) | PASS |
| Smoke (supporting) | loss falls, ≤ 10 min; 3 serializations round-trip | loss 58.6267 → 13.8225 over 30 steps in 0.2 s; round-trip 1800/1800 | PASS |
| Throughput (report only) | none | 133,120 tokens / 120.2 s = 1,107.8 tok/s, full 61.8M model fwd+bwd, 1 CPU thread | n/a |

Every move: built `scripts/claude_own_o0e_model.py` (12 blocks, width 640, SwiGLU 1600, RMSNorm, rotary, 8192 tied embeddings, ctx 1024, 10×64 heads — head count was my pre-sealed detail, count is exact regardless), `scripts/claude_own_o0e_serialize.py` (documented dialogue format; B-plain / B-RAG word-overlap top-2 / B-notebook rows; one greedy extractor), `scripts/claude_own_o0e_train.py` (deterministic (seed,step) batches, atomic ckpts every 10 min, auto-resume, restart loop, bf16 on CUDA else fp32), `scripts/claude_own_o0e_tests.py` (seed-7 toy generator + T1–T5). Ran audit, kill, smoke, leak, 2-min throughput. No TEST-ONLY panel opened; fictional names only; disk was fine (19 GB free).

Every miss: 0 misses in every check (0/1800 leaks, 0/1800 round-trip failures). One crash pre-result (the rotary bug), fixed.

Deviations: D1 — the seal-breaking 2-line fix (`cos`/`sin` gained `.repeat_interleave(2, dim=-1)`; forward math only, zero param-count impact; no mark/bar/prediction changed). D2 — heads 10×64, pre-sealed. Nothing else.

What it means (plain high-school English): the baseline code exists at exactly the planned size; the trainer survives kills bit-for-bit; all three input formats work with one shared answer-reader, and a poison test proves questions never smuggle answers; the full model trains at ~1,100 tok/s on one CPU thread. What it doesn't mean: the baseline is not trained or smart — the smoke used a tiny model on 200 toy sentences just to prove the pipes; nothing here says anything about two-hop, reversal, abstention, or edits, and the stage-B comparison still needs GPU work. The FAIL is about the broken seal, not wrong code.

PUSH paths ready: `artifacts/claude-own-o0e-20260923` (PASSMARKS.md, SEAL.sha256.txt, TESTLOG.md, RESULTS.md, ckpt dirs), `scripts/claude_own_o0e_model.py`, `scripts/claude_own_o0e_serialize.py`, `scripts/claude_own_o0e_train.py`, `artifacts/fable-predictions-ledger.md` (4 lines appended, existing lines untouched).
