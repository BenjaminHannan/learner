# bm-398w PLAN: train the 1B to read 20 lines as well as it reads the right ones (benchmarks thread, written 2026-09-27 05:49 UTC)

Registered before any data is generated or anything is trained. Reviewed by the Thread manager (05:30 and 05:46 UTC)
on PLAN-DRAFT.md (492ee192b, e15352161); its fixes are in. Every LoCoMo number is "after development use". LoCoMo is
practice only and is never trained on. LongMemEval stays the untouched final exam. Nothing from LoCoMo, LongMemEval,
MMLU or GSM8K goes into training. Counts only in every report.

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
- **Chats.** scripts/claude_bm398w_data.py plans every chat in code: seed 3993 for training chats (170 planned) and
  seed 3994 for the panel (20 planned). Not 320-329, 4027 or the selftest seeds 1, 2 and 7 (Reading facts, 05:27
  UTC); the build refuses chats from any other seed. Each chat has two fictional speakers, 6 to 8 dated sessions of
  10 to 14 messages, and a turn plan saying which message tells which fact: 8 facts about the speakers
  (lis-320's seed world: job, employer, city, hobby, pets and so on), 4 introductions of another person ("my sister
  X") and 4 facts about those people in a later session, and 6 dated events ("went to a concert last Saturday").
  Both avoid lists are passed (artifacts/claude-lis320-20260926/avoid_names_dev.txt and avoid_test.sha256). The plan
  files' hashes are pinned in the Mac job. Small talk uses topics chosen to stay clear of the fact values.
- **Wording.** GPT-6 Luna words each session from its turn plan through the Director's helper
  (scripts/claude_luna_codex.py, sha256 342a0fb7…024e, model gpt-6-luna), then one question and a short answer per
  asked fact of each fully kept chat. One writer for the whole set, recorded per row. The prompts give instructions
  and values only, never example sentences.
- **Code checks (no model judge).** A session is kept only if it has the planned number of messages from the
  planned speakers, each fact message holds its own required words, and no fact value, other person's name or date
  phrase appears in any other message. A chat is kept only if all its sessions are. A failed session is retried once
  at once, and each rerun of the command gives it one more try, up to 3 failed rows (6 calls). An error-like or
  empty reply is a failed call (the helper raises), never a row. A question is kept only if it does not give away
  its value (or a dated event's month or year), and a two-step question does not name the person.
- **Targets.** Luna's short answer is the training target. Code keeps it only if it contains the gold value (a dated
  answer: day, month and year), no other value of the same relation, and no negation word. The gold value is the
  code's; for a dated event, code computes the date from the session date and the phrase it planned. No Claude agent
  checks the targets (Ben's 16:39 rule). Practice-dev and panel rows carry the code's gold value, not Luna's answer.
- **Context (the RAFT part).** For each question: 20 lines from the same chat, the evidence message(s) plus the
  non-evidence messages ranked highest by BM25 against the question (hard distractors), laid out in chat order under
  session dates, exactly as claude_bm398d_evidence.context does for LoCoMo, with bm-390's system prompt and QA prompt
  (and its date suffix for dated questions). The evidence is always among the 20. Teaching "I don't know" is y1t's
  job and stays out of this test.
- **Size.** 18 questions per chat before code drops; 15% of kept training chats are held out as practice-dev (report
  only). If about 150 chats are kept, that is about 2,300 training items. Floor: at least 100 kept training chats and
  17 kept panel chats, else DATA-SHORT and nothing is trained.
- **Pilot gate.** The Mac job first words the first 5 training chats (up to three runs). It goes on only if at least
  3 of the 5 are fully kept; else PILOT-FAIL.
- **Training.** scripts/claude_bm398r_train.py unchanged: rank-16 LoRA on q/k/v/o, 1 epoch, AdamW 2e-4, 8 per step,
  loss on the answer tokens, seed 3992, thinking off. Run with --no-save, which only skips writing a merged copy of
  the weights (BensPC's disk gate); the adapter file is written as always. On BensPC, $0.

## Arms (the same 20 lines, layout and prompt; only the weights differ)
- **BN:** the plain 1B.
- **BR:** the 1B with the bm-398w adapter.
- Both run in one process: the plain 1B wrapped in bm-398i's on/off switch with the adapter loaded; off gives BN, on
  gives BR. The switch is a **hand-given stand-in switch (disclosed scaffolding)**: the panel decides on or off (on
  for LoCoMo and the practice panel, off for MMLU and GSM8K). There is no switch in the build; a switch or MoE in
  the build needs Ben's yes, and dl-9 is only testing whether a learned switch can work. In a CPU smoke here, the
  switch-off arm reproduced bm-398n's store-B replies byte for byte (2 of 2).
- Report only: Qwen3.5-2B on the same 20 lines, word-overlap F1 only (not judged), and only if it is already on
  BensPC (no download).

## Panels
1. **A fresh held-out panel (a panel that has driven no choice).** 20 chats from seed 3994, worded by Luna; 300
   questions drawn by seed 3995. Its file hash is sealed (SEAL-panel.sha256.txt) before training starts. It is never
   read by the builder and never used for any choice. Judged blind. It is written by the same writer, from the same
   code plan, as the training set, so R2 is in-distribution by design: it shows learning, not transfer.
2. **LoCoMo, all ten conversations, categories 1-4 with evidence (1,531 questions), store B's first 20 distinct
   turns** (rd-378L's ranked_turns.jsonl for 0-4, sha256 2792906c…97d4; rd-378u's for 5-9, sha256 785c9c9a…ff5e).
   Labelled "after development use": both halves drove retrieval choices (bm-398n, bm-398u, bm-398v). No
   reader-training choice has been made on LoCoMo, and the recipe is bm-398r's, unchanged. BN is re-generated and
   re-judged in the same blind panel as BR, not reused.
3. **General:** MMLU-Redux-300 and GSM8K-300 (bm-390's sets and prompts): the unwrapped plain 1B (P), then BN and BR.
4. **The Qwen bar from bm-398d's setup (report only).** BN and BR on bm-398d's 297 questions (all inside the 1,531)
   against Qwen's 138 (whole chat) and the 1B's 137 (right lines only). The layouts and judges differ, so this is a
   reference line, not a mark.
- **Judging.** INSTRUCTIONS.md (bm-398d's rubric: A right, B right plus a conflicting answer, C partly, D wrong, E
  doesn't know). Two Latin-square groups hold each of the 1,831 questions once per arm (seed 3996); 60 items are
  re-asked for a relabel check; 3,722 items in 75 batches of up to 50. Judges see the question, the gold answer, the
  evidence lines and one reply, never the arm. Byte-identical replies from the two arms count as one answer (both
  take group L0's label). Judge prompts forbid quoting any item text, examples included. An independent recount
  (its own script, reading only the key and the labels) follows.

## Marks (fixed now; claude_bm398w_eval.py verdict())
- **R1 (LoCoMo):** BR A ≥ BN A + 30 of 1,531 (about 2 points, the effect size of +15 of 759), with more gained than
  lost and a two-sided exact McNemar p < 0.05.
- **R2 (fresh panel):** BR A ≥ BN A + 15 of 300, more gained than lost, p < 0.05.
- **R3 (fewer-wrong guard on LoCoMo):** BR D ≤ BN D + 10, and no category's A drops by more than
  max(3, round(3% of its n)).
- **R4 (the stand-in switch):** on MMLU-Redux and GSM8K, the switch-off replies equal the unwrapped plain 1B's
  replies on all 600, and the right counts are equal, on the same machine. This checks the hand-given stand-in switch
  (disclosed scaffolding), not the adapter.
- **PASS** = R1, R2, R3 and R4. A PASS reads "the reader gains, given a switch", never "no harm". Anything else is a
  registered FAIL.
- **Proved wrong (it learned the practice form, not reading):** R2's gain is at least 15 while BR A ≤ BN A on
  LoCoMo. Also proved wrong if BR A ≤ BN A on both panels.

## Report only (no mark)
- MMLU-Redux and GSM8K with the adapter always on (BR), next to P. bm-398r's always-on adapter took GSM8K from 191
  to 20 and MMLU from 50 to 137 (MMLU mostly measures answer format for this 1B).
- On the 246 LoCoMo questions whose evidence is not among store B's 20 lines: A, D and E for BN and BR. Every
  practice item has its evidence among the 20, so training may make the 1B guess more here.
- F1, abstentions and confident-wrong counts; A split by whether the evidence is among the 20; A by category; the
  Qwen rows; practice-dev before and after (the trainer's dev check); A by question kind on the panel; relabel and
  identical-pair agreement; 95% intervals by conversation or chat.

## Predictions
- P1 (60%): R2 passes.
- P2 (15%): R1 passes. Point guess +12 of 1,531.
- P3 (60%): R3 holds.
- P4 (97%): R4 holds.
- P5 (12%): PASS.
- P6 (30%): proved wrong.
- P7 (80%, report only): with the adapter always on, GSM8K drops by 20 or more below P.
- P8 (60%, report only): with the adapter always on, MMLU is above P (answer format).
- P9 (55%, report only): on the 246 no-evidence LoCoMo questions, BR says "don't know" (E) less often than BN and
  is wrong (D) at least 5 more times.

## Limits
- The panel is in-distribution by design (same writer, same plan code); only LoCoMo speaks to transfer.
- The switch is a hand-given stand-in; it is not a build component and not a claim about routing.
- LoCoMo is development data here; LongMemEval stays untouched.
- The practice kinds are narrow (single facts, facts about a named other person, dated events). LoCoMo asks wider
  questions, so R1 is the hard mark.

## Open questions answered before sealing
- Overlap with y1t (Answering from memory, 05:29 UTC): none. Nothing there trains the 1B to read among store lines
  with distractors. y1t trains doubt on its own graded drafts from 0-7 earlier lines of short one-speaker chats;
  y1tH1 is evaluation only; y1r trains the MiniLM retriever (which lines get into the 20), not the reader. Their
  seed-4027 dialogs are free after their data gate, but at 1-8 kept user turns and one speaker they cannot give a
  20-line window of same-chat distractors, so bm-398w writes its own chats. If y1t goes GO, its adapter can run
  through bm-398v's BN arm as a report-only row for them.
- Seeds: Reading facts (05:27 UTC) says 320-329, 4027 and 1, 2, 7 are reserved and any other number is free. They
  asked for fresh seeds, not seed 324's rows, and both avoid lists.

## Order of work
1. Mac (the Director's queue, Luna, $0): plans, pilot, word, ask and build, for training and panel chats. Luna
   throughput sets the time: about 1,350 calls before retries; a guess is 3 to 4 hours with 3 workers, in runs of 70
   minutes (the builders' 80-minute command limit).
2. Here: SEAL-panel.sha256.txt (the panel file's hash, taken without opening it), committed before step 3.
3. BensPC ($0): train; then `claude_bm398w_eval.py locomo`, `panel`, `general` and, if present, `qwen20`.
4. Here: score, prep, blind judges, jscore, independent recount, RESULTS.md, sent to the Thread manager.

## Cost and owners
- $0: Luna through Ben's Codex plan, BensPC for training and GPU replies, blind judges as Opus agents. No rental.
- Benchmarks writes and runs it. Reading facts: seed world and avoid lists. The Director: the Mac Luna queue and
  BensPC's order.

## Plain summary for Ben
The small model answers well when it sees only the right lines of a past chat, but badly when those lines are
mixed with 19 others. Picking fewer lines didn't help, because the picker drops the right line too often. So this
trains the model to read the whole mix: practice chats written by Luna, questions whose answers code can check, and
each practice question comes with the right line hidden among look-alike lines. It passes only if it gets clearly
more right answers on fresh practice chats and on the LoCoMo benchmark, without more wrong answers. The trained part
is only switched on for memory questions by a switch we set by hand for this test; maths and general questions are
also checked with it always on, and that number is reported honestly.
