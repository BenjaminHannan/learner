# lis-319k panel read (lis319k-panel, Mac, 2026-09-26)

One read of the sealed corrections panel with the lis-319 reader. Code run, never edited.
PASSMARKS read first (origin/main:artifacts/claude-lis319k-20260926/PASSMARKS.md).

## Seals and reader
- lis319k seal (`shasum -a 256 -c artifacts/claude-lis319k-20260926/SEAL.sha256.txt`, run from the temp tree root): all 4 OK (PASSMARKS.md, claude_lis319k_score.py, claude_lis319_read.py, claude_lis319_rows.py).
- readpanel319k seal (`SEAL.sha256.txt` inside artifacts/claude-readpanel319k-20260926): all 8 OK.
- Reader `~/premonition-models/lis319-merged/model.safetensors` sha256 = e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 (match, not READER-FAIL).
- Gate: lis319k-devbank-mac finished first (queue shows .go1.done, exit rc=0); no other reader job ran during this read.

## Rows
- `scripts/claude_lis319_rows.py` printed: `rows 240 with history 210` (as expected).

## Read
- `scripts/claude_lis319_read.py` printed: `read 240 rows on mps`.
- Device: mps. Wall time: 423 s. Median per-row ms: 1579.6 (median over the 240 per-row ms values; counts-only aggregation, file otherwise unread).
- Panel read exactly ONCE. Reads files pushed unread (240 lines each, counts only).

## Bar rewrite
- `scripts/claude_lis319k_score.py bar --reads reads_panel.jsonl --out reads_panel_new.jsonl` printed verbatim:
  `{"reads": 240, "mode_facts": 30, "raised": 8}`

## Deviation
- Step 4 first failed with FileNotFoundError for `design/v3/60-listener/relation-names.txt`: the step-1 archive paths omit it, but `scripts/claude_lis300_compiler.py` (line 23, unedited) reads it relative to the tree root. Added only that data path to the temp tree (`git archive origin/main design/v3/60-listener`, from the worktree). No code file touched; seals unaffected (checked before the addition); panel still read exactly once (step 3 ran once, before this).

## Verdict
K1-K4 pending judges (scored later from this one read by the reading thread).
