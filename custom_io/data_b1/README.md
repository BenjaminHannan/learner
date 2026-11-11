# Test B1 training data, built (read-only)

`plan_b.tgz` = the output of `python -m custom_io.english build --teach teach_clean.jsonl --gen gen_matched_94831.jsonl`
(sources from the teacher-data thread, PR #46, in `/mnt/project-files/plan-b/data/`), packed so the PC can get it from
git. It unpacks to `teach/` and `gen/`, each with `train.jsonl` (187,667 rows), `dev/in_dist.jsonl` (the held-out
in-dist slice), `charvocab.json` and `MANIFEST.json`. The manifests' sha256 are recorded in `PASS-MARKS.md` addendum 3.
The same folders are in `/mnt/project-files/plan-b/built/`. No eval row is in it (the adapter's overlap guard).
