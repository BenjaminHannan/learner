# mu-405b verdict ("Making things up about you"), written 2026-09-26 23:36 UTC (date -u)

Marks: PASSMARKS.md, sealed 774865c0d before the run. Talk: run/talk_U.jsonl (this test) plus mu-405's registered
run2 talk_N / talk_W / talk_H, copied unchanged into judge/runs (hashes below). Claims: 240 packets (60 chats x arms
N, W, U, H, mixed and shuffled, seeds 4061/4062/4063), two fresh blind Opus judges per packet, each in its own private
folder. Count: `python3 -B scripts/claude_mu405b_judge.py count ...` -> judge/marks.json. Blind recount by a fresh agent
with its own script (no repo scripts reused): exact match, 240 pids, each judged twice, 0 flag-length mismatches.

## Verdicts

| Mark | Reading | Verdict |
|---|---|---|
| VB (talker uses the memory): U asks right >= N + 10 | U 12, N 0 | **PASS** |
| R (placement changes recall): U >= W + 10 and sign p <= 0.05 | U 12 vs W 4 (needed 14); per chat U-only 10, W-only 2, p 0.0193 | **FAIL, not proved wrong** (proved wrong needs U <= W) |
| Q3 (using the memory raises made-up claims): C_U - C_W >= 10 and sign p <= 0.05 | C_U 166 vs C_W 31; per chat U more 34, fewer 9, tied 17, p 0.0001 | **PASS** (bad news) |

In plain words: moving the user's own words from the system message into the user message made the plain 1B answer
3 times as many stored-fact questions (12 vs 4 of 60), but that is short of the fixed gain, and it still misses 48 of
60. The same move made it say about 5 times as many unsupported things about the user (166 vs 31 flags over two
judges). A talker that really reads its memory, in this form, invents more about the user, not less.

## Report-only rows

| Arm | C (two judges) | replies flagged by both | by either | asks right |
|---|---|---|---|---|
| N (no memory) | 46 | 20 | 26 | 0 |
| W (block in system message, mu-405) | 31 | 11 | 20 | 4 |
| U (block in user message) | 166 | 77 | 89 | 12 |
| H (whole chat as history) | 56 | 23 | 33 | 1 |

Each arm: 300 session-2 replies, 60 chats, all judged by two judges.

- U vs N per chat: U more 33, fewer 6 (p < 0.0001). U vs H: U more 32, fewer 9 (p 0.0002).
- Flags by turn kind (summed over two judges; recomputed at 23:36 UTC and equal to the earlier count):

| Arm | smalltalk | feelings | advice | followup | ask |
|---|---|---|---|---|---|
| N | 0 | 5 | 13 | 16 | 12 |
| W | 4 | 5 | 9 | 12 | 1 |
| U | 39 | 35 | 29 | 31 | 32 |
| H | 17 | 4 | 15 | 11 | 9 |

U's extra flags are spread over every kind of turn, including small talk (39 vs W's 4), so the block does not only
change answers to direct questions: it leaks into every reply.

## What this does and does not show

- Shown (DEV, one prompt form, plain MiniCPM5-1B, greedy): with the y1f L1 block in the user message, recall rises a
  little and made-up claims about the user rise a lot.
- Suggested, not tested: judges' notes described garbled or misattributed stored facts (a detail given to the wrong
  person, an event reversed, an allergy turned into a medication). That reads like source-monitoring failure: the
  talker mixes up which remembered fact belongs where. No count of this was registered.
- Not shown: that placement is the cause in 0.2d's full build (different reader, notes, reasoner note); that any other
  memory wording behaves the same; anything about the TEST-ONLY panels (not read).
- W's own 31 is below N's 46: with the block in the system message the talker largely ignores it (mu-405, 4 of 60).
  That W looks cleaner is not a success; it is the talker not using its memory.

## What follows

- For Month-end's W_PLACE02D choice (ADDENDUM-35): U raises recall 4 -> 12 of 60 but costs 135 extra claim flags on
  the same 300 replies. Copying U into 0.2d's system_text is likely to worsen row S1. That choice is Month-end's.
- For this thread: placement alone fails. The fix for S1 has to be trained (mu-406, rejection-sampling fine-tuning on
  the 1B's own clean replies with GLM or code labels). mu-406's plan now needs the memory block in its training inputs,
  because a talker trained without memory would not face this failure.
- Prediction check: P405b.1 (VB and R PASS, lowered to 35%) missed on R. P405b.2 (Q3 PASS, 35%) came true.

## Hashes (sha256)

- judge/keys/claims_key.json f41e339f995d1580c2b744dccff44320c8b77bc55a8d443afadbf04129f6ff5c
- judge/out/claims_j1.jsonl c90d9e3d4688df10cbb7158f45fd04d2319a0f2d946c2a91ea2fd4645c8c0272
- judge/out/claims_j2.jsonl c364055f5c0b2796402d1b54f1403e5e077ca2d06a73911457c58fa80c0fb912
- judge/out/claims_j3.jsonl 87e0e54811f4bac9ff866556ac45e2fe24afdff49b228be0e3277b61f9862dfd
- judge/out/claims_j4.jsonl 65928795985958a523deaf0e6c0ae3cb9d85f3979ddfab0a915f1b999fb6ab7c
- judge/out/claims_j5.jsonl cc26bfb36d1104c4234ff11d951c99e12b4b2b038758fd6feed19d91bb5fce16
- judge/out/claims_j6.jsonl 8965134dba6cdfa3d4bf81ab5eb83b2bcddefa3ed2c9bd06240bf6cf2988143b
- judge/out/claims_j7.jsonl 564a003ca0a37c1e64f31b1cf5e0115308cce7365eb86577462b45f4bc772b35
- judge/out/claims_j8.jsonl 70c232acf2fb77dd629ea56ac9679c73b5bbb9fc425a96b59c4ba1b4fe7c9327
- judge/marks.json ca12c8287f90236caa0b3b87017fe93e3e3514df2dfba50a26ef359daa2299ee
- judge/runs/talk_N.jsonl 1ed656f1749beeb4eabee778b6e32c213c7d3dfda3de1376cae815573293df76
- judge/runs/talk_W.jsonl 3a6a73409645e29ab9a88e4af7edf2911af56cb372facdc19fb29c3223aa7ce5
- judge/runs/talk_U.jsonl dbbe502e5bd84036a5521de81b53dd2f724722a208d3d638f870a888882a93c3
- judge/runs/talk_H.jsonl d3466d7242db1784962120bbc7390ce8d1d277c5320d7a7211dd785b422b0884

Cost: $0 (this container's CPU; judges are blind agents, not training data). Nothing trained on any of it.

## Note on the panel's wording (added 2026-09-26 23:45 UTC, date -u)

The 60 chats' user turns were written by Claude writer agents from code-chosen facts (mu-405 PASSMARKS.md, Setup).
Nothing was trained on them or on any reply here. I read the 16:39 rule ("nothing a model trains on is Claude-written")
and its "finding only" label as covering rows a model trains on. dl-5's reason was a Claude prefix in its trained
target, so the rule does not cover this untrained comparison, and mu-405b is reported as a registered result. The
Thread manager can overrule that reading. mu-406's registered test panel will be GLM-worded either way
(PLAN-draft-2.md).

## Note on what VB and R measured (added 2026-09-27 02:54 UTC, date -u; verdict words unchanged)

VB and R count "asks right" with mu-405's code check, claude_mu405_talk.ask_right (claude_mu405_talk.py:129-131). It
counts a reply right when it contains the asked value anywhere, as a substring. It does not check that the reply
answers the question, or that the value is said about the right thing. GPT's review (reviews/gpt-reply-memory-confab-
2026-09-27.md) pointed this out, and the Thread manager checked the code.

The Thread manager read U's 12 counted-right asks (02:51 UTC), and so did I (02:52 UTC). Both reads were unblinded
and are not registered counts.
- Most of the 12 name the value while reciting session 1 or while going off-topic. mu405-12 lists the old
  conversation line by line. mu405-54 says "you mentioned Vashti, but I don't have any information about her name".
  mu405-45 says "I'm not allergic to strawberries".
- The Thread manager counted about 2 that actually answer the question (mu405-41, mu405-56). I found 2 to 4
  (mu405-41, mu405-56, and possibly mu405-49 and mu405-11).
- W's 4: about 1 or 2 answer (mu405-28, maybe mu405-45).

So VB PASS measured this: with the block in the user message, the talker's ask replies contain the stored value
(12 vs 0). The talker reads the block, but the check does not show that it recalls correctly. R's FAIL is compared on
the same measure. Q3 is judged blind, so its claims counts do not depend on this scorer. Q3's validity condition
(VB) holds only in that weaker sense: the talker reads its memory, often by reciting it. The verdict words stay as
registered: VB PASS, R FAIL (not proved wrong), Q3 PASS (bad news).

For every next test, recall needs a real answer to the current question with correct attribution, judged blind or
checked by code on answer form. The substring count stays as report-only.

Addendum to the note (2026-09-27 03:00 UTC, date -u):
- How many of U's 12 "right" asks truly answer depends on the reader. None of these reads is blind or registered.
  - The Thread manager: about 2 (mu405-41, -56).
  - Me: 2 to 4 (adding -49, -11).
  - The coordinator's worker: 5 (-41, -49, -56 plain; -11, -20 indirect).
  - So the range is 2 to 5 of 60.
- Repeats (a second candidate mechanism, report only, counted at 02:59 UTC from judge/runs and judge/out):
  - Greedy decoding often repeats a reply word for word later in the same chat. Per arm, replies identical to an
    earlier reply in the same chat, with the claim flags they carry (two judges summed): N 41 (5 flags), W 19 (0),
    U 104 (46 of 166), H 102 (18).
  - Chats where advice, follow-up and ask got the same reply: N 14, W 3, U 28, H 19.
  - U's claims are well above W's even on replies that are not repeats: 120 vs 31.
