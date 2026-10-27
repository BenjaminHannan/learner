# assistant-sft: synthetic tool-calling data for LFM2.5-24B-A2B-Base

Local MacBook personal-assistant conversations (user: fictional high-school senior/developer), generated with `claude-sonnet-5-5`.

**Files** (master copy: `/mnt/project-files/data/assistant-sft/`; same files in `data/` here, 16 MB train)
- `train.jsonl` 1,792 / `eval.jsonl` 200 (held out, never train on), `tools.json` (15 tools), `stats.json`, `raw_generations.jsonl` (mount only).
- Each line: `{"scenario", "tools": [15 OpenAI-style function schemas], "messages": [system, user, assistant(tool_calls), tool, ..., assistant]}`. `tool_calls[].function.arguments` is a JSON *string* (OpenAI format); tool messages carry `tool_call_id` and `name`. Assistant content is null or one short sentence on tool turns; no reasoning text.
- Scenarios (train): single_tool 287, multi_step 390, clarify 156, confirm_irreversible 204, direct_answer 163, error_recovery 205, summarize_long 114, parallel 273. Eval is stratified from the same mix.

**Cost**: 421 API calls (5 conversations each), see `stats.json` (`estimated_cost_usd` 37.75 at assumed $3/$15 per M tokens). Generation stopped at the cap, so ~2,000 valid conversations instead of the 3,000 target (~$0.019 per valid conversation).

**Regenerate**
```
export LEARNER_ANTHROPIC_API_KEY=...
python3 make_tools.py                       # writes tools.json
python3 generate.py --calls 430 --raw raw.jsonl --cap 38 --workers 8   # appends raw output, tracks cost in raw.jsonl.cost
python3 build.py raw.jsonl OUT_DIR --eval 200   # validate, dedupe, stratified split, stats.json
```
Validation (`build.py`): JSON parses (with salvage of complete objects from malformed/restarted outputs), role order, tool names in schema, args validated with `jsonschema`, one tool message per tool_call id in order, final turn is assistant, send_email / rm / force-push only after an assistant turn plus a later user turn (confirmation), no `<think>` leakage, dedupe on normalized first user message. Systems prompts (3 styles) are added by code.
