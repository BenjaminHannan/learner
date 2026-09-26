# Prompt for GPT (web): a 1B chat model with memory makes things up about the user; what to try first?

(Written 2026-09-26, committed 23:45 UTC (date -u) by the "Making things up about you" thread. GPT cannot see the repo, so everything it needs is below.)

---

You are an expert in small language models, retrieval-augmented chat and fine-tuning for faithfulness. You have **no
access** to my code, files or machine; everything you need is pasted below. Do not ask me to run anything before you
answer. If a fact you need is missing, say exactly what it is and how it would change your answer. Mark every claim
as **shown by the data below**, **suggested**, or **untested**.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

This question is only about the chat model (the "talker") described here. Please don't mix in ideas from other
experiments or architectures I haven't described.

## Setup
- Talker: MiniCPM5-1B (a 1-billion-parameter chat model), plain (no fine-tuning), greedy decoding, 160 new tokens,
  thinking off, a short fixed system line.
- Test panel: 60 two-session DEV chats. In session 1 the user mentions 3 facts about themselves, e.g. a pet's name, a
  job, a home town, an allergy, a relative's name, or the day of an event. Code chose the facts; the user turns were
  written by an AI writer. Session 2 has 5 user turns in fixed kinds: small talk ("hello again"), a feelings turn, an
  advice request, a follow-up, and a last turn asking for one stored fact ("what's my cat called again?"). Only
  session 2's replies are scored.
- Arms (the only difference is where session 1 appears):
  - N: no memory; session 2 only.
  - W: session 1's user lines as a block ('User said, "..."' per line, under a short header) in the SYSTEM message.
  - U: the same block at the top of the LATEST USER message on every session-2 turn, then a blank line, then the
    user's actual turn. Earlier session-2 turns stay as plain history.
  - H: both sessions as ordinary chat history.
- Scoring:
  - "Asks right": the last-turn reply contains the stored value (code check, 60 possible).
  - "Claims": two blind judges read each (arm, chat) transcript, with arms mixed and shuffled. Each flags every reply
    that states or assumes something specific about the user that the user never said (in either session), or that
    gets a stated fact wrong. C = flags summed over both judges and 300 replies. A blind recount matched exactly.

## Results

| Arm | Asks right (of 60) | C (two judges) | replies flagged by both | by either |
|---|---|---|---|---|
| N | 0 | 46 | 20 | 26 |
| W | 4 | 31 | 11 | 20 |
| U | 12 | 166 | 77 | 89 |
| H | 1 | 56 | 23 | 33 |

- Per chat, U has more flags than W in 34 chats, fewer in 9, tied in 17 (sign test p 0.0001).
- Flags by turn kind:

| Arm | smalltalk | feelings | advice | follow-up | ask |
|---|---|---|---|---|---|
| N | 0 | 5 | 13 | 16 | 12 |
| W | 4 | 5 | 9 | 12 | 1 |
| U | 39 | 35 | 29 | 31 | 32 |
| H | 17 | 4 | 15 | 11 | 9 |

- Post-hoc and suggested:
  - 75 of U's 300 replies contain one of the chat's stored values; they carry 58 of U's 166 flags.
  - Only 1 of U's 300 replies names a made-up value from the fact lists.
  - Reading 10 flagged U replies that name no stored value, most answer the memory block instead of the user's
    current turn. Examples:
    - "hello again" got "I'm glad to hear you're having a good week", although the old chat said "long week
      already".
    - "What's my cat called?" got sympathy about the grandmother's texts from the old chat.
    - "What's my tortoise called?" got advice about stepping on a dance partner's feet, from the old chat's salsa
      dancing.

## Constraints
- Training data may come only from a GLM model (GLM 5.3 Flash through an API) or from code. Nothing a model trains on
  may be written or judged by Claude.
- Compute: one RTX 5070 Ti 16 GB. LoRA is fine.
- No hand-written rules in the talker (for example, no regex that strips memory on small-talk turns).
- Bigger talkers are out of scope for this question.

## My current plan (please critique)
1. Rejection-sampling fine-tuning.
   - The 1B samples 4 conversations per practice chat, using the U input.
   - GLM marks each reply for made-up claims. GLM must first pass a gate against the blind judges' flags on the
     transcripts above.
   - On ask turns, code keeps only replies that contain the stored value.
   - LoRA training on the kept replies.
2. If GLM fails its gate: distillation. GLM writes the replies itself, given the same memory block and told to answer
   the present turn and use memory only when needed. The 1B trains on those.
3. If step 1 fails: DPO on kept vs dropped samples of the same turn.

## How I'd like the answer
- Propose one change at a time, each tested against the same plain model on the same test chats.
- For each change, fix its pass mark in advance and say which result would prove it wrong.
- Mark every claim as shown by the data above, suggested, or untested.

## Questions
1. What best explains U's rise in made-up claims? Candidates:
   - the model can't tell remembered text from the present turn;
   - lost-in-the-middle, or recency pulling attention to the block;
   - small-model over-use of any context it is given;
   - something else.
   For each, name a cheap test on the data above that would tell them apart.
2. Given the constraints, which single change would you test first, and why? Consider: rejection sampling on own
   replies, distillation from GLM, DPO, training with distractor memories (RAFT-style), or a learned retrieval step
   that passes memory only when the turn needs it.
3. For your pick, give:
   - a pass mark fixed in advance;
   - the result that would prove it wrong;
   - the most likely way it could pass while still being wrong (e.g. bland replies that avoid all claims).
4. Is a practice set of ~200 chats (~1,000 turns, 4 samples each) enough for a LoRA on a 1B, and what dose would you
   expect to need?
5. A plain-language summary for me at the end.
