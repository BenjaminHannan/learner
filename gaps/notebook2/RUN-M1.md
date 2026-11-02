# Notebook-2 Qwen3.6 reader run: harness on the M1, server on the M3 (start when M1 swap < 3 GB)
Server: the assistant thread's raw mlx_lm.server at http://127.0.0.1:18081/v1, model id `default_model`. Do NOT use the
gateway (:8090, it logs to Ben's diary). Do NOT load any other model. ASSISTANT_RUNNING is fine; stop only on PAUSE_OTHERS
(stage1.py waits on it by itself, and retries every 5 min for ~2 h if the server is down).

```
cd ~/learner-ops && git clone -q -b claude/project-thread-qhf0vt --depth 1 https://github.com/BenjaminHannan/learner nb2-src \
  || (cd nb2-src && git pull -q)
cd ~/learner-ops/nb2-src/gaps/notebook2 && mkdir -p data && gunzip -c lme120.json.gz > data/lme120.json   # the 120-question subset (62 MB)
python3 -m venv ~/learner-ops/nb2-venv && . ~/learner-ops/nb2-venv/bin/activate && pip install -q rank_bm25 sentence-transformers
# (no full dataset needed; sha256 of data/lme120.json should start with 99d0c76b7c1c310c)
shasum -a 256 data/lme120.json
export EMB_CACHE=~/learner-ops/nb2-emb
ssh -fN -L 18081:127.0.0.1:18080 m3   # tunnel to the M3 4-bit server (harness stays on the M1)
curl -sf http://127.0.0.1:18081/v1/models
python stage1.py --backend openai --base-url http://127.0.0.1:18081/v1 --model default_model --reader qwen36 \
  --retriever S2 --out-dir ~/learner-ops/nb2-out --limit 1     # smoke: preds must be short answers, not long reasoning
nohup python stage1.py --backend openai --base-url http://127.0.0.1:18081/v1 --model default_model --reader qwen36 \
  --retriever S2 --out-dir ~/learner-ops/nb2-out > ~/learner-ops/nb2-run.log 2>&1 &
```
Resume-safe (rerun the same command). Report back the contents of ~/learner-ops/nb2-out/rows_qwen36.jsonl (or push it to
the branch under gaps/notebook2/results/qwen36/) and the tail of nb2-run.log.
