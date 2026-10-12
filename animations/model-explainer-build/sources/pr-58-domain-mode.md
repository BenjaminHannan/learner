# PR #58 body (copied from GitHub, open, 10-09): Domain mode
Title: Domain mode: the model teaches itself a domain (spreadsheets first)

Before: the model learned only from data we prepared. Nothing let it take on a new domain ("learn how to do spreadsheets") by itself.

After: `python -m domain.mode` gives T1SDR 3M a domain tool and its help page, with one worked example per kind. The model then makes its own practice by changing those examples and checks each one with the tool. It keeps tries that match the tool's working and learns from the tool's working on misses. Each night it trains at lr 1e-4 with half self-replay, and it undoes any night that makes its answers to old questions drift. It practises most where its own quiz moves, and stops when that quiz stalls. Every choice comes from the model's own scores, through fixed constants that are the same for every domain (domain/constants.json).

The design and sealed marks (DM1-DM6, plus the A8 "bigger picks better" report) are in domain/DESIGN-AND-MARKS-2026-10-09.md (also at /mnt/project-files/domain-mode/DESIGN-AND-MARKS-2026-10-09.md). The marks were written before any run.

How:
- domain/tools/sheet.py and rpn.py are plain-code tools. Their working is calls to the model's existing outside calculator (calc).
- domain/panel.py generates sealed scoring panels with its own generator and seeds.
- domain/mode.py is the loop, and every decision is logged. --even-mix and --fixed-nights exist only for the A8 control arm.
- Tests: test_tools (10 pass), test_review_fixes (6 pass).
- Before any practice, T1SDR s200 scores 4.67% near and 2.50% far on the sheet panel. The first real run (sheet, seed 200) is running on the cloud CPU.
