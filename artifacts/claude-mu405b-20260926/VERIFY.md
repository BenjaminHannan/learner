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
