# ch-403 verification (everyday-chat thread, 2026-09-26 16:18 UTC)

Verdict: DEV-FAIL. The sealed practice gate stopped the job before the registered panel, so ch-403 has no panel
result and no pass or fail on M1-M5 or C1. chatpanel403 was never run or opened (rental report; its SEAL checked OK).
Under Ben's Redirect (16:04 UTC) ch-403 is not rerun: recall403 is a rule gate.

Checked here, from the republished files (builder-outbox, copied to this folder):
- sha256 of dev/chat_X.jsonl, dev/chat_X403.jsonl, dev/key_a.json, dev/summary.json match RESULTS-rent.md.
- Rows: X 336, X403 336, each one per (conversation, turn), no repeats (the crashed early attempts left no rows).
- Recount: claude_ch403_run.py score on the DEV chats (artifacts/claude-chatdev-20260926) gives a summary.json
  identical to the rental's.
- Gate, arm X403: notebook events on non-teach turns 6 (bar 0: FAIL); ask_unknown "don't know" 5 of 6 (bar 4: pass);
  released 22 + pretend handed 2 = 24 (bar 5: pass).
- The 6 events are 2 turns with 3 events each (one advice turn, one smalltalk turn). Arm X, without the change, has the
  same 6 on the same 2 turns, so they come from the shared reader, not from ch-403.

Report only (DEV, readable; not judged):
- Stock lines on everyday turns: X 24 (honest 22, pretend 2), X403 1.
- think_split lines on everyday turns: X 17, X403 18. Think questions with a numeric answer: 11 of 27 right in both.
- ask_known right 6 of 8 in both. ms per turn median X 1737.8, X403 1835.3.
- The 21 DEV conversations that differ (pair_a) were not judged: the design drops stock lines anyway (0.2d
  ADDENDUM-12), so the judgement would not change what happens next.

What was wrong on this side: the gate's first bar was absolute (0 events). It should have compared with the unchanged
build (X403 <= X), since the shared reader saves on some non-teach turns. Separately, the job file's push line said
"PUSH to builder-outbox:" where the watcher read only "PUSH:" (watcher now accepts both, 5f6119809).
Cost: about $0.79 of the $1.60 cap (rental report; two hosts lost to a registry proxy outage).
