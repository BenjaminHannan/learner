# RESULTS-rent k1a/k1b registered run (Creative answers in chat thread, 2026-09-26, label claude-creativechat-k1a)

Verdict: RUN COMPLETE (no K1a/K1b marks decided here; blind judging + recount happen later per PASSMARKS-k1a.md).
All six arms ran once each on one RTX 5090 rental, 60/60 items each, both scorers exit 0.

- Credit (`vastai show user --raw` balance): 0 (vast auto-refills; not a gate).
- GPU: 1x RTX 5090, offer 39998394, instance 52768302, dph 0.49629629629629624.
- Rental window: 2026-09-26 15:15:49Z (start) to ~15:52:15Z (destroy) = ~0.607h x $0.496296 = ~$0.30 of $0.80 BUDGET.
- BASE: /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc (revision 87179e5c1f455ef22e6223592d2d61351b525bfc as tasked); all-MiniLM-L6-v2 snapshot 1110a243fdf4706b3f48f1d95db1a4f5529b4d41. No other model.
- route122 check: no raise (D8 top1 conf 0.9732, guard pass).
- Seals: `sha256sum -c artifacts/claude-k1a-20260926/SEAL.sha256.txt` every line OK; `sha256sum -c --ignore-missing artifacts/claude-e2e02c-20260926/SEAL-code.sha256.txt` every present line OK; `(cd artifacts/claude-k1apanel-20260926 && sha256sum -c SEAL.sha256.txt)` creative/items.jsonl OK.
- Tests: k1a 7/7 OK; k1b 5/5 OK; k1ab 4/4 OK; mu402 selftest 7/7 ok.
- Adapter: BensPC file sha (Get-FileHash) A33211DC...F86E7936F5 matches a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5; rental `sha256sum ~/adapter/adapter02c.pt` = a33211dc9bdb4e26bc7161b62147cb4dfc04fb605ba1aecbb26948f86e7936f5. self122_head.pt 5ca02173dc7bd4ae400957375be3cf7e1d39574df5dca2a4119fb807c6c8ee25 match.
- DEV gate: K exit 0 with 3 `[382/creative/K]` lines + `k1a: creative writer = install_creative_k1a`; KB exit 0 with 3 `[382/creative/KB]` lines + `k1ab: creative writer = install_creative_k1ab`.
- V1 (first `[382/creative/` line seen per log): logX/logK/logB/logKB `mu402: adapter loaded = /root/adapter/adapter02c.pt`; logKB0 `mu402: adapter loaded = none (B = 0, base 1B)`; logT no adapter line. Exact writer lines: logK only `k1a: creative writer = install_creative_k1a` (1x); logB only `k1b: creative writer = install_creative_k1b` (1x); logKB + logKB0 only `k1ab: creative writer = install_creative_k1ab` (1x each); logX none of the three (0/0/0). No `refusing to load` in any log.

Rows per arm (expected 60 items each): X 60, K 60, B 60, KB 60, KB0 60, T 60 (`[382/creative/<arm>] kc-01..kc-60` counts; outk1a/creative_<arm>.jsonl 120 lines each).
Exit codes: all six 0 by completion evidence (60/60 lines, output files written, no Traceback in any log; wait status not captured for detached setsid launches, see deviations).
Wall minutes per arm (log birth to output mtime): X 4.10, K 5.08, B 5.12, KB 5.07, KB0 4.77, T 2.88.
Median ms per turn per arm (from --score stdout): X 1393.3, K 1672.2, B 1845.8, KB 1764.4, KB0 1714.6, T 1049.9.
Scorer 1 (`claude_panel382_run.py --score`, exit 0): {"items": 60, per-arm "messages": 120, "distinct_replies": 115, "most_common_reply_count": 3 (T: 2), "events_on_non_teach": 0, "puzzles": 0}.
Scorer 2 (`claude_k1a_score.py --dedupe`, exit 0): {"lines": 360, "distinct_lines": 206, "shared_by_2plus_arms": 84}.
Dollars: ~$0.30 total (1 rental of max 3; no re-rents). Post-destroy 0 claude-creativechat-k1a live.

Deviations (every deviation):
1. `scp -3 benspc:... <rental>:...` failed (port flag conflict, `18302: No such file or directory`); used the allowed fallback: one Mac mktemp dir for the 16.5 MB adapter only, removed by exact path right after (verified gone). Nothing else staged on the Mac.
2. Kit pip line installed transformers 5.17.0, which hard-requires torch>=2.5 while the image had torch 2.2.1 (first DEV attempt: `torch_dtype` ok but `AutoModelForCausalLM requires the PyTorch library`; full traceback in run/dev/logdev.txt history on rental, not copied). Upgraded torch to 2.11.0+cu128, then torchvision to 0.26.0+cu128 (image torchvision 0.23 broke `LlamaConfig` import via `torchvision::nms does not exist`), then torchaudio to 2.11.0+cu128 (image torchaudio 2.2.1 `.so` unloadable). No repo code edited or created; same failure mode as rd378L's WRITE-FAIL, fixed here at env level.
3. Six-arm launch: the single combined ssh command timed out client-side after launching X only (server-side X fine, PID 1096); K/B/KB/KB0/T launched individually seconds later (PIDs 1160/1197/1234/1271/1308), each arm launched ONCE total. Staggered starts 15:36:12-15:37:54; per-turn seeds make order irrelevant.
4. Exit codes inferred from 60/60 item lines + written outputs + zero tracebacks (no `wait` on setsid-detached PIDs).
5. dph actual 0.496296 vs search-list estimate 0.469 (vast surcharges/rounding).

Copied back (21 files, sha256-verified 21/21) to artifacts/claude-k1a-20260926/run/ (+ run/dev/): creative_{K,X,B,KB,KB0,T}.jsonl, creative_judge.jsonl, creative_key.json, creative_judge_u.jsonl, creative_key_u.json, summary_creative.json, log{X,K,B,KB,KB0,T}.txt, dev/creative_{K,KB}.jsonl, dev/logdev{,kb}.txt. No reply quoted in this report. Adapter stays off git; no weights pushed.
