# bm-398r PLAN: a reader adapter trained on LoCoMo-length made-up chats (benchmarks thread, 2026-09-26 ~14:50 UTC)

Registered and sealed before any training or scored run. Before sealing, a 4-example smoke run on this CPU (bf16
weights, lines layout only, not scored) ran every step end to end: dev check, one step, adapter file, merge, save.
Every LoCoMo number is "after using LoCoMo for development". Counts only: no question, answer or reply is quoted.

## Why
Problem #4: past-chat answers are too long and right less often than Qwen. bm-398d (RESULTS.md there, recount
agrees) found where right answers are lost, blind-judged on 297 LoCoMo questions:
- Whole chat: the plain 1B is right on 109, Qwen3.5-2B on 138.
- Only the right lines: the 1B is right on 137. So finding the lines in a long chat costs about 28.
- Even with only the right lines, 160 are not fully right. Dates are right 17% of the time, multi-part
  questions 23%. Reading is the larger loss.
Its sealed "next" puts the evidence-trained reader adapter first. bm-397t's adapter taught brevity on short,
narrow practice (median 1.6k tokens, three question kinds, one date template) and was no more right (107 vs
112). The Mac agent's report (checked) blamed exactly that: short practice, few date phrasings, no why/how.

## The one change
A LoRA on the plain MiniCPM5-1B, trained once on code-made practice (scripts/claude_bm398r_data.py; training in
scripts/claude_bm398r_train.py):
- **Chats:** 22-38 dated sessions, about 15k-28k tokens (median about 21k; LoCoMo's are 14k-26k, median 24k).
  - Small talk comes from a template grammar (about 6,900 distinct lines in 12 chats).
  - Each speaker has about 14 facts of the same kinds with different values, plus named relatives.
    Every answer sits beside look-alike lines.
- **Eleven question kinds:**
  - single facts, why, how and opinions;
  - where someone lives now after two moves, and where they lived before;
  - what someone chose after nearly choosing something else;
  - dates said in 16 ways: today, this morning, yesterday, two days ago, last <weekday>, last weekend, last week,
    a couple of weeks ago, last month, last year;
  - lists of 2-5 said in different sessions;
  - a relative named in one session whose news comes in another;
  - a few questions with no answer in the chat.
- **Answers** are the shortest complete supported answer, made by code:
  - a calendar date when one day is meant, else "the week before <date>" and similar, "May 2023" or "2022";
  - "Not mentioned in the conversation" for the questions with no answer.
- **Weighting:** dates and multi-part questions are drawn three times as often (train: 432 date, 516 multi-part,
  852 other).
- **Layouts:** the same answer is taught from three layouts of the input:
  - the bm-390 harness's whole chat (450 examples);
  - bm-397t's chat log with its six instructions (150), so the adapter is not tied to one wording;
  - bm-395's store layout of the evidence lines, alone or among other lines up to 10 or 20 (1,200).
- **Recipe:** bm-397t's recipe, so only the data differs.
  - rank 16, alpha 32, dropout 0.05 on q/k/v/o;
  - lr 2e-4, 8 examples a step, one epoch (225 steps), seed 3992;
  - loss on the answer tokens only; thinking off.
  - Long inputs use gradient checkpointing, with logits only at the answer positions. The selftest shows both give
    the same loss and gradients.
- **Train and dev files:**
  - train: seed 3990, 150 chats, 1,800 examples, sha256 7e1ec301…f120;
  - dev: seed 3991, 20 chats, 240 examples, sha256 1f001546…ba58.
  - The dev set uses held-out names, towns, pet names and events, two held-out date phrasings and one held-out
    wording per fact kind. It is report only.
- Never trained on LoCoMo, LongMemEval, GSM8K or MMLU. No model output, teacher or Claude-written text is used.

**How it is used:** behind bm-398i's switch, on only for answering from a chat.
- Math and general questions go through the base weights. Once bm-398i passes, GSM8K and MMLU are unchanged by
  construction.
- If bm-398i fails, the adapter is kept as a separate merged copy for memory questions only, which costs a second
  1B in memory.
- The rows below with the adapter always on show the cost of a misrouted question. They are report only.

## Runs (one rental; the adapter stays on the Mac and is never pushed)
1. Train once. Dev check before and after (greedy, 50 tokens).
2. TR: the merged adapter reads the whole chat, via bm-390's sealed harness (`plain:MERGED`), on all 1,986 LoCoMo
   questions.
3. G, GD and E20 on bm-398d's 297, with the adapter (GR, GDR, E20R) and with the base on the same GPU (GB, GDB,
   E20B). Report only.
4. GSM8K-300 and MMLU-300 with the adapter merged (report only: the misroute cost).

## Scoring (this cloud machine)
- F1: `claude_bm398r_eval.py score`, the sealed bm-390 scorer, on all 1,540 category 1-4 questions. T is bm-390
  run2's plain 1B (locomo_T sha256 35bdf151…b3db).
- Blind check: `claude_bm398r_eval.py prep` and `jscore`.
  - bm-398d's rubric; judges see the evidence lines.
  - Three arms: T, TR and Q2 (Qwen3.5-2B, whole chat, bm-390 run2).
  - A Latin square, so each judge sees each question once.
  - 7 blind Opus judges in private folders: 6 main judges each take 3 batches of one group; 1 relabel judge takes
    X1 and no group.
  - Then a blind recount by a separate agent.

## Marks (fixed now)
- **R1 (more right answers, blind):** TR's A-count ≥ T's A-count + 15 on the 297, and the conversation-level 95%
  interval of TR − T is above 0 (seed 3993, 10,000 draws).
- **R2 (better scored):** TR's official F1 on categories 1-4 ≥ 32.50 (T 27.50 + 5), and the conversation-level
  95% interval of TR − T is above 0 (seed 3994).
- **R3 (not a refuser):** TR's category 1-4 abstentions ≤ T's + 20. T has 7, so the bar is 27.
- **PASS** = R1 and R2 and R3. Anything else is a registered FAIL.
- **Proved wrong:** TR − T ≤ 0 points blind. That would mean the adapter adds no right answers, as with bm-397t.
- **Report only:**
  - TR against Q2 blind (problem #4's bar);
  - F1 by category;
  - median words;
  - gained and lost;
  - the T-by-TR label table;
  - relabel agreement;
  - the evidence arms' F1 on the 297 (adapter vs base, same GPU);
  - GSM8K and MMLU with the adapter always on;
  - dev right by kind and layout;
  - training loss, tokens, seconds and peak memory.

## Predictions
- P1 (35%): R1 passes. Point guess: TR A-count = T's + 20.
- P2 (85%): R2 passes.
- P3 (85%): R3 passes.
- P4 (30%): PASS.
- P5 (10%): TR's A-count ≥ Q2's.
- P6 (70%): not proved wrong.
- P7 (80%): dev right rises by at least 30 of 240.
- P8 (60%): GSM8K with the adapter always on drops by 20 or more (report only; why the switch matters).

## What it leads to
- **PASS:** the adapter joins the memory path behind the switch, as one change handed to Month-end and
  "Answering from memory".
  - If bm-398e's trimmer passed, the trimmer is then tested on TR's replies.
  - A blind check of E20R against E20 follows for the agent's own path.
- **R1 fails but dev rose by 30 or more:** made-up practice does not carry over to real chat language.
  - Next, one change: practice chats in natural language written by the GLM teacher on the Mac, with answers
    checked by code against the facts it was told to include, and the same recipe.
  - It needs the Director to confirm the Mac can run the teacher.
- **Proved wrong:** training on made-up chats does not add right answers, and this route stops. Problem #4 then
  rests on the retrieval change (GD's ceiling: +31 on the agent path) and on the trimmer.

## Files
- scripts/claude_bm398r_data.py (selftest 16/16), scripts/claude_bm398r_train.py (selftest 6/6),
  scripts/claude_bm398r_eval.py (dry run on fake labels: score, prep 951 items and jscore all ran).
- The repository gets counts only: RESULTS.md, train398r.json, score.json and the judge key and labels.
- Judge work folders stay outside the repository.
