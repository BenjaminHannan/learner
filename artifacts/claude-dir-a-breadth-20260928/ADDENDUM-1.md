# Addendum 1 (A)

Written 2026-09-28 21:46 UTC (`date -u`) by the Director before any run, dev score or holdout score of this test, from artifacts/claude-dir-review2-20260928/REVIEW.md section 8 (claims checked: A marks.py:81, ruler stop rule claude_fewex_bench.py:76-78, R2g PASSMARKS:37/39). These change the words a verdict may use and add read-only checks. They never change a number a seed was already judged by, and none can turn a REJECTED into a PASS. Where a rule names a script line to change, the verdict is read by hand from the script's numbers under this rule until a new *_add1 script exists; the sealed script is not edited.

- **A-1 (BM2).** BM2 is judged only when `plain_label` is "few-example" (V1a_plain and V4 true in the dev gate). If the label is "expressivity", BM2 is "n/a", and the kind verdict cannot be PASS; the best word is NOT-SHOWN (no fair plain comparison). In `claude_dir_a_marks.py` `main_pass` and `kind_verdict` must read the label.
- **A-2 (noise, REFUTED).** REFUTED needs gain below 0.0 in both seeds (not below 2.0). The roll-up sentence adds: "the run-to-run noise of one F_eq is estimated at 1.4 to 3.3 points; two source nets were not re-drawn". One extra control is welcome and is not a mark: the two-kind practice with the ten-kind stream base 7100000+seed, same code, reported next to Aloop.
- **A-3 (plain gain).** The roll-up sentence quotes "Bloop minus Aloop" and "Bplain minus Aplain" for each kind, both seeds, side by side.
- **A-4 (neighbours).** The roll-up sentence ends "nearest practised neighbours: multi (rank), compose (graph); leave-out untested".
- **A-5 (V3).** V3 must hold in **both** seeds (change `any` to `all` at `claude_dir_a_marks.py:185`; PASSMARKS:28).
- **A-6 (seal).** Add PASSMARKS.md, DESIGN.md, `claude_dir_h1_marks.py`, `claude_dir_h1_bench.py`, `claude_dir_h1_kinds.py` to `SEAL-code.sha256.txt` and have step 1 of the queue check them.
