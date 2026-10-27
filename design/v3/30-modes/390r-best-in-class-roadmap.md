# 390r road map: best in class on public benchmarks (Benchmarks thread, 2026-09-25 ~03:00 UTC)

Ben, 01:49 UTC: "Make this model perform better on public benchmarks than other models its size."
Ben, 02:18 UTC: "architect a road map for how you plan to get to better on class."
This is the one whole-model road map for public benchmarks. 380 (joined agent) points here for the definition of
best in class; the part road maps (370 reader, 365 sleep, reasoner, 360 grammar, creative) are linked, not repeated.
Numbers: bm-390 to bm-399. Plan and marks for tonight's run: 390-public-bench-plan.md and
artifacts/claude-bm390-20260925/PASSMARKS.md.

## Short version (for Ben)
- We can honestly try to win on **long-term memory tests** (LoCoMo now, LongMemEval as the final exam) and later on
  **step-by-step reasoning tests**. Those measure the parts we built: the reader, the notebook, sleep, the reasoner.
- We can't honestly win on **general tests** (MMLU, GSM8K). Premonition answers those with MiniCPM5-1B, which
  already leads its size on its makers' own table. That lead is OpenBMB's, not ours. Our job there is "no harm".
- Tonight: **bm-390**, the starting line, runs on Ben's PC: Premonition 0.1 against plain MiniCPM5-1B, Qwen3.5-2B
  and LFM2.5-1.2B, all on the same code. My prediction (written down before the run): we lose on score and make
  fewer made-up answers. The reader is the main reason.
- Not by Sept 30. The final exam comes when a 0.x build beats every rival on LoCoMo practice; realistically October.

## What "best in class" means (the one definition)
A Premonition 0.x build (about 2.2B parameters today) beats **every** same-size rival on the LongMemEval final exam,
run once after its marks are registered, **and** stays within 3 points of plain MiniCPM5-1B on MMLU-Redux and GSM8K.
Rivals: plain MiniCPM5-1B with the whole chat in its prompt, Qwen3.5-2B, LFM2.5-1.2B-Instruct (Ben approved both
at 02:12 UTC), thinking off for all, same harness, official scoring. Published numbers from other same-size memory
systems (A-Mem with Llama 3.2 1B and Qwen2.5-1.5B on LoCoMo) are cited next to ours, labelled "different harness",
never counted as a win.

## The tests and their jobs
| Test | Job | Status |
|---|---|---|
| LoCoMo (10 chats, 1,986 questions; headline = categories 1-4, 1,540 questions, official F1) | starting line tonight, then our **practice test** | bm-390 queued on BensPC |
| LongMemEval (500 questions: 70 single-session-user, 56 single-session-assistant, 30 preference, 133 multi-session, 78 knowledge-update, 133 temporal; some marked abstention; the S version is ~115k tokens, ~50 sessions per question) | **final exam**, run once | untouched; nobody downloads or reads it. Counts are from the paper and repo summaries (search results), not checked in the PDF |
| MMLU-Redux-2.0 (300 seeded) and GSM8K (300 seeded) | **no harm** check on every run | in bm-390 |
| CLUTRR (kinship stories; practise 2-4 steps, test up to 10; CC BY-NC 4.0) | candidate public **reasoning** test for the learned reasoner, zero-shot | not downloaded; only checked that it is public. Our practice worlds already use family chains, so the report must say it is partly home ground |
| ARC-AGI-1 | parked | TRM gets 44.6% with 7M parameters after ~3 days on 4 H100s; far over the $30 cap |

## Which part moves which score
| Score | What it needs | Part and owner (road map) | Where it stands |
|---|---|---|---|
| LoCoMo single-hop (841), LongMemEval single-session-user (70) | save a fact when it is said; understand the question | reader: Reading thread (370: lis-318 retrain tonight, lis-319 context, rd-370 open relations, rd-371 learned checker, rd-372 question side) | 336: 57% of taught facts saved, 22% of answerable asks right |
| LoCoMo multi-hop (282), LongMemEval multi-session (133) | join two or more saved facts | reasoner: Sleep research (reasoner road map R2-R4, R7, R10); joins in 0.3 (380) | 336: two-step asks 8/37 |
| LoCoMo temporal (321), LongMemEval temporal (133) | know **when** each fact was said; date arithmetic | **gap, nobody owns it yet** (see below) + reasoner | shown: a saved fact has no date field (scripts/fable_notebook_contract.py:345-348); the date line reaches the agent only as a chat turn |
| LongMemEval knowledge-update (78) | replace an old fact with a newer one | notebook (a relation declared one-value keeps one value; the old row goes inactive) | untested risk: a new taught value without the word "correction" returns CONFLICT (fable_notebook_contract.py:337-341), so a plain "I moved to X" may not update |
| LongMemEval single-session-assistant (56) | recall what the assistant itself said | turn log (nb-323 keeps every reply) | untested: nothing answers questions from the turn log today; the notebook saves only what the user taught |
| Facts missed live | re-read the day at night with a better reader | sleep: Fix-sleep (365 stage 3, 362 parked until the reader improves) | parked on the reader |
| Not making things up (M3), abstention | say "I don't know" instead of guessing | whole agent (0.1's rules) | our expected lead; reported, never a win by itself |
| MMLU-Redux, GSM8K | no harm | think299b calculator vote, 338b chat | bm-390 measures it |

Grammar (360) and creative do not move these scores; they matter for Ben's conversation and creativity rows (380).

## Steps in order (each registered before it runs, one change each)
| When | Step | Gate to move on |
|---|---|---|
| Tonight | **bm-390** starting line on BensPC (P, T, Rb, C, Q2, L12; MMLU/GSM8K) | valid run; I score it, a blind Opus recount checks it, wins and losses reported |
| After bm-390 | diagnosis from counts only: which LoCoMo category loses most, how many facts P saved, how long reading takes. The single biggest lever goes to its owner through the coordinator | none; no LoCoMo text leaves this thread |
| Sept 26-29 | the parts pass on their **own** blind tests, not on LoCoMo: lis-318, then lis-319 and rd-370..373 (reader); 364/366 (sleep); R1-R4 (reasoner). New asks from here: **dates on saved facts** and **updates without the word "correction"**, proposed to the Reading thread with their own blind banks | each part's registered PASS |
| After 0.2 (380, bank C, by Sept 29) | **bm-391**: 0.2 on LoCoMo practice, same arms and marks as bm-390, labelled "after using LoCoMo for development" | P - rival >= 3 F1 points with the bootstrap interval above 0, for every rival; no harm |
| October | 0.3 (learned reasoner joined, 380) then **bm-392**: 0.3 on LoCoMo practice; CLUTRR zero-shot registered for the learned reasoner (hand-written rules for its domain switched off or reported apart) | same marks; CLUTRR marks fixed before download |
| When a 0.x beats every rival on LoCoMo practice | **bm-399**: LongMemEval final exam, registered and run once against the same rivals | the definition above |

Cost check before bm-399: P reads every turn, and LongMemEval gives each of its 500 questions its own ~50-session
history, so P may have to read hundreds of thousands of turns. bm-390's reading time per turn tells us whether BensPC
can do it in a few nights; if not, a faster reader is a road-map step, never a smaller or easier exam.

## Honesty rules (every step)
- Official data, splits and scoring code; deviations registered in advance (bm-390 lists five).
- Rivals run on our harness with the same text; published numbers are cited only, labelled "different harness".
- No LoCoMo or LongMemEval text, or anything built from it, in any training data, practice set or prompt choice.
  After bm-390, every LoCoMo number says "after using LoCoMo for development".
- LongMemEval stays sealed: nobody downloads, reads or quotes it before bm-399.
- Contamination check every run (arm C: the model with no chat; above 10 F1 points is flagged).
- One change per run; marks and predictions registered first; blind Opus recount; losses reported; a FAIL stays FAIL.
- Improvements come from general abilities (reading, dates, updates, reasoning), each passed on our own blind banks
  first, never from practising the benchmark's questions.

## Where we honestly can't win (this month)
- General tests: at best we tie MiniCPM5-1B, and its lead over same-size models is OpenBMB's work.
- Context length gives us no free win: MiniCPM5-1B holds 131,072 tokens, Qwen3.5-2B 262,144 and LFM2.5-1.2B 128,000
  (their config files), so each can read a whole LoCoMo chat and, on paper, a ~115k-token LongMemEval history.
  A memory win has to come from reading and answering better, not from the rivals running out of room.
- Open-ended reasoning against chat models: our learned reasoner works on symbols, not words, until R10.
