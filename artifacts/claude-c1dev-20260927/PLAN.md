# c1-dev: can a plain 1B talker reach C1's no-harm bar? (practice chats, report only)

Everyday-chat thread, written 2026-09-27 00:27 UTC, before any run. Marks below are a DRAFT sent to the Thread manager
for review (Ben 19:28: send the practice-chat check's marks before sealing them). The seal follows that review.

## Question

The Thread manager (00:19 UTC 09-27) asked whether 0.2d's C1 no-harm bar (margin = conversations won minus lost
>= -12 of 60 against every rival, 02d ADDENDUM-14) is reachable at all with a plain 1B talker, before the build runs.
The answer feeds Ben's open pick on how K1 and C1 are judged against Qwen and LFM (02d ADDENDUM-27).

## Why the practice chats and not chatpanel404

chatpanel404 is TEST-ONLY and runs once (its README), for 0.2d's registered C1 run. Judging the rivals on it now would
spend it, and the result would then shape how C1 is judged (ADDENDUM-27), which is choosing a bar after seeing the
test. The DEV practice chats (artifacts/claude-chatdev-20260926: 60 conversations, 336 turns, same writing spec, names
A to M) answer the same question and may be read. They were used to diagnose chat338 (ch-403), which is not in 0.2d,
so nothing in the four arms below was tuned on them.

## Arms (one run each, BensPC, $0)

- D  0.2d's talker alone (scripts/claude_c1dev_talker.py): claude_e2e02d.Agent02d unchanged, with no reader and no
     reasoner. Plain MiniCPM5-1B, greedy, thinking off, the 336 twin's system line plus the W block (every earlier user
     turn, in the system message as committed), the last 6 exchanges, 160 new tokens. On these chats its input is the
     build's: every chat fits the W limit (largest 565 of 12000 characters, so saved facts never reach the talker), no
     turn is a number square (read_latin: 0 of 336), and no chat has more than 6 turns. Selftest 6/6 shows the
     talker's input is identical with a fact-saving reader and with none.
- T  MiniCPM5-1B, Q  Qwen3.5-2B, L  LFM2.5-1.2B-Instruct: the plain twin recipe (claude_e2e336_twinb.py: its system
     line, the whole chat, thinking off, greedy, 160 new tokens), bm-390's pinned snapshots. These are C1's rival arms.
On these chats D differs from T only by the W block, so D vs T also says whether that block harms everyday replies.

## Scoring (unchanged sealed scorer)

`claude_c1rival_run.py score --panel-dir artifacts/claude-chatdev-20260926 --out RUN --build D` (sealed 6f6a6e17d):
one blind pair set per rival over all 60 conversations (seeds 4061-4063), 12 packets of 15, one blind Opus judge per
packet with artifacts/claude-ch403-20260926/JUDGE-BRIEF.md. Then `marks --bar -12`. A blind worker recounts the three
margins from the judge files and keys before anything is reported.

## Readings (fixed now; report only)

- R1 against Qwen: margin(D vs Q) >= -12 reads "C1's bar is reachable against Qwen on the practice chats".
- R2 against LFM: margin(D vs L) >= -12, the same for LFM.
- R3 the build's input: margin(D vs T) >= -12 reads "the W block does no harm by C1's bar".
- Answer to the question: "reachable on the practice chats" only if R1, R2 and R3 all hold; otherwise "not reached
  against <each rival that fails>". Each margin also gets c1rival's reading: behind <= -14, ahead >= +14, else level
  (each side 4.6% by chance for equal systems over 60 decisive pairs).
- Also reported, no mark: ties, made-up-about-the-user counts per arm, median words, "I don't know" on ask_unknown,
  ask_known right, median ms per turn.

## Prediction (written before any reply exists)

R3 holds (D level with T). R1 and R2 fail, with D behind both Qwen and LFM (margin <= -14). Basis: on the creative
panel the same three plain models gave MiniCPM 46, LFM 103, Qwen 114 useful replies of 160
(artifacts/claude-k1c-20260926/VERIFY-k1c.md:8-9); everyday chat
may differ. The prediction "a plain MiniCPM talker cannot reach C1 against Qwen and LFM" is proved wrong on the
practice chats if D vs Q >= -12 and D vs L >= -12.

## What this cannot show

It is a finding only, never a registered result, and it changes no bar: C1 stays as ADDENDUM-14 fixed it, run once on
chatpanel404. The practice chats and the judges are Claude-written and Claude-run (judging is allowed, Ben 16:39); the
reader and notebook are absent (they do not change the talker input on these chats, shown by the selftest, but
everything else in the build is untested here); 60 conversations cannot separate margins inside about +-13.
