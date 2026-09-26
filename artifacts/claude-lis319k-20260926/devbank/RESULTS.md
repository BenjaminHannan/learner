# lis-319k devbank read (lis319k-devbank, Mac, 2026-09-26)

DEV only (the e2e331 dev bank). No TEST-ONLY panel touched. Code run, never edited.
REQUEUE of lis319k-devbank-mac: step-1 archive adds design/v3/60-listener (claude_lis300_compiler reads relation-names.txt). Ran after lis319k-panel-mac finished (one reader job on the Mac at a time).

## Seals and reader
- Reader `~/premonition-models/lis319-merged/model.safetensors` sha256 = e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76 (match, not READER-FAIL).
- e2e331 dev seal (`shasum -a 256 -c SEAL.sha256.txt` inside artifacts/claude-e2e331-dev-20260924): turns.jsonl OK, truth.jsonl OK, README.md OK (all OK).

## Rows
- `scripts/claude_lis319k_devbank.py rows --run artifacts/claude-e2e330-dev-20260924/run/arm_G.jsonl --out rows.jsonl` printed verbatim:
  `{"missing_run_row": 0, "teach": 59, "correct": 10, "rows": 69}` (as expected: teach 59, correct 10, rows 69, missing_run_row 0).

## Read
- `scripts/claude_lis319_read.py --model $READER --rows rows.jsonl --out reads_devbank.jsonl` printed verbatim:
  `read 69 rows on mps`
- Device: mps. Wall time: 157 s (2026-09-26 15:22:05 UTC to 15:24:42 UTC). Median per-row ms: 2083.9 (median over the 69 per-row `ms` values in reads_devbank.jsonl; 69 lines).
- Reader env: OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONUTF8=1; uv run --offline --no-project --python 3.12 --with torch --with numpy --with transformers --with safetensors.

## Classify
- `scripts/claude_lis319k_devbank.py classify --rows rows.jsonl --reads reads_devbank.jsonl --out classes_all.json` printed verbatim:
  `{"below_bar:ASSERT:0.95-0.98": 6, "below_bar:ASSERT:0.98-0.995": 17, "below_bar:ASSERT:<0.95": 21, "below_bar:CORRECT:0.95-0.98": 1, "below_bar:CORRECT:<0.95": 4, "compiler_reject:ASSERT": 11, "not_read": 37, "saved": 34}`
- classes_all.json: facts 131 (saved 34, not_read 37, compiler_reject:ASSERT 11, below_bar ASSERT<0.95 21 / 0.95-0.98 6 / 0.98-0.995 17, below_bar CORRECT<0.95 4 / 0.95-0.98 1).
- `scripts/claude_lis319k_devbank.py classify ... --out classes_y1.json --facts dev01-f04,... (52 facts)` printed verbatim:
  `{"below_bar:ASSERT:0.95-0.98": 2, "below_bar:ASSERT:0.98-0.995": 6, "below_bar:ASSERT:<0.95": 10, "below_bar:CORRECT:0.95-0.98": 1, "below_bar:CORRECT:<0.95": 3, "compiler_reject:ASSERT": 4, "not_read": 16, "saved": 10}`
- classes_y1.json: facts 52 (saved 10, not_read 16, compiler_reject:ASSERT 4, below_bar ASSERT<0.95 10 / 0.95-0.98 2 / 0.98-0.995 6, below_bar CORRECT<0.95 3 / 0.95-0.98 1).

## Files
- artifacts/claude-lis319k-20260926/devbank/reads_devbank.jsonl (69 lines), classes_all.json, classes_y1.json, RESULTS.md.
- Temp tree removed.
