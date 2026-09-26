# lis-319o panel read — RESULTS-read (lis-319f, one read)

Label: lis319o-panel
Date (UTC): 2026-09-26
Task: lis-319o, one read of the sealed history-owner panel with the lis-319f reader
GPU: no (Mac CPU/MPS; the reader runs on MPS)
Worktree: /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
Code: run, never edited; panel read exactly ONCE.

PASSMARKS first: read origin/main:artifacts/claude-lis319o-20260926/PASSMARKS.md before running.

## 1. TREE + SEALS

Temp code tree: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.owEFp7EgU9
Built with: `git fetch -q origin main` + `git archive origin/main scripts design/v3/60-listener artifacts/claude-lis319o-20260926 artifacts/claude-readpanel319o-20260926 | tar -x -C $D`

Seal 1 — `shasum -a 256 -c artifacts/claude-lis319o-20260926/SEAL.sha256.txt` (all OK):
```
artifacts/claude-lis319o-20260926/PASSMARKS.md: OK
scripts/claude_lis319o_owner.py: OK
scripts/claude_lis319k_score.py: OK
scripts/claude_lis319_read.py: OK
scripts/claude_lis319_rows.py: OK
scripts/claude_lis319_fullclaim_b.py: OK
scripts/claude_lis300_compiler.py: OK
```

Seal 2 — `(cd artifacts/claude-readpanel319o-20260926 && shasum -a 256 -c SEAL.sha256.txt)` (all OK):
```
panel.jsonl: OK
label_B.jsonl: OK
adjudication.jsonl: OK
WRITER.md: OK
LABELLER.md: OK
ADJUDICATE.md: OK
README.md: OK
AUDIT.md: OK
```
Any failure: none — both seals all OK, continued.

READER = ~/premonition-models/lis319f-merged (`/Users/ben-hannan/premonition-models/lis319f-merged`)
`shasum -a 256 $READER/model.safetensors`:
```
970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b  /Users/ben-hannan/premonition-models/lis319f-merged/model.safetensors
```
Expected: 970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b — match, continued.

Python env (per task): `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1; uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers --with safetensors python -B <script> ...`

## 2. Rows

`python -B scripts/claude_lis319_rows.py --rows artifacts/claude-readpanel319o-20260926/panel.jsonl --out rows.jsonl`
Printed verbatim:
```
rows 240 with history 210
```
Expectation: rows 240 with history 210 — match.

## 3. One read (lis-319f)

`python -B scripts/claude_lis319_read.py --model $READER --rows rows.jsonl --out reads_panel_319f.jsonl`
Printed verbatim:
```
read 240 rows on mps
```
- device: mps
- start (UTC): 2026-09-26T16:10:24Z
- end (UTC): 2026-09-26T16:17:24Z
- wall: 420 sec (7m0s)
- timing stats from reads file (ms field only, no frames quoted):
```
n 240
median_ms 1526.65
mean_ms 1715.4
min_ms 890.0
max_ms 6272.6
```
- reads file: reads_panel_319f.jsonl, 240 rows, 92587 bytes
- Independence: panel.jsonl, label_B.jsonl, adjudication.jsonl never opened/printed/quoted; reads file copied unread (cp only) into artifacts/claude-lis319o-20260926/; stats script printed timing counts only.

## 4. Outputs

- artifacts/claude-lis319o-20260926/reads_panel_319f.jsonl (pushed unread)
- artifacts/claude-lis319o-20260926/RESULTS-read.md (this file)

Temp dir removed: `rm -rf "/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.owEFp7EgU9"` — confirmed gone (ls returns no such file).

## 5. Marks

O1-O4 pending judges.
Report only: correction_right, stale_saves, OLD vs NEW — pending compiler/judge steps (not this read task).

PUSH:
- artifacts/claude-lis319o-20260926/RESULTS-read.md
- artifacts/claude-lis319o-20260926/reads_panel_319f.jsonl
