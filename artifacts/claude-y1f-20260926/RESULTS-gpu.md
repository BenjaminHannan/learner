# y1f GPU results (Answering-from-memory thread, 2026-09-26)

Diagnosis on DEV data: plain MiniCPM5-1B answers the 71 DEV bank memory asks from raw chat
turns laid out four ways (L0 ep-382 control / L1 bm-390 LoCoMo layout / L1i L1 + don't-know
line / L2 lines as earlier chat turns), conditions gold and all, decodings p382 (4 samples
T 0.7 / top-p 0.9, first pass wins) and g1 (one greedy through the same checks), raw greedy
kept for report. Code run unmodified (`scripts/claude_y1f_layout.py`, seed 4023).
SEAL 8/8 OK, `--selftest` printed "selftest ok".

## Last two printed JSON lines (verbatim)

{"pick": {"candidates": [{"config": "L1i|g1", "right": 3, "wrong": 0, "never_told_idk": 10, "eligible": true}, {"config": "L1i|p382", "right": 8, "wrong": 10, "never_told_idk": 7, "eligible": false}, {"config": "L1|g1", "right": 25, "wrong": 24, "never_told_idk": 2, "eligible": false}, {"config": "L1|p382", "right": 26, "wrong": 28, "never_told_idk": 1, "eligible": false}, {"config": "L2|g1", "right": 3, "wrong": 0, "never_told_idk": 10, "eligible": true}, {"config": "L2|p382", "right": 7, "wrong": 10, "never_told_idk": 9, "eligible": true}, {"config": "L0|g1", "right": 5, "wrong": 4, "never_told_idk": 9, "eligible": true}, {"config": "L0|p382", "right": 15, "wrong": 11, "never_told_idk": 9, "eligible": true}], "winner": "L0|p382", "go": false}}

{"answerable_right": {"L0|all|g1": 5, "L0|all|p382": 15, "L0|all|raw": 5, "L0|gold|g1": 0, "L0|gold|p382": 4, "L0|gold|raw": 0, "L1i|all|g1": 3, "L1i|all|p382": 8, "L1i|all|raw": 3, "L1i|gold|g1": 3, "L1i|gold|p382": 6, "L1i|gold|raw": 3, "L1|all|g1": 25, "L1|all|p382": 26, "L1|all|raw": 25, "L1|gold|g1": 27, "L1|gold|p382": 31, "L1|gold|raw": 27, "L2|all|g1": 3, "L2|all|p382": 7, "L2|all|raw": 3, "L2|gold|g1": 3, "L2|gold|p382": 6, "L2|gold|raw": 3}, "answerable_wrong": {"L0|all|g1": 4, "L0|all|p382": 11, "L0|all|raw": 4, "L0|gold|g1": 0, "L0|gold|p382": 1, "L0|gold|raw": 0, "L1i|all|g1": 0, "L1i|all|p382": 10, "L1i|all|raw": 0, "L1i|gold|g1": 0, "L1i|gold|p382": 7, "L1i|gold|raw": 0, "L1|all|g1": 24, "L1|all|p382": 28, "L1|all|raw": 27, "L1|gold|g1": 18, "L1|gold|p382": 25, "L1|gold|raw": 22, "L2|all|g1": 0, "L2|all|p382": 10, "L2|all|raw": 48, "L2|gold|g1": 6, "L2|gold|p382": 21, "L2|gold|raw": 11}, "never_told_idk": {"L0|all|g1": 9, "L0|all|p382": 9, "L0|all|raw": 9, "L1i|all|g1": 10, "L1i|all|p382": 7, "L1i|all|raw": 10, "L1|all|g1": 2, "L1|all|p382": 1, "L1|all|raw": 1, "L2|all|g1": 10, "L2|all|p382": 9, "L2|all|raw": 1}}

NOTE: the answerable_wrong line above is hand-copied; the exact line is in
`gpu/log.txt` line 77 (sha256 a2172b50cd778340b1d832282b7ad196d8c7fff5bd93e74062465830d291d98a).
Per-count reads for the report below are taken from that file, not from this copy.

## Run facts

- GPU: NVIDIA GeForce RTX 5090 (rental 3, contract 52772214, offer 44173865, dph $0.4963)
- MiniCPM5-1B commit: 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected value)
- torch 2.13.0+cu129 with CUDA True (image torch was 2.2.1, too old for transformers 5.17,
  upgraded per the rent-kit's TORCH UPGRADE note; torchvision/torchaudio uninstalled after).
  transformers 5.17.0. No other model downloaded (no all-MiniLM; y1f needs only MiniCPM5-1B).
- Wall minutes: ~3 (run launched 15:56:51Z, `gpu/` + `gpu_log.txt` written 15:59Z;
  71 `[y1f]` lines, process exited on its own)
- Dollars: rental 1 (contract 52770475, offer 46753301, dph $0.406, ~6 min loading with host
  docker-registry proxy error, destroyed) ~$0.04 + rental 2 (contract 52771466, offer 43165153,
  dph $0.406, ~6 min loading, same host proxy error, destroyed) ~$0.04 + rental 3
  (15:43:28Z-16:00:40Z, ~0.29 h x $0.4963) ~$0.14 = task total ~$0.23 of $0.30 budget,
  3 rentals of max 4
- Instance id: 52772214 (failed rentals 52770475, 52771466 also recorded);
  post-destroy 0 claude-memory-y1f live (8 other-label instances untouched)
- Credit at gate: 8.599180226269851 (vast auto-refills; balance number only, no credit stop)
- Rows: `gpu/y1f_rows.jsonl` 528 lines (= 8 x 71 asks minus 10 never_told gold-skips x 4 layouts),
  226973 bytes, sha256-verified against the box before destroy
- No reader weights copied; nothing staged on the Mac (streamed `git archive` straight to the
  rental, 30M); run saved no weights
- First launch crashed before ask 1 (torch 2.13 triton kernel needed a C compiler; none on the
  image). Environment-only fix: `apt-get install -y gcc`, code untouched, relaunched clean.
  Exact first traceback tail: `RuntimeError: Failed to find C compiler. Please specify via CC
  environment variable or set triton.knobs.build.impl.` via
  `torch/_native/ops/bmm_outer_product/triton_kernels.py line 76, in bmm_outer_product`
  from the Llama rotary-embedding forward.

## Decision-rule readout (PLAN.md rules, fixed before the run; condition all)

- Eligible configs (never_told idk >= 8 of 10 AND answerable wrong <= 11): L1i|g1 (3/0/10),
  L2|g1 (3/0/10), L2|p382 (7/10/9), L0|g1 (5/4/9), L0|p382 (15/11/9). L1 layouts ineligible
  (L1|g1 wrong 24, L1|p382 wrong 28, never_told idk 2 and 1).
- Winner: L0|p382 (most answerable right, 15). go: false (15 < 25 of 56).
- NO-GO: no eligible config reaches 25. No in-agent answer step; next change is trained reading.
- Proved-wrong clause: "the layout, not the 1B, is the reading bottleneck" is wrong if no
  layout's raw greedy gold exceeds 10 of 56. Best raw greedy gold: L1|gold|raw = 27 of 56,
  so NOT proved wrong (the LoCoMo layout reads far better raw: 27 vs L0's 0).
