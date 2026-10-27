# 0.2c manifest: exactly what X is (frozen 2026-09-26 ~05:20 UTC, before any registered run)

Month-end thread. Written from verified verdicts only (PASSMARKS-02c.md composition rule and addenda). Sealed with
the code in SEAL-code.sha256.txt. Builder: scripts/claude_e2e02c.py:build_02c.

## Switches (scripts/claude_e2e02c.py)
| Switch | Value | Why |
|---|---|---|
| SLEEP02C | on | dl-2 registered PASS, blind recount agrees (artifacts/claude-dl2-20260926/VERIFY.md) |
| READER02C | "r319" (save bar 0.995) | lis-319 registered PASS (artifacts/claude-lis319-20260925/VERIFY.md); whole-claim re-score keeps its wrong-save result (65 right, 1 wrong of 240); lis-319c-full (0.98) registered FAIL on F2 (artifacts/claude-lis319c-20260926/VERIFY-full.md) |
| MEM02C | 0 (off) | 382b has no verdict: rent-382b stopped INCOMPLETE (the 2 GB reader could not be uploaded to the rental at 0.37 MB/s; only arm T ran) |
| ROUTE02C | off | 383 has no verdict (same run) |
| TRIM02C | off | bm-397 registered FAIL (LoCoMo F1 +0.28, mark +5) |
| FIX02C | on | only F1 (delivered history) is active; F2 needs the route, F3 and F4 need memory |
| STORE02C | v3 | not used while MEM02C = 0 |
Creative breadth (brd-5): registered INCONCLUSIVE, no code to join. Reading's note checker (006i): no verdict and no
joining code; out.

## Arms
- X = claude_e2e02c:build_02c, --model = lis-319 merged reader (model.safetensors sha256 e688e1b2...6a76),
  --gen-model = openbmb/MiniCPM5-1B snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc, SLEEP02C_ADAPTER = the
  adapter the registered sleep step saves (its sidecar adapter02c.json must match; the run reports its sha256).
  Layers in order: 330a_334 (lis-319 history reader, 6 pairs of history, save bar 0.995) -> rec360 -> cre333d ->
  think299b -> chat338b -> vary330c -> gram360 -> delivered02c -> turnlog323. The sleep adapter (LoRA r 16, alpha 32,
  on q/k/v/o of every layer) sits inside the one shared 1B that every 1B layer calls.
- G = claude_e2e360:build_360 (0.1 + gram-360), --model = lis-301 merged reader (sha256 b4fd93a2...b890), same base.
- T = twin b, plain MiniCPM5-1B, thinking off, whole chat.

## Resources (counted on the machine by scripts/claude_params02c.py; reported in RESULTS)
X and G each keep two full 1B-class models resident (generator + fine-tuned reader), plus the self122 router's MiniLM
and a small hand-built reasoner, so the joined assistant is about 2B resident, not "1B". X adds the LoRA adapter.
T is one 1B.

## Status labels (never merged in the report)
| Part | Label now |
|---|---|
| copy-practice sleep | passed its own test (plain 1B, dl-2); joined test = this run's L rows |
| lis-319 history reader at 0.995 | passed its own test (lis-319) |
| gram-360 | passed its own test; already in G |
| F1 delivered history; sleep sidecar and refusal checks | fixed in code (CPU tests only) |
| F2-F4, store v3 | fixed in code, NOT active in X (need route or memory) |
| 382b memory, 383 route | no verdict; out; open |
| 0.98 save bar, bm-397 trim | registered FAIL; out |
| breadth recipe | INCONCLUSIVE; out |
"Passed in the joined assistant" applies to nothing until 0.2c passes every mark.

## Expected before running (said now, so it can't be said after)
With memory and route off, Q1 (think turns X - G >= +3) and Y1 (bank D M4 X - G >= +10 points) are unlikely to
pass, so 0.2c as registered is likely to FAIL overall. The rows that still carry information: sleep L1-L6 (does
sleep learn inside the real agent), no harm H1-H6, conversation C1-C2, creative K1-K2, safety S1, milestone ME1.
