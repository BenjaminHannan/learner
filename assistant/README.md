# Local assistant (OpenBot + MLX on the MacBook)

Pieces
- `gateway.py` — OpenAI-compatible proxy on 127.0.0.1:8090. Models: `qwen36` (thinks), `qwen36-fast` (no thinking), `k2-helper` (small; hidden when its server is down). Always sends `model=default_model` upstream, renames `reasoning` to `reasoning_content`, and writes the diary.
- `diary_mcp.py` — MCP server giving the model `diary_search`, `diary_read`, `diary_days` over the diary.
- `serve.sh` / `stop.sh` / `status.sh` — start, stop, inspect. `serve.sh` is safe to run twice; it writes `~/learner-ops/ASSISTANT_RUNNING` so experiment jobs know the Mac is in use, and asks first if `~/learner-ops/PAUSE_OTHERS` exists (`--yes` skips).
- `opencode.json` — template for `~/.config/opencode/opencode.json` (`__HOME__`, `__PY__` are filled in by `install.sh`, which merges and backs up any existing file).
- `install.sh` — copies everything to `~/learner-ops/assistant/`, writes configs, creates the Desktop "Start Assistant" / "Stop Assistant" launchers.

Ports: big model 8080, small model 8081, gateway 8090 (all localhost).

Diary: `~/learner-ops/diary/`
- `raw/YYYY-MM-DD.jsonl` — one full record per request (UTC date). Tools and system prompts are stored once in `raw/blobs/<sha>.json` and referenced by hash.
- `diary.sqlite` — FTS5 search index, one row per turn.

Start/stop: double-click the Desktop launchers, or run `~/learner-ops/assistant/serve.sh` / `stop.sh`.
Small model: set `ASSISTANT_SMALL_MODEL` (and `ASSISTANT_SMALL_ARGS`) before `serve.sh`. Other overrides: `ASSISTANT_PY`, `ASSISTANT_BIG_MODEL`.

Troubleshooting
- First reply is slow: the first request prefills the ~10k-token tool prompt cold. Later turns reuse the prompt cache (the gateway log shows `cached=`).
- "model server not running" (HTTP 503): run `status.sh`, then Start Assistant.
- Logs: `~/learner-ops/assistant/run/{big,small,gateway}.log`.
- Tests (Linux or Mac): `python3 -m unittest discover -s assistant/tests`.
