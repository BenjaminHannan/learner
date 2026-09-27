# mu-407 run note (written 2026-09-27 03:06 UTC, date -u)

- Not started. The GLM prep job (madeup-mu407-prep-mac) never launched: the Mac's local job slots were full.
- At 03:06 UTC it moved to handoff/held/ (214e69905). The Director reported, from Ben's Mac Claude, that the opencode Go plan hit its usage limit around 00:57 UTC, and this job needs about 80 GLM calls.
- It goes back to handoff/queue/ when GLM calls work again.
- After the data lands:
  1. SEAL-data.
  2. Smoke test on 3 chats.
  3. Talk runs N, U0 and U1 on the "Making things up" container's CPU, about 9 s per turn, 900 turns in all. Each run gets its start time and PIDs here.
