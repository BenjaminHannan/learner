# c1-dev re-seal 2 (2026-09-27 12:19 UTC, before any run)

At the 12:18 UTC check, `sha256sum -c SEAL.sha256.txt` failed on one line: scripts/claude_e2e02d.py. Month-end changed it in
252e07a2a (0.2d ADDENDUM-43), adding three lines to the module docstring, which now names stand-in E1. Its code is otherwise
unchanged: the parsed module with the docstring removed is identical at e4fae451a and now. W_PLACE02D is still "system".
The c1dev talker selftest passes 6/6, and the 0.2d wiring selftest passes 18/18.

SEAL-2.sha256.txt covers the same 24 files as SEAL.sha256.txt. Only the claude_e2e02d.py line differs. The job
(handoff/queue/k2-c1dev-benspc.md) now checks SEAL-2. PLAN.md and its marks are unchanged, and SEAL.sha256.txt stays as the
record.
