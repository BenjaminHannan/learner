---
name: shared-scripts-new-file
description: Don't edit a shared script other threads may have sealed (e.g. claude_lis300_train.py); add a new file or warn owners first
metadata:
  type: feedback
  modified: 2026-09-26T18:14:52.299Z
---
At 17:15 UTC on 09-26 the reading thread edited scripts/claude_lis300_train.py to add a grad-none log line (commit f99793d78). The change was logging only, but Trustworthy notes had sealed that trainer's hash for rd-378k and rd-378g. Its label-gate job stopped with SEAL-MISMATCH, and it re-sealed the trainer at 5f938199b.

**Why:** jobs seal the hashes of the scripts they run, so even a harmless edit to a shared script stops other threads' jobs.

**How to apply:**
- Before changing a script another thread might use, grep handoff/ and artifacts/*/SEAL* for its path.
- If anything seals it, make the change in a new file (for example claude_<x>_v2.py) or warn the owners first with send_message.
- This follows the additive-files rule in the project rules.
