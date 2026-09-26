# lis319f-ch403chk — 2 DEV chat turns, OLD vs NEW reader (ch-403 false-save lead)

Label: lis319f-ch403chk. Date (UTC): 2026-09-26. Worktree: card-experiment-handoff-7c5b27.
DATA: DEV only, 2 rows from everyday-chat DEV chats (readable, quotable). No TEST-ONLY panel touched, opened, quoted, or tuned.

## Setup
- TREE: `D=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.LRXJ8Wx0aD` via `git archive origin/main scripts design/v3/60-listener artifacts/claude-lis319f-20260926/chk_ch403 | tar -x -C $D` (29 MB, 2 rows).
- Reader gate: no `claude_lis319_read.py` process running at start (one reader job on the Mac at a time satisfied).
- Env: `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1; uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers --with safetensors python -B`.
- GPU: no (Mac CPU/MPS).

## SHA checks (both match, 2/2)
- OLD `~/premonition-models/lis319-merged/model.safetensors`: `e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76` = expected e688e1b2…776a76. MATCH.
- NEW `~/premonition-models/lis319f-merged/model.safetensors`: `970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b` = expected 970ef0ac…4aa6b4f9b. MATCH.

## Runs
- OLD: `python -B scripts/claude_lis319_read.py --model ~/premonition-models/lis319-merged --rows artifacts/claude-lis319f-20260926/chk_ch403/rows.jsonl --out reads_old.jsonl` → exit 0, stdout tail `read 2 rows on mps`. Device: mps. Rows read: 2/2.
- NEW: same with lis319f-merged → exit 0, stdout tail `read 2 rows on mps`. Device: mps. Rows read: 2/2.

## Input rows (DEV, quoted verbatim)
Row 1 id `dev02e-chat-31:1`: turn `im 19 and have zero credit history. whats the smartest way to start building it`.
Row 2 id `dev02e-chat-57:4`: turn `ok ty, gonna sleep on it. night!`, prev_reply `Just to check: is Kim's occupation marine biology?` (a probe question in the assistant's previous reply; the user's own history is about picking coding vs marine-biology summer programs).

## Results, verbatim per row per reader

### Row dev02e-chat-31:1 — OLD (lis319)
- frame.act: STATE
- facts (1): owner=me, rel=age, value=19, mode=ASSERT, conf=0.9997677206993103
- full line verbatim: `{"id": "dev02e-chat-31:1", "frame": {"act": "STATE", "facts": [{"owner": "me", "rel": "age", "value": "19", "mode": "ASSERT"}], "ask": null}, "conf": [0.9997677206993103], "raw": "{\"act\": \"STATE\", \"facts\": [{\"owner\": \"me\", \"rel\": \"age\", \"value\": \"19\", \"mode\": \"ASSERT\"}], \"ask\": null}\n<END>", "ms": 1987.5}`

### Row dev02e-chat-31:1 — NEW (lis319f)
- frame.act: STATE
- facts (1): owner=me, rel=age, value=19, mode=ASSERT, conf=0.9995421171188354
- full line verbatim: `{"id": "dev02e-chat-31:1", "frame": {"act": "STATE", "facts": [{"owner": "me", "rel": "age", "value": "19", "mode": "ASSERT"}], "ask": null}, "conf": [0.9995421171188354], "raw": "{\"act\": \"STATE\", \"facts\": [{\"owner\": \"me\", \"rel\": \"age\", \"value\": \"19\", \"mode\": \"ASSERT\"}], \"ask\": null}\n<END>", "ms": 1610.4}`

### Row dev02e-chat-57:4 — OLD (lis319)
- frame.act: STATE
- facts (1): owner=Kim, rel=occupation, value=marine biology, mode=ASSERT, conf=0.9517437219619751
- full line verbatim: `{"id": "dev02e-chat-57:4", "frame": {"act": "STATE", "facts": [{"owner": "Kim", "rel": "occupation", "value": "marine biology", "mode": "ASSERT"}], "ask": null}, "conf": [0.9517437219619751], "raw": "{\"act\": \"STATE\", \"facts\": [{\"owner\": \"Kim\", \"rel\": \"occupation\", \"value\": \"marine biology\", \"mode\": \"ASSERT\"}], \"ask\": null}\n<END>", "ms": 2017.4}`

### Row dev02e-chat-57:4 — NEW (lis319f)
- frame.act: CHAT
- facts (0): none, conf=[]
- full line verbatim: `{"id": "dev02e-chat-57:4", "frame": {"act": "CHAT", "facts": [], "ask": null}, "conf": [], "raw": "{\"act\": \"CHAT\", \"facts\": [], \"ask\": null}\n<END>", "ms": 1024.4}`

## Reading
- Row 1 (age 19): OLD and NEW agree, 1 fact each, STATE me/age/19 ASSERT. Counts: OLD facts=1, NEW facts=1.
- Row 2 (goodnight turn after a probe question): OLD saves Kim/occupation/marine biology ASSERT at conf 0.9517 (1 fact); NEW saves nothing, act CHAT (0 facts). This matches the ch-403 false-save lead: OLD echoes the assistant's probe question as a user fact, NEW does not. Counts: OLD facts=1, NEW facts=0. Total facts: OLD 2, NEW 1 across 2 rows.
- No TEST-ONLY data involved. Nothing tuned. Fictional names only in this report (Kim appears only as quoted DEV content).

## Outputs
- `artifacts/claude-lis319f-20260926/chk_ch403/reads_old.jsonl` (2 lines), `reads_new.jsonl` (2 lines), this RESULTS.md.
- Scratch tree removed: `rm -rf /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.LRXJ8Wx0aD`, confirmed gone.
