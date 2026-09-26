Renting the GPU and running your train-and-score job — starting with credit and setup checks.
Credit and duplicate checks passed — now finding a rental GPU.
Found a cheap 5090 that meets the requirements — renting it now.
Rental is running — building the code package and setting up the box.
Rental is up but SSH needs a moment — checking access and preparing upload.
SSH key isn't attached to the instance — fixing that.
All keys rejected — checking if this is host-specific or a wider issue.
First host had a broken SSH tunnel — new rental is running, testing access.
Upload is slow but progressing (103M of 176M) — resuming until complete.
Setup complete (torch 2.8.0, transformers 5.17.0, BASE cached) — running seals and selftests.
Selftests pass — fetching the benchmark data.
Practice data hashes match — starting the training run.
Training finished — launching the scoring lanes.
MMLU done — launching GSM8K while LoCoMo continues.
GSM8K done, LoCoMo at 4/10 conversations — waiting for it to finish.
All scoring complete — copying results back and verifying.
Copy-back verified — gathering final details before destroying the rental.
Rental destroyed and confirmed gone — writing the results file and ledger.
Results file written — appending the ledger line.
DONE — rent-bm397t complete, all commands finished, no BUDGET/TIME stop.

CREDIT GATE: 7.337024797469866

DUPLICATE GATE: pass (no builder-outbox run/ or RESULTS-rent.md; no live rent-bm397t; started with rent-bm391, 02c-dev, rent-brd6 only).

lis-302 first-13-lines compliance: additive only (new run/ files + new RESULTS-rent.md + ledger append + out-of-repo adapter; zero existing files edited), fictional names only in code-made data, this is the report.

RENTALS (RTX 5090 first, kit filter reliability>=0.98, 8+ CPU, 60+ GB, 200+ Mbps prefer):
- 52684428 (offer 45669313, dph 0.5037): running in 30s but SSH proxy rejected all keys while 2 other instances worked → destroyed ~03:18:05Z, ~0.181h ~$0.09.
- 52685550 (offer 44188476 KR, dph 0.5037037, 80GB, runtime image): running 03:20:51Z, destroyed 04:23:49Z, ~1.091h ~$0.55.
- Total ~1.27h ~$0.64 of $1.40. 0 rent-bm397t live after (confirmed).

SETUP: torch 2.8.0+cu128 (CUDA True), transformers 5.17.0, pyarrow 25.0.1 (installed; nothing else), box python 3.11.13. BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc. All box commands under setsid/nohup with own logs.

STEP 1: seal bm397t 10/10 OK; seal bm390-code 8/8 OK; data selftest "BM397T-DATA-SELFTEST PASS 8/8"; train selftest "BM397T-TRAIN-SELFTEST PASS 5/5" (first launch hit my wrapper cwd bug, relaunched unchanged — deviation reported).

STEP 2 fetch (verbatim):
{"fetch": "OK", "locomo_convs": 10, "locomo_qa": 1986, "locomo_by_category": {"1": 282, "2": 321, "3": 96, "4": 841, "5": 446}, "mmlu_ok_rows": 5330, "mmlu_sample": 300, "gsm8k_rows": 1319, "gsm8k_sample": 300, "mmlu300_sha256": "e294f5fc0c94726e640d276d67af3503b9d9a48574dbae357f8e72289f76c049", "gsm8k300_sha256": "df57d09b50357481931bfc5b13903821d22afb986c7bf170941c30038706b949"}

STEP 3: train rows 1800, dev rows 200; sha256 0654bd2f60ac002d1465cc55a45cd462bd8b68be8d9c7606c2894b7856f06237 / 675a2d854153700c80eee701a290cb4b2c39c58a4dd2065640b56caa67942da9 — both match.

STEP 4 train once: dev_before 116/200 median 6.0w; steps 25–225 losses 0.1563/0.021/0.0306/0.4272/0.0044/0.0081/0.0025/0.0556/0.0029; dev_after_lora 199/200 median 2.0w; dev_after_merged 199/200 median 2.0w; final {"steps": 225, loss_first10 0.7709, loss_last10 0.078, lora_params 4128768, merged_layers 96, seconds 189.7}; merged model.safetensors 9719c266db9bb9d4ffe41ed7bbcb6d5952e948b80db7c25731b08448923a8e3a.

STEP 5 (each launched once, ps-checked; lanes 1+2a together):
- locomo TS: start 03:58:27Z, end 04:19:12Z (mtime), exit 0 (inferred: wrote line + 0 traceback), first `[bm390] conv-26 plain questions=199`, last `wrote locomo_TS.jsonl rows=1986 convs=10`.
- mmlu TS: start 03:58:27Z, end 03:58:42Z, exit 0, first/last `wrote mmlu_TS.jsonl rows=300`.
- gsm8k TS: start 04:00:35Z, end 04:03:18Z, exit 0, first/last `wrote gsm8k_TS.jsonl rows=300`.

STEP 6: copied back OUT + adapter, sizes+sha match box, then destroyed + confirmed + ledger appended. Adapter ~/premonition-models/bm397t-adapter397t.pt 16576151 B sha256 621edd1631072a152f77c83cd1967ac811d1a3d80c66fa9a85bd576af88f7233 (never pushed). MERGED not copied.
OUT: locomo_TS.jsonl 1986 rows 276376 B 30eb5dc4…; mmlu_TS.jsonl 300 rows 18933 B fa830d32…; gsm8k_TS.jsonl 300 rows 57772 B c6bb2f14…; train397t.json 1012 B 0919dac9…. Peak GPU mem 5074 MiB on RTX 5090 32GB. Tracebacks: none (0 in all 10 logs). No scoring done here.

PUSH: artifacts/claude-bm397t-20260926/RESULTS-rent.md, artifacts/claude-bm397t-20260926/run, artifacts/fable-predictions-ledger.md.
