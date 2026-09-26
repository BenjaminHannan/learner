# RESULTS-rent k1c (label claude-creativechat-k1c, 2026-09-26)

Verdict: RUN-COMPLETE. All ten registered arms ran exactly once per panel, DEV gate and V1
checks passed, both panels scored + deduped, 38 files copied back sha-verified. Judging
(judges 1-3) is not part of this rental; no k1c PASS/FAIL is decided here. No reply quoted.

## Money / credit / GPU
- Credit (`vastai show user --raw` balance number only): 0 (vast auto-refills; not a gate).
- GPU: NVIDIA GeForce RTX 5090, 32607 MiB. torch 2.8.0+cu128 (CUDA True), transformers 5.17.0,
  Python 3.11.13. No TORCH UPGRADE (image torch imports fine under transformers 5.17.0).
- Rentals (2 of max 3): 52778638 (offer 46753301, $0.406/hr) docker-proxy pull refusal,
  destroyed un-run ~$0; 52779278 (offer 48989736, host 406325, actual dph $0.4944 incl.
  volume fees) ~16:35Z to ~17:06Z ≈ 0.52h x $0.4944 ≈ $0.26. Total ≈ $0.26 of $0.80 budget.

## Models (rental only, HF_HUB_OFFLINE=0 download, then OFFLINE=1)
- BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
- Q2DIR = /root/.cache/huggingface/hub/models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc
- L12DIR = /root/.cache/huggingface/hub/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada3f766f9f257460c4c9f0b5d6f69d431b
- MiniLM = /root/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/snapshots/1110a243fdf4706b3f48f1d95db1a4f5529b4d41
- Adapter: /root/adapter/adapter02c.pt
  sha256 a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5 MATCH.
  Sidecar adapter02c.json (395 B) from origin/builder-outbox. self122_head.pt local
  5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 MATCH.
- route122 check: returned ('D8', {...}) without raising.

## Seals / tests / selftests (all from ~/tree, origin/main code, never edited)
- `sha256sum -c artifacts/claude-k1c-20260926/SEAL.sha256.txt`: every line OK
  (incl. both panel SEAL.sha256.txt lines OK).
- `sha256sum -c --ignore-missing artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt`:
  every present line OK.
- `(cd artifacts/claude-k1cpanel-20260926 && sha256sum -c SEAL.sha256.txt)`: creative/items.jsonl OK.
- `(cd artifacts/claude-k1apanel-20260926 && sha256sum -c SEAL.sha256.txt)`: creative/items.jsonl OK.
- `python -B scripts/claude_k1a_test.py`: k1a tests: 7/7 OK.
- `python -B scripts/claude_k1c_test.py`: k1c tests: 7/7 OK.
- `python -B scripts/claude_k1c_score.py --selftest` last line: k1c score selftest 5/5 ok.
- `python -B scripts/claude_mu402.py --selftest`: mu402 selftest 7/7 ok.

## DEV gate (3 items, artifacts/claude-panel382-dev-20260925/creative)
- logdevC/Q/L: 3/3/3 "[382/creative/<name>]" lines; all three processes exited; NO_TRACEBACK.
- logdevC.txt contains "k1c: creative writer = install_creative_k1c(use_hist=True, whole=False)" (1 match).
- Empty-reply counts (python, counts only): Q rows=4 empty=0; L rows=4 empty=0.

## V1 (first "[382/creative/" line per log)
- Round A: logKA + logCA contain "mu402: adapter loaded = /root/adapter/adapter02c.pt";
  logKA "k1a: creative writer = install_creative_k1a"; logCA
  "k1c: creative writer = install_creative_k1c(use_hist=True, whole=False)".
  logTA/QA/LA: "twinb: the plain twin is Twin336b" x1 each, 0 mu402:/k1a:/k1c: lines.
- Round B: same pattern (mu402 lines in K+C; k1a x1 in K; k1c x1 in C; T/Q/L twin=1 bad=0).
- No "refusing to load" error anywhere. No V1-FAIL; no kills needed.

## Runs (each arm launched ONCE per panel, own ssh, detached setsid/nohup)
- Round A panel k1cpanel (100 items): K/C/T/Q/L logs 100/100 lines; runners gone; NO_TRACEBACK.
  Rows per arm file: C=195 K=195 T=195 Q=195 L=195 (multi-turn items).
- Round B panel k1apanel (60 items): K/C/T/Q/L logs 60/60 lines; runners gone; NO_TRACEBACK.
  Rows per arm file: C=120 K=120 T=120 Q=120 L=120.
- Exit codes: 0 x10 (basis: full expected rows + final item line + no traceback + process gone;
  numeric codes not captured).
- Wall minutes per arm, approx (finish mtime exact, launch staggered over ~10 min by ssh hangs):
  A finishes K 16:50:41, T 16:53:07, C 16:53:33, L 16:54:22, Q 16:55:05Z
  -> K~6 C~6 T~5 Q~6 L~5.5 min (incl. model load under 5-way contention).
  B finishes K 16:59:53, T 17:00:03, L 17:00:38, C 17:01:10, Q 17:01:39Z
  -> K~3 T~2.5 L~3 C~3.5 Q~3.5 min.
- Median ms per turn (scorer, exact): A C=1367.2 K=1121.0 T=662.9 Q=956.7 L=286.4;
  B C=1536.2 K=1316.0 T=792.0 Q=1107.5 L=519.6.
- Peak GPU memory seen: 7237 MiB of 32607 (single nvidia-smi sample mid round-A, util 86%).

## Scorer outputs (exact, counts only)
- A score: {"C": {"distinct_replies": 190, "messages": 195, "most_common_reply_count": 3,
  "ms_median": 1367.2}, "K": {"distinct_replies": 191, "messages": 195,
  "most_common_reply_count": 3, "ms_median": 1121.0}, "L": {"distinct_replies": 195,
  "messages": 195, "most_common_reply_count": 1, "ms_median": 286.4}, "Q":
  {"distinct_replies": 195, "messages": 195, "most_common_reply_count": 1,
  "ms_median": 956.7}, "T": {"distinct_replies": 179, "messages": 195,
  "most_common_reply_count": 4, "ms_median": 662.9}, "items": 100, "panel": "creative"}
  (events_on_non_teach 0 and puzzles 0 / puzzles_solved 0 for all arms, both rounds.)
- A dedupe: {"prefix": "A", "lines": 500, "distinct_lines": 448, "shared_by_2plus_arms": 52}
- B score: {"C": {"distinct_replies": 116, "messages": 120, "most_common_reply_count": 2,
  "ms_median": 1536.2}, "K": {"distinct_replies": 116, "messages": 120,
  "most_common_reply_count": 2, "ms_median": 1316.0}, "L": {"distinct_replies": 120,
  "messages": 120, "most_common_reply_count": 1, "ms_median": 519.6}, "Q":
  {"distinct_replies": 120, "messages": 120, "most_common_reply_count": 1,
  "ms_median": 1107.5}, "T": {"distinct_replies": 115, "messages": 120,
  "most_common_reply_count": 2, "ms_median": 792.0}, "items": 60, "panel": "creative"}
- B dedupe: {"prefix": "B", "lines": 300, "distinct_lines": 268, "shared_by_2plus_arms": 32}

## Copy-back
- run/A, run/B: creative_{C,K,T,Q,L}.jsonl, creative_judge.jsonl, creative_key.json,
  creative_judge_u.jsonl, creative_key_u.json, summary_creative.json,
  grammar_creative_C.jsonl + 5 logs each. run/dev: devk1c creative_{C,Q,L}.jsonl +
  logdev{C,Q,L}.txt. 38/38 files size+sha256 match rental before destroy.

## Deviations (every one)
- D1: first rental (52778638) docker-proxy pull refusal; destroyed un-run; second host used.
- D2: scp -3 failed on the benspc leg; one Mac mktemp dir used, sha verified on Mac,
  copied to rental, file+dir removed by exact path (confirmed gone).
- D3: every arm-launch ssh hung on teardown (tool timeouts) while the remote launch
  succeeded; all arms verified via logs/ps; pid files stayed empty so PIDs came from ps;
  no kills needed, exact-PID path unused.
- D4: billed dph $0.4944 vs search $0.469 (volume fees).
- D5: no TORCH UPGRADE needed (torch 2.8.0+cu128 + transformers 5.17.0).
- D6: peak GPU mem is one sample, not profiling.
- D7: exit codes inferred as above, not captured numerically.
- D8: credit balance 0 recorded only (auto-refill; not a gate).
