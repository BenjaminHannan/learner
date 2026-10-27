# bm-398w PLAN DRAFT: train the 1B to read 20 lines as well as it reads the right ones (benchmarks thread, written 2026-09-27 05:28 UTC)

A draft for the Thread manager's review. It is not registered or sealed, and nothing has been generated or trained.
Revised 2026-09-27 05:45 UTC after the first send (05:28); the changes are listed at the end.
Every LoCoMo number is "after development use". LoCoMo is practice only and is never trained on. LongMemEval stays
the untouched final exam. Nothing from LoCoMo or LongMemEval goes into training.

## Why (all blind, counts only)
- bm-398d (56c71354c): given only the right lines, the plain 1B was right on 137 of 297, and Qwen3.5-2B reading the
  whole chat on 138. With the right lines plus distractors, the 1B dropped to 119. It can read, but distractors cost
  it.
- bm-398u (d8078eda4) and bm-398v (df149a5b8): cutting store B's 20 lines down to the model's own top 3 or top 8
  never beat all 20 (236 vs 264 of 759; 256 vs 264 of 772). Every cut loses evidence, and that loss is bigger than
  the gain from fewer distractors. In bm-398v's pre-registered split, 8 lines helped by 5 answers where they held the
  evidence and lost 16 where they did not.
- So fewer lines is not the lever. What is left is the reader: answer from all 20 lines as well as from the right
  ones. The textbook fix is RAFT (Zhang et al. 2024): train the reader on questions whose context mixes the right
  lines with distractors.
- Earlier failure to avoid: bm-398r (84c414325) trained a reader adapter on code-templated chats with code-written
  answers. It gained on its own practice set and not on LoCoMo (110 vs 111): it learned the answer's form. Here the
  chats, questions and answers are worded by Luna (varied), the context is store-layout lines with hard distractors,
  and the claim needs both a fresh held-out panel and LoCoMo.

## Brain first (a textbook-level guess)
When several memories match a cue, prefrontal cortex holds back the ones that don't fit the goal (retrieval
interference and its control). That control improves with practice on exactly this kind of competition. Here the
practice is questions whose context holds near-miss lines, with the right answer as feedback.

## The one change
A LoRA on the plain MiniCPM5-1B's answer step, trained on RAFT-style items. The retrieval, the 20 lines, the layout
and the prompt stay exactly as bm-398v's BN arm.

## Training data (Luna and code only; nothing written or judged by Claude)
- **Chats.** A new code seed script (scripts/claude_bm398w_data.py) uses fresh seeds: 3993 for training chats and
  3994 for the panel (not 320-329, 4027, or the selftest seeds 1, 2 and 7; the build refuses any other seed). For
  each practice chat it sets two fictional speakers, 6 to 8 dated sessions, and a turn plan: which turn states which
  fact, taken from lis-320's seed world (occupation, city, hobby, pets and so on), plus dated events. Both avoid
  lists are passed: artifacts/claude-lis320-20260926/avoid_names_dev.txt and avoid_test.sha256. Luna words each
  session from its turn plan through the Director's helper (scripts/claude_luna_codex.py, sha256 342a0fb7…024e,
  model gpt-6-luna). One writer for the whole set, recorded per row. Small talk uses topics chosen to stay clear of
  the fact values (no jobs, hobbies, food, music, pets or gardens).
- **Code checks (no model judge).** A session is kept only if it has the planned number of messages from the
  planned speakers, each fact message holds its own required words, and no fact value, other person's name or
  date phrase appears in any other message. A chat is kept only if all its sessions are. A failed session is
  retried once at once, and each rerun of the command gives it one more try, up to 3 failed rows (6 calls). An
  error-like or empty reply is a failed call (the Director's helper raises), never a row.
- **Questions.** Luna words one question per planned fact from a code frame: owner, relation, and a time for dated
  events. Code rejects any question that contains the answer value. The gold answer is the code's value. For dated
  events, code computes the date from the session date and the relative phrase it planned. Two-fact questions (a
  fact about a person named in another fact) come from code frames too.
- **Context (the RAFT part).** For each question: 20 lines from the same chat, the evidence turn(s) plus the
  non-evidence turns ranked highest by BM25 against the question (hard distractors). They are laid out in chat order
  under session dates, exactly as claude_bm398d_evidence.context does for LoCoMo. The evidence is always among the
  20. Teaching "I don't know" is y1t's job and stays out of this test.
- **Targets.** Luna writes a short answer for each item from the gold value, so there is no fixed sentence frame.
  Code keeps it only if it contains the gold value (a dated answer: day, month and year), no other value of the
  same relation, and no negation word. No Claude agent checks the targets: Ben's 16:39 rule says nothing a model
  trains on is judged by Claude. Practice-dev and panel rows carry the code's gold value instead of Luna's answer.
- **Size.** 170 planned training chats (18 questions each before code drops). If about 150 are kept, that is about
  2,300 training items after holding out 15% of chats as practice-dev (report only). Floor: at least 100 kept
  training chats and 17 kept panel chats, else stop with DATA-SHORT and train nothing.
- **Training.** scripts/claude_bm398r_train.py unchanged: rank-16 LoRA on q/k/v/o, 1 epoch, AdamW 2e-4, 8 per step,
  loss on the answer tokens, seed 3992. On BensPC, $0.

## Arms (the same 20 lines, layout and prompt; only the weights differ)
- **BN:** the plain 1B, as in bm-398n and bm-398v.
- **BR:** the 1B with the bm-398w adapter, switched on only for memory questions (bm-398i's switch, as in Ben's
  separate-experts design).
- Report only: Qwen3.5-2B on the same 20 lines, F1 only (not judged), and only if it is already on BensPC (no
  download).
- The arms run in one process: the plain 1B wrapped in bm-398i's switch with the adapter loaded; off gives BN, on
  gives BR. In a CPU smoke here, the switch-off arm reproduced bm-398n's store-B replies byte for byte (2 of 2).

## Panels
1. **A fresh held-out panel (a panel that has driven no choice).** 20 chats from seed 3994, worded by Luna; 300
   questions drawn by seed 3995. Its file hash is sealed (SEAL-panel.sha256.txt) before training starts. It is never
   read by the builder and never used for any choice. Judged blind. It is the same kind of chat as the training data,
   so it shows learning, not transfer.
2. **LoCoMo, all ten conversations, categories 1-4 (1,531 questions), store B's 20 lines** (rd-378L's turns for 0-4
   and rd-378u's for 5-9). Labelled "after development use": both halves drove retrieval choices (bm-398n, bm-398u,
   bm-398v). No reader-training choice has been made on LoCoMo, and the recipe is bm-398r's, unchanged. BN is
   re-generated and re-judged in the same blind panel as BR, not reused.
3. **The Qwen bar from bm-398d's setup (report only).** BR on bm-398d's 297 questions (all inside the 1,531)
   against Qwen's 138 (whole chat) and the 1B's 137 (right lines only). The layouts and judges differ, so this is a
   reference line, not a mark.
- **Judging.** bm-398d's rubric (A right, B right plus a conflicting answer, C partly, D wrong, E doesn't know). Two
  Latin-square groups hold each of the 1,831 questions once per arm; 60 items are re-asked for a relabel check;
  3,722 items in 75 batches of up to 50. Judges see the question, the gold answer, the evidence lines and one reply.
  Byte-identical replies from the two arms count as one answer. An independent recount follows.

## Marks (draft)
- **R1 (LoCoMo):** BR A ≥ BN A + 20 of 1,531, with more gained than lost and a two-sided exact McNemar p < 0.05.
- **R2 (fresh panel):** BR A ≥ BN A + 15 of 300, with p < 0.05.
- **R3 (no harm):** on LoCoMo, BR D ≤ BN D + 10, and no category drops by more than max(3, round(3% of n)).
- **R4 (no harm elsewhere):** on MMLU-Redux and GSM8K (bm-390's 300-item sets), the switch-off replies equal the
  unwrapped plain 1B's replies on all 600, and the right counts are equal, on the same machine. With the adapter
  always on, the counts are reported, not marked, because the design only runs it for memory questions. (Open
  question to the Thread manager.)
- **PASS** = R1, R2, R3 and R4. Anything else is a registered FAIL.
- **Proved wrong (it learned the practice form, not reading):** R2's gain is at least 15 while BR A ≤ BN A on
  LoCoMo. Also proved wrong if BR A ≤ BN A on both panels.
- **Report only:** F1, abstentions and confident-wrong counts; A split by whether the evidence is among the 20; A
  by category; the Qwen rows; practice-dev before and after; relabel and identical-pair agreement.
- **A risk the split watches:** every practice item has its evidence among the 20 lines, but 246 of the 1,531
  LoCoMo questions do not (store B found evidence for 1,285). Trained this way, the 1B may guess more on those,
  which R3 would catch as more wrong answers.

## Predictions (draft)
- R2 passes: 60%. R1 passes: 25% (point guess +12 of 1,531). PASS: 20%. Proved wrong: 30%.

## Open questions before sealing
- Overlap with y1t (Answering from memory, answered 05:29 UTC): none. Nothing there trains the 1B to read among
  store lines with distractors. y1t trains doubt on its own graded drafts from 0-7 earlier lines of short one-speaker
  chats; y1tH1 is evaluation only; y1r trains the MiniLM retriever (which lines get into the 20), not the reader.
  Their seed-4027 dialogs are free after their data gate, but at 1-8 kept user turns and one speaker they cannot
  give a 20-line window of same-chat distractors, so bm-398w writes its own chats. If y1t goes GO, its adapter can
  run through bm-398v's BN arm as a report-only row for them.
- Seeds: Reading facts (05:27 UTC) says 320-329, 4027 and 1, 2, 7 are reserved and any other number is free. They
  asked for fresh seeds, not seed 324's rows, and both avoid lists. Their lis-320 Luna wrapper words lis-320's
  one-to-one dialogs only, so bm-398w calls the Director's helper directly, with the batch and stop pattern of
  claude_lis320_glm_oc.run_batches.
- Luna throughput on the Mac (the Director's queue) sets how long the data takes: about 1,350 calls for 190 chats
  (about 1,330 sessions, plus one question-and-answer call per kept chat), before retries. The k1h pilot's short
  Luna calls took about 9 seconds each; session calls are longer. A guess is 3 to 4 hours with 3 workers, in runs
  of 70 minutes (the builders' 80-minute command limit).
- A pilot first: the same commands on the first 5 training chats. It goes on only if at least 3 of the 5 chats are
  fully kept after up to three runs; else PILOT-FAIL, with the failure reasons as counts.

## Order of work (after sealing)
1. Mac (the Director's queue, Luna, $0): plan, pilot, word, ask and build, for training and panel chats. The panel's
   hash goes into SEAL-panel.sha256.txt before step 2.
2. BensPC ($0): train with claude_bm398r_train.py unchanged; then `claude_bm398w_eval.py locomo`, `panel` and
   `general`.
3. Here: score, blind judging, independent recount, RESULTS.

## Cost and owners
- $0: Luna through Ben's Codex plan, BensPC for training and GPU evaluation, blind judges as Opus agents. No rental.
- Benchmarks writes and runs it. Reading facts: seed world and avoid lists. Answering from memory: the switch and
  the y1t overlap. The Director: the Mac Luna queue and BensPC's order.

## Plain summary for Ben
The small model answers well when it sees only the right lines of a past chat, but badly when those lines are
mixed with 19 others. Picking fewer lines didn't help, because the picker drops the right line too often. So this
trains the model to read the whole mix: practice chats written by Luna, questions whose answers code can check, and
each practice question comes with the right line hidden among look-alike lines. It passes only if it gets more right
answers on fresh practice-style chats and on the LoCoMo benchmark, without more wrong answers and without hurting
maths or general questions.

## Changes since the first send (05:28 UTC)
- Dropped the Claude agent's 60-target gate (it would have been Claude judging training data, against Ben's 16:39
  rule). Replaced by a code negation check.
- Seeds pinned: 3993 training, 3994 panel, 3995 panel draw, 3996 judge order.
- Size corrected: about 2,300 training items, not 3,000 (18 questions per chat, 15% of chats held out).
- Small-talk topics narrowed away from the value pools; failed sessions get up to three runs; a 5-chat pilot gate
  and a DATA-SHORT floor.
- The Qwen same-lines row is F1 only and only if Qwen3.5-2B is already on BensPC.
- R4 spelled out as coded; judging load spelled out (3,722 items).
- Code: scripts/claude_bm398w_data.py (selftest 27/27 with a stub writer) and scripts/claude_bm398w_eval.py (selftest
  11/11; score, prep and jscore run end to end on old replies and made-up labels; locomo, panel and general run on 2
  items each on this CPU with a random adapter).
