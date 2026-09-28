---
name: everyday-chat-line
description: Everyday-chat thread (0.2c row C1): c1-dev (MiniCPM talker) fails C1 vs Qwen/LFM; c1-dl (LFM talker + W block) meets C1 on practice chats, LFM mark exactly at the bar
metadata:
  type: project
  modified: 2026-09-27T14:46:01.940Z
---
Owner: Everyday chat thread (root cmsg_01FuvegZXjMmeUzStiEFVnEW5eSpJqUgzbPJR7QkE4QRwC). Problem: 0.2c C1 = X 30 vs T 30 (bar 40/60), a registered FAIL.

- Diagnosis artifacts/claude-ch403-20260926/DIAG.md: 46 stock lines on everyday turns; X won 18-10 without them. Explainer for Ben: https://claude.ai/artifact/2Xo7spiAFkWBph2dDYLxfK
- ch-403 DEV-FAIL 09-26 16:02 (vast ~$0.79): gate "0 saves on everyday turns" 6 vs 0, but unchanged X also had 6 (VERIFY-ch403.md). Lesson: gate bars vs the unchanged arm. Panels chatpanel403/404 never run.
- Redirect (Ben 16:04): ch-403b/404 stopped. C1 is a 0.2d row vs rivals; C1 scorer sealed 6f6a6e17d (scripts/claude_c1rival_run.py): build vs T/Q/L twin rivals, seeds 4061-4063, bar margin >= -12 per rival (02d ADDENDUM-14); chatpanel404 is 0.2d's C1 panel.
- c1-dev (TM 00:19 09-27; report only, DEV practice chats, not chatpanel404): arms D (0.2d talker alone, scripts/claude_c1dev_talker.py), T, Q, L; noise via claude_c1dev_noise.py. Sealed e4fae451a; SEAL-2 097938ff8. Main's claude_e2e02d.py changed after SEAL-2 (ADD-46/49, talker path same with SLEEP02D off): runs must use the tree of 62a5944c8.
  - BensPC: BASH-ONLY kit handoff/kit/c1devpc (pin 62a5944c8), passes handoff/held/190-c1dev-benspc-bo-p1..p3 (ADDENDUM-1).
  - Vast (Director 14:15 09-27, Ben's vast order): kit handoff/kit/c1devv pinned d0072550e, ADDENDUM-2-vast, SEAL-kit-vast; held jobs rent-c1dev-1-start + 2..4-collect (b25eb918a); $1.50 stop, task cap $2; out run-vast/ + RESULTS-vast.md. Sent to TM 14:45 and Director 14:46; release after TM check. Only one of BensPC/vast may run (BensPC passes don't check run-vast).
  - RESULT 17:24 UTC 09-27 (RESULTS.md, main dc29132b0; vast 4090 $0.87, destroyed): D vs T 27-26-7 (+1 PASS), vs Q 3-57 (-54 FAIL), vs L 0-60 (-60 FAIL); C1 NOT met on practice chats, prediction confirmed; blind recount matched (worker needed a redo to apply key[id][int(winner)-1]). ask_known right D 0/8, T 0, Q 6, L 4. Verdict sent to TM.
- c1-dl (TM 17:22-17:24 09-27, marks OK'd): arm DL = arm D's command with --gen-model = pinned LFM2.5-1.2B (no code change; LFM template takes the system W block). Judged vs c1-dev's T/Q/L chats (reused, 5a34cce3d). RL (DL vs L) main, RT, RQ; bar -12; prediction RL level, RT ahead, RQ holds. Sealed 19af6d294 (artifacts/claude-c1dl-20260927/PLAN.md), kit handoff/kit/c1dlv, held rent-c1dl-1-start + 2..3-collect (7f2a66b5c); $1.00 stop, $1.50 cap. RAN 18:12 (4090, $0.23, destroyed). RESULT 19:25 UTC (RESULTS.md, main 3b5717258): DL vs L 22-34-4 (-12, PASS exactly at bar, p 0.14), vs T 57-3 (+54), vs Q 33-26-1 (+7); C1 met on practice chats; prediction confirmed; blind recount matched. ask_known DL 6/8 (L 4). Verdict sent to TM. Talker swap is Ben's call.
- Found 14:37 09-27: 358u vast rental had no guard (launch ssh hang) -> [[vast-launch-ssh-hang]].
- Later: when 0.2d runs, check its C1 packets/marks with claude_c1rival_run.py. See [[never-read-blind-agent-transcripts]], [[month-end-results]].
