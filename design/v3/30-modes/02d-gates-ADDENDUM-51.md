# 0.2d gates, ADDENDUM-51: the talker becomes LFM2.5-1.2B-Instruct. Written Sun Sep 27 19:30:43 UTC 2026, before any seal

Month-end. Additive only. No 0.2d code is sealed and nothing has run.

## Ben's yes (goals :96 architecture change, this change only)
- Thread manager card cmsg_01FuvegZXjMmeUzStiEFVnEW6CLKBsytdgAep4Pm1h5rMn (19:26:03 UTC): "Swap the talker from
  MiniCPM5-1B to LFM2.5-1.2B?". The Thread manager reports Ben (user_01BiwYsg5FPe4qAbWVrvM2Q7) tapped "Swap to LFM"
  at 19:27:28 UTC. The option's stated consequence: the talker becomes LFM, the biggest model inside becomes 1.2B, and
  the MiniCPM-only fixes are dropped or redone on LFM.
- Evidence (Everyday chat, artifacts/claude-c1dl-20260927/RESULTS.md, 3b5717258): 0.2d's talker path with the W block
  on LFM, against plain LFM 22-34 (margin -12, exactly at the bar), MiniCPM5-1B 57-3, Qwen3.5-2B 33-26. Report only,
  on 60 DEV practice chats, not chatpanel404, one judge model. C1 itself is still judged on the sealed panel.

## What changes
- TALKER02D = LFM2.5-1.2B-Instruct at revision 0f604ada3f766f9f257460c4c9f0b5d6f69d431b (the pin c1-dev's arm L and
  c1-dl ran). The build's --gen-model must be that snapshot. The talker path is unchanged: greedy, the 336 twin's
  system line, the W block in the system message, the last 6 exchanges, 160 new tokens.
- Nothing else changes: reader (lis-320, H-R), reasoner (358b3, H-A), sleep (the reasoner's nights, H-B).
- Size (goals page, "Counting size"): the biggest model inside is now 1.2B (the talker), and the total is about 2.2B
  with the 1B reader. Both counts are reported. Qwen3.5-2B stays a rival for both.
- MiniCPM-only talking adapters no longer load unless they are redone on LFM: mu-406 and y1t (DOUBT02D). Until an
  LFM version passes, DOUBT02D stays "" (no doubt step, ADDENDUM-29).
- The rival plain-LFM arm is now the same base model as the talker, so rows judged against it measure what 0.2d's
  inputs add or cost.

## Code (scripts/claude_e2e02d.py, unsealed)
- The header's talker line, a TALKER02D pin constant, and talker_for's message now name LFM. Wiring selftest 18/18;
  claude_c1dev_talker selftest 6/6.
