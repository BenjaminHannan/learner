# k1h ADDENDUM 2: GLM calls go through helper v1.1, 2 at a time (Creative answers in chat thread, written 2026-09-26 20:13 UTC)

Written before any k1h chat or answer exists. It changes how the GLM calls are made, and nothing else. Registered
FAILs stay FAILs.

## What happened to the first launch
The Mac job k1h-glm was launched at 19:39:43 UTC (the watcher log, per the Thread manager) on GLM helper v1
(scripts/claude_glm_opencode.py, sha256 3b597086...), 4 calls at once. At 20:01 I held it, because v1 leaves one
opencode session behind per call and k1h's share of the opencode budget is 2 calls at once. The Director's
000-stop-k1h stopped it by exact PID during the chats step: its output folder was empty, with 0 chats and 0 answers,
and only a partial log remained (artifacts/claude-stop-k1h-20260926/REPORT.md on builder-outbox). Nothing from that
launch is used. There are no rows from helper v1. Had there been any, they would be recorded for bookkeeping only: v1
calls share nothing across calls, and its leak left sessions behind and deleted nothing, so the route would not be a
reason to treat a row as suspect (the Thread manager's point, 20:09 UTC).

## The change (route only)
- Every GLM call goes through scripts/claude_k1h_glm_v11.py: it runs the sealed scripts/claude_k1h_glm.py unchanged,
  with its call function replaced by scripts/claude_glm_opencode_v11.py's call (sha256 7a067cfba8fd147f342d46ed71449ab3
  e065c46eee3615a9b263a22da5c708c4; the Director's artifacts/claude-glm-helper-v11-20260926/REPORT.md: every one of its
  17 test sessions was deleted and none was left).
- At most 2 calls at once (the wrapper refuses more): k1h's share of the Director's opencode budget of 16.
- Each call may take up to 600 s instead of 300. When the first launch was stopped, one 20-chat writing call had run
  4 min 58 s.
- Order of the same commands: the 240 k1e chats are answered first, then GLM writes the new chats, then those are
  answered (the answer step resumes and skips answered chats). The job's cap is 8 hours; if it stops early, the rows
  so far are pushed and a resume job continues from them.

## What does not change
The model (opencode-go/glm-5.3-flash), the chat-writing and answer instructions, the parsing, the 36 chat calls and
their subject areas, the code filters, gates 1 to 3 (DATA-GATE-k1h.md), the size floor, the training recipe, the arms,
the panel, the marks and the scope (ADDENDUM-1-scope.md).
