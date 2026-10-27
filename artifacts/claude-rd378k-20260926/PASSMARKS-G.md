# rd-378k addendum G (2026-09-26 20:09 UTC): the opencode helper v1.1, before gate3oc runs

Written before rd378k-gate3oc has run (it is held; no opencode grade exists). PASSMARKS.md and addenda B-F stay as
sealed; this file adds to them.

The Director's helper v1 (scripts/claude_glm_opencode.py, sha256 3b597086...) leaves one opencode session behind per
call: its cleanup compares session lists inside the call's temp dir, but opencode files sessions under the enclosing
worktree, so the comparison is always empty (builder-outbox cd1bf6977: 150 calls left 150 sessions, 0 errors at 16 in
parallel). That is the only reason for this change; v1's replies were fine. v1.1 (scripts/claude_glm_opencode_v11.py,
sha256 7a067cfba8fd147f342d46ed71449ab3e065c46eee3615a9b263a22da5c708c4) tags each call's session and deletes exactly
that one; same call() interface and reply text. gate3oc runs claude_rd378k_teacher3oc.py unchanged under
scripts/claude_glm_v11_run.py, which binds the helper's module name to v1.1. Rows, bars, dialogs and the rule after the
result are addendum F's. It runs as one process (the Thread manager's opencode share for this thread is 2 in parallel).
