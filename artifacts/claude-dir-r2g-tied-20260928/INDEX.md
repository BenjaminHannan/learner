# R2g tied-directions design: files (written 2026-09-28 21:31:43 UTC, `date -u`)

All files are NEW. No sealed or existing file was edited. This INDEX cannot hash itself.

| file | what | sha256 |
|---|---|---|
| `artifacts/claude-dir-r2g-tied-20260928/DESIGN.md` | design note: general form, what is learned vs fixed | `d660f91e429d81c8c36be3423031c0dc555ef0d619c62fc0f7efbfa68ed7869d` |
| `artifacts/claude-dir-r2g-tied-20260928/PASSMARKS.md` | sealed race entry (marks, proved-wrong, credit checks) | `9b2921c44839e5a87dccd4cad5de9d5287300f86512b48134db78114876e3a87` |
| `artifacts/claude-dir-r2g-tied-20260928/eli5.html` | plain-words page for Ben (published: https://claude.ai/artifact/8UtgyrKYjUXYtsyBRMugp9) | `caaae7e469a1205921606a047ee510cf09efc5b29bf3706f9758b5c364417064` |
| `artifacts/claude-dir-r2g-tied-20260928/selftest.json` | CPU selftest output, 60-step smoke (torch 2.14.0+cpu), ends selftest ok | `a2a62e0e48b4fa7d10bba758afbe15481cfa4e1f41f891825fa75a2e771527f6` |
| `artifacts/claude-dir-r2g-tied-20260928/harness-selftest.log` | harness selftest with --plugin claude_dir_r2g_net (pool and panel checks) | `4c3f69b0c8c2d222bb917812bc9e587d5f4152e89ddeddb838be121b882d94ef` |
| `artifacts/claude-dir-r2g-tied-20260928/queue-r2g-1-practice.md` | job 1: selftests, source practice both seeds, source guard (HELD) | `5321002f7c37f56916a6544cdc29cd65b6d80f1f7ed8df5d5a0df18ff9309bfc` |
| `artifacts/claude-dir-r2g-tied-20260928/queue-r2g-2-dev.md` | job 2: four dev ladders, dev table, swap and tie checks (HELD) | `ac239ee5ee68969d56e7b6896543ca0bfcd98ebb051a957a9f5564ea708049c1` |
| `artifacts/claude-dir-r2g-tied-20260928/queue-r2g-3-sleepdraws.md` | job 3: three sleep draws per side (HELD) | `035ef6cb0b7aa79fae6eb11182f6ce0fd2b5fb709fc859e16087539b274da491` |
| `artifacts/claude-dir-r2g-tied-20260928/queue-r2g-4-holdout.md` | job 4: holdout once, verdict (HELD) | `424868fa4380c8c994bb727a529fc84304922d8c2de14d743c02c193838472a6` |
| `scripts/claude_dir_r2g_net.py` | the plug-in (Net, Practice, TiedBlock, layout-general tied_bias and cross_far) | `1b1051d36f4144beb42f9b4960b5d862af247607a024f6c92a7dbe2dc96314f8` |
| `scripts/claude_dir_r2g_selftest.py` | CPU selftest (11 checks) | `6c76f05a048c6ae04aeaf62af2ca2d22ffcc07d534f6017201a9e707ecc7e41e` |
| `scripts/claude_dir_r2g_practice.py` | source practice (copy of H3 v2 practice with this plug-in) | `baabeaae72ea720463700264d07db821742c50f19b27d162b3bf7e1f31a63f9e` |
| `scripts/claude_dir_r2g_sleepdraws.py` | three-draw sleep driver (the one H3 ADDENDUM-1 (b) planned) | `3539c091e24e1bbd33cf37c2dfe07ac75e01959225ecb12dff23037f465eba46` |
| `scripts/claude_dir_r2g_swapcheck.py` | dev-panel transpose credit check | `5db9da4bcbc379841cc0cb5064e5148b6c13c13d1977357773bdd009c3b752f9` |
| `scripts/claude_dir_r2g_report.py` | verdict wrapper over claude_dir_h3_report_add1.py | `f749e7bdd9c25593c700a01781d82fac7bbade984f1d7447eeb2f1be496e0d12` |

## What ran (shown) and what did not (untested)
- Ran on CPU (torch 2.14.0+cpu, this box): `claude_dir_r2g_selftest.py` (all 11 checks, ends "selftest": "ok", output in selftest.json), `claude_dir_r2g_swapcheck.py selftest` (ok), `claude_dir_r2g_report.py selftest` (ok; reads the baseline's raw JSON and reproduces 51.00 / 51.29 and F_few 13.83 / 16.17), the harness selftest with this plug-in (support pools and panels).
- Plumbing runs with a random-init net and a 2-update sleep (`swapcheck score`, `sleepdraws`): both ran and draw 0 repeated exactly, but a random net scores 0 of 300 and 0 of 200 everywhere, so this shows the code path and determinism only, not real scores.
- NOT run: any practice, source guard, adaptation ladder, sleep draw, or maze score of this design. All queue jobs are STATUS: HELD.
