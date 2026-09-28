# Addendum 1 (R2g)

Written 2026-09-28 21:46 UTC (`date -u`) by the Director before any run, dev score or holdout score of this test, from artifacts/claude-dir-review2-20260928/REVIEW.md section 8 (claims checked: A marks.py:81, ruler stop rule claude_fewex_bench.py:76-78, R2g PASSMARKS:37/39). These change the words a verdict may use and add read-only checks. They never change a number a seed was already judged by, and none can turn a REJECTED into a PASS. Where a rule names a script line to change, the verdict is read by hand from the script's numbers under this rule until a new *_add1 script exists; the sealed script is not edited.

- **R2g-1.** PASSMARKS:39-40 is read as "Rows 1 and 3 both failing in both seeds is reported NOT PROMOTED; the idea is rejected only by the REJECTED rule (:33-35)".
- **R2g-2 (swap).** "The gain can be read as symmetry" also needs R2g's original dev count >= the loop's original count minus 15 in both seeds.
- **R2g-3 (sleep).** The Director decides now, before job 1, whether the loop's k64 / k1024 / k16384 checkpoints exist (a four-line `ls` on the Mac), and commits the result; a later skip is not allowed.
- **R2g-4 (source guard).** "Source guard fails" reads INVALID-AT-0.3, not REJECTED.
- **R2g-5 (wording).** The PASS sentence adds "tie table and cross mask changed together; table-only variant not run".
- **R2g-6 (seal).** A `SEAL.sha256.txt` in `sha256sum -c` format for PASSMARKS, DESIGN, the six scripts and `claude_dir_h3_report_add1.py`.
