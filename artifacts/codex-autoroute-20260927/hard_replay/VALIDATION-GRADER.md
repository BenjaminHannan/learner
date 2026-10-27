# AR2 grader software validation

Ran 2026-09-27 14:53:32 UTC on MacBook-Pro, PID 65546, using the installed
`/Users/ben-hannan/premonition-chat/chatdemo-venv/bin/python -B`.
Command: `python -B artifacts/codex-autoroute-20260927/hard_replay/test_grade_results.py`
with the installed Python path above. Raw output is in `software-grade-tests.log`.

All **11 synthetic software tests passed**. They cover the five registered
verdicts; missing, incomplete, erroneous, raw-only, and score-mismatched full
recounts; zero-mismatch checkpoint replay; phase size totals and the candidate's
grid5-only B/C replay; and refusal to overwrite existing CLI reports. Temporary
JSON fixtures were created and removed within this `hard_replay` folder. The
test imports only the grader and standard library; it does not construct or
evaluate a model, generate puzzle panels, or run scientific training.

This validation checks grader logic against synthetic records. The independent
prediction recount and actual MPS trajectories remain separate registered work.
