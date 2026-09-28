---
name: clock-stamps-from-command
description: Never type a time stamp by hand; let the shell write it with date -u and paste the exact HH:MM:SS output, seconds included (coordinator 00:53 UTC 09-27)
metadata:
  type: feedback
  modified: 2026-09-27T00:54:02.686Z
---
Coordinator note 2026-09-27 00:53:55 UTC, after three window-C clock slips by the Thread manager. Stamps were typed before the `date -u` output was read, or rounded up to the next minute.

**Rule:** never type a time. Log lines are written by the command itself, e.g. `echo "$(date -u +%H:%M:%S) text" >> round-log.md`. A time in a message or file is pasted from that exact output, seconds included, with no rounding.

**Why:** "run date -u first" still failed three times in 30 minutes, because the rounding step stayed. Ben's rule is times from `date -u`, copied verbatim.
**How to apply:** this applies to round-log lines, messages to other sessions, board ledes and batch headers. Related: [[verify-before-ben]], [[model-comparison-0926]].
