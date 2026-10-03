# Premonition LIVE status (execution owner)

## 2026-10-03 English pilot scored: UNDERFIT-VOID (no claim)
Ran: 4 pilot endpoints (seeds 0,1 x control,treatment; 2304 updates each, BensPC) trained by another session; froze after launch (PILOT-FREEZE-v1.json, hashes match what ran). Fresh eval v3 generated (sealed, 6 states) and scored with the H1-fixed scorer. V1 pass, V3 pass.

| state | TRAIN fit /48 (gate 40) | understanding P1 /48 | transfer P2 /48 |
|---|---|---|---|
| seed0 parent | 0 | 0 | 0 |
| seed0 control | 6 | 4 | 4 |
| seed0 treatment | 5 | 3 | 5 |
| seed1 parent | 0 | 0 | 0 |
| seed1 control | 14 | 0 | 1 |
| seed1 treatment | 6 | 0 | 1 |

Marks (pre-fixed): PASS needs D>=6 on P1 and P2 both seeds; harm = loss vs own parent >3 on P1 (none: parents score 0). All four endpoints fail the 40/48 train-fit gate, so the verdict is UNDERFIT-VOID: the models did not learn the TRAIN set in 2304 updates (last-pass train CE 1.5-1.9). The treatment-vs-control comparison is not interpretable. Shown: scorer output RESULTS-v1/SCORES-v1.json. Suggested (untested): more updates or higher LR; next step is a decision after these numbers (exploratory held-out retrain not built).

Treatment-only arithmetic benchmark retry (v2 seal): completed, 64 updates, mechanical test only.
Notes: I briefly overwrote EVAL-CONFIG-v1.json then restored the exact original bytes (sha bb9aae3b...). Failed first eval attempt (base-Python ImportError, gold not read) kept at eval-v1-failed-importerror-20261003T1554Z on the PC.

## 2026-10-03 17:50Z Underfit diagnosis + sweep (exploratory fast lane, seed 0, TRAIN panel only; eval untouched)
Harness: scripts/cap256_launch/sweep_english_trainfit_v1.py (train fit = correct of 48 TRAIN QA, greedy decode, same as pilot).

| config (seed 0) | control fit /48 | treatment fit /48 | last-pass CE |
|---|---|---|---|
| pilot baseline (lr 1e-3, 2304 upd) | 6 | 5 | 1.9 / 1.7 |
| lr x3 | 6 | 4 | 1.73 / 1.62 |
| lr x10 | 3 | 1 | 2.07 / 2.06 |
| 2x updates (4608) | 22 | not run (see below) | 1.01 |
| QA-only, 48 items, 2304 upd | 12 | - | 1.02 |
| overfit 4 items, 400 upd | 4/4 on the 4 | - | 0.0007 |

Shown: (a) the pipeline can memorise 4 items (CE 0.0007, 4/4 correct) so training+scoring are not broken. (d) teacher-forced exact answers during training (4,4,7 /48 last pass) match free-generation fit (6,5,14): no decode mismatch. (c) loss asserts an independent masked-token CE on every update (never failed); answers ~4.2 tokens incl. EOS. (b) 64 of 114 tensors get no gradient: halt/tok/slot/head/ln_out/tool are by design (contract NONE_GRAD_CORE_CHILDREN, 4 fixed loops bypass them); core MLP experts 2-7 get zero gradient in every block (8 experts, top-2 routing, aux balance loss observed-only, not in the loss): routing only ever uses experts 0 and 1, inherited from the parent. No accidental cut found.
Shown: higher lr does not help (x10 worse); more updates does (6 -> 22 at 2x); removing the auxiliary frames does not fix it (QA-only 12/48 at same count).
Suggested (untested): the limit is optimisation speed / capacity on 48 items, not a bug; routing collapse onto 2 experts may reduce capacity.
Mistakes/notes: I killed the sweep chain at ~16:45Z which also killed the up2 treatment run at update 4195/4608 (no treatment number); stale GPU-BUSY cleared. up4 not yet run.
Next: 4x updates (9216), both arms, seed 0.

## 2026-10-03 ~19:00Z 4x updates (9216) reaches the train-fit bar on seed 0
Shown (exploratory, TRAIN panel only): seed 0 at lr 1e-3, 9216 updates: control 43/48 (CE 0.23), treatment 41/48 (CE 0.43). Both >= 40. Mechanism note (shown): router balance aux was constant 0.001 in the pilot log, i.e. router weights never moved off zero; with identical expert clones the CE gives the router zero gradient, so experts 0 and 1 stay identical and the 8-expert MLP acts as one plain MLP. Not yet tested whether putting the balance loss in the loss helps (aux64 did not run; not needed now).
Running: seed 1 both arms at 9216 updates (tag up4s1). Next: rescore seeds 0+1 on fresh eval v3 once, same pass marks. Caveat: eval v3 was already scored once (numbers seen), so this rescore is exploratory, not a sealed claim.

## 2026-10-03 ~20:10Z 9216-update rescore on fresh eval v3: NULL (exploratory, no claim)
Ran: seed 1 at 9216 updates (control 40/48, treatment 43/48 train fit), then generated and scored all 6 states on fresh eval v3 once, same scorer and marks (only the run-length check changed 2304 -> 9216). V1 and V3 pass. Train fit: s0 control 43, s0 treatment 41, s1 control 40, s1 treatment 43 (all >= 40).

| state | understanding P1 /48 | transfer P2 /48 |
|---|---|---|
| seed0 control | 3 | 1 |
| seed0 treatment | 3 | 1 |
| seed1 control | 7 | 2 |
| seed1 treatment | 2 | 3 |
| parents | 0 | 0 |

Treatment minus control: seed 0 = (0, 0); seed 1 = (-5, +1). PASS needs >= 6 on both P1 and P2 for both seeds (T=6): not met. Harm vs parent: none (all runs score above the parents' 0). Verdict NULL by the pre-fixed rule.
Shown: the models memorise the 48 TRAIN questions (40-43/48) but answer only 2-7/48 fresh understanding questions and 1-3/48 transfer questions; no treatment benefit over control in either seed. Suggested (untested): the training set is memorised, not generalised, so the paraphrase auxiliary at this scale, data size and design does not buy comprehension. Untested: more/diverse data, router balance loss, stronger treatment.
Caveats: eval v3 had already been scored once (UNDERFIT-VOID numbers seen) and the length was chosen on TRAIN only; this is exploratory, not a sealed claim. S1 paraphrase scoring not done. Seed 0 endpoints came from the sweep (tag up4), seed 1 from tag up4s1; same code, same lr.
Stopping per the coordinator's plan; next step is a decision for Ben / the coordinator.

## 2026-10-03 ~19:2xZ (real UTC; corrected from 20:40Z) Next test registered BEFORE training: router balance loss (aux weight 0.01), seed 0, 9216 updates
Pass mark (fixed now, from the Projects coordinator): the test passes if, for the aux-loss endpoints, understanding (P1) OR transfer (P2) reaches >= 6/48 on fresh eval v3 AND harm <= 3 (P1 lost vs the parent, T_harm = 3). Train-fit gate stays 40/48 (below it the test is void). Treatment-minus-control difference reported separately (needs >= 6 on both for a treatment claim). Wrong if: both arms stay below 6 on both measures.
Setup: same recipe as tag up4 (lr 1e-3, 9216 updates, seed 0, control + treatment) plus 0.01 x router balance aux in the loss (aux was constant 0.001 in earlier runs: router never moved). Seed 1 states in the rescore are the existing up4s1 endpoints (not retrained), so this is a seed-0 comparison only. Exploratory; eval v3 already seen; not a sealed claim.
Disk: PC free ~4.9 GB before this run (one run writes ~0.12 GB per arm); will report if < 2 GB.
Held for Ben: committing the parent checkpoints to GitHub (claude/real-pipeline-checkpoints) is an outward-facing publish of trained weights; not done without his OK.

### 19:3xZ (real UTC; corrected from 20:55Z) step log
- Balance-loss run `bal9216` (seed 0, control+treatment, 9216 updates, aux 0.01) started on the PC GPU; train fit comes first, then I rescore fresh eval v3 with the registered pass mark above.
- Calculator/reasoner configs found and exported to branch `claude/real-pipeline-code` (commit 70ef16198): RELEASE-MANIFEST-v3, TRAIN frames, schedules, runners. Eval/fresh frames and the source checkpoints are not exported.
- Disk on the PC: 4.57 GB free (above the 2 GB warning line).
- Parent-checkpoint branch (`claude/real-pipeline-checkpoints`) NOT created: publishing trained weights to GitHub waits for Ben's OK.

### 19:53Z checkpoints pushed (Ben answered "Yes, push them" in the Terminal)
Branch claude/real-pipeline-checkpoints, commit 56d720549: seed0/seed1 parent final-resume.pt (60.7 MB each) + bootstrap-English-s0.pt (0.31 MB), hashes match config pins. Not merged to main.

## 20:00Z QUEUED, pass marks registered BEFORE training: skills-curriculum pretraining of the core (PR #32, commit 4344acad4)
Runs only after bal9216 and its rescore finish. Exploratory (fast lane); not a sealed claim; eval v3 has been seen several times.
Stage A (pretrain, frozen LFM, same reader+core, prompt -> short answer, easy-to-hard stages, ~2 h cap, >=200k never-repeating rows, streamed if disk < 2 GB):
- VOID if in_dist dev accuracy < 80% at the end (the core did not learn the curriculum).
- Report accuracy on each single-shift dev file (answer, frame, vocab, variant, family) vs in_dist. "Generalises" only if answer, frame and vocab are each within 15 points of in_dist. family shift is reported, no pass mark (whole new skills).
Stage B (English pilot seed 0, 9216 updates, control+treatment, starting from the pretrained core, rescored on fresh eval v3):
- Train-fit gate 40/48 (else void). Null baseline so far: understanding (P1) 2-7/48, transfer (P2) 1-3/48.
- PASS if P1 >= 12/48 OR P2 >= 8/48 for the pretrained-core endpoints, with harm <= 3. Treatment minus control reported separately (>= 6 for a treatment claim).
- Wrong if: P1 <= 7 and P2 <= 3 (same as the null baseline).
Open engineering step: PR #32 rows are not in the pilot's frame format; I need a small skills trainer that reuses english_graph/english_loss with prompt as the passage and answer as the target. Not written yet.

## 20:51Z RESULT bal9216 (router balance loss 0.01, seed 0, 9216 updates): FAILS the registered pass mark
Train fit gate passed: control 40/48, treatment 41/48. Fresh eval v3 (exploratory, seen before; seed 1 endpoints are the old up4s1 ones, not retrained):
| state | P1 understanding /48 | P2 transfer /48 |
|---|---|---|
| seed0 parent | 0 | 0 |
| seed0 control (balance loss) | 2 | 1 |
| seed0 treatment (balance loss) | 5 | 1 |
Pass mark was P1 or P2 >= 6/48 with harm <= 3: NOT met (best 5). The registered "wrong if" (both arms stay below 6 on both measures) IS met. Treatment minus control: P1 +3, P2 0 (needed >= 6). Harm vs parent 0 (no loss). Scorer verdict NULL.
Shown: every correct fresh answer, in all six endpoints, is a yes/no item; short-answer fresh items are 0/38 (P1) and 0/35 (P2) correct for every state. Suggested: the model still copies/produces training-style answers for open questions (matches the coordinator's copy finding). Untested: whether a pointer exit or wider entry fixes that (cloud thread).
Files: artifacts/.../ENGLISH-PILOT-v1/RESULTS-v3-bal/ (SCORES-bal.json, RAW, SEALED, closed receipts), scorer now takes an optional results-dir argument.
Next: skills-curriculum pretraining speed probe is running on the PC GPU.

## 20:56Z LAUNCHED skills-curriculum pretraining (stage A), pass marks as registered above
Speed probe (600 updates, clean, ~500 updates/min; 0/20 in_dist at 600 updates, too early to judge). Real run: task skmain, seed-0 parent, 50,000 updates taken as an even stride (every 4th row) through the 200,000-row stream (PR #32 @ 57c45293f, ambiguity filter; train hash matches the manifest after CRLF->LF), lr 1e-3 continuing the parent's Adam, in_dist dev check every 4000 updates, 100 dev rows per shift file at the end, time cap 120 min. Output: artifacts/skills/main/ on the PC (SKILLS-RESULT.json, parent-shaped final-checkpoint.pt). Stage B (English pilot from this core) only starts if in_dist >= 80% (else VOID).

## 21:29Z INTERIM skills pretraining main run: not learning; stopped at ~16k of 50k updates for a diagnosis
Shown: in_dist dev accuracy 5, 6, 3, 6 of 100 at 4k, 8k, 12k, 16k updates. Even stage 1 (copy and look-up) only reached ~13% exact in training and its loss plateaued near 2.1; loss rose when harder stages began (stage 4 ~2.4-3.0). The registered pass mark (in_dist >= 80% at the end) cannot be reached on this trajectory. No checkpoint was saved (it saves at the end only).
Suggested (not tested): the 8-vector exit is the bottleneck, even for copying a made-up word; matches the cloud thread's finding that wrong fresh answers are copies.
Untested: whether many more updates would fix it.
Diagnosis registered BEFORE running: copy_word family only, 3000 updates, seed-0 parent, lr 1e-3, dev check every 1000 on 50 held-out copy_word rows. Copy accuracy >= 80% = copying is learnable through the exit (so the failure is curriculum/other skills). Copy accuracy < 30% = the 8-vector exit cannot even copy a made-up word. In between = inconclusive.

## 21:39Z RESULT copy-only diagnosis: BELOW the 30% mark, 0/40
copy_word rows only, 3000 updates (stride 4 through 13,436 rows), seed-0 parent, lr 1e-3. Held-out copy_word dev rows (n=40 per shift file with enough rows; family shift has none): 0/40 correct on in_dist, answer, frame, vocab and variant at every check (1000, 2000, 3000 updates). Training loss fell only from 4.2 to 3.2 and training exact match stayed ~0.
(First launch of this test lost its --families flag to a shell-expansion slip in my launcher, trained on all families, was stopped after ~1 minute; its output was not used.)
Shown: with the current exit, the model does not learn to copy a short made-up word from its own prompt in 3000 updates (0%), while the English-pilot QA training set was fit at 40-43/48 in the same architecture (memorised answers, not copying).
Suggested (not proven): the 8 pooled exit vectors do not carry the spelling of the prompt, so copying new words fails; matches PR #33 (pooled exit: 0.3% on unseen answers) and the earlier fresh-eval pattern.
Untested: more than 3000 updates; a different learning rate; whether the parent's memorised QA habits slow copying (a fresh-weights start).
Choice (coordinator asked for the PR #33 copy path): PR #33 copies a calculator tool RESULT into the answer, but here the answer is a span of the PROMPT, so a straight port does not apply. The same idea for prompts: let the frozen LM read the prompt's own token embeddings directly next to the 8 pooled vectors (prefix = 8 pooled + the prompt's raw token embeddings, up to 64), so the talker can copy tokens. One change only.
Pass marks for that test, fixed now: same setup as above (copy_word only, 3000 updates, seed-0 parent, lr 1e-3, same dev rows). PASS if copy_word in_dist dev accuracy >= 80% at 3000 updates. Wrong if < 30% (then the failure is not just the exit). 30-80% inconclusive.

## 21:48Z RESULT copy-path test: PASS (copy_word held-out dev 40/40; was 0/40 without it)
Change: prefix = the 8 pooled exit vectors + the prompt's own token embeddings (frozen LM embedding table), nothing else different (copy_word only, 3000 updates, seed-0 parent, lr 1e-3, stride 4). Note: the first attempt to launch this test failed on a quoting error before anything ran; this is the only run.
Shown (one run, exploratory, copy_word dev rows n=40 per file): in_dist 40/40 at 1000, 2000 and 3000 updates; at 3000: answer-shift 38/40, frame-shift 40/40, vocab-shift 39/40, variant-shift 30/40. Training exact match was 85% by update 500 (0% in the same time without the copy path). Registered mark (>= 80% in_dist at 3000) met; the variant shift (75%) is the weakest.
Limits: copy_word is the easiest family; dev rows are held-out words but the family is trained on; one seed; says nothing about the other 37 families, and the other skills need computing, not just copying.
Suggested: the 8 pooled vectors cannot carry a new word's spelling; letting the talker see the prompt tokens removes that limit for copying (consistent with PR #33's copy path for tool results).
Untested: all-families training with the copy path (next, registered below); whether arithmetic-type answers (computed, not copied) improve at all.

## 21:48Z NEXT job, pass marks fixed BEFORE launch: all-families skills pretraining with the prompt-token copy path (stage A)
Same as the earlier main run except --copy-path: 50,000 updates (every 4th row of the 200,000-row stream, PR #32 @ 57c45293f), seed-0 parent, lr 1e-3, in_dist check every 4000 on 100 rows, final per-shift dev (answer, frame, vocab, variant, family) on 100 rows each, time cap 120 min.
PASS: in_dist >= 80% at the end. Report all per-shift accuracies; "generalises" only if answer, frame and vocab are each within 15 points of in_dist (family reported, no mark).
STOP EARLY: at the 16,000-update check, if in_dist is still <= 10/100 (earlier run without the copy path: 5, 6, 3, 6 of 100 at 4k/8k/12k/16k).
If PASS, stage B (English pilot from this core, seed 0, 9216 updates, eval v3) uses the marks registered earlier (P1 >= 12/48 or P2 >= 8/48, harm <= 3, train fit >= 40/48).

### 22:16Z INTERIM skills pretraining WITH copy path (task skmain2, 13k of 50k updates in)
Shown: in_dist dev accuracy 35, 53, 54 of 100 at 4k, 8k, 12k updates (same run without the copy path: 5, 6, 3). Training exact match: 94% on stage 1, 80% stage 2, ~70% stage 3 (it falls as harder stages start, as expected). Stop-early rule (<= 10/100 at 16k) cannot trigger. Still below the 80% pass mark; final check at 50k (~23:35Z). PC disk free 4.06 GB (> 2 GB).
Suggested: the copy path unlocked learning in the earliest, copy-style stages; whether the harder reasoning stages (levels 5-8) get learned is the open question.

### 23:12Z INTERIM skills pretraining with copy path (40k of 50k updates)
Shown: in_dist dev accuracy of 100 at 4k..40k updates (every 4k): 35, 53, 54, 49, 59, 66, 67, 69, 67, 73. Slowly rising, still below the 80% mark; final value and per-shift numbers at 50k (~23:30Z). PC disk free 4.05 GB.

## 23:33Z RESULT skills pretraining WITH copy path (50,000 updates): FAILS the registered 80% mark; big gain over no copy path
Shown (one seed, exploratory; 100 dev rows per file; PC disk free 4.0 GB):
| dev file | correct /100 |
|---|---|
| in_dist (mark: >= 80) | 72 |
| answer shift | 63 |
| frame shift | 65 |
| vocab shift | 78 |
| variant shift | 50 |
| family shift (whole new skills) | 13 |
In-dist over time (every 4k updates): 35, 53, 54, 49, 59, 66, 67, 69, 67, 73, 72, 72, 72, so it plateaued near 72 from about 24k updates on. Same run without the copy path: 5, 6, 3, 6 of 100 (stopped at 16k). Answer, frame and vocab are each within 15 points of in_dist (the registered "generalises" rule), variant is 22 below, family 13/100 as expected for unseen skills.
Training exact match by stage (last 3 reports): stage 1 copy/look-up 91-94%, 2 arithmetic 89%, 3 sequences 69-71%, 4 tracking/binding 63-67%, 5 logic 78-79%, 6 multi-step 67-69%, 7 rule-from-examples 59-67%, 8 reading/composing 70-74%, 9 uniform mix 72-75%. Weakest: stages 3, 4, 6, 7.
Verdict by the registered mark: VOID for the English-pilot stage B (in_dist < 80%), so stage B was NOT launched.
Plain language: letting the talker see the prompt words turned a model that could learn nothing into one that gets about 7 in 10 curriculum problems right, including new wording and new words, but it stops improving at ~72% and fails whole new skills.
Suggested: the remaining errors are on skills that need several computed steps (sequences, tracking, multi-step, learn-a-rule), not on copying.
Untested: constant lr 1e-3 may be what plateaus it; step supervision (the curriculum rows carry worked steps); more loops; the cloud thread's contextual reader.
Checked against the code (coordinator suggested a contextual reader): skills_pretrain_v1.py already feeds the reader the frozen LM's final-layer contextual hidden states (extract_question_features with arm 'contextual' = last_hidden_state), so that change is already in this run, not a new lever here.
Checkpoint kept on the PC: artifacts/skills/main2/final-checkpoint.pt (60.7 MB, parent-shaped), SKILLS-RESULT.json copied to artifacts/skills-main2/ in the repo. Nothing deleted.
PROPOSED next single change (not launched; needs marks fixed first): same run, plus a cosine-style learning-rate decay (1e-3 down to 1e-4 over the 50k updates), everything else identical. Suggested marks: PASS if in_dist >= 80; improvement claim only if in_dist >= 78 (the earlier plateau 72 +/- 3 noise from the last 6 checks); wrong if in_dist <= 75. Alternative if Ben/coordinator prefer: step supervision on the worked steps.

## 23:44Z LAUNCH skills pretraining, copy path + LR decay (task skmain3, tag main3)
One change vs main2 (72/100): learning rate cosine-decays 1e-3 -> 1e-4 over the 50,000 updates (--lr-final-mult 0.1); copy path, seed-0 parent, stride 4, dev rows, eval every 4k all unchanged. Marks fixed before launch (coordinator confirmed): PASS in_dist >= 80 (then straight to stage B); improvement claim only if >= 78; wrong if <= 75. If it fails, step supervision is next (needs its own marks). main2 checkpoint kept (artifacts/skills/main2/); output goes to artifacts/skills/main3/. PC disk free 4.0 GB before launch (> 2 GB). Ends ~01:25Z.
