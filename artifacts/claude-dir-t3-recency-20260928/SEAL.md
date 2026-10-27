# T3 seal (newer-weighted rehearsal across three nights)

Sealed 2026-09-28 22:13 UTC (`date -u` at commit) by Director helper "sleep tests sealer" (Claude). Hashes: `SEAL-code.sha256.txt`.

| sealed file | what it fixes |
|---|---|
| `artifacts/claude-dir-t3-recency-20260928/PASSMARKS.md` | arms S, U, W, weights, draws, bars (24 of 400 grids), gates G1 to G5, integrity flags, verdict words, predictions, self-check |
| `artifacts/claude-dir-t3-recency-20260928/DESIGN.md` | numbers' sources, jobs, risks, next steps |
| `scripts/claude_dir_t3_recency.py` | the run and smoke; imports `claude_slp358n3_nights.py` (sealed by slp-358n3, 18 of 18 hashes checked by the job) and edits nothing |
| `scripts/claude_dir_t3_marks.py` | the marks as code (pure python; selftest 9 cases) |

## State at sealing (checked)
- No T3 run exists (no `runs/`, no `dirt3-seed*.json` on main). Marks selftest passes (9 cases, run here). The weight and night-index logic was tested in pure python (S puts 100% on the current night, U 33/33/33, W 14/29/57 over 70,000 draws). `claude_dir_t3_recency.py` has only been py_compiled: **it never ran** (no torch here); the first BensPC step after the seals is `smoke`, and any failure is reported, not patched.
- Disclosed: H6's nights repeat the same two kinds, so T3 adds a night memory and tests weights on those kinds (PASSMARKS "Disclosure"); F_few is not applicable in this harness (no maze).

## VOID if
INTEGRITY flags false; fewer than 3 seeds finished all arms, draws and nights; seal mismatch.

## Order for the Director
Inputs: the 4 Mac checkpoints (`000-bash-h7-dirh6-inputs` prints "4 of 4 Mac checkpoints match their seals"), BensPC free (GPU-BUSY.txt) with CUDA torch. Release `dst-t3-1-s13-benspc` first (sets up BensPC, seals, CUDA check, smoke, seed 13), then `-2-s14`, `-3-s15`, `-4-s16` (each 40 to 90 minutes, inferred; cap 150). $0. Then a blind recount from PASSMARKS.md and the raw JSONs only, `python3 scripts/claude_dir_t3_marks.py report`, RESULTS.md. If BensPC cannot run it and Ben allows a rental under $0.50, note the H6 vast kit pattern (`handoff/kit/sleeph6r`); that is the Director's call, none is built here.

## Disclosed changes from the draft TESTS.md
(1) Nothing to weight in the original nights, so a night memory is added and the weights are the only difference (S / U / W dose); (2) bar 20 on both kinds replaced: sums have 12 to 24 of 400 left, so sums is a no-harm gate and grids carries a 24-of-400 bar; (3) fair comparator = the higher of S and U; (4) plain-net row = N + 40 floor (no plain same-size net in this harness); (5) F_few not applicable; (6) 3 draws per arm for the margin.
