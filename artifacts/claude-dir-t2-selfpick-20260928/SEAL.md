# T2 seal (the model picks its own replay store)

Sealed 2026-09-28 22:13 UTC (`date -u` at commit) by Director helper "sleep tests sealer" (Claude). What is fixed, in one place. The hashes are in `SEAL-code.sha256.txt` (check with `shasum -a 256 -c` from the repo root; the queue jobs do it).

| sealed file | what it fixes |
|---|---|
| `artifacts/claude-dir-t2-selfpick-20260928/PASSMARKS.md` | every mark, bar, arm, cell, draw, comparator, verdict word, prediction, and the 6-point self-check |
| `artifacts/claude-dir-t2-selfpick-20260928/DESIGN.md` | where each number comes from; jobs; risks |
| `scripts/claude_dir_t12_sleep.py` | the sleeps (T2 arms R16, R16b, PICK, HARD; T1 arms D16, K16, FRESH); imports the sealed fewex harness and distill sleep, edits none |
| `scripts/claude_dir_t12_marks.py` | the marks as code, for T2 and T1 (pure python; selftest 12 cases) |

## State at sealing (checked, not assumed)
- No sleep of any T2 arm has run: this folder has no `sleeps/` and no `PICK`, `HARD` or `R16b` record exists anywhere on main.
- `python3 scripts/claude_dir_t12_marks.py selftest` prints "t12 marks selftest ok: 12 cases" (run here). `python3 -m py_compile` passes for both scripts. **`claude_dir_t12_sleep.py` has never run** (this box has no torch); its `selftest` command runs first in the queue job and any failure is reported, not patched.
- Shared with T1: the R16 records (`dst-t2-1-r16-mac`) and the scripts. T1's seal covers the T1 marks.

## What would make the run VOID
Any of R16, R16b or PICK with fewer than 3 draws in a cell; a start net that is not the ks prep net for its seed; a seal mismatch. A crashed job is re-run unchanged and its crash reported; nothing is tuned.

## Order for the Director
1. `ks-1-lead0` must have written `$HOME/premonition-ks/nets/loop-s{0,1}-pre/{k0,k64,k16384}.pt` (the job says WAITING otherwise; T1 and T2 do not rebuild nets).
2. Release `dst-t2-1-r16-mac` (runs the torch selftest, then 12 R16 sleeps), then `dst-t2-3-r16b-mac`, `dst-t2-2-pick-mac`, `dst-t2-4-hard-mac`. Delete the `STATUS: HELD` line to release. Each is about 40 minutes (inferred), $0.
3. After all four: a separate blind recount from PASSMARKS.md and the raw `sleeps/*.json` only, then `python3 scripts/claude_dir_t12_marks.py report t2`, then RESULTS.md.

## Disclosed changes from the draft `design/research/sleep-design-2026-09-28/TESTS.md`
(1) "8 wrong + 8 right" replaced by the model's own loss ordering (the net scores 0 of 200 after a maze day, so nothing is "right"); (2) bar +15 replaced by measured bars 12 and 16 plus a "which-16" noise rule; (3) "at most 6 loss on the day's kinds" replaced by max(6, 2 x SE) on the 9x9 count and a plain-net floor; (4) comparator = R16 (no-sleep is 0); (5) F_few row added as a k = 64 stand-in.
