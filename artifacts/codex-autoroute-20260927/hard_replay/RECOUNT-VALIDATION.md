# AR2 recount synthetic validation

- UTC: 2026-09-27 14:53:49 UTC
- Machine: MacBook-Pro
- Test process PID: 65587
- Command: `/Users/ben-hannan/premonition-chat/chatdemo-venv/bin/python -B test_recount.py > test_recount.log 2>&1`
- Result: six tests passed in 0.313 seconds; details in `test_recount.log`.

The tests use temporary synthetic fixtures inside `hard_replay/` and stub the checker API. They cover the registered stop rule, exact kind and size budgets, panel seeds and uniqueness, raw stream scoring and corruption, context agreement, required source paths, and the pushed registration document. The temporary fixtures were removed by the test harness. No model was constructed, checkpoint loaded, MPS inference run, or scientific panel generated. Full checkpoint replay remains for the parent after training.
