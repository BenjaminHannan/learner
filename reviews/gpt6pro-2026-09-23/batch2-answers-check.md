# GPT-6 Pro batch 2: what the 17 answers say, and what holds up (2026-09-23)

Checked by the research thread against the repo and builder-outbox, 10:25-10:45 UTC. Answers: `batch2-answers.md` (verbatim). Question 18 (web mode) has not come back yet.
No blind-panel item was opened for this check. Only the board, design notes, RESULTS/PASSMARKS files, the relation table and gate code were read.

## Result first

1. **Two of my prompts had wrong facts, and GPT caught both.**
   - **Baseline size (Q11).** GPT said a 33M baseline can't match a ~62M system. The plan already sizes every baseline at 61,783,680 against a system total of 61,783,463 (`design/v3/50-own-model/01-own-ear-mouth-plan.md` §7.1). My prompt wrongly said "about 33M". The plan was right; the prompt was not.
   - **O0a miss counts (Q2).** GPT noticed that the reasons added up to 89, not 88. The real table (o0a RESULTS.md) is: no relation cue 58, OTHER 12, WE 10, typo 5, DENY value not repeated 2, owner 1, total 88. The board summary line ("59 / 7 / 1") had merged these wrongly.
2. **Part of the speed advice is already done.** The gate already sends `cache_prompt: true` and reads one token (`n_predict 1`, first-token log-probabilities). Thinking is closed in the template. P(YES) is pYES/(pYES+pNO) (`scripts/claude_earcheck261_checker.py:6-42`, `_qwen.py:5-32`). So GPT's CACHE-PRESERVE-01 would stop at its own "is caching already on?" check. What's left is measuring how many prompt tokens actually get reused. Reordering the prompt so the shared part comes first would be a real (semantic) change.
3. **A real flaw in experiment 267, confirmed.** GPT said pick-1-of-4 "picking the other name" on plural turns may not be an error. The 267 REPORT confirms it: all 14 plural frames the ear kept were correct (0 wrong of 14). The "other name" option was the swapped name, which is also true in "Mira and Tal are my sisters". So the "breaks on a second name" finding is partly a test-design fault. It isn't evidence that the checker misreads.
4. **The relation-table worry is mostly already handled.** GPT warned that "inverse" might be treated as a two-way equivalence (mother ↔ child). In table v2, mother's inverse is a never-store question "Who are {Y}'s children?" that collects mother and father facts. `narrower` is one-way (dog, cat ⊂ pet; wife, husband ⊂ spouse, with the note "a wife fact answers a spouse question, not the reverse"). New small defect found while checking: `dog` has `value_kind: person` while `pet` has `literal`. That doesn't look intended.
5. **The O0a builder had already answered part of Q2.** Its "even if" arithmetic: plural folding rescues 26 list facts → 210/272 = 77.2%; plural + WE→ME → 219/272 = 80.5%. So plurals alone can't reach 85%. Verb constructions (and the 12 OTHER relations) are needed. GPT also pointed out that if "held back" counts every unsaved true fact, the recall bar is really **88%, not 85%**. That's correct arithmetic (1 − 12% = 88%), and our marks should pick one reading.
6. **The QA gate's 30.4% held back** (GPT said it couldn't rebuild it) is 38/125 = 37 statement frames QA held + 1 held by the guard (earcheck264 PASSMARKS M3b). It counts frames held, including some wrong ones. It isn't 1 − recall.
7. **The comparison benchmark (Q11) is 5 families × 500 worlds** (two_hop, reversal, abstention, mquake_edit, long_chain; task-own-o0f-bench.md). GPT's power figure (about 444 worlds per claim to detect a 5-point gap at q=0.1) fits 500 per family, but not a noisier q=0.3 (about 1,336). Caveat: the worlds come from 30 or more templates per family, so they test template generalisation, not free wording.

## Each answer: its one next experiment, and my verdict

| Q | Topic | GPT's one next experiment | Verdict |
|---|---|---|---|
| 1 | Gate on fresh wording | Frozen-score threshold rescue: fit one cutoff on 150 fresh calibration turns, test on 3 new writers × 150; also compute the best hindsight cutoff to see if **any** threshold could work | **Adopt, high priority.** Cheap (no new model); it settles "threshold problem vs reader problem". |
| 2 | Write rules 67.6% | Cue-v1 permission audit (plurals + verb constructions), measuring both coverage and whether wrong readings can pass; 88% bar | **Adopt as a change to the queued own-o0a2.** Add the "can a wrong ASSERT pass?" challenge half. Builder arithmetic already shows plurals alone fall short. |
| 3 | Speech acts | Per-fact write-permission detector (small own encoder, 4 layers × 256) as a veto before commit, 400 paired families | **Adopt later.** Good idea, but it needs a data pipeline first (Q4). The per-fact (not per-turn) point fits the own-ear plan. |
| 4 | Own ear on synthetic data | Matched-data swap on ear v4.1: templates vs scenario-first + contrasts + adversarial data, 3 seeds, 600 fresh turns | **Adopt, high priority.** Separates "bad data" from "small model" before any GPU spend on the own ear. Cost: about 67 h of teacher generation at an assumed 50 tokens/s, so start at 20k examples. |
| 5 | Question reader | Typed query language + compositional reader, run in shadow on 360 fresh questions, 0 wrong accepted | **Adopt as the reasoning line's long-term plan.** Very large build; run it in shadow only. |
| 6 | Evaluation | EVAL-GOLD-01: source-first answer-key audit with 40 planted bad keys + 40 good keys + 100 owner-checked turns | **Adopt, but needs Ben.** It asks Ben to label 100 turns by reading them (no commands). Ask him first. A scorer preflight on hand-made fixtures can start now without him. |
| 7 | Plural binding | Guarded coordination constructor for explicit relative lists, 500 turns | **Adopt, but after Q1.** It adds another hand-written stage, which is the kind of patch Q5 warns about. |
| 8 | Own mouth | Learned chooser over the existing small-talk replies only; 600 contexts | **Adopt, low cost.** It uses talker101, which is ours. |
| 9 | Corrections | Typed edit transactions + history, tested with perfect (oracle) inputs first; then English correction pairs | **Adopt Piece 1.** Useful before the ear gets delete powers. |
| 10 | Casual typing | Retrain ear v4.1 on raw casual text (8k examples); no normaliser | **Adopt.** Matches the 270 lesson (the normaliser itself added wrong saves). |
| 11 | Fair comparison | Shared-notebook answerer swap: Qwen answers from the same notebook, 500 worlds | **Defer.** The baseline size already matches. The swap would use up 500 test-only worlds for a diagnostic, so use a dev set instead. |
| 12 | our/we | Oracle test of group-owner storage (group entity + membership, no copying facts to members) | **Adopt after 269-resume finishes.** |
| 13 | Honest replies | Evidence-checked reply adapter, 400 episodes | **Adopt later.** Overlaps with the 280/255b work. |
| 14 | Relation vocabulary | Source-preserving provisional relations with unknown properties, oracle audit | **Adopt later**, after Q2. |
| 15 | Merging pieces | Contract-aware merge checker run in shadow against 42 constructed good and bad merges | **Adopt, medium.** Would have caught the 138p wording clash earlier. |
| 16 | Speed | Paired interleaved (ABBA) timing with bootstrap bounds; prefix-cache test | **Adopt the timing protocol** for future speed marks. The cache test is mostly moot (point 2). |
| 17 | Sleep | Shadow LoRA ear adapter with replay; release check must reject both "no change" and "1 wrong save" | **Defer.** Sleep isn't the bottleneck. Adopt the fixed "merge mark that can fail" now. |

## Claims I could not check here
Paper claims (arXiv IDs) have not been checked against full texts yet. GPT marked several as abstract-only (MinIE, CommitmentBank, FrugalGPT, MQuAKE-Remastered). A few IDs are from 2025-2026 (2506.07962, 2510.04581, 2603.24704) and are unverified. Treat all paper claims as "suggested" until someone downloads and reads them.

## Suggested order (what I'd run first)
1. Q1 frozen-score threshold rescue (gate).
2. Q2's challenge half added to own-o0a2 (write rules).
3. Q4 matched-data swap on ear v4.1 (data vs model size).
4. Q10 casual-text retrain. This could share Q4's data pipeline, but it must stay a separate registered experiment.
5. Q6 answer-key audit, once Ben agrees to label about 100 turns.
