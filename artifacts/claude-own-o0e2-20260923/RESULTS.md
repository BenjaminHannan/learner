# own-O0e2 RESULTS (2026-09-23, builder task, CPU only)

## Verdict: FAIL (seal rule), with all four marks PASS as measured

The registered verdict is FAIL for one reason only: after sealing, the
first registered run showed T6 (the new rotary unit test) FAIL, and I
fixed it with a driver-only change to the sealed
`scripts/claude_own_o0e2_tests.py` (my check compared different random
vectors, so it could never agree; the model was never wrong). The rules
say any post-seal change to a sealed file makes the verdict FAIL, so FAIL
it is. I did not re-seal. The seal file still verifies model.py and
PASSMARKS.md; only the tests file mismatches (diff below). Every mark
below was measured in a full re-run from scratch on the fixed driver.

## Marks table (integer counts)

| Mark | Bar (from PASSMARKS.md) | Measured | Result |
|---|---|---|---|
| Pown0e2.1 audited count exactly 61,783,680 | `--audit` prints exactly 61,783,680 | printed exactly 61,783,680 (== expected, diff 0) | PASS |
| Pown0e2.2 kill test identical | tiny-width params byte-equal after resume vs uninterrupted | all tensors torch.equal: True (tiny model 147,776 params) | PASS |
| Pown0e2.3 0 answer leaks in 1,800 prompts (200 toy dialogues x 3 arms) | poison-swap leaves all prompts byte-identical AND 0 gold-after-Q leaks | 1800/1800 prompts unchanged, poison in 0; 0 leaks in 1800 prompts | PASS |
| Pown0e2.4 rotary unit test: same-offset rotation leaves q.k unchanged, max abs err <= 1e-5 | per-position AND cross-position (0,d) vs (m,m+d) errors both <= 1e-5 | err_same_pos = 2.861e-06, err_offset = 0.000e+00 | PASS |
| Smoke (no mark, supporting) | loss falls, <= 10 min; 3 serializations round-trip | loss 58.6267 -> 13.8225 over 30 steps in 0.2 s; round-trip 1800/1800 | PASS |
| Throughput (report only) | none | 129,536 tokens / 120.0 s = 1,079.3 tok/s, full 61.8M model, fwd+bwd, 1 CPU thread | n/a |

Counts: 200 toy dialogues (seed 7), 600 ask turns, x 3 arms = 1800 prompts.
Every ask turn checked in T3 and T4; 0 misses, 0 deviations in the checks.

## The ONE change (diff against the sealed o0e hash)

`scripts/claude_own_o0e2_model.py` is the current
`scripts/claude_own_o0e_model.py` (which already carries the o0e fix)
copied with identical code; only the header comment/docstring is new.
The diff against the sealed o0e model hash
(0dd2ebf2e3ac54eeb86370f5d17307d555c463130862c0a66820a0244a8b5bda,
from artifacts/claude-own-o0e-20260923/SEAL.sha256.txt) is exactly the
2-line rotary fix documented in o0e RESULTS.md D1, plus header comments:

  sealed o0e:  cos = self.cos[:t].to(q.dtype)[None, None, :, :]
               sin = self.sin[:t].to(q.dtype)[None, None, :, :]
  o0e2 (same as current o0e file):
               cos = self.cos[:t].to(q.dtype)[None, None, :, :].repeat_interleave(2, dim=-1)
               sin = self.sin[:t].to(q.dtype)[None, None, :, :].repeat_interleave(2, dim=-1)

The fix touches forward math only and adds no learned numbers, so the
audit is byte-for-byte the o0e number. The o0e serialize and train scripts
are imported unchanged (hashes re-verified at seal time: 48db8110... and
2c8f9c38..., equal to the o0e SEAL values).

## Every move (what was built and run)

1. `scripts/claude_own_o0e2_model.py`: copy of the current o0e model
   (12 blocks, width 640, SwiGLU 1600, RMSNorm, rotary, 8192 tied
   embeddings, ctx 1024, no biases); fix documented in the header.
2. `scripts/claude_own_o0e2_tests.py`: the o0e tests pointed at o0e2
   (model import switched; serialize/train imports unchanged) plus the new
   T6 rotary unit test; pushed per the brief.
3. `artifacts/claude-own-o0e2-20260923/PASSMARKS.md`: Pown0e2.1-2.4 sealed
   before any run.
4. Registered runs: first full run (T6 FAIL on the driver bug, see D1);
   then one full re-run from scratch after the driver-only fix (all PASS).
   TEST-ONLY panels: none opened (this task uses only generated toy
   dialogues).

## Deviations

- D1 (seal-breaking, driver-only): the sealed T6 cross-position check
  compared pair (0, d) against pair (m, m+d) built from DIFFERENT random
  vectors at each position, so the two dots could never agree
  (measured err_offset = 12.74, i.e. pure noise difference). The fix plants
  one vector v at positions 0 and m of the q sequence and one vector w at
  d and m+d of the k sequence, then compares the two cross dots
  (measured err_offset = 0.0). No mark, bar, or prediction was changed; no
  model code was touched. SEAL.sha256.txt now reports tests FAILED,
  model + PASSMARKS OK; not re-sealed, per the rules.
- No other deviations. No gold/TEST data touched. Fictional names only.
  No secrets. Nothing written to repo-root notebook/.

## What it means (plain high-school English)

- The follow-up model file exists with the o0e crash fix baked in and
  documented, and its size is exactly what the plan asked for: 61,783,680
  learned numbers, not one more or less.
- The trainer can be killed and restarted without losing or changing
  anything: resuming gives bit-for-bit the same model as never stopping.
- The three baseline input formats all work with the same answer-reader,
  and a poison test proves the questions never smuggle in the answers
  (1800/1800 clean, 0 leaks).
- The position-rotation math is correct: turning both sides by the same
  amount leaves their agreement unchanged (error 0.0000003 at most, bar
  was 0.00001), so the "relative position" property the plan relies on
  really holds in this code.
- On one CPU thread the full-size model does about 1,080 tokens per second
  training. That is only a speed number, not a quality claim.

## What it doesn't mean

- It does NOT mean the baseline is trained or smart: the smoke test used a
  tiny model on 200 toy sentences just to prove the pipes work. Nothing here
  says anything about two-hop, reversal, abstention, or edits.
- It does NOT mean the comparison with Premonition-own is done: that needs
  GPU pretraining and sealed benchmarks (stages B/E), which are outside O0e2.
- The FAIL verdict does not mean the code is wrong; it means the seal was
  broken by the test-driver fix, exactly as the rules require to be reported.
