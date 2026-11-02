# Notebook-2 stage 1: how to run

Files to ship: `stage0.py`, `stage1.py`, `data/lme120.json` (62 MB; made by `python stage1.py --make-subset` from the full file). `stage0.py` needs `emb_cache/` only as a speed-up (optional).
Pip: `pip install rank_bm25 sentence-transformers` (plus `transformers` for hf). Dense retrieval uses bge-small (CPU is OK, GPU is used automatically if present).
Rows go to `stage1_out/rows_{reader}.jsonl`; reruns skip finished (question, arm). `--limit 1` is a smoke test. Retriever default S2; use `--retriever S3` only if Stage 0 says so.

## (a) Kaggle T4, K2-Horizon-3.7B (hf backend)
```
!pip uninstall -y -q torchao
!pip install -q rank_bm25 sentence-transformers 'transformers==5.20.2' accelerate   # K2 remote code needs transformers 5.x
!python stage1.py --backend hf --model-path IFM/K2-Horizon-3.7B --reader k2 --limit 1     # smoke
!python stage1.py --backend hf --model-path IFM/K2-Horizon-3.7B --reader k2               # full, 120 q x 5 arms
```
Internet must be on (model download, ~10 GB fp16). The script checks one forward pass is finite in fp16 and stops if not. Download `stage1_out/rows_k2.jsonl` afterwards (the Kaggle session has no API key; never put one there).

## (b) Ben's Mac, Qwen3.6-35B-A3B 4-bit (openai backend)
Before starting, and in any loop: stop if `~/learner-ops/PAUSE_OTHERS` or `~/learner-ops/ASSISTANT_RUNNING` exists.
```
[ -e ~/learner-ops/PAUSE_OTHERS ] || [ -e ~/learner-ops/ASSISTANT_RUNNING ] && { echo "paused"; exit 1; }
pip install mlx-lm rank_bm25 sentence-transformers
mlx_lm.server --model <mlx-community 4-bit repo or local path of Qwen3.6-35B-A3B> --port 8080 &
python stage1.py --backend openai --base-url http://127.0.0.1:8080/v1 --model <same name as --model above> --reader qwen36 --limit 1
python stage1.py --backend openai --base-url http://127.0.0.1:8080/v1 --model <same name> --reader qwen36
```
The script sends `chat_template_kwargs: {"enable_thinking": false}`, temperature 0, and strips any `<think>` block. Check the smoke rows: if preds start with long reasoning, the server ignored the switch (see notes in the report). Resume-safe: if a pause file appears, kill it and rerun later. llama.cpp works the same (`llama-server --jinja -m ... --port 8080`).

## (c) Judge in the cloud (no GPU, needs the API key; rows files from (a) and (b) copied into `stage1_out/`)
```
pip install anthropic scipy
export LEARNER_ANTHROPIC_API_KEY=...
python judge_batch.py --dry-run     # builds requests, prints the table with fake labels, sends nothing
python judge_batch.py               # submits one batch (claude-sonnet-5-5, effort low), polls, writes stage1_out/judged.jsonl, prints tables
```
Prints accuracy per arm (overall and per type) and paired win/loss with exact McNemar p versus R, per reader. Refuses above 3000 requests. If it is interrupted while the batch runs, rerun: `batch_state.json` makes it resume the same batch.
