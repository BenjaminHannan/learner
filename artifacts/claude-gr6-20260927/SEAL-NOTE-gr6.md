# gr-6 sealing note (2026-09-27 01:29 UTC)

Owner: Plain-English puzzles thread. Times from `date -u`. The order PASSMARKS-gr6 fixes was kept:
1. Marks sealed (dc32468b2).
2. The 40 layouts drawn by code (seed 5040) and frozen with the code (SEAL-layouts-code, 0f7679ead): 32 train, 8 dev
   only; 20 put rows on one line, 14 have a header and 4 a divider.
3. The fresh blind writer (no repo, no earlier panel, no training layout) wrote 30 wrappers, 60 lookalikes and 40
   formats; its file was sealed by sha256 (SEAL-writings, 6ba05adae) before the maker read it.
4. The maker (refuses an unsealed writings file) ran the same-format check and made the panel
   (artifacts/claude-panel-gr6-20260927, SEAL-panel). Counts only:
   - formats: 40 written; the first 30 were looked at to keep 20: 9 wrote a row the same way as a training or dev
     layout, 1 the same way as a format kept before it. 17 of the 20 kept formats use a cell separator some training
     layout uses (sep_seen); 3 do not.
   - squares 100 (21 broken; read_latin reads all 100 exactly); unseen 60 (12 broken; read_latin exact 0; token
     clash 0); lookalikes 60, of which **52 are "none" by read_latin (R2's denominator)** and 8 hold a square.
5. Training rows built (train/rows.jsonl): 1398 rows; train 579 none and 493 squares (1072); dev 123 squares and 139
   none; 64 squares in the 8 dev-only layouts. No near miss was read as a square by read_latin (0 dropped). Every new
   square's target goes through gr-4's grammar and parses back to its grid (320 of 320).
6. SEAL-rows-chain: the rows, cpu/chain.sh and the gr-5/gr-4/devclean code the chain calls.

Code checks before sealing (practice data and fake files only, no panel, nothing changed after them): the score code
was run on a made-up 100-row panel; `run` was run with the gr-5 adapter on 2 made-up messages; `dev` was run with
the gr-5 adapter on 4 practice rows (2 held-out new-layout squares, 1 near miss, 1 dev-only-layout square) plus the 30
format-dev messages, to test the code path. The chain's first check was fixed before sealing: SEAL-marks lists a bare
file name, so the chain checks it from inside this folder. The seal file itself is unchanged.
