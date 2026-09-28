# T1 seal (fresh made-up questions instead of a stored replay)

Sealed 2026-09-28 22:13 UTC (`date -u` at commit) by Director helper "sleep tests sealer" (Claude). Hashes: `SEAL-code.sha256.txt` (`shasum -a 256 -c` from the repo root).

| sealed file | what it fixes |
|---|---|
| `artifacts/claude-dir-t1-fresh-20260928/PASSMARKS.md` | arms, bars (21 and 29 of 200), SIZE (50), gates, comparator (highest of R16, D16, K16), verdict words, predictions, self-check |
| `artifacts/claude-dir-t1-fresh-20260928/DESIGN.md` | numbers' sources, literature, jobs, risks |
| `artifacts/claude-dir-t2-selfpick-20260928/PASSMARKS.md` | the R16 comparator's definition and the shared setup (T1 reads R16 records written under T2's folder) |
| `scripts/claude_dir_t12_sleep.py`, `scripts/claude_dir_t12_marks.py` | the sleeps and the marks as code (same files as T2's seal) |

## State at sealing (checked)
- No FRESH or K16 sleep has run; no `sleeps/` in this folder. Marks selftest passes (12 cases, run here). `claude_dir_t12_sleep.py` never ran (no torch); the queue job runs `selftest` first (it is run once, by the first job that finds no `selftest.json`).
- Disclosed stand-in: FRESH uses code-made fresh puzzles with the pre-maze net's answers as labels; it does not show that a model can write its own questions.

## VOID if
FRESH, K16, D16 or R16 has fewer than 3 draws in any cell; nets are not the ks prep nets; seal mismatch.

## Order for the Director
Needs `ks-1-lead0` nets and the R16 records of `dst-t2-1-r16-mac`. Release `dst-t1-1-k16-mac`, `dst-t1-2-fresh-mac`, `dst-t1-3-d16-mac` (each about 40 to 45 minutes, inferred, $0, delete the `STATUS: HELD` line). Then a blind recount from PASSMARKS.md and the raw records only, then `python3 scripts/claude_dir_t12_marks.py report t1`, then RESULTS.md. Order among T1 jobs does not matter; FRESH is the one that decides.

## Disclosed changes from the draft TESTS.md
(1) bar 20 replaced by measured 21 and 29 and a SIZE row of 50; (2) comparator widened from R16 to the highest of R16, D16, K16; (3) added K16 so the single change is fresh versus stored inputs; (4) "plain-net row not able to do it" made concrete (plain 9x9 floor at k = 64, SIZE row); (5) "generated replay is dead for this net at any cost" withdrawn as too strong; (6) F_few and F_eq rows added as stand-ins at k = 64 and 16,384.
