# Diagnose why nightly fine-tuning makes a small LLM stop reading its retrieved notes (no code or file access needed)

You are an expert in continual learning, LoRA fine-tuning, retrieval-augmented generation and memory consolidation. You have
**no access** to my code, files or machine, so everything you need is pasted below. Do not ask me to run anything before you
answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer.
Mark every claim as **shown by the data below**, **suggested**, or **untested**. Each number is from **one run (one seed)**,
so treat gaps under about 10 points as possibly noise.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow.

This is a separate project from my earlier small "card" experiments and my "village" model. Please don't mix them in.
It is a borrowed pretrained model (Qwen3.5-2B, thinking mode off) with a LoRA adapter trained each "night".

## 1. Goal
A personal assistant keeps every chat word for word in a searchable "diary" (BM25 over user turns, top 8 turns pasted into
the prompt, each labelled with its day). Each night, "sleep" fine-tunes a LoRA adapter so that facts that **keep coming up**
(seen on 2 or more days) move into the weights. The diary is never deleted. The design wants the slept model, **with** the
diary in front of it, to beat the plain model with the same diary.

## 2. The test world
- 7 simulated days, 982 chat turns written by an LLM. The user, "Sam", asks for everyday help, and facts about Sam's contacts come up in passing ("my neighbor Veikreim's boat, the Segaglix, ...").
- 120 facts across 6 relations: 40 mentioned on 1 day (C1), 40 on 2 days (C2), 40 on 4 days (C4).
- 20 facts change mid-week: an old value on days 1-3, a new value on days 4-7.
- 12 routines are told as episodes on 3-4 days and never stated as habits.
- Tests after night 7 use fixed templates that never appear in the diary or in training data. There are 120 forward questions ("Which boat does Veikreim own?"), 120 reverse questions, 27 two-hop questions ("Where does the mentor of Vudalal live?"), 20 "changed" questions and 12 "usually" questions. Each test runs twice: weights only (no diary), and with diary search.
- "Pooled" is all of these questions together. "Integration" is the mean of the two-hop, routine and changed-new scores.

## 3. The training recipe ("brain sleep", arm AB)
- **Tagging.** After each session the model extracts facts from user turns. An item is eligible for the weights only if it was seen on 2 or more days, or flagged important or as a correction.
- **Steps per night:** min(300, 40 + 4 x eligible items not yet consolidated). The realized schedule was 0, 136, 260, 300, 300, 300, 300.
- **Four cycles per night.** NREM takes 80%, 65%, 50% and 35% of each cycle's steps, and REM takes the rest.
- **NREM data.** For each eligible item, its diary turns (up to 4) go in context. The model writes 4 paraphrases and 4 Q&A pairs in both directions, stating the current value. Each Q&A is re-answered with the same turns in context and kept only if it matches.
- **The training examples are closed-book:** the question alone, then the answer.
- **Replay is weighted:** days_seen x (1 + importance + correction) x (1 + surprise) x 0.25 if consolidated. Each batch is about 75% new items and 25% rehearsal of consolidated items.
- **REM data.** Chained questions join two eligible items that share a name. Gist "usually" questions cover items seen on 3 or more days. Each is checked against the diary before it is used for training.
- **Loss.** LoRA r=16, alpha=32, lr 2e-4. Cross-entropy on the answer tokens, plus a KL guard to the adapter-disabled base model on generic prompts every step.
- **Downscaling ("SHY")** at the end of each night, per LoRA module: SVD of B·A, singular values x 0.85, drop any below 5% of the largest, and refactor to the same rank.
- **Consolidated:** the held-out probe is right 2 mornings in a row. A morning gate reverts the night's update if a 100-item ARC-Easy validation set drops more than 3 points.
- **Flat sleep (AF).** Each night trains on that day's turns only. It has no eligibility rule, no priority, no REM and no downscaling, and it uses AB's step counts.

## 4. Results (percent correct; one seed each)
Weights only:
| arm | C4 | C2 | C1 | two-hop | changed new/stale | routine | integration | pooled | ARC-Easy (500) |
|---|---|---|---|---|---|---|---|---|---|
| base | 0 | 0 | 0 | 0 | 0/0 | 0 | 0 | 0 | 89.6 |
| AB brain sleep | 67.5 | 52.5 | 0 | 11 | 70/15 | 67 | 49 | 39.8 | 89.6 |
| AF flat sleep | 45 | 30 | 15 | 0 | 75/0 | 58 | 44 | 26.1 | 90.6 |
| AB without REM (REM steps go to NREM) | 85 | 48 | 0 | 4 | 65 | 67 | 45 | 42 | ? |
| AB without downscaling | 82 | 42 | 0 | 4 | 60 | 75 | 46 | 41 | ? |
| AB with uniform replay | 82 | 32 | 0 | 15 | 65 | 67 | 49 | 39 | ? |
| AB with every item eligible (the 2-day rule off; this also means more steps) | 85 | 55 | 40 | 4 | 65 | 75 | 48 | 53 | ? |
| AB + open-book rehearsal (50% of Q&A examples show the BM25 top-8 diary turns before the question) | 80 | 40 | 0 | 11 | 70 | 75 | 52 | 38 | ? |
| AB + KL guard also on ~100 diary-format prompts per night (base model answers as targets) | 75 | 42 | 0 | 22 | 60 | 67 | 50 | 38 | ? |

With diary search:
| arm | C4 | C2 | C1 | two-hop | changed new | routine | pooled |
|---|---|---|---|---|---|---|---|
| base + diary | 100 | 92 | 80 | 7 | 100 | 100 | **84.6** |
| AB | 82 | 80 | 55 | 4 | 75 | 83 | 65.9 |
| AF | 35 | 35 | 15 | 4 | 40 | 75 | 32.1 |
| AB without REM | 92 | 85 | 55 | 11 | 75 | 75 | 71 |
| AB without downscaling | 68 | 52 | 10 | 4 | 40 | 92 | 40 |
| AB with uniform replay | 98 | 82 | 72 | 11 | 75 | 100 | 76 |
| AB, rule off | 90 | 92 | 75 | 11 | 80 | 92 | 77 |
| AB + open-book rehearsal | 100 | 98 | 80 | 11 | 95 | 100 | **85** |
| AB + KL on diary prompts | 100 | 90 | 78 | 7 | 100 | 100 | 83 |

A router was also tested. It used the open-book adapter's answer when the first answer token's probability was 0.5 or more,
and otherwise used base + diary. It scored 60 pooled (57 with the KL-on-diary-prompts adapter).

## 5. Questions
1. Why does closed-book fine-tuning make the model worse at using facts that are pasted into its prompt, falling from 84.6 to 65.9 and to 32.1 for flat sleep? Rank the candidate mechanisms. Examples: learning to ignore context; parametric answers overriding the context; a format shift; damage to attention or retrieval heads from the LoRA targets. For each one, give the cheapest test that would separate it from the others.
2. Removing the downscaling step hurt diary use the most, 40 against 66. What would explain downscaling **protecting** in-context reading? Is the gap likely to be real, given one seed?
3. Turning the 2-day rule off scored best overall, but it trained on more items for more steps. How would you test the rule fairly?
4. Two-hop stays at 0-22 everywhere, with or without the diary, even though one-hop recall is 80-100 with the diary. What is the most likely bottleneck? Would multi-step retrieval (look up, then look up again) be the right next step, rather than more sleep?
5. Propose **one change at a time** (at most three changes in total) to raise "slept model + diary" clearly above "base + diary". For each change, give a pass mark fixed in advance and the result that would prove the idea wrong.

## 6. Plain-language summary for me
Explain in a few short paragraphs, for a high-school senior, why studying with the book closed might make a model ignore the
book when it is open, and what the single best next experiment is.
