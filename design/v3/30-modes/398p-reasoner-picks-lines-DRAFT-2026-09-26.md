# 398p DRAFT: the reasoner picks which lines the talker reads (benchmarks thread, written 2026-09-26 18:19 UTC)

A draft, not a registered test. It goes to the Thread manager and the owners named below only if bm-398n shows that
better notes don't turn into more right answers. If bm-398n passes, the notes path goes to Month-end and Answering
from memory instead, and this waits.

## Why (evidence, all blind, LoCoMo dev)
- bm-398d: given only the right lines, the plain 1B is right on 137 of 297, and Qwen3.5-2B reading the whole chat on
  138. The 1B reading the whole chat gets 109, and the store's top 20 lines 88. The 1B can read. What it lacks is the
  right lines.
- bm-397t, bm-398r and bm-398e: shortening answers raised word overlap but not right answers. bm-398c: prompted
  copying at 1B doesn't make a tool route work.
- rd-378u (Trustworthy notes): notes lift finding (any@10 489 → 585 of 772 on unseen chats). But the ranking is
  still a fixed recipe, not a learned choice.
- Ben's design: the reader and talker only translate; the learned reasoner decides. Deciding what to recall for a
  question is a reasoner job.

## Brain first (a textbook-level guess, not checked)
Recall is a loop. A cue brings back part of an episode (hippocampal pattern completion). Prefrontal cortex checks
it against the goal and, if something is missing, uses what came back as a new cue. Multi-hop questions ("where did
the person she met at the gym move to?") need that second pass. A looped net that updates a state over rounds fits
"retrieve, check, re-cue" better than one ranking pass. Silicon can do better than biology here: the lines it picks
are exact and carry pointers to the raw turns.

## The one change (sketch)
- Inputs: the question and up to N candidate lines (the chat's turns, or rd-378u's notes with their pointers). Each
  is a vector from the frozen 1B reader.
- Reasoner arm: a 358-family loop net (Sleep research's code and size rules) reads the set, runs its rounds, and
  outputs a score per line. The top k lines go to the plain 1B talker, laid out as bm-398d's G arm.
- Plain twin: a same-size, non-looped net with the same inputs and training. Ben's rule: judged against same size.
- Fixed recipe: store v4 ranking (rd-378u) with the same k.
- Training data: lis-320's GLM-worded dialogs (Reading facts). Their seeds already mark, by code, which turn holds
  each fact. The questions must also be GLM-worded from code seeds; code templates written by Claude don't count.
  Labels are "the turn(s) the seed put the fact in". Nothing from LoCoMo or LongMemEval, and nothing written or
  judged by Claude.

## What it would measure (marks to be fixed before any run)
1. Finding: any@k and all@k on LoCoMo categories 1-4 (reasoner, plain twin, fixed recipe). Multi-hop (category 3)
   is reported on its own, since the loop should help most there.
2. Answers: blind A on bm-398d's 297, with the talker given the picked lines. Compared with the 1B on the whole chat
   (109) and with Qwen (138). The D and E no-harm rows are included.
3. Carry-over (Ben's transfer goal): how few practice dialogs the reasoner needs on a new kind of question after
   practising others, against a fresh net.

## Owners (to agree before anything is written)
- Sleep research: the loop net, its size and its exit rule. The concrete question for them: can a 358 net take a
  set of line vectors plus a question vector and give per-line scores, and at what width?
- Reading facts: the GLM dialogs and seeds (lis-320), and GLM-worded questions.
- Trustworthy notes: the store v4 baseline and the note pointers.
- Answering from memory: the recall path this would replace or feed.
- Benchmarks: the measurement (finding counts, blind answers, the rival bar).

## Cost
- Training two small nets (reasoner and twin) and one GPU pass for the vectors: a rental well under the $0.72 left
  in this thread's $2. To be measured on a slice before sealing (the bm-391 lesson).
