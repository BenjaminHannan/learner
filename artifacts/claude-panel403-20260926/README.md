# chatpanel403 (TEST-ONLY, sealed 2026-09-26)

60 conversations, ids chat403-01..60, written blind by three separate writers (plus one fresh writer for 58-60,
see artifacts/claude-ch403-20260926/PASSMARKS.md, Disclosure) from design/v3/30-modes/338-chat-panel-spec.md and the
chatpanel382 section of 382-panels-spec.md, names N-Z; blind audited (escrow /mnt/project-files/escrow-403/chat/
AUDIT.md and AUDIT-v3.md) and copied here unread. Never read, quote, train or tune on it. Only the ch-403 runner,
scorer and blind judges open it. Run once.

Checker (scripts/claude_chatdev_check.py, counts only):

```
{"conversations": 60, "turns": 331, "kinds": {"smalltalk": 51, "advice": 78, "followup": 48, "think": 36, "explain": 59, "feelings": 33, "teach": 13, "ask_known": 7, "ask_unknown": 6}, "share": {"smalltalk": 15.4, "advice": 23.6, "explain": 17.8, "feelings": 10.0, "followup": 14.5, "think": 10.9, "teach": 3.9, "ask_known": 2.1, "ask_unknown": 1.8}, "conv_teach": 13, "conv_ask_known": 7, "conv_ask_unknown": 6, "problems": {}}
CHECK OK
```

Seal: SEAL.sha256.txt (sha256sum -c from this folder).
