# rent-382b RESULTS-rent (partial, TIME-CAP-INCOMPLETE)

Verdict: INCOMPLETE. Registered run 382b not finished. READER upload (2 GB) infeasible within 3.5 h TIME CAP at measured uplink (~0.1 MB/s sequential, ~6 MB/min). Completed: seals, tests, base checkpoint, Bank C T arm, T chat panel, T creative panel. Missing: DEV gate, Bank C E/G/R/ER, scorer, E/G/R/ER panels, panel scores, EP382 logs, sleep logs. No marks judged.

## 1. Seals (rental /root/tree, before anything else)
- SEAL-code.sha256.txt: all lines OK, 0 failures, exit 0.
- BankC SEAL.sha256.txt: 3 OK (turns.jsonl, truth.jsonl, README.md), exit 0.
- Panel382 SEAL.sha256.txt: 2 OK (chat/items.jsonl, creative/items.jsonl), exit 0.
- claude_e2e382_test.py: 10/10 OK.
- claude_e2e383_test.py: 13/13 OK.

## 2. Base checkpoint
- JSON line: {"stage": "base", "seed": 4102, "seconds": 13.2, "fresh_hop1to3": 1.0, "fresh_depth10": 1.0, "big_depth10": 1.0, "unknown_rate": 1.0}
- .pt sha256: 1dfd95f5e6917cb5a5a73a408456555e27f4706a5bfae752cd0b0b632db63c86
- .pt bytes: 2900 approx (2.9K).

## 2b. DEV gate
- NOT RUN. READER incomplete, no DEV E/R launched. No DOUT, no RESULTS-dev.md.

## 3. Bank C
- T (twin, BASE path): wrote arm_T.jsonl rows=653 lives=40. First two lines: "sleepcheck: logging every sleep to (no log); stop on missing checkpoint = False" and "twinb: the plain twin is Twin336b (enable_thinking=False)". Wall ~5 min (02:28-02:33 UTC).
- E/G/R/ER: NOT RUN (READER missing).
- SLEEPCHECK env deviation: T launches omitted SLEEPCHECK_STOP/SLEEPCHECK_LOG (log shows "(no log)", False). No sleep_T.jsonl. SLEEP-NOT-LEARNING not triggered (no checkpoint check).
- Order deviation: T Bank C run before DEV gate (gate blocked by READER).

## 3b/4. Scorer
- NOT RUN. No score/ folder. No per-arm scorer lines.

## 5/5b. Panels
- T chat: chat_T.jsonl rows=318, 60/60 chats, wall ~11 min (02:33-02:44 UTC).
- T creative: creative_T.jsonl rows=91, 60/60 replies, wall ~4 min (02:44-02:48 UTC).
- E/G/R/ER chat/creative: NOT RUN.
- Panel scores: NOT RUN (no score/ folder, no chat_*.jsonl copy, no summary lines).

## EP382 logs
- 0 files, 0 rows. No E/ER arms launched.

## Sleep logs
- 0 files. No checkpoint_exists true counts, no attempted true counts.

## GPU / money / time
- Instance 52674739, label rent-382b, GPU RTX 5090, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, disk 80 GB.
- Offer search re-run before create. Offer 43982846, $0.469/hr search; actual dph $0.5037037037037037.
- Credit at start: 9.77. Budget $2.50.
- Rental start 01:16:34 UTC, destroy ~02:56 UTC. Hours 1.64. Dollars 1.64 x 0.5037 = $0.83. Within budget. 1 rental, no re-rents. Post-destroy 0 rent-382b live.
- BASE openbmb/MiniCPM5-1B commit 87179e5c1f455ef22e6223592d2d61351b525bfc. Torch 2.8.0+cu128 True. route122 selftest ok.
- READER ~/premonition-models/lis301-merged/model.safetensors sha b4fd93a2b29fc9e246cfdd2ae5c815576957480f410d85eb24bb8df00d21b890 verified on Mac. Uploaded 16/104 chunks (~320 MB of 2 GB) before stop; remainder infeasible (see traceback section for speed evidence).
- Wall per step: setup+HF ~10 min, seals+tests ~3 min, base 13.2 s, T Bank C ~5 min, T chat ~11 min, T creative ~4 min, READER upload interleaved ~60 min total. Copy-back verified (sizes+sha256 match rental).

## Tracebacks (full)
1. T Bank C first launch (literal "BASE" instead of path, HF_HUB_OFFLINE=1):
```
sleepcheck: logging every sleep to (no log); stop on missing checkpoint = False
twinb: the plain twin is Twin336b (enable_thinking=False)
Traceback (most recent call last):
  File "/opt/conda/lib/python3.11/site-packages/transformers/utils/hub.py", line 438, in cached_files
    hf_hub_download(
  ...
huggingface_hub.errors.LocalEntryNotFoundError: Cannot find the requested files in the disk cache and outgoing traffic has been disabled. To enable hf.co look-ups and downloads online, set 'local_files_only' to False.
...
OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't find them in the cached files.
Check your internet connection or see how to run the library in offline mode at 'https://huggingface.co/docs/transformers/installation#offline-mode'.
```
Relaunched with BASE=/root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc, succeeded.

2. HF rate limit on sentence-transformers download (retried after 20 s, succeeded):
```
huggingface_hub.errors.LocalEntryNotFoundError: Got: HfHubHTTPError 429 Too Many Requests: you have reached your 'api' rate limit. Retry after 17 seconds.
```

3. READER upload bottleneck (no traceback, evidence):
- scp/rsync sequential 20 MB chunks ~4-5 min each (~0.1 MB/s). 16 chunks in ~60 min.
- 3+ parallel scp repeatedly failed with "client_loop: ssh_packet_write_poll: Connection to 180.189.55.38 port 56660: Result too large / lost connection".
- Certain 20 MB chunks (safe-af, safe-an, tree chunk ah) consistently failed at 20 MB, succeeded when split to 5 MB / 1 MB.
- Projected remainder 88 chunks x 5 min = 440 min = 7.3 h, exceeding 3.5 h TIME CAP and $2.50 budget headroom. Stopped early, copied back partial, destroyed.

## Files copied back (verified)
- artifacts/claude-e2e382-20260925/run/arm_T.jsonl 251K sha ea1d543680cfaa43f075a35671ac8a95d59fa1ea3cb2c988898fdf22fbe982dd
- artifacts/claude-e2e382-20260925/run/chat_T.jsonl 157K sha 42fe7744b5955b5b7813fb22d7b15232cde63c2bf957381771a92a409b5e3372
- artifacts/claude-e2e382-20260925/run/creative_T.jsonl 44K sha f6d628db4a6759605fc4a7412e8065bf42f8c775d3246ca4c1bb80c3fadaeb8d
- No score/, no DEV folder, no EP382/sleep logs (none existed).

## What this means
- T-only partial proves rental pipeline (seals, BASE, twin, panels) works, but says nothing about 382b/383 marks (Y2, C1/C2, Q1-Q3, etc.).
- No E/G comparison, no scorer, no judges run. Registered verdict for 382b/383 remains open.
- READER transfer is the blocker for any retry on this network; recommend pre-staging READER on a fast host or running READER arms where the 2 GB already lives.
