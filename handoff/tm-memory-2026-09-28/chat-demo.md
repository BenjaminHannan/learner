---
name: chat-demo
description: Ben's local chat page for Premonition (exp 260 base) at http://127.0.0.1:8765 on his Mac; flags arrive on branch chat-flags
metadata:
  type: project
  modified: 2026-09-23T04:17:31.532Z
---
Built 2026-09-23 ~03:59 UTC by builder chat-demo-build (thread cmsg_01FuvegZXjMmeUzStiEFVnEW3og6MfV5dymA5MZPHTixez). Code on main: scripts/claude_chatdemo_{server.py,page.html,start.sh}; selftest artifacts/claude-chatdemo-20260923/selftest.md.
- Runs the exp 260 base (138m + openers), no ear v4.1 (261 FAIL). The notebook lives in ~/premonition-chat/state; "New notebook" moves the old one to ~/premonition-chat/old/.
- launchd agent com.premonition.chat (KeepAlive, starts again at login). macOS privacy settings block launchd from ~/Desktop, so it runs a verbatim copy in ~/premonition-chat/runtime with a venv at ~/premonition-chat/chatdemo-venv. A new base means refreshing that runtime copy.
- Ben's flagged exchanges get pushed to branch chat-flags (flags.jsonl). Line 1 is the BUILDER TEST flag. Nothing else he types is pushed. The transcript stays on the Mac.
- Weak-spot probe: artifacts/claude-chatweak-20260923/WEAKSPOTS.md (52/90 OK, 0 wrong saves). These are leads for sealed experiments only.

**How to apply:** when Ben flags something, read origin/chat-flags and turn it into leads. Never tune on it directly.
