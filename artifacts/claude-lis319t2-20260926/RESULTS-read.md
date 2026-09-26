# lis-319t2 panel read (lis319t2-panel, Mac, 2026-09-26)

One read of the sealed corrections panel with the lis-319f reader. Code run, never edited.
PASSMARKS read first (origin/main:artifacts/claude-lis319t2-20260926/PASSMARKS.md).

## Seals and reader
- lis319t2 seal (`shasum -a 256 -c artifacts/claude-lis319t2-20260926/SEAL.sha256.txt`, run from the temp tree root): all 4 OK (PASSMARKS.md, claude_lis319_read.py, claude_lis319_rows.py, claude_lis319_fullclaim_b.py).
- readpanel319k seal (`SEAL.sha256.txt` inside artifacts/claude-readpanel319k-20260926): all 8 OK.
- Reader `~/premonition-models/lis319f-merged/model.safetensors` sha256 = 970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b (match, not READER-FAIL).
- Gate: ran after lis319k-panel-mac AND lis319k-devbank-mac-r2 finished (both local RESULTS present; no other reader job running during this read).

## Rows
- `scripts/claude_lis319_rows.py --rows artifacts/claude-readpanel319k-20260926/panel.jsonl --out rows.jsonl` printed verbatim:
  `rows 240 with history 210` (as expected).

## Read
- `scripts/claude_lis319_read.py --model $READER --rows rows.jsonl --out reads_panel_319f.jsonl` printed verbatim:
  `read 240 rows on mps`
- Device: mps. Wall time: 424 s (2026-09-26 15:29:54 UTC to 15:36:58 UTC). Median per-row ms: 1610.9 (median over the 240 per-row ms values; counts-only aggregation, file otherwise unread).
- Reader env: OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1; uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers --with safetensors.
- Panel read exactly ONCE by this reader. Reads file pushed unread (240 lines, counts only).

## Files
- artifacts/claude-lis319t2-20260926/reads_panel_319f.jsonl (240 lines), RESULTS-read.md.
- Temp tree removed.

## Verdict
B1-B3 pending judges.
