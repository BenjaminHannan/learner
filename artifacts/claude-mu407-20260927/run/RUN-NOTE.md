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
- Update 2026-09-27 03:57 UTC (date -u): ADDENDUM-1 (Luna writes chats and frames) sealed in 36e6710b8. The seals verify from an archive (SEAL 22, SEAL-prep 7, SEAL-luna 3, all OK). Job madeup-mu407-luna-mac is queued: a pilot on the frames and 3 smoke chats, then a background write, with 1 Luna call at a time. The GLM job madeup-mu407-prep-mac stays in held and will not run.
- Update 05:51 UTC (date -u): madeup-mu407-luna-mac is still queued. At 05:28 UTC the watcher was holding it behind its Zen-builder cap (4 running). Not launched yet.
- Update 06:43 UTC (date -u):
  - The watcher launched madeup-mu407-luna-mac at 01:57:07 local = 05:57 UTC.
  - Agent pass go1 ended at about 06:30 UTC, and pass go2 was running at 06:38 UTC.
  - No RESULTS yet.
- Update 06:53 UTC (date -u):
  - madeup-mu407-luna-mac finished. Its results were pushed to builder-outbox at 06:41:54 UTC (411d55e94). The pilot
    was PASS; all 78 chats were kept with 0 errors; 0 scan hits; 26 repeated user lines were reviewed and kept.
  - The data is sealed in SEAL-data.sha256.txt (9 files, 612277144), with SEAL-data-NOTE.md.
  - The smoke run started at 06:47:31 UTC on this container's CPU. It covers the 3 smoke chats, arms U1, U0 and N in
    turn, into run/smoke/. Shell PID 2287, talker PID 2293 (U1). torch 2.14.0+cpu, transformers 5.17.0,
    HF_HUB_OFFLINE=1, MiniCPM5-1B snapshot 87179e5c.
  - The worker running this thread was replaced at about 06:50 UTC (the coordinator's note). The smoke process kept
    running.
