Fixing the follow-up build — sealing the corrected model and proving the marks.
Sealed o0e state confirmed — the model carries the documented 2-line rotary fix. Building the o0e2 follow-up now.
Files created. Sealing before any run, then registering predictions.
Seal done, predictions registered, machine clear (load 25.8 < 60, disk 12 GB free). Running the registered suite once.
All green on the full re-run. Writing the sealed artifacts.
**Verdict: FAIL (seal rule), with all four marks PASS as measured.**

**Marks table (integer counts)**

| Mark | Bar | Measured | Result |
|---|---|---|---|
| Pown0e2.1 audit exactly 61,783,680 | prints exactly 61,783,680 | 61,783,680 (diff 0) | PASS |
| Pown0e2.2 kill test identical, tiny width | resume-to-8 == fresh-8, all tensors byte-equal | torch.equal True, 147,776 params | PASS |
| Pown0e2.3 0 answer leaks in 1,800 prompts | 1800/1800 poison-unchanged AND 0 gold-after-Q leaks | 1800/1800 unchanged, poison in 0, 0 leaks | PASS |
| Pown0e2.4 rotary unit test, max abs err <= 1e-5 | same-offset rotation leaves q.k unchanged | err_same_pos 2.861e-06, err_offset 0.0 | PASS |
| Smoke (supporting) | loss falls; round-trip all | 58.6267 → 13.8225 in 0.2 s; 1800/1800 | PASS |
| Throughput (report only) | none | 129,536 tok / 120.0 s = 1,079.3 tok/s | n/a |

**Every move:** (1) wrote `scripts/claude_own_o0e2_model.py` = current o0e model code unchanged, fix documented in header; (2) wrote `scripts/claude_own_o0e2_tests.py` = o0e tests pointed at o0e2 (serialize/train imported unchanged, hashes re-verified equal to o0e seal) + new T6 rotary test; (3) wrote `artifacts/claude-own-o0e2-20260923/PASSMARKS.md`, sealed model+tests+PASSMARKS, appended 4 prediction rows to the ledger; (4) ran once → T6 FAIL on a driver bug (see below); fixed the driver, full re-run from scratch → all PASS; wrote TESTLOG.md, RESULTS.md, OUTCOME ledger row. No TEST-ONLY panel opened. Machine checks: load 25.8 < 60, disk 12 GB free.

**Every miss:** exactly one — first run T6 err_offset = 12.74 (FAIL). Cause: my check compared position pairs built from *different* random vectors, so agreement was impossible. Model was never wrong (same-pos check passed at 2.86e-06 in that same run).

**Deviations:** D1 (seal-breaking, driver-only): fixed T6 to plant the same vectors at both position pairs (err_offset = 0.0). No mark/bar/prediction changed, no model code touched, never re-sealed — hence registered FAIL per the rules. No other deviations; fictional names only; no secrets; nothing in repo-root notebook/.

**What it means:** the o0e2 file carries the o0e crash fix baked in and documented; size exactly 61,783,680; kill-resume is bit-identical; questions never smuggle answers (1800/1800 clean); the rotation math provably has the relative-position property. **What it doesn't mean:** the model is not trained or smart (tiny toy smoke test only); no Premonition comparison yet (needs GPU stages); the FAIL is a seal-rule FAIL, not a wrong-code FAIL.

**PUSH:** `artifacts/claude-own-o0e2-20260923` `scripts/claude_own_o0e2_model.py` `scripts/claude_own_o0e2_tests.py` `artifacts/fable-predictions-ledger.md`
