# Creative prototype v2: review notes (2026-10-03)

Raw reports behind `../creative-prototype.md` (v2). All are design-only Opus subagent outputs; nothing was trained or run on a GPU.

| File | What |
|---|---|
| FACTS.md | The facts pack every reviewer started from (task, rules, system, code facts) |
| critic-report.md | Adversarial review of v1 (15 defects, 5 fatal) |
| fresh-design.md | Independent from-scratch design, written without reading v1 or the critic |
| math/math-report.md | CPU-only maths: puzzle counts, exact random-policy floors, word-problem floors, power tables. Scripts and JSON results beside it; `validate_tool.py` drives the real `execute_integer_call` |
| v2-check.md | Independent Opus check of v2 against the sources |

v1 is in git history (commits 28cf37fd8 to ede7b3546 on this branch). Paths inside the reports point to a scratch folder; the files referred to are the ones in this folder, the integrated design text (commit c5cfd9176 on `claude/premonition-launch-recovery-96c708`) and the pipeline code on `claude/critical-thinking-data-128-outputs`.
