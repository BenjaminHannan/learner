# mu-407 run note (written 2026-09-27 03:06 UTC, date -u)

- Not started. The GLM prep job (madeup-mu407-prep-mac) never launched: the Mac's local job slots were full.
- At 03:06 UTC it moved to handoff/held/ (214e69905). The Director reported, from Ben's Mac Claude, that the opencode Go plan hit its usage limit around 00:57 UTC, and this job needs about 80 GLM calls.
- It goes back to handoff/queue/ when GLM calls work again.
- After the data lands:
  1. SEAL-data.
  2. Smoke test on 3 chats.
  3. Talk runs N, U0 and U1 on the "Making things up" container's CPU, about 9 s per turn, 900 turns in all. Each run gets its start time and PIDs here.
- Update 03:16 UTC (date -u), after the Director's 03:16 UTC note. claude_glm_opencode_v11 returns stdout on exit 0, so a usage-limit notice could come back as a reply.
  - In this prep, such text cannot pass as data. Chats must be JSON that passes check_chat (claude_mu407_prep.py:112-131, including all 3 code-picked values in session 1). Frames must be JSON with the four keys that passes check_frames (:134-143).
  - Even so, before SEAL-data I will scan raw.jsonl, the panel and frames.json for error or limit wording, and for any user message repeated across 3 or more chats. The counts go in SEAL-data's note. This check changes no mark.
