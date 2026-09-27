# mu-406: does training the 1B on Luna's replies stop it treating its memory as the present?

"Making things up about you" thread. Written 2026-09-27 09:55 UTC (date -u). This is the plan to seal. It is PLAN-draft-3.md
(47be9f210, corrected f9d24854a) with the Thread manager's 09:40 UTC review adopted and the code's details written
in. PLAN-draft.md, PLAN-review-1.md, PLAN-draft-2.md and PLAN-draft-3.md stay as written. DEV data only. Cost: $0.

## Why this test
- mu-407 (VERIFY.md, 2c1dea000) showed a "reply to this now" label is not enough. It is FAIL, not proved wrong.
  With the memory block in the latest user message (U0), the plain 1B:
  - made 151 claim flags against 44 with no memory (N);
  - gave 6 real answers of 60 on the ask turn;
  - stayed on the turn in 105 of 240 non-ask replies;
  - repeated an earlier reply 95 times in 300.
- The one change here: a LoRA trained on replies GPT-6 Luna writes for practice chats. Luna is told to reply to the
  present turn and to use memory only when the turn calls for it. The test is against the same plain 1B with the
  same input.
- Why distillation first (the Thread manager agreed at 09:40 UTC): rejection sampling can keep only good replies the
  1B already makes, and it makes few real answers and few on-turn replies. GPT suggested this order
  (reviews/gpt-reply-memory-confab-2026-09-27.md:11, :40).
- Brain reading (a guess): the filter that keeps "remembered" apart from "now" is learned in people; here the 1B
  learns it by imitation.

## Data (Luna writes; code picks the facts and checks everything)
- Writer: Luna (gpt-6-luna) through scripts/claude_luna_codex.py (sha256 342a0fb7e15ebf22...). At most 2 calls at a
  time, the Director's 03:54 UTC share. Nothing reads anything under ~/.codex.
- Chats: scripts/claude_mu406_prep.py, which uses mu-407's writer prompt, checks and write loop unchanged
  (claude_mu407_prep.chat_prompt). Code picks facts with claude_mu405_facts.slots.
  - Test panel: seed 4060, 75 candidates and 3 smoke chats; the first 60 passing candidates in id order. It is
    written, checked and sealed before any practice chat exists. I do not read its rows.
  - Practice: seed 4061, 260 candidates; the first 220 passing in id order. Code holds out 20 of them (seed 4062) for
    the teacher gate. They are never trained on.
  - Overlap is reported, not used to drop chats. mu-407's Luna chats repeat small-talk and ask lines across chats:
    I counted, from its DEV panel, that 25 of 30 chats share a message of 4 or more words with the other 30, mostly
    small talk and ask turns. The report gives shared messages by session and turn kind.
- Teaching replies: scripts/claude_mu406_teach.py, one Luna call per turn, in order.
  - Luna sees session 1's user messages, session 2's turns so far and its own earlier replies, never a later turn.
  - Its prompt (HEAD and TAIL in the script) describes the job and gives no example reply.
  - Code checks each reply before the next turn is written. The reply must be non-empty and at most 500
    characters, with none of mu-407's scan strings. On the ask turn it must contain the stored value. It must not
    use a person, pet or place name from the fact generator's lists, written as the lists write it (capitalised),
    that no user message in the chat contains. It must not repeat an earlier reply.
  - The name check is review 1's list check narrowed to name-like slots (the Thread manager's 09:53 UTC review).
    Case matters, so "pepper" or "olive" as food does not count. Invented foods, days, jobs and hobbies are left to
    the teacher gate's claims judges.
  - A failed call or check counts as one attempt, up to 3 per turn. If all 3 fail, the chat stops, and its later
    turns get no reply. Failures and stops are reported by reason, slot kind and turn kind.

## Teacher gate (before any training; the 20 held-out chats only)
- scripts/claude_mu406_judge.py gate-prep and gate-count. Luna's replies are laid out as mu-407 packets, twice in
  two shuffled orders.
- 2 fresh claims judges (JUDGE-claims405.md) and 2 fresh fit judges (JUDGE-fit407.md), each in its own folder. Their
  verdicts decide pass or fail only. They never pick or drop a reply, and these chats are never trained on.
- Pass needs all three. The marks are shares, so a chat that stopped early still counts; the numbers in brackets are
  for 20 whole chats.
  - G1: claim flags summed over both claims judges, at most 3% of judgements (6 of 200). This is M1's measure (the
    Thread manager's fix). Both and either are reported.
  - G2: non-ask replies on the turn by both fit judges, at least 90% (72 of 80).
  - G3: real answers by both fit judges, at least 80% of ask turns (16 of 20).
  - Every packet needs 2 claims and 2 fit judgements that parse, or the gate is not decided.
- If the gate fails, there is no training. The teacher prompt may change once, in a dated addendum. Then every
  teaching reply is written again with the new prompt, and 20 fresh held-out chats (seed 4090) are judged. A second
  failure ends distillation as INCONCLUSIVE, and the plan moves to rejection sampling.

## Training (BensPC, torch 2.11)
- scripts/claude_mu406_train.py rows makes one row per kept turn of the 200 training chats. Held-out chats are
  refused.
  - The input is exactly what claude_mu407_talk.run gives the talker on U0 at that turn (selftest), with Luna's
    earlier replies as history. The frames are mu-407's Luna frames (prep/frames.json, 612277144).
  - The target is Luna's reply plus the end-of-turn token (<|im_end|>, a stop token). Loss is on the target only.
- train runs claude_k1h_train.run_train unchanged, with k1h's fixed recipe:
  - LoRA rank 16, alpha 32, dropout 0.05, every linear layer;
  - AdamW lr 2e-4, 2 epochs, batch 8 (4 x 2);
  - 5% warmup, then cosine;
  - rows over 1,536 tokens dropped and counted;
  - 10% of chats held back for dev loss, reported only;
  - the last step's adapter is kept; the first-step gradient check.
  Two functions are swapped: the rows and the talker's own template call.
- merge writes a merged copy and checks its logits against base plus adapter (at most 1e-3).

## Test (greedy; mu-405's talk settings; one BensPC job for all arms)
- scripts/claude_mu406_talk.py on the 60 test chats:
  - Registered: P (plain 1B, U0) and T (merged LoRA, U0).
  - Report only: N (plain, no memory), PW and TW (the memory lines in the system message after the Luna system
    line: 0.2d's form).
  - The script refuses T or TW on the plain model and P, N or PW on the merged one.
  - A 3-chat smoke run of P and T comes first. It is not judged.
- Judges (claude_mu406_judge.py), all fresh, blind and in private folders:
  - Claims and fit judges: 300 packets (5 arms x 60) in 20 batch files. One claims judge and one different fit judge
    per file, so every packet has two of each. The judge files are unchanged.
  - Pair judges: P against T per chat, with JUDGE-pair406.md. 2 layouts with the sides swapped, 4 batch files, 4
    judges.
- No-harm: bm-390's harness (claude_bm390.py general --arm plain:DIR) on GSM8K 300 and MMLU-Redux 300, for the plain
  1B and the merged copy, on BensPC, scored with claude_bm390_score.score_general.

## Marks (fixed now)
- PASS needs all five:
  - M1, fewer made-up claims: C_T <= 0.5 x C_P, and per chat T has fewer flags than P more often than more
    (one-sided sign test, ties dropped, p <= 0.05). C is claim flags summed over both claims judges.
  - M2, recall: real answers (both fit judges) T >= P and T >= 15 of 60. The floor tests the main reason for
    distillation (the Thread manager's point a).
  - M3, answers the turn: on-turn non-ask replies (both fit judges) T >= P and T >= 192 of 240.
  - M4, no worse to talk to: the pair judges do not prefer P. Per chat, P is better when more of its 2 judges
    prefer P than T (ties dropped); the one-sided sign test for "P better" must have p > 0.05.
  - M5, no harm: GSM8K and MMLU-Redux each T >= plain - 6 of 300, both run in the same job.
- Proved wrong: C_T >= C_P.
- INCONCLUSIVE (no verdict on distillation):
  - the teacher gate fails twice;
  - fewer than 800 kept turns before the dev split;
  - a step that cannot finish within 3 launches. Each launch is listed with its rc, including launches that make
    no call.
- Scope (the Thread manager's point b): the teacher and the test panel are both Luna-worded. Any PASS is reported
  as "on Luna-worded DEV chats" until a transfer check on other wording runs. A PASS adapter needs fresh
  confirmation chats before it joins any build, and adopting the U form stays Month-end's call.
- Report only:
  - C_T against C_N;
  - real answers against GPT's 30 of 60;
  - repeats and their flags per arm;
  - turn 1 against turns 2-5 for C (turn 1 has no reply history, so it isolates Luna's history at training
    against the 1B's own at test);
  - claims and on-turn per kind;
  - TW against PW, for Month-end;
  - kept turns per kind, the teacher gate's counts, and training and dev loss.
  Nothing measures unprompted memory use on turns 2-4; M2 checks recall on the ask turn only.
- Predictions (before sealing): P406.1 PASS, 20%. P406.2 proved wrong, 10%. P406.3 teacher gate passes the first
  time, 70%.

## Order (the Director orders the Mac and BensPC queues; nothing else runs until the step before is checked)
1. Seal this file, the five scripts, JUDGE-pair406.md and the helper hash (SEAL.sha256.txt).
2. Mac, BASH-ONLY: the test panel (about 12 minutes). Then here: check, scan, and seal the panel (SEAL-panel).
3. Mac: the practice chats (about 45 minutes). Here: select, split, scan, overlap report.
4. Mac: the teaching replies for all 220 chats, 1,100 turns, in launches of under 75 minutes (new file names; the
   writer keeps finished chats).
5. Here: the teacher gate. If it passes, seal the data (SEAL-data).
6. BensPC: rows, training, merge, smoke, then the 5 arms. A second job runs the no-harm check.
7. Here: the judges, the count, the verdict, a blind recount, VERIFY.md. Then the verdict goes to the Thread manager
   and to Month-end.
- Luna calls: about 1,400 (at most about 4,200 with every retry), on Ben's Codex plan.
