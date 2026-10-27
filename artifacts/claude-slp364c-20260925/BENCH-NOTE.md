# slp-364c bench note (written when the bench was sealed, before the run)
Bench written by a separate agent. Its self-check passes 20/20 faults and 20/20 honest nights (bench_check.json).
It made two fixes before the check passed: slp364c-16 (an extra world fact stopped learning episodes from queuing) and
slp364c-06 (two corrections landed on the same person). Only those cases were re-run.
Blindness slip, reported by the agent: while listing the scratchpad it ran `head` on scratchpad/dev364c.py (my dev
script), which shows how the gate is installed and the names of its result fields, not how any check works. It
says no fault design came from it. Recorded here; the bench is used as written.
