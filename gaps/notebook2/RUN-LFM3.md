# Notebook-2 stage 1, small reader = LFM3-1.7B (Amendment D)

Needs a llama.cpp built at/after the LFM3 merge (2026-10-27 16:06Z; the M1 has one) and LiquidAI/LFM3-1.7B-GGUF QAD-Q4_0 (~1 GB).
No big downloads on the hotspot: use a GGUF already on the machine.

1. `llama-server -m <LFM3-1.7B-QAD-Q4_0.gguf> --jinja -ngl 99 -c 32768 --host 127.0.0.1 --port 18095 -np 1`
   (Windows Radeon: llama-server.exe, same flags, only if that build supports lfm3; else transformers bf16 via the backend `hf`).
2. Smoke (1 question, check `pred` fields are short answers, no `<think>`):
   `python stage1.py --backend openai --base-url http://127.0.0.1:18095/v1 --model lfm3 --reader lfm3q4 --retriever S2 --limit 1`
3. Full: same without `--limit` (nohup; resumes). Respect ~/learner-ops/PAUSE_OTHERS (built in).
4. Commit rows to gaps/notebook2/results/lfm3q4/ plus a `runtime.txt` (llama.cpp commit, GGUF file name and sha256), push to
   claude/project-thread-qhf0vt. Stop llama-server.
Data and venv as in RUN-M1.md (lme120.json from lme120.json.gz, sha256 prefix 99d0c76b7c1c310c; emb cache optional).
