---
name: made-up-facts-line
description: Thread "Making things up about you" (problem 12: made-up user facts); verdicts mu-402..mu-407; mu-406 withdrawn 09-27 after the LFM talker swap; shared picker
metadata:
  type: project
  modified: 2026-09-27T19:35:00Z
---
Thread cmsg_01FuvegZXjMmeUzStiEFVnEWD2NFAwFWqJa1AU5g4YmQ22, started 2026-09-26 13:00 UTC. H3 CLOSED (Month-end 17:22, VERIFY-02dr.md).
- Diagnosis (artifacts/claude-mu402-20260926/DIAGNOSIS.md): S1's extra claims are 1B-written chat replies (assumed feelings/situations).
- mu-402 FAIL; mu-403 FAIL proved wrong; mu-404 INCONCLUSIVE; mu-405 INCONCLUSIVE (1B ignores SYSTEM-message memory).
- mu-405b (VERIFY.md 00816bdbe, 23:36 UTC, recount exact, $0 CPU): block in the latest USER message (U). VB PASS asks 12 vs N 0; R FAIL not proved wrong (12 vs W 4, needed 14); Q3 PASS = BAD: claim flags U 166 vs W 31 (N 46, H 56), per chat 34/9 p 0.0001, up on every turn kind. Usable memory -> ~5x made-up claims about the user. Sent to Thread manager + Month-end (W_PLACE02D is Month-end's call).
- 09-27 02:51 Thread manager + GPT review (reviews/gpt-reply-memory-confab-2026-09-27.md): ask_right is a SUBSTRING scorer; of U's 12 'right' asks only ~2-4 really answer (unblinded reads). Note added to mu-405b VERIFY (31c296498); verdict words unchanged. RULE: recall marks must need a real answer with correct attribution (blind fit judge, JUDGE-fit407.md); substring = report only.
- mu-407 (label U1 vs U0; no training) = FAIL, not proved wrong (VERIFY 2c1dea000, 09:31 UTC 09-27, blind recount exact; Luna-written chats+frames): C N 44, U0 151, U1 137 (bar 75.5; sign 17/19 p 0.69); real answers 6 vs 7; on-turn non-ask U1 128/240 (bar 192), N 200. Label is NOT a 0.2d fix (sent TM + Month-end). g406b-L (artifacts/claude-g406l-20260927) = PASS 09:25 UTC 09-27 (VERIFY e549ca074; blind recount exact): V 240/240, G1 130/131, G2 0.0124, G3 0.672, not proved wrong; So mu-406 may pick training replies with Luna two-session marks (labeller: Luna gpt-6-luna). mu-406 SEALED fb92c1dee 09:59 UTC 09-27 (PASSMARKS.md, 30 files): distillation (Luna teaching replies), teacher gate on summed flags <=6/200, name check person/pet/place only, M2 floor 15/60, PASS worded 'on Luna-worded DEV chats'. Panel sealed aad8e5941; practice 200+20 on main 2ee0d2fff (56/63 panel ask lines seen in training: split lopsided, told TM). mu-406 got teach 220/220, gate PASS 5d592c0f4 (2/200, 80/80, 20/20), rows 1,000 sealed 3a8f6c0a4, vast kit madeup406v 53860363b (8 fake cases pass; reusable pattern). WITHDRAWN 19:3x UTC 09-27 (RUN-NOTE ef184c081), $0 spent: Ben swapped talker to LFM2.5-1.2B 19:27; c1-dl LFM made-up 3-5/60 (MiniCPM 17, Qwen 30), W block adds none, asks 6/8. Stood down, no LFM fix test; asked Director to move rent406-* to held/superseded; trigger disabled. Caveat: pair-judge side count; 0.2d S1 row should re-measure with JUDGE-claims405. Run log: run/RUN-NOTE.md. Trigger trig_01DBDTMsYDHaKNgmHZ6aRqP1. Luna max 2 at a time.
- g406 (GLM) INCONCLUSIVE, replaced by g406b-L (Luna). Month-end wants mu-406's verdict.
- TRAINING DATA: nothing trained is Claude-written or Claude-judged (Ben 16:39). This thread has trained nothing.
- SHARED PICKER: this thread owns scripts/claude_pick403.py (frozen; changes = new file). Reorder-only, NEVER on the loop, one layer via on_layer().
- Container: nohup jobs die on idle reclaim [[cloud-container-idle-reclaim]].
- BEN'S CHANNEL: reports to the Thread manager (session_01T8RjGifsQdqHsTQnCvPjPr) only; no reply() in own thread; status line 1 "Reports go to the Thread manager, not Ben".
**Why:** a new session must not redo judged tests, re-read TEST-ONLY panels, or rebuild the picker.
**How to apply:** fresh blind judges in private folders, blind recount, verdict to the Thread manager (and Month-end when it touches 0.2d). See [[fix-sleep-line]], [[month-end-results]], [[everyday-chat-line]].
