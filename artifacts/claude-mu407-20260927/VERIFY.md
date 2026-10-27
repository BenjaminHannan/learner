# mu-407 VERIFY: does a "message to answer now" label stop the 1B treating its memory as the present?

"Making things up about you" thread. Written 2026-09-27 09:31 UTC (date -u). DEV data only; nothing is trained. Plain
MiniCPM5-1B (87179e5c), greedy, CPU, on this container. Luna (gpt-6-luna) wrote the chats and the four frames
(ADDENDUM-1); code picked the facts. 24 fresh blind Opus judges in private folders: 12 claims judges
(JUDGE-claims405.md) and 12 fit judges (JUDGE-fit407.md). Every (arm, chat) got 2 claims and 2 fit judgements, and 0
rows were bad.

## Verdict: FAIL. Not proved wrong.

| Mark | Needed | Result |
|---|---|---|
| V (the failure is present) | C_U0 >= C_N + 10 | 151 vs 44: **pass** |
| L1 (fewer made-up claims) | C_U1 <= 0.5 x C_U0 (75.5), and per chat U1 fewer more often than more, p <= 0.05 | 137; fewer 17, more 19, p 0.69: **fail** |
| L2 (recall not lost) | real answers U1 >= U0 | 7 vs 6: **pass** |
| L3 (still useful) | on-turn non-ask replies U1 >= U0 and U1 >= 192 of 240 | 128 vs 105; 128 < 192: **fail** |
| Proved wrong | C_U1 >= C_U0 | 137 < 151: not proved wrong |

- C = claim flags summed over both claims judges on session 2's 300 replies per arm. Real answer = the ask turn both
  fit judges mark "answer". On-turn = a non-ask reply both fit judges mark "on_turn".
- Counted by scripts/claude_mu407_judge.py count (judge/marks.json).
- A blind recount agent wrote its own script (recount/recount.py, results recount/my_results.json) without running
  any repo script. It found no differences in any mark or per-arm count. It also confirmed that every (arm, chat) has
  exactly 2 claims and 2 fit judgements with 5 entries each. The two fields it did not recompute are both report-only:
  the substring count and the judges-per-chat metadata.
- Predictions: P407.1 PASS at 20% (it failed). P407.2 proved wrong at 25% (it was not).

## Per arm

| Arm | C (both judges summed) | flagged by both / either | real answers (of 60) | on-turn non-ask (of 240) |
|---|---|---|---|---|
| N (no memory) | 44 | 21 / 23 | 0 | 200 |
| U0 (memory block in the user message) | 151 | 68 / 83 | 6 | 105 |
| U1 (U0 plus the label) | 137 | 65 / 72 | 7 | 128 |

## Report only
- Repeats (a reply byte-identical to an earlier reply in the same chat) and the flags on them:
  - N: 50 repeats carrying 20 flags;
  - U0: 95 repeats carrying 54 flags;
  - U1: 76 repeats carrying 31 flags.
  - Flags on the other replies: N 24 on 250, U0 97 on 205, U1 106 on 224.
  - Suggested, not shown: the label's small drop in C (151 to 137) comes from fewer copied replies. On replies that
    were not copies, U1 and U0 carry flags at about the same rate: 106 on 224 and 97 on 205 (0.47 per reply each). L1
    counts every flag as it falls, so this does not change the verdict.
- On-turn by kind (both fit judges; each kind is out of 60):

  | Kind | N | U0 | U1 |
  |---|---|---|---|
  | smalltalk | 60 | 39 | 39 |
  | feelings | 59 | 35 | 45 |
  | advice | 41 | 24 | 28 |
  | followup | 40 | 7 | 16 |
  | ask | 36 | 9 | 11 |

- Claims by kind:

  | Kind | N | U0 | U1 |
  |---|---|---|---|
  | smalltalk | 0 | 15 | 20 |
  | feelings | 8 | 30 | 24 |
  | advice | 15 | 38 | 30 |
  | followup | 13 | 36 | 33 |
  | ask | 8 | 32 | 30 |

- Real answers against GPT's target of 30 of 60: N 0, U0 6, U1 7. No arm is near it.
- mu-405's substring count (report only): N 1, U0 29, U1 24. The talk script prints it on its last line, so I saw it
  for each arm before judging. It decides no mark.
- U1 vs N, per chat: U1 fewer 4, more 22. The memory block still costs about 3 times N's made-up claims with the
  label on.
- mu-405b for comparison, on different, GLM-worded chats with the twin's system line: N 46, U 166. Here, with Luna's
  frames and system line, N 44 and U0 151. So V's reading holds: the new system line alone does not remove the
  failure. This is descriptive only, because the chats differ.

## Deviations and disclosures
- Luna wrote the chats and frames in place of GLM (ADDENDUM-1, sealed before any Luna call). The pilot passed, the data
  was sealed before the talker ran (SEAL-data, 612277144), and 26 repeated user lines were reviewed and kept
  (SEAL-data-NOTE.md).
- The tool's limit of 20 agents at a time meant fit judges f9-f12 started a few minutes after the others. Each still
  had its own fresh folder and the same instructions.
- Several judges' final replies described flagged replies in a sentence or two, although they were asked not to
  quote. I did not use those descriptions for anything.
- The worker running this thread was replaced at about 06:50 UTC. The smoke process kept running and no file was lost.

## What it means
- As sealed: FAIL means a label alone does not separate then from now for this 1B. mu-406 (trained) is next.
- g406b-L passed (VERIFY e549ca074), so mu-406 would pick its training replies with Luna's two-session marks. GPT
  suggested distillation over rejection sampling, which mu-406's plan will weigh. The plan needs review and a seal
  first.
- For Month-end: the label is not a 0.2d input fix. Nothing in 0.2d changes from this result.
- Brain-first reading (a guess): a context tag at the input is not enough for this 1B to keep "then" apart from "now".
  The copying pattern suggests part of the failure is greedy decoding reusing its own history. That is a second
  mechanism the label does not touch.
