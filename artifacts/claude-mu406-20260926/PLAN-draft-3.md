# mu-406 plan, draft 3 (written 2026-09-27 09:39 UTC by date -u; not sealed; for the Thread manager's review)

PLAN-draft.md, PLAN-review-1.md and PLAN-draft-2.md stay as written. Draft 2 left the training route open until
g406b and mu-407 had verdicts (draft 2, "Update 02:56"). Both verdicts are in, so this draft picks the route.

## What changed since draft 2
- g406b-L PASS (artifacts/claude-g406l-20260927/VERIFY.md, e549ca074). Luna can mark made-up claims about the user
  on mu-405b's DEV replies about as the blind judges do. That is shown for the plain 1B's replies only.
- mu-407 FAIL, not proved wrong (artifacts/claude-mu407-20260927/VERIFY.md, 2c1dea000). A "reply to this now" label
  cut claim flags only from 151 to 137 (U0 to U1), against N's 44.
  - U0 gave 6 real answers of 60 and 105 on-turn non-ask replies of 240. N gave 200 of 240.
  - U0 had 95 byte-identical repeats of an earlier reply in the same chat, carrying 54 flags.
- Ben allowed GPT-6 Luna as a training-data writer at 03:47 UTC.
- Month-end keeps the memory block in the system message for 0.2d (ADDENDUM-41, 7802b01af).

## The choice: distillation first (Luna writes the teaching replies)
- Rejection sampling (draft 2) can keep only good replies the 1B already makes. Three facts from mu-407 make that
  weak here:
  - Recall. U0 gave a real answer on 6 of 60 ask turns. Few ask turns would get a kept reply that answers them, so
    the 1B would get little practice at answering from memory. Distillation gives every ask turn a right answer.
  - On the turn. U0 answered the present turn in 105 of 240 non-ask replies. Rejection sampling would first need a
    new gate for Luna's on-turn mark (the Thread manager's 02:58 fix), then about 800 label calls. Distillation
    replies are written to answer the present turn, and a teacher gate (below) checks that they do.
  - Copying. U0 copied earlier replies 95 times in 300. Rejection sampling trains on the 1B's own histories, copies
    included. Distillation targets are never copies (a code check drops them).
- GPT recommended distillation if the boundary test failed (reviews/gpt-reply-memory-confab-2026-09-27.md:11, :40).
  The boundary test was mu-407, and it failed.
- Against distillation, stated now:
  - The training histories hold Luna's replies. At test, the history holds the 1B's own replies. So the report
    splits turn 1, which has no reply history, from turns 2-5.
  - The 1B may pick up Luna's style instead of the behaviour. The pair judges and the no-harm check guard this.
  - GPT warned that a writer's replies are not trustworthy just because the writer passed as a marker. The teacher
    gate measures the teaching replies themselves, on held-out chats, before any training.
- Brain reading (a guess): the 1B learns by imitation what a filter between "remembered" and "now" does. That filter
  is learned in people too (draft 2, Schnider).
- Rejection sampling stays named as the next test if this one fails (see the end).

## Design (one change: a LoRA trained on Luna's teaching replies, against the same plain 1B with the same input)
- Input: mu-407's U0 form with mu-407's Luna frames (prep/frames.json, sealed in 612277144): the Luna system line,
  then the latest user message holds the memory header, one prefixed line per session-1 message, a blank line and
  the user's turn (scripts/claude_mu407_talk.py:10-11). The current_label frame is not used.
  - P is the plain 1B with this input. It is measured fresh on the new panel.
- Chats: mu-407's Luna writer prompt, unchanged (claude_mu407_prep.py through claude_mu407_prep_luna.py). Code picks
  the facts with claude_mu405_facts.slots on new seeds. Same five session-2 turn kinds, ending in a stored-fact ask.
  - Test panel: 60 fresh chats on their own seed. It is written, checked and sealed before any practice chat exists.
    I do not read its rows.
  - Practice: 220 chats on another seed. Code splits off 20 as the held-out teacher-check set (fixed seed). Those
    20 are never trained on.
  - A code check before sealing: no practice chat shares a user message with a panel chat.
- Teaching replies (Luna, one call per turn, in order):
  - Luna sees session 1's user messages as earlier messages, session 2's turns so far and its own earlier replies.
    It never sees a later turn.
  - The prompt describes the job and gives no example reply. The job: reply to the latest message; use something
    from the earlier messages only when this turn calls for it; say nothing about the user that they did not say;
    when asked about something they said before, answer with that detail; keep it short and plain.
  - Code checks every reply before the next turn is written. The reply must be non-empty and at most 120 tokens by
    the 1B's tokenizer. On the ask turn it must contain the stored value (the substring test in
    claude_mu405_talk.ask_right). It must not
    name a slot value that is absent from session 1 (review 1's drop). It must not repeat an earlier reply.
  - A failed check asks again, up to 3 attempts per turn. If all 3 fail, that chat stops, and its later turns give
    no rows.
- Teacher gate (before training, on the 20 held-out chats only):
  - 2 fresh claims judges (JUDGE-claims405.md) and 2 fresh fit judges (JUDGE-fit407.md), each in its own folder.
  - Their verdicts decide pass or fail only. They never pick or drop a reply, and the judged chats are never
    trained on. k1h's gate 2 is the precedent (scripts/claude_k1h_train.py:4-6, :15).
  - Pass needs all three: at most 3 of 100 replies flagged by both claims judges; at least 72 of 80 non-ask replies
    on the turn by both fit judges; at least 16 of 20 real answers by both fit judges.
  - Fail means no training. The teacher prompt may be changed once, in a dated addendum, and checked again on 20
    fresh held-out chats. A second fail ends distillation, and the plan moves to rejection sampling.
- Training rows: one per kept turn. The input is exactly the test-time U0 input for that turn, with Luna's earlier
  replies as history. The target is Luna's reply plus the end-of-turn token. Loss is on the target only.
- Training recipe: k1h's fixed recipe (claude_k1h_train.py:23-27). LoRA rank 16, alpha 32, dropout 0.05, every
  linear layer; AdamW lr 2e-4; 2 epochs; batch 8; 5% warmup, then cosine; bf16 weights on CUDA with the adapter in
  float32; rows over 1,536 tokens dropped and counted; the last step's adapter is kept; the first-step gradient
  check (14dc0c013). Torch 2.11 on BensPC. A new script imports k1h's loop where it can and changes only the rows.
- Arms on the test panel, greedy, all in one BensPC job, with the talk settings unchanged (claude_mu405_talk):
  - Registered: P (plain, U0) and T (LoRA, U0).
  - Report only: N (plain, no memory); P_W and T_W (the same memory lines added to the Luna system line after a
    blank line, the turn as written: 0.2d's form).
- Checks after the run:
  - Claims judges (JUDGE-claims405.md) and fit judges (JUDGE-fit407.md): two of each per packet, all 5 arms mixed
    and shuffled, fresh judges in private folders, as in mu-407. The judge files are unchanged.
  - Pair judges, P against T: 2 per chat, sides shuffled, private folders. Their instructions are written and
    sealed with the marks.
  - No-harm: bm-390's harness (scripts/claude_bm390.py general, GSM8K 300 and MMLU-Redux 300), plain and T with the
    adapter merged as claude_bm398r_eval.py does, in the same BensPC job so both run on one machine.

## Draft marks (fixed before sealing; the Thread manager reviews first)
- PASS needs all five:
  - M1, fewer made-up claims: C_T <= 0.5 x C_P, and per chat T has fewer flags than P more often than more
    (one-sided sign test, ties dropped, p <= 0.05).
  - M2, recall not lost: real answers T >= P (both fit judges).
  - M3, still answers the turn: on-turn non-ask replies T >= P and T >= 192 of 240 (both fit judges).
  - M4, no worse to talk to: the pair judges do not prefer P (one-sided sign test for "P better", p > 0.05).
  - M5, no harm: GSM8K and MMLU-Redux each T >= plain - 6 of 300.
- Proved wrong: C_T >= C_P.
- INCONCLUSIVE, with no verdict on distillation: the teacher gate fails twice, or fewer than 800 training rows
  survive.
- Changes from draft 2's marks: M1 uses GPT's 0.5 (as mu-407 did) in place of 0.67; M2 is T >= P in place of
  P - 3; M3 is GPT's usefulness mark, which draft 2 lacked. Draft 2's follow-up memory-use question (report only)
  is dropped so the claims judges' file stays unchanged. So nothing measures whether T uses its memory on turns 2-4
  when it is relevant but not asked for. M2 checks recall on the ask turn only.
- Report only:
  - C_T against C_N. The goal is a talker that uses its memory and invents no more than one without it.
  - Real answers against GPT's target of 30 of 60.
  - Repeats per arm, with their flags; turn 1 against turns 2-5 for C and on-turn; claims and on-turn per kind.
  - P_W and T_W, for Month-end. Rows kept per kind; the teacher gate's counts; training loss.
- Predictions (before sealing): P406.1 PASS, 25%. P406.2 proved wrong, 10%. P406.3 teacher gate passes first time,
  80%.
- A PASS is DEV only. Before a mu-406 adapter joins any build it needs fresh confirmation chats, and whether to
  adopt the U form stays Month-end's call. The transfer check on mu-405's Claude-worded panel moves to after a PASS
  (finding only, by the 16:39 rule).

## Training data source (Ben's 16:39 rule; Luna allowed at 03:47)
- User turns and teaching replies: Luna. Facts and all checks: code. Frames: Luna's, from mu-407.
- Claude writes only prompts and code. No example reply appears in any prompt.
- Blind Claude judges read only the 20 held-out chats (never trained) and test outputs after training.
- Luna runs through scripts/claude_luna_codex.py (sha256 342a0fb7...) on the Mac. Nothing reads anything under
  ~/.codex.

## Where, order and budget ($0; the Director orders the queue)
- Luna runs at most 2 calls at a time, the Director's 03:54 UTC share for this thread
  (artifacts/claude-mu407-20260927/ADDENDUM-1-luna.md:45). mu-407 wrote 78 chats in 29 minutes with 1 call at a
  time (prep/write.log). Every Mac job is BASH-ONLY, stays under its 75-minute alarm and keeps finished rows on a
  restart.
1. Scripts and selftests here. The Thread manager reviews the prompts, marks and pair-judge text.
2. Seal the plan, the scripts and the judge files.
3. Mac, Luna: the 60-chat test panel (about 12 minutes), then its seal.
4. Mac, Luna: the 220 practice chats (about 45 minutes).
5. Mac, Luna: the teaching replies, 1,100 turns, 2 chats at a time. The time per call is not measured yet (a guess
   of 10-20 seconds gives 1.5-3 hours), so this takes 2 to 4 launches.
6. Here: code checks, then the teacher gate (4 blind judges).
7. Seal the data.
8. BensPC: training, then the 5 arms on the panel (1,500 turns). A second job runs the no-harm check (1,200 items).
   Each job stays under 75 minutes.
9. Here: the blind judges, the count, a blind recount and VERIFY.
- Luna calls: about 1,400, or at most about 4,200 with every retry. Luna is on Ben's Codex plan, which he called
  unlimited. BensPC and the judges cost $0. No rental.

## If mu-406 FAILs (named now, not sealed)
- If M1 fails but the teacher gate passed: rejection sampling on the 1B's own samples. It needs the on-turn gate
  for Luna's marks first (the Thread manager's 02:58 fix).
- If M1 passes but M3 or M4 fails: DPO. Each pair shares the exact same input history: Luna's reply against a
  flagged 1B sample drawn from that same history.

## Open questions for the review
- Is distillation first right, given mu-407's recall and copying numbers?
- Are the teacher gate's three marks strict enough?
- Should the W arms (0.2d's form) stay report only?

## Correction (09:40 UTC, date -u)
- The first version of this file said on-turn on follow-up turns measures memory use "since a follow-up asks about
  session 1". That was wrong. In mu-407's writer prompt the follow-up turn follows up on session 2's advice turn
  (claude_mu407_prep.py:41). Fixed in place above.
