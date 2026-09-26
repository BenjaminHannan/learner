# How can a 1B memory assistant honestly beat 2B-class models on long-chat memory tests? (no code or file access needed)

You are an expert in small language models, retrieval-augmented answering, long-context evaluation and honest
benchmarking. You have **no access** to my code, files or machine, so everything you need is below. Do not ask me to
run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and
how it would change your answer, rather than guessing.

Rules for your answer:
- Mark every claim as **shown** (by the data below), **suggested** (your reasoning) or **untested**.
- Keep two kinds of evidence apart. The **full agent** is the 1B chat model with its memory parts, scored on public
  tests. **Small experiments** are tiny CPU nets and synthetic practice banks. A result on one says nothing about the
  other until it is tested there.
- Propose **one change at a time**. For each change, give the pass mark I should fix before running it, and the result
  that would prove the idea wrong.
- Don't just agree with my plans. Where you think a plan is wrong, say so and why.
- I am a high-school senior building this with AI help. End with a plain-language summary I can follow (section 9).

## 1. The project (Premonition)

Premonition is a small assistant meant to remember what it is told over weeks, never make up facts, say "I don't
know" when it doesn't know, and get better overnight by practising what it can check. Version 0.1 (frozen on
2026-09-24) has these parts:

- **Chat model:** MiniCPM5-1B, run with its thinking mode off. Greedy decoding everywhere below.
- **Notebook:** a fact store that holds only facts it was taught, each with where it came from. It answers memory
  questions only from the notebook, never from its own guesses.
- **Reader:** a small trained net that turns chat lines into notebook facts. It was built for facts about people and
  relations ("my sister is Mara"). It has an "am I sure?" gate: below a confidence bar it asks the speaker to confirm
  instead of saving.
- **Reasoner:** hand-written rules that look things up in the notebook. (A learned reasoner, a ~6.4M-weight net that
  thinks in rounds on puzzles, is being built separately. It is not in any build and is not part of this question.)
- **Sleep:** nightly practice on answers a checker confirmed. On the tests below it never ran on anything.
- **Turn log:** every chat line is logged, but 0.1 never answers from it.

The road map counts the whole 0.1 build at about 2.2B parameters. Because the chat model is 1B, I compare it with
~1-2B models.

## 2. The goal and the honesty rules

The goal is to beat same-size models on public benchmarks for real: no reward hacking and no practising the test.

- **LoCoMo** (long-conversation memory QA) is now a **practice** set. It has been used for development, so every
  LoCoMo number is labelled "after using LoCoMo for development".
- **LongMemEval** is the **final exam**. Nobody downloads or reads it until one registered run. Its public
  description: 500 questions in six types (single-session user, single-session assistant, preference, multi-session,
  knowledge update, temporal), some requiring "I don't know". The S version gives each question its own history of
  ~115k tokens (~50 sessions).
- **MMLU-Redux** and **GSM8K** (300 items each) are no-harm checks. The build must stay within 3 points of the plain
  MiniCPM5-1B on both.
- No LoCoMo or LongMemEval text, or anything built from it, may go into training data, practice sets or prompt
  choices. Improvements must come from general abilities, passed first on our own blind banks.
- Every arm gets the same prompts and the official scoring. Marks are registered and sealed before a run, and a
  failed run stays failed. A second scorer recounts every result.
- Text written by Claude (my coding assistant) is not used as training data. Allowed sources: code-made labels, the
  model's own drafts after grading, or an outside teacher model (GLM 5.3 Flash through an API).
- **Rivals:** plain MiniCPM5-1B, Qwen3.5-2B, LFM2.5-1.2B-Instruct. All run with thinking off, the same harness and the
  same text. Context windows: MiniCPM5-1B 131,072 tokens, Qwen3.5-2B 262,144, LFM2.5-1.2B 128,000. So every rival
  can read a whole LoCoMo chat, and on paper a whole LongMemEval history.
- Switching the base model to a bigger one is my decision, not a default. A 2B base would then be judged against 2B
  models, with plain Qwen3.5-2B as the bar.

## 3. The LoCoMo harness (as run)

- 10 conversations between two people. Each has 19 to 32 dated sessions, 5,882 lines in all (369 to 689 per chat).
  Scored on categories 1-4: 1,540 questions (multi-hop 282, temporal 321, open-domain 96, single-hop 841).
- **Whole-chat arms:** the entire chat goes in the prompt, about 24k tokens (median), in time order. Each line is
  written as `<Speaker> said, "<text>"` under a `DATE: ... CONVERSATION:` header per session.
- **Question prompt (the LoCoMo repo's own):** "Based on the above conversations, write a short answer for the
  following question in a few words. Do not write complete and lengthy sentences. Answer with exact words from the
  conversations whenever possible." Temporal questions get the suffix: "Use DATE of CONVERSATION to answer with an
  approximate date." The system prompt says to answer from the conversation and not share false information. At
  most 50 new tokens; only the first line of the reply is scored.
- **Score:** the LoCoMo repo's token F1 (lowercase, strip punctuation and articles, Porter-stem, bag-of-words
  overlap), times 100 and averaged over the 1,540 questions. Multi-hop answers split on commas.
  Saying "I don't know" scores 0 (categories 1-4 always have an answer).
- **Retrieval arms:** the plain 1B is shown only the top-k lines, in the same layout.
  - BM25 top 10.
  - The "memory store": every heard line kept word for word with its date, ranked by reciprocal-rank fusion of
    MiniLM embeddings and BM25, with the question as the query.
- LoCoMo marks which lines hold each answer (evidence). That lets me split scores by "an evidence line was shown" or
  not.

## 4. Results (LoCoMo categories 1-4, 1,540 questions, F1 × 100; after using LoCoMo for development)

| Arm | F1 | multi-hop / temporal / open-domain / single-hop | confident wrong* |
|---|---|---|---|
| Premonition 0.1 | 2.98 | 3.05 / 1.73 / 5.31 / 3.17 | 450 |
| Plain MiniCPM5-1B, no chat shown (guessing check) | 3.27 | 3.65 / 0.65 / 9.71 / 3.40 | - |
| LFM2.5-1.2B, whole chat | 19.01 | 19.46 / 22.91 / 15.24 / 17.80 | 660 |
| Plain 1B + BM25 top 10 | 25.06 | 13.63 / 26.93 / 12.06 / 29.65 | 615 |
| Plain 1B + memory store top 10 | 26.84 | 21.22 / 25.57 / 12.48 / 30.85 | 569 |
| Plain MiniCPM5-1B, whole chat | 27.50 | 24.37 / 19.46 / 16.07 / 32.92 | 467 |
| Plain 1B + memory store top 20 (k chosen on LoCoMo) | 29.85 | 25.58 / 27.34 / 12.92 / 34.17 | 498 |
| **Qwen3.5-2B, whole chat (the bar)** | **47.87** | 36.29 / 34.37 / 14.72 / 60.69 | 402 |

*Answered (did not say "I don't know") and shared no word with the gold answer.

Paired differences (bootstrap, 95% interval):
- 0.1 − plain 1B whole chat: −24.52 [−26.00, −23.08].
- Qwen − plain 1B whole chat: +20.37 [18.43, 22.32] (the second scorer's bootstrap).
- Store top 10 − BM25 top 10 on the same machine: +1.66 [0.31, 3.03]. That run was registered to need +3, so it failed.

**Where 0.1's points go (shown):**
- While reading the 10 chats, 0.1 saved 18 facts in total (0 to 4 per chat).
- 2,334 of its 6,164 replies while listening were "am I sure?" confirmation questions. In LoCoMo nobody answers them,
  because 0.1 is overhearing two other people.
- It said "I don't know" on 923 of 1,540 questions.
- Most LoCoMo facts are events, plans and dates, which the relation-shaped reader does not cover.

**Evidence shown vs not (plain 1B, 1,531 questions with marked evidence):**

| What the plain 1B is shown | evidence line shown | F1 when shown | F1 when not | overall |
|---|---|---|---|---|
| BM25 top 10 | 51.7% | 38.6 | 10.9 | 25.2 |
| Memory store top 10 | 65.7% | 35.8 | 9.7 | 26.8 |
| Memory store top 20 | 75.2% | 36.1 | 10.9 | 29.9 |

The store found evidence for 276 questions BM25 missed; BM25 found 62 the store missed. F1-when-shown is lower for
the store than for BM25. Why is untested; one guess is that the other lines it shows are near-misses by meaning.

**Tonight's diagnostic: are the 1B's answers wrong, or too long? (shown)**
Gold answers are 3 words (median; mean 4.3) after normalising. Token precision and recall are per-question means.

| Arm | reply words (median) | token precision | token recall | replies ≥ 3× gold length |
|---|---|---|---|---|
| Qwen3.5-2B, whole chat | 3 | 54.5 | 48.6 | 72 |
| Plain 1B, whole chat | 8 | 23.7 | 43.6 | 638 |
| Plain 1B + store top 20 | 6 | 27.6 | 39.7 | 413 |
| Plain 1B + BM25 top 10 | 5 | 24.5 | 32.7 | 384 |
| LFM2.5-1.2B, whole chat | 7 | 17.2 | 28.6 | 496 |

So on whole chats the 1B's recall is close to Qwen's (43.6 vs 48.6), but its precision is less than half (23.7 vs
54.5): it ignores "a few words".

Qwen's lead is also biggest on single-hop (60.69 vs 32.92) and temporal (34.37 vs 19.46). The plain 1B reading
everything beats the same 1B shown BM25's top 10.

**General tests (of 300 each):**

| | GSM8K (math) | MMLU-Redux |
|---|---|---|
| Premonition 0.1 | 29 | 85 |
| Plain MiniCPM5-1B | 191 | 50 |
| Qwen3.5-2B | 209 | 201 |
| LFM2.5-1.2B | 217 | 159 |

- **Inside 0.1:** 257 of 0.1's 300 GSM8K replies contain no number, because the agent treats a math problem like a
  memory question and abstains.
- **Plain 1B on MMLU:** it gets 16 new tokens and is asked to answer "with the letter of the correct option only".
  234 of its 300 replies name no letter, so its low MMLU score is mostly answer format.

## 5. Already in motion (please critique, don't just repeat)

- **Next build (0.2)** = 0.1, plus a grammar fix, plus:
  - the memory store (top 20 heard lines) as a fallback when the notebook has nothing;
  - a route that sends questions that are not about the user or their people straight to the plain 1B.
  The route is meant to recover GSM8K and MMLU. It keeps questions that name someone heard earlier in the chat on
  the honest path.
- **Reader save bar:** being lowered from 0.995 to 0.98. On the reading thread's own practice data this saved 771 of
  1,053 facts instead of 611, with the same 3 wrong saves. It will be confirmed on a fresh sealed panel.
- **Reader notes:** the reader is being changed to also write short plain-sentence notes about anything worth
  remembering (events, plans, opinions, who and when), each citing its source lines.
- Retrieval tuning on LoCoMo has stopped, to avoid overfitting the practice set.

## 6. Resources

- One home GPU (RTX 5070 Ti, 16 GB, Windows) and rented RTX 5090s.
- Budget: at most $4 per job and $30 for the whole project, most of it already spent. Fine-tuning a 1B with LoRA on a
  few thousand examples is affordable. Pretraining is not.
- An outside teacher model (GLM 5.3 Flash) can write or grade training data on general, non-benchmark material.
- Month-end target: 2026-09-30. The final exam comes later, when a build beats every rival on LoCoMo practice.

## 7. The questions

1. **The answering limit.** With the right line in front of it, the plain 1B scores only 36-39 F1. Reading the whole
   chat it scores 27.5, and Qwen3.5-2B scores 47.9.
   - How much of this gap is answer length, and how much is content (wrong span, wrong date, missed second hop)?
     Describe a count I can run on existing replies to split them, without reading or quoting benchmark items.
     (A second scorer is fine.)
   - What single, general change would fix the larger part? Examples to judge, not to adopt:
     - a separate answer-extraction step;
     - a LoRA fine-tune for "answer from these lines in a few words" on non-benchmark data from the teacher;
     - rereading the lines that were found.
2. **Honest vs gaming.** Shorter answers raise F1. Where is the line between a real skill (following "answer in a few
   words", which the question asks for) and gaming the metric? What second measure would show a real gain? For
   example, an LLM judge of correctness on a random sample, the same for all arms, set before the run.
3. **Beating 2B-class models from a 1B.** With the parts above, which levers could close most of the 20-point base
   model gap, and which are dead ends? Levers to consider:
   - memory (store and notes);
   - date handling;
   - multi-hop joining;
   - teacher-made fine-tuning;
   - honest abstention;
   - switching the base model.
   Rank them by expected gain per dollar, with your uncertainty, and say which is most likely to fail.
4. **Transfer to the final exam.** LoCoMo chats are ~24k tokens between two other people. LongMemEval histories are
   ~115k tokens of a user talking to an assistant, with knowledge updates, preferences, "what did you (the
   assistant) say", and questions that need "I don't know".
   - Which LoCoMo-driven choices are most likely not to transfer?
   - What should I test on my own blind banks first, without touching LongMemEval?
5. **The 0.2 plan in section 5.** What is most likely to go wrong with it, and what should its registered marks be?

## 8. The form I'd like

- A short diagnosis first. Then a ranked list of at most five changes, each a single change with:
  - what changes;
  - why;
  - its cost on the hardware above;
  - the pass mark to fix in advance;
  - the result that would prove it wrong;
  - a shown / suggested / untested label.
- Then the one you would run first.
- Keep full-agent claims and small-experiment claims separate throughout.

## 9. Plain-language summary for me

End with 5 to 8 short sentences a high-school senior can follow:
- why we lose;
- what to try first;
- what result would mean we were wrong.
