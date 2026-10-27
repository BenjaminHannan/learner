# JEPA and Premonition (research write-up, 2026-09-28)

Labels: SHOWN = I read it on the paper's arXiv abstract page today. FROM-MEMORY = my recollection, not re-checked today. SUGGESTED = argument, no test. UNTESTED = nobody in this project has run it. No experiment was run for this write-up. I did not read the reasoner code, so the insertion point below is a design guess.

## 1. What JEPA is
Predict the embedding of a hidden part of the input from the visible part, instead of predicting the raw pixels or tokens. The target embedding comes from an encoder, and something must stop the encoder collapsing to a constant. Older versions use a slow-moving copy of the encoder (EMA) plus stop-gradient. LeJEPA replaces those with SIGReg, a regulariser that pushes embeddings toward an isotropic Gaussian, about 50 lines of code, no teacher (SHOWN, arXiv 2511.08544).

## 2. Family, in order
- LeCun 2022 position paper (FROM-MEMORY). I-JEPA (image blocks), V-JEPA and V-JEPA 2 (video; V-JEPA 2 adds action-conditioned robot planning) (FROM-MEMORY).
- VL-JEPA, ICLR 2026: predicts text embeddings instead of generating tokens, 1.6B parameters, matches classical VLMs on four VQA sets (SHOWN, arXiv 2512.10942, from the search summary).
- LLM-JEPA (2509.14252): an extra loss "two views of the same thing embed alike", added to normal fine-tuning of pretrained Llama3, Gemma2, OpenELM, Olmo. Beats plain fine-tuning on NL-RX, GSM8K, Spider, RottenTomatoes (SHOWN, abstract only; loss form and compute not checked).
- LeWorldModel (2603.19312): ~15M parameters, one GPU, next-latent error plus SIGReg, visual control (SHOWN in this repo's own note design/research/final-sweep-2026-09-19/05-alternatives.md:21).
- Causal-JEPA (ICML 2026): hide whole object slots, ~20% absolute gain on counterfactuals (as cited in design/research/2026-09-18-novel-mechanisms.md:38).
- Semantic Step Prediction (2604.18464): a latent-prediction regulariser on LLM hidden states at reasoning-step boundaries; the abstract reports 168x lower multi-step latent prediction error than frozen baselines on ProcessBench. That is a latent-error number, not an accuracy number (SHOWN).

## 3. The warnings (they matter more than the wins here)
- Language paradox (2607.23531): squared-error latent prediction collapses when several completions are valid, so text needs a way to keep multiple alternatives (SHOWN, abstract).
- LeWM reproduction (2608.10145): one-step latent error fails to rank long-horizon planners (SHOWN via 05-alternatives.md:23; narrow evidence, one seed). So never judge a JEPA change by its latent loss, only by answers.
- PSG-JEPA (2608.06799): forward prediction alone was not enough for robot world models; extra grounding losses were needed (SHOWN, abstract).
- Astra's earlier review (reviews/astra-review-2026-09-18.md:105): compare against ordinary masked prediction at the same cost first.
- Most wins are vision, or big pretrained LLMs used as fine-tuning aids. Nothing found is a ~2M from-scratch looped reasoner. Any claim of gain at that size is UNTESTED.

## 4. Already covered in this repo
JEPA was scoped in three earlier places and never run: knock-out prediction (novel-mechanisms.md:28-38, ranked first there), event-conditioned latent prediction (05-alternatives.md:57, "plausible, reject now" because the bottleneck was exact selection), and a JEPA card-writer term (broad-sweep idea 81, "run after pool controls"). All of those were for the old village/card-store design. The current reader -> looped reasoner -> talker has no JEPA in it. Nothing in design/research/standing/ mentions it.

## 5. Where it could plug into the current design
The puzzle answers are exact and checkable, so JEPA's usual selling point (skip unpredictable detail) is weak: a plain answer loss already gives a clean target. The distinctive thing JEPA offers is a training signal that needs no labels. Ben's premise is a model that improves with use, and use produces unlabelled inputs. That is the angle worth testing.

A. Sleep signal on unlabelled inputs (best fit; items 3, 4, 5). During sleep, take the day's puzzle inputs (no answers), hide one part (a cell, a row, an entity), and train the reasoner's latent for the visible part to predict the latent of the hidden part, with SIGReg against collapse. Question: does this make the net learn a new kind faster from a few labelled examples, without hurting old kinds? SUGGESTED, UNTESTED. Ties directly to the F_eq ruler and the 3-draw sleep gates.
B. Loop-state prediction (item 2; weak). Ask loop step t to predict the state at t+k, as a regulariser and possibly a stop hint. Risk: the loop is already trained to end at the answer, and a predictor can be satisfied by a fixed point. SUGGESTED, low.
C. Reader/talker side (item 1; parked). LLM-JEPA style two-wording loss for the talker, or the card-writer term (idea 81). Not needed until end-to-end runs.

## 6. Cheapest honest test of A (one change, marks fixed before running)
Three arms, same net, same sleep steps, same unlabelled maze inputs, then the F_eq and F_few rulers on mazes: (0) sleep as now; (1) comparator: masked-cell token prediction, same cost; (2) JEPA latent prediction with SIGReg. Only arm 2 minus arm 1 counts as evidence for JEPA. Rows: F_eq and F_few, old-kind gates (sums, grids), a collapse check (per-dimension spread of the target embedding above a floor), plain same-size net control, mean of 3 sleep draws.
- Bars: reuse the lr thread's measured noise bars (F_eq +8.0, F_few +10.5, per the 21:50 board line; recheck before sealing). 2+ seeds; "every seed" reading for rejection.
- Wrong if: arm 2 does not beat arm 1 by the bars in both seeds, or the embedding collapses, or old kinds lose points. Mazes with tied directions have several valid answers (R2g), which is exactly the case the language-paradox paper warns about; report that split.
- Cost: unmeasured. Needs a new Learner plug-in (a second head and a SIGReg term) on the loop code and a CPU/GPU job through the queue. I did not price it; if it would cost $0.50 or more on vast, Ben's OK is needed.
- My odds that arm 2 beats arm 1 by the bars: about 1 in 6 (guess, no data). Why still worth it: it is the only idea I found that gives sleep a learning signal without labels, and it scales by construction (more use = more unlabelled inputs).

## 7. Recommendation
Do not add JEPA to the architecture. Send the arm test in section 6 to the Director as a proposal, to run after the sleep tests (dst-*) and the patch race free the Mac queue. Architecture changes stay Ben's call. If the arm-2-minus-arm-1 gap is not shown, drop JEPA for the reasoner and keep only idea C as a later talker option.
