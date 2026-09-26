Labeling drafts and writing practice chats — fetching latest sources to run the teacher.
Selftest checks out — now running the teacher labeling and generation.
The labeling format failed — checking if practice chat generation works.
VERDICT: FAIL — phase 1 blocked, do not train critic on these labels.

Counts (integers):
- DEV packet drafts: 157
- teacher labelled: 0
- unparsed: 157
- label calls: 48 (16 chunks x 3 tries)
- agree compared: 0
- agree matches: 0
- train practice chats written: 0 / 240
- write batches ok: 0 / 12

What I did (origin/main only, script never edited, key never printed — no `sk-or` in any output):
- `git fetch -q origin main`, tmpdir `/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/opencode/k1e-teacher-tVmTTH` via `git archive origin/main scripts/claude_k1e_teacher.py artifacts/claude-k1e-20260926/dev | tar -x -C <tmp>`, ran with `uv run --offline --no-project --python 3.12 python -B`.
- `selftest` -> `k1e teacher selftest 2/2 ok`

Exact printed output:
- `label --packet artifacts/claude-k1e-20260926/dev/packet_dev.jsonl --out artifacts/claude-k1e-20260926/teacher-dev`:
```
[k1e-teacher] lines 0-9 unparsed
[k1e-teacher] lines 10-19 unparsed
[k1e-teacher] lines 20-29 unparsed
[k1e-teacher] lines 30-39 unparsed
[k1e-teacher] lines 40-49 unparsed
[k1e-teacher] lines 50-59 unparsed
[k1e-teacher] lines 60-69 unparsed
[k1e-teacher] lines 70-79 unparsed
[k1e-teacher] lines 80-89 unparsed
[k1e-teacher] lines 90-99 unparsed
[k1e-teacher] lines 100-109 unparsed
[k1e-teacher] lines 110-119 unparsed
[k1e-teacher] lines 120-129 unparsed
[k1e-teacher] lines 130-139 unparsed
[k1e-teacher] lines 140-149 unparsed
[k1e-teacher] lines 150-156 unparsed
{"lines": 157, "labelled": 0, "unparsed": 157, "calls": 48, "useful_yes": 0, "cost_usd": 0.024}
```
`labels.jsonl` is 0 lines (vs packet 157 lines).

- `agree --labels .../teacher-dev/labels.jsonl --key .../dev/key_dev.json --verdicts .../dev/verdicts_dev.json`:
```
{"compared": 0, "teacher_useful": 0, "opus_useful": 0, "both_useful": 0, "agree": 0, "kappa": 0.0, "passes_label_rule": false}
```
Label rule (>=85% and kappa>=0.5) NOT met — 0 compared, cannot pass.

- `write --out artifacts/claude-k1e-20260926/train`:
```
[k1e-teacher] batch 0 try 1: not 20 chats
[k1e-teacher] batch 0 try 2: fact not in teach turns
[k1e-teacher] batch 0 try 3: fact not in teach turns
k1e-teacher: batch 0 failed 3 times
```
SystemExit, no `items.jsonl` written. 0/240 chats.

Root cause (probe of 2-line chunk, default model `z-ai/glm-5.3-flash`):
- Model returns JSON lines, not a JSON list, e.g. LEN 312 with 2 objects `{"id":"E0000",...}` newline `{"id":"E0001",...}`, no `[` `]`.
- Script `json_list()` does `re.search(r"\[.*\]", txt)` so returns None -> `got is None` -> `unparsed` for all 48 calls. JUDGE prompt is contradictory: “write one JSON object on its own line” then tail “Reply with ONLY a JSON list”.
- Write fails separately on `check_batch()` structural checks.

Stopped per “if it breaks, stop”. Nothing copied to worktree, nothing pushed (no valid `teacher-dev/labels.jsonl`, no `train/items.jsonl`, no `teacher-log.txt` to push). GPU: no (Mac CPU only).
