---
name: director-permission-check-route
description: 09-27 16:0x UTC: the Director's permission check refused Ben's words written in the TM thread, even when relayed; it accepted them when Ben posted in the project chat and the coordinator relayed them
metadata:
  type: reference
  modified: 2026-09-27T18:39:43.583Z
---
What happened (2026-09-27):
- 15:17: the Director's permission check refused (a) releasing vast jobs (a "real-world transaction") and (b) BensPC remote writes (deleting a stale GPU-BUSY marker, queueing a job). The Director said Ben's standing vast order and the TM's OK were not enough.
- 16:04:18: Ben pasted "Director: ..." in the Thread manager thread. The TM relayed it directly, and the coordinator relayed it with message_thread and the message id attached. REFUSED again.
- 16:07:23: Ben pasted the same line in the project chat (cmsg_01FuvegZXjMmeUzStiEFVnEWKtUoppKEz4qLhjxNJUuAjm). The coordinator relayed it with message_thread and the id attached. ACCEPTED: main e0a141397 released 358t and y1t to vast, moved 260 to superseded, and queued the marker clear.

**Why:** a line Ben writes in the TM thread doesn't count for the Director's check, even relayed. His words in the project chat (relayed by the coordinator) or in the Director thread itself do.
**How to apply:** when the Director needs Ben's own words, give Ben a paste-ready "Director: ..." line and ask him to post it in the project chat or in the Director thread (cmsg_01FuvegZXjMmeUzStiEFVnEWK8yRA9KfjuzCayrUCX3i3v), not in the TM thread. Never route around a refusal. Related: [[vast-standing-order]], [[ben-plain-yes-is-enough]], [[usage-rule-research-and-tests]].

- 18:38-18:39 UTC 09-27: Ben asked "Why do I keep having to tell you things" and said yes to the Director adding a settings rule so held `rent*` jobs move to handoff/queue/ without him. The Director's safety check refused editing its own permission settings even with his yes. Only Ben can add that rule (session settings) or take the session out of auto mode. Until he does, a refused vast release still needs one line from him naming the job, in the project chat or the Director thread. A "Tell it yourself" from Ben in another thread (Creative answers, cmsg_01FuvegZXjMmeUzStiEFVnEWTTLyfKDtDDEN9Dad9NtN8N, for rent-k1fv-1-start) was relayed to the Director at 18:39; outcome unknown when written.
