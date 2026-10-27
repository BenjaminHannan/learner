---
name: answering-from-memory-line
description: Problem 5 (Answering from memory, row Y1) state 09-27 20:50 UTC: y1t, y1u, y1v (trained doubt on LFM, 39/12/6) all NO-GO; thread stopped by Ben 19:57
metadata:
  type: project
  modified: 2026-09-27T19:32:07.954Z
---

Thread root cmsg_01FuvegZXjMmeUzStiEFVnEW65oqEXkZhiQhmQSKJXceM2 (session_01FvBgkwGgPDpWmFhe9tmkfU). Reports go to the Thread manager [[ben-talks-only-to-thread-manager]].

- DEV check (y1t bars, A1, bank artifacts/claude-e2e331-dev-20260924, 71 asks): GO needs right >= 22 of 56 AND wrong <= 8 AND never-told "I don't know" >= 8 of 10.
- y1g: NO-GO. y1r (trained MiniLM retriever): FAIL, proved wrong (184c59930).
- y1t (LoRA on MiniCPM's own code-graded drafts; items glm2/items GATE-PASS, GLM-written, train 47e2e295, dev c0288f2c): NO-GO 22/20/5 vs plain 26/24/2 (VERIFY-y1t.md e510853fb; vast kit v3 44c385094, RTX 5000 Ada, $0.20). Practice-dev idk 100->136 of 145 (+24.8 pt), proved-wrong not fired. H1 rows in claude-y1tH1-20260926/run are never opened. The BensPC route (y1tpc, 180-y1t-benspc-*) is superseded.
- y1u: plain LFM2.5-1.2B (rev 0f604ada) on the same DEV check, CPU here: 35/18/1 vs same-CPU MiniCPM 26/24/2. NO-GO; proved-wrong not fired (VERIFY-y1u.md f78c2b8d2). LFM C4 was 25/7/6 (report only).
- y1v-20260927 (TM 19:09 "yes, write it"; a test only, LFM as talker is Ben's call): y1t's recipe on plain LFM. Sealed 37d05c9f9 (PLAN, SEAL 6 lines, scripts/claude_y1v_train.py, kit handoff/kit/y1vvast).
  - Wrapper: LoRA on self_attn q/k/v/out_proj only (24 modules, 1.28M params vs MiniCPM's 96 and 4.13M), because the trainer matches child names and LFM names its attention output out_proj.
  - Held jobs handoff/held/rent-y1v-vast-p1..p3 (main 65749a179). Cap $1.00, at most $0.70/h, estimate $0.15 to $0.40. The adapter goes to the Mac at ~/y1v-lfm-adapter (export MAY1T in the job).
  - Asked the Director at 19:35 to release p1 under Ben's 14:05 order. Results land in artifacts/claude-y1v-20260927/run, then VERIFY-y1v.md.
  - RESULT (09-27 20:47, p1 on RTX 5090, $0.41, builder-outbox ce8469eac; VERIFY-y1v.md main a736b34c8): NO-GO. A1 merged 39/12/6 vs plain LFM same card 35/18/1. Proved-wrong not fired (practice-dev idk 22->136/145; DEV +5). Kept 32 of 35. Trained C3 35/8/7 (report only). Sent to TM; thread stopped per Ben 19:57 (no next step chosen).
- TM 19:27 (relayed): Ben chose to swap the talker to LFM2.5-1.2B, so y1v is now the real build candidate for "don't know". The sealed PLAN still says "test only"; no addendum (wording only).
- NAME CLASH: artifacts/claude-y1v-20260926 (+ held rent-0y1v, benspc-y1v, scripts/claude_y1v_judge.py) is an OLDER y1v, the trained yes/no judge, never run. It is not the 09-27 y1v.

**Why:** a later session should not re-derive these.
**How to apply:**
- Run `date -u` in its own call before writing any time into a file.
- Mock-test every rental kit against a fake vast CLI and a fake rental (scratchpad mockv/) before holding jobs.
- The kit's card choice is the best TFLOPS per $/h that fits (Ben 14:05). It destroys only after a manifest-checked copy. Only p1 rents; p2 and p3 go in after a NEXT-PASS-NEEDED note.
- Have a checker recount numbers when counts are large; recount from the rows files yourself when they are small.
