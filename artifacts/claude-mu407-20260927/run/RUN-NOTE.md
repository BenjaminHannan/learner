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
- Update 07:00 UTC (date -u):
  - Smoke done, 06:47:31 to 06:59:26 UTC, exit 0 for each arm. Each arm gave 15 rows on the 3 smoke chats, with 0
    empty replies. Median seconds per turn: U1 6.5, U0 7.3, N 6.0. Files are in run/smoke/. The smoke chats are
    never among the 60, and these rows are not judged.
  - Full run started at 06:59:41 UTC, after SEAL and SEAL-data re-checked OK. Arms run U0, then U1, then N, on the 60
    panel chats, into run/talk_<arm>.jsonl with logs in run/log<arm>.txt. Shell PID 3314, first talker PID 3321 (U0).
    Each arm writes its file only when it ends. At about 7 s per turn, 900 turns is about 1 h 45 min plus loading
    (an estimate).
- Update 08:23 UTC (date -u):
  - Arm U0 ended at 07:47:40 UTC, exit 0: 60 chats, 300 rows, median 8.2 s per turn. run/talk_U0.jsonl and
    run/logU0.txt are committed now. I have not read any reply; the judges read them blind.
  - Arm U1 started at 07:47:40 UTC and was at 44 of 60 chats at 08:19 UTC. N follows. My estimate for the end of N
    is about 09:25 UTC.
- Correction (08:24 UTC, date -u): the "Update 08:23 UTC" line above was typed ahead of the clock. It was committed at 08:22:42 UTC (a2b9585f3).
- Update 08:44 UTC (date -u): arm U1 ended at 08:34:52 UTC, exit 0: 60 chats, 300 rows, median 7.1 s per turn. talk_U1.jsonl
  and logU1.txt are committed now. Arm N started at 08:34:52 UTC and was at 12 of 60 at 08:44. The talk script's own
  last line prints mu-405's substring count, and I saw it for U0 and U1. It is report-only and decides no mark. I have
  read no reply.
- Update 09:18 UTC (date -u): arm N ended at 09:18:38 UTC, exit 0: 60 chats, 300 rows, median 6.2 s per turn. All three arms have 300 rows, 60 chats and 0 empty replies. Next: judge packets.
