# Notebook-1: does premonition's notebook beat plain search for remembering a user? (pre-registration, 2026-10-24 ~02:50Z)

Labels: shown / suggested / untested. This is neither the village model nor the card experiments. It tests one
premonition mechanism (the notebook: write dated notes as you go, read them back later) on a public
assistant-memory benchmark, as the first step toward the MacBook assistant.

## Why
Premonition's founding idea is a memory that is written during the day and read back later. No thread is testing
it for the assistant: Sleep-1 moves 120 taught facts into weights, Tricks-1 looks things up in Wikipedia. Nobody has
measured remembering what the *user* said across weeks of chats, including facts that change ("I moved to Boston").

## Data
LongMemEval-S (cleaned, `xiaowu0162/longmemeval-cleaned`, `longmemeval_s_cleaned.json`): each question comes with
~50 past chat sessions (~115k tokens), a few of which hold the evidence. Sample: 10 questions per question type
(6 types: single-session-user, single-session-assistant, single-session-preference, multi-session,
knowledge-update, temporal-reasoning) = 60 questions, `random.Random(0)` over question ids sorted. Abstention items
(`_abs`) are kept where the sample draws them.

## Stand-in models (untested for the local model)
Writer, reader = `claude-haiku-5-5` (effort low), judge = `claude-sonnet-5-5`. This isolates the memory FORMAT with
the reader held fixed. The local Qwen3.5-4B / 35B-A3B replaces writer and reader in Notebook-2 on Ben's PC/Mac.

## Arms (one change between neighbours)
- F  full history: all sessions, dated, in the prompt (long-context baseline; a 4B on a Mac cannot do this fast).
- R  plain search: BM25 over user+assistant turn pairs, top 10 pairs with their session dates.
- N  notebook: after each session the writer reads that session alone and writes short dated notes about the user
     (facts, plans, preferences, changes, and things the assistant told them). BM25 over notes, top 20, shown in date
     order, reader told later notes replace earlier ones.
- O  oracle: only the evidence sessions (ceiling for the reader).

## Pass marks (fixed now)
- P1 N >= R + 8 points overall (60 questions).
- P2 N >= R on knowledge-update + temporal-reasoning together (20 questions).
- P3 (speed-relevant) N's prompt is <= 1/20 of F's prompt tokens on average, and N >= F - 10 points.
**Wrong if** N <= R overall: writing notes adds nothing over searching raw chats, so the notebook is not worth
building into the assistant in this form.

One seed, 60 questions: differences under ~10 points are within noise (binomial SE ~6 points per arm); report
paired counts. Cost cap: $10 of Claude API credit.
