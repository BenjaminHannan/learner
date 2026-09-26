Starting smoke run 2 — checking gates and kit rules.
Gates check next — verifying no duplicates and credit balance.
Gates pass (credit 8.83, no duplicate). Searching for cheapest GPU now.
Cheapest passing offer is RTX 4090.t Claus Müller, Malaysia. Creating the rental now.
Instance running. Testing SSH and streaming the code tree.
Environment ready (torch 2.8.0, transformers 5.17.0). Downloading the three pinned models.
Models downloaded. Running seal check (panel hash + selftest).
Seal passes (hash match, selftest 12/12). Launching all three lanes.
Lane 1 running; lanes 2–3 didn't launch. Starting them now.
All three lanes running (PIDs 972/1030/1068). Monitoring progress and spend.
Two lanes finished, one still going. Collecting completion lines.
Spend has passed $0.18 — enforcing BUDGET-STOP: killing lane 2, copying back, destroying.
Lane 2 killed (7/8 rows kept). Copying results back before destroy.
Copy-back verified (sizes + sha256 match). Capturing exact timestamps, then destroying.
Destroyed and confirmed. Writing ledger line and results file.
Files are on disk at the PUSH paths (worktree .gitignore covers `artifacts/`; smoke 1's files were force-added by the watcher flow, so I leave the index untouched for the watcher). Task complete.

# BUDGET-STOP — claude-benchmarks-bmrivsmoke2 (smoke run 2)

**Gates:** credit 8.83074058626977 (≥ $0.20, pass). Duplicate gate pass (no run2/RESULTS-rent2.md on builder-outbox, no live bmrivsmoke2 instance). Panel seal pass, selftest pass. Code unmodified. No traceback. Counts only, no replies quoted.

**Setup (as rent-bmrivsmoke.md):** streamed `scripts/claude_bm390.py scripts/claude_bmriv_rivals.py artifacts/claude-panel-rsn358b3-smoke-20260926/panel.jsonl artifacts/claude-bmriv-smoke-20260926` (no Mac staging); kit pip line only; pinned snapshots BASE/Q2DIR/L12DIR; offline env for all runs.
- torch 2.8.0+cu129, transformers 5.17.0, python 3.11.13
- BASE `…/models--openbmb--MiniCPM5-1B/snapshots/87179e5c…`; Q2DIR `…/models--Qwen--Qwen3.5-2B/snapshots/15852e8c…`; L12DIR `…/models--LiquidAI--LFM2.5-1.2B-Instruct/snapshots/0f604ada…`
- Panel sha256 `da7202db858cee9537acbb4d40d2316921673e00cf27a19a60ef09c1973012e7` (match); `BMRIV-SELFTEST PASS 12/12`

**Step 2 JSON lines (verbatim):**
- Lane 1 plain1b_4k (PID 972, 16:39:05Z–16:43:41Z, exit 0 inferred): `{"name": "plain1b_4k", "rows": 8, "think": "off", "max_new": 4096, "shard": "1/4", "seconds": 277, "hit_max": 2, "think_closed": 0, "empty_replies": 0, "median_new_tokens": 841.0, "median_ms": 20351.050000000003, "sha256": "596f1386a95b701cdad3fbbabbc6f4ec42880e3700138a510a29e31e2d8f65d7"}`
- Lane 2 qwen2b_4k (PID 1030, start 16:40:22Z, SIGTERM-killed ~16:56:55Z, exit 143 inferred): no JSON line; 7 rows kept
- Lane 3 lfm12b_4k (PID 1068, 16:40:28Z–16:44:46Z, exit 0 inferred): `{"name": "lfm12b_4k", "rows": 8, "think": "off", "max_new": 4096, "shard": "1/4", "seconds": 258, "hit_max": 0, "think_closed": 0, "empty_replies": 0, "median_new_tokens": 2175.0, "median_ms": 31916.3, "sha256": "2277023dc9a113a4a8d1772cf37ab4dcc4e5c78f32a39a9e6f7130b5731e2bde"}`

**OUT (run2/, copied back before destroy, sizes+sha256 match box):** rival_plain1b_4k.jsonl 8 rows / 33197 B / 596f1386…; rival_qwen2b_4k.jsonl 7 rows / 49956 B / cdfedadb…; rival_lfm12b_4k.jsonl 8 rows / 40403 B / 2277023d…. Total 23 rows.

**Rental:** instance 52778379 (cheapest passing offer 43681503, RTX 4090 MY, dph $0.38222222), created 16:27:10Z, running ~16:31:36Z, destroyed 16:58:03Z → ~0.515 h ≈ **$0.197 of $0.20**. 1 rental of max 4. Post-destroy: 0 bmrivsmoke2 live (confirmed). Peak GPU mem seen 9665/24564 MiB. Finished: plain1b_4k, lfm12b_4k. Killed: qwen2b_4k.

**Deviations:** (1) lanes 2–3 started 77–83 s after lane 1 (combined-launch ssh timed out client-side; relaunched individually; all overlapped 16:40:28–16:43:41Z). (2) Exit codes inferred, not captured (detached runs; evidenced by final JSON + full files; lane 2 by kill). (3) Money-rule overshoot: ~$0.172 at 16:54:06Z poll, ~$0.189 at 16:56:45Z poll, killed immediately; final ~$0.197 within budget. (4) Peak GPU mem from sparse polls. (5) One client-side ssh timeout, no rental effect.

**PUSH (builder-outbox, on disk for watcher):** `artifacts/claude-bmriv-smoke-20260926/RESULTS-rent2.md`, `artifacts/claude-bmriv-smoke-20260926/run2`, `artifacts/fable-predictions-ledger.md` (line appended).
