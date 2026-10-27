# R1g (general reach channel): files

Written 2026-09-28 by helper R1G. All files are new; nothing existing was edited. Torch 2.14 (CPU) was installed in a scratch venv outside the repo on the cloud box, so the self-test and the report selftest were really run; no maze was scored and nothing was practised at scale.

| file | what | how far checked |
|---|---|---|
| DESIGN.md | mechanism, what changed from R1, size, risks | text |
| PASSMARKS.md | sealed single-change race entry | text; numbers reproduced by the report script from the raw baseline files |
| scripts/claude_dir_r1g_net.py | plug-in (Net, Practice, Learner) | selftest ok |
| scripts/claude_dir_r1g_selftest.py | CPU self-test, 14 checks | run: selftest-cloud.log ends `"selftest": "ok"` |
| scripts/claude_dir_r1g_practice.py | source practice (copy of the H3 v2 one) | 20-step run OK; full run untested |
| scripts/claude_dir_r1g_credit.py | dev-only credit check and channel-use numbers | run on a fake run folder OK; real run untested |
| scripts/claude_dir_r1g_report.py | dev table and verdict | `selftest` ok; loop F_eq/F_few reproduced |
| scripts/claude_dir_r1g_sleepdraws.py | three-draw sleeps and merge | py_compile only |
| queue-r1g-1-practice.md, -2-dev.md, -3-holdout.md | HELD jobs | bash -n only; not run |
| selftest-cloud.json / .log, report-selftest.log | outputs | shown |
| SEAL.sha256.txt | sha256 of the sealed files (marks, design, scripts) | shown |
