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

### 00:40Z INTERIM main3 (copy path + LR decay), 28k of 50k updates
Shown: in_dist of 100 at 4k..28k: 32, 55, 53, 56, 61, 65, 66 (main2 at the same points: 35, 53, 54, 49, 59, 66, 67), so no difference so far; the decay only bites late. PC disk free 4.0 GB. Final ~01:25Z.

## 01:26Z RESULT main3 (copy path + LR decay 1e-3 -> 1e-4, 50,000 updates): WRONG by the registered mark; decay did not help
Shown (one seed, exploratory, 100 dev rows per file; disk free 3.9 GB): in_dist 65 (mark: pass >= 80, improvement >= 78, wrong <= 75). Per-shift vs main2: answer 59 (63), frame 63 (65), vocab 77 (78), variant 51 (50), family 13 (13). In-dist curve: 32, 55, 53, 56, 61, 65, 66, 64, 61, 63, 63, 62, final 65; it peaked near 66 at 28k and drifted down as the rate fell, i.e. slightly worse than constant rate (72), within noise of 5-7 points on 100 rows.
Plain language: lowering the learning rate did not unstick it; the ~70% ceiling comes from something else.
Suggested: the limit is the training signal or the model's capacity for multi-step skills, not the optimiser rate. Untested: step supervision, longer runs, bigger/different core.
Stage B not launched. main2 and main3 checkpoints both kept (artifacts/skills/main2, main3 on the PC); SKILLS-RESULT.json in artifacts/skills-main3/.
NEXT (coordinator said step supervision), NOT launched; marks fixed now: curriculum rows have a "steps" list (e.g. ["copy sune"]). Change: train target = steps joined as a short worked line followed by the final answer, scored only on the final answer (generation cap raised from 12 tokens to fit), everything else as main2 (copy path, constant lr 1e-3, 50k updates, seed 0, same dev rows). PASS in_dist >= 80; improvement claim >= 78 (main2 72, +/- ~5); wrong <= 75; stop at 16k if in_dist <= 40. Needs a code change (target builder, longer generation, answer extraction) written and tested on a small run before launch.

## 01:34Z LAUNCH skills pretraining, copy path + step supervision (task skstep, tag main4)
Smoke test (600 updates, 20 dev rows, tag smoke4): end to end OK; answers are extracted from the text after the last "#" and scored (in_dist 5/20, other shifts 2-12/20 at 600 updates, nothing claimed); checkpoint written. Code: --steps in skills_pretrain_v1.py (target = steps joined by " ; " + " # " + answer, EOS; generation cap 12 -> 48 tokens; scored only on the final answer; no "#" in the output = wrong). Steps are short (mean 20 chars, max 106).
Full run = main2 setup (constant lr 1e-3, copy path, seed-0 parent, 50,000 updates stride 4, dev 100 rows, eval every 4k) + steps. Marks (registered above, coordinator confirmed): PASS in_dist >= 80; improvement claim >= 78 (main2 72); wrong <= 75; stop at 16k if in_dist <= 40. Note: many steps are bare labels ("compose", "read passage"), so only some families get real worked computation; main2/main3 checkpoints kept; disk free 3.9 GB. Ends ~03:20Z.

### 02:02Z INTERIM main4 (copy path + step supervision), 13k of 50k updates
Shown: in_dist of 100 at 4k, 8k, 12k: 21, 39, 39 (main2: 35, 53, 54; main3: 32, 55, 53). Behind both so far; the 16k stop check (<= 40) is due in a few minutes and the stop rule may trigger. PC disk free 3.85 GB.

### 02:10Z main4 16k stop check: PASSED the check, run continues
Shown: in_dist 47/100 at 16k (stop rule was <= 40), curve 21, 39, 39, 47 (main2 35, 53, 54, 49). Still not above main2; nothing claimed. Disk free 3.85 GB. Ends ~03:20Z.

### 03:01Z WARNING: BensPC unreachable since ~02:44Z
SSH to the PC (Tailscale 100.75.113.114:22) times out; scp also fails. Last good read of main4 (step supervision) was 02:10Z: in_dist 21, 39, 39, 47 at 4k-16k; the run was scheduled-task based and was due to end ~03:20Z, but its state is unknown. Stage-B prep code (rebase_skills_parent_v1.py, sweep --parent0) is pushed but NOT yet copied to the PC. Nothing launched, nothing deleted. Needs the PC woken/restarted by Ben if it stays down. Coordinator's rule on file: if main4 < 80, stage B runs from the best skills checkpoint (main2 72 unless main4 beats it), exploratory, no copy path in the English exit.

## 04:20Z RESULT main4 (copy path + step supervision, 50,000 updates): in_dist 71/100, WRONG by the registered mark (<= 75); no better than main2 (72)
Shown (one seed, exploratory, 100 dev rows per file): in_dist 71, answer 63, frame 68, vocab 74, variant 58, family 15 (main2: 72, 63, 65, 78, 50, 13; main3: 65, 59, 63, 77, 51, 13). In-dist curve every 4k: 21, 39, 39, 47, 66, 68, 57, 63, 71, 73, 74, 72, final 71 (ended 03:18Z, 103.5 min). Step supervision gave no gain in in_dist; variant shift is +8 over main2 (58 vs 50), within the roughly +/-5-7 noise of 100 rows plus one seed, so not claimed.
Three skills variants now: constant-lr copy path 72, LR decay 65, step supervision 71. All plateau at about 65-72, so the ceiling is not the learning rate and not (with these short steps) the missing steps. Suggested; untested beyond that.
Incident (logged for honesty): BensPC was unreachable over Tailscale from ~02:44Z to ~04:15Z (network only; no reboot, last boot 09/28). The PC clock is local time = UTC-4. My scheduled tasks were created with a one-time 23:59 PC-local trigger; at 23:59 local (03:59Z) skstep4 fired a SECOND copy of main4 (pid 10552). It had reached ~9.5k updates when I found it at 04:19Z. I first copied the run-1 result and checkpoint to artifacts/skills/main4-run1/ (sha256 1e427b2b..., matches the result file), then stopped the duplicate with schtasks /End and cleared the GPU-BUSY marker; no python running, disk free 3.7 GB. Run-1 SKILLS-RESULT.json is in the repo under artifacts/skills-main4/. The duplicate had overwritten the main4 *log* file (not the result files). The same trigger may have made other old tasks (skmain2/3, skstep, etc.) start and exit at the GPU-BUSY guard, so their .log files may be overwritten; their SKILLS-RESULT.json and checkpoints are intact (main2 19:27, main3 21:22 local). Fix: future tasks will be deleted after use (schtasks /Delete).
Coordinator rule on file: main4 did not reach 80, so stage B runs from the best skills checkpoint = main4 run1 at 71 does NOT beat main2 (72), so main2 it is. Next: register stage-B marks, copy prep scripts, rebase and launch.

## 04:21Z STAGE B registered (exploratory; the "skills in_dist >= 80" gate was waived by the coordinator): English pilot, seed 0, from the main2 skills checkpoint
Checkpoint choice: main2 (in_dist 72) vs main3 65 vs main4 71: main2 is the best, so main2 (artifacts/skills/main2/final-checkpoint.pt, sha256 of the 60.7 MB file recorded below). Change vs the earlier 9216-update English runs: only the seed-0 parent (core, reader, prefix, Adam state continued) is the main2 skills checkpoint instead of the 5120-update parent; English exit unchanged (8 vectors, NO copy path), schedule/data/lr/9216 updates identical (sweep --passes 128 --seeds 0, arms control and treatment). The update counter on the checkpoint is reset to 5120 (rebase_skills_parent_v1.py; weights/Adam/RNG untouched) so the unchanged trainer accepts it; sha pinned in the config.
Marks (fixed before launch): PASS (P1 or P2 effect) if seed-0 fresh understanding P1 >= 12/48 or transfer P2 >= 8/48 for either arm, AND harm <= 3 (vs own parent on P1), AND train fit >= 40/48. WRONG if P1 <= 7 and P2 <= 3 for both arms (earlier 9216 baseline: P1 2-7, P2 1-3). Between = inconclusive. Reference: bal9216 best P1 5/48, P2 1/48.
Caveats: one seed (seed 0 only; seed-1 numbers in the scorer reuse the earlier 9216 receipts), fresh eval v3 has now been looked at several times (exploratory, nothing sealed), the English frozen LM no longer sees the prompt tokens (no copy path) while the pretrained core was trained with prompt tokens in the prefix, so the English adapter has to adapt; a PASS would be suggested, not a claim.

### 05:14Z Stage B training done (seed 0, main2 skills parent, 9216 updates): train fit 46/48 control, 45/48 treatment
Shown: train fit (TRAIN panel, gate >= 40/48) 46 (control, final CE 0.050) and 45 (treatment, final CE 0.230); earlier 9216 runs from the 5120-update parent: 40-43/48. Gate met, and a few points higher than before; one seed, so the gap is not claimed. Fresh eval (P1/P2) next. PC disk free 3.5 GB.

## 05:24Z RESULT stage B (English pilot seed 0 from the main2 skills checkpoint, 9216 updates): WRONG by the registered marks; NULL. Skills pretraining did not carry over to fresh English questions
Shown (seed 0 is new; the seed-1 rows are the earlier 9216-update runs re-scored in the same frame; exploratory, eval v3 seen many times, nothing sealed):
| seed-0 state | train fit /48 | fresh understanding P1 /48 | meaning transfer P2 /48 |
|---|---|---|---|
| skills parent (before English training) | 0 | 0 | 0 |
| control endpoint | 46 | 2 | 0 |
| treatment endpoint | 45 | 3 | 0 |
Registered marks: PASS needed P1 >= 12 or P2 >= 8 (with harm <= 3, train fit >= 40): not met. WRONG if P1 <= 7 and P2 <= 3 for both arms: met (P1 2 and 3, P2 0 and 0). Harm vs parent: none (parent scores 0). Short-answer items: 0 of 38 (P1) and 0 of 35 (P2) correct in every seed-0 state; the only correct answers are 2-3 of 10 yes/no items on P1 (below the 50% a coin would give) and 0 of 13 on P2. Treatment minus control (the pilot's own effect): +1 on P1, 0 on P2.
Compared with before: train fit 46/45 (was 40-43 from the 5120-update parent), but fresh scores are no better than the earlier 9216 runs (P1 2-7, P2 1-3; bal9216 best 5/1). The scorer verdict is NULL.
Plain language: learning the skills curriculum first made the model fit its 48 practice questions slightly better, but it still cannot answer new questions asked in new words; every free-answer fresh question was wrong.
Suggested: the skills core did learn skills but they do not reach the English exit: the English path still goes through the 8 pooled vectors, which (as the copy-only test showed) cannot carry content such as names or numbers copied from the question, and the fresh questions need exactly that. Untested: the English exit with the copy path (stage B2; it hands the frozen LM the question tokens, so a PASS would partly measure the frozen LM reading the question, not our core), a longer or different English schedule, other seeds.
Files: artifacts/.../ENGLISH-PILOT-v1/RESULTS-v3-stageB/ (SCORES-stageB.json, RAW, SEALED, closed receipts, EVAL-CONFIG-stageB.json); sweep scripts rebase_skills_parent_v1.py, eval_english_9216_from_v1.py. Stage B task and eval task deleted; PC idle, disk free 3.5 GB; no checkpoints deleted (skills main2/main3/main4/main4-run1, rebased parent, stageB endpoints all kept).

## 12:21Z NEW (coordinator relay): port the cloud allptr + generated-practice recipe to the PC; marks registered before any run
Read: cloud rounds 4-5 (branch claude/project-thread-ajo58u): allptr + 8000 generated rows scored 92.6% on its fresh set vs 75.0% for the bare LM 8-shot (round 4, in-family test, shown by the cloud); round 5 +12.2 on six new kinds. Their model is the same real pipeline modules but a fresh 9.0M ordered core (not the pilot's 'shallow' core), so whether the main2 skills checkpoint plugs in is untested.
Marks and design are in docs/premonition-status/PASS-MARKS-PTR-PC.md (committed with this entry): arms S (scratch) and M (main2 init, only if it loads strictly), 6 seeds each, bar = bare LM 8-shot on the same 192 fresh questions; PASS >= bar + 5, FAIL < bar; M vs S claim only with +3 and a CI above 0. Changes: one flag --init-ckpt (scripts/cap256_launch/ptr_english/run_english_pc.py). First: unpack on the PC, plug-in check, short dry run, then the seeds one at a time holding GPU-BUSY.txt.

## 12:24Z cloud-recipe port launched on BensPC (GPU-BUSY held by each job in turn)
Shown: main2 skills checkpoint plugs into the cloud model class strictly (core/reader/prefix/tool: 0 missing, 0 unexpected); dry run 20 steps ~1.1 s/step -> ~37 min per 2000-step run.
Queue (ptrqueue.cmd, sequential): lm_fewshot baseline, then seeds 0-5 of arm S (scratch) and arm M (main2 init), interleaved by seed, 8000 generated rows each, plus NEW-KINDS-R5 as a read-only extra. About 8 h total. Marks: PASS-MARKS-PTR-PC.md. Logs/results under C:\Users\benja\ptr-english\ (out\, S*.log, M*.log). No checkpoints written; disk ~3.5 GB free.

## 12:27Z cloud-recipe port: baseline reproduced, 12-run queue (S0..S5, M0..M5) running
Shown: bare LM 8-shot on the same 192 fresh questions = 75.0% exact / 77.6% contains on the PC, identical to the cloud's number. So the bar is 75.0%; PASS needs mean >= 80.0 (marks unchanged). First queue attempt failed instantly (argparse: '--tag -S'); fixed with '--tag=-S', no GPU time lost, no results discarded. Seed 0 arm S started; ~37 min per run, ~7.5 h for 12.

## 14:00Z Stiffness test v1 queued on BensPC (after the English queue)
Request from the Fernando-thesis thread (PR #34, commit fe22d7ebf); spec and marks: artifacts/stiffness-test-v1/STIFFNESS-TEST-v1.md (fixed before training). Pulled its 3 new flags into skills_pretrain_v1.py (defaults unchanged), the data (6 seeds) and the scorer into this branch; the PC copy of skills_pretrain_v1.py replaced (sha256 9D1964BA...; the old version stays in git).
Queue: C:\Users\benja\stiffrun.ps1 (task stiffjob) waits until the English queue's last result (out\allptr-gen-M-seed5.json) exists and GPU-BUSY.txt is clear, then runs A1 B1 ... A6 B6 sequentially (4000 updates each, no checkpoints; A reads main2 final-checkpoint.pt read-only). Gives up after 14 h of waiting. Logs C:\Users\benja\stiffness-{A|B}{s}.log and stiffness-queue.log. English queue not touched. Est. start ~20:00Z, finish ~23:00Z. No spec changes needed so far; the main2 metadata check (update 55120) is untested until A1 starts.

## 14:44Z Stiffness test moved to a Vast box (Fernando thread, Ben's go-ahead relayed); PC copy removed
Removed the waiting stiffjob task and its two waiting processes (exact PIDs; English queue processes untouched, M1 still running). Pushed main2 final-checkpoint.pt (sha256 e82bd12b...04f6, 60698601 bytes, copy only) to claude/real-pipeline-checkpoints at skills/main2/final-checkpoint.pt. Seed-0 parent (sha 49a35023...) and TRAIN-CONFIG-v2.json (sha f0709733...) were already on that branch under pipeline/.

## 16:05Z Stiffness test v1 result (run on Vast by the Fernando thread): NOT STIFF
main2 20.9% vs parent 10.4% on two unseen skill families after 4000 updates; main2 ahead on 6 of 6 seeds (mean +10.5). Registered rule gives NOT STIFF; the 65-72 skills plateau is suggested not to be plasticity loss. Write-up (their run, not re-checked by me): artifacts/stiffness-test-v1/results/RESULT-v1.md on branch claude/project-thread-aya9pk. Confirmed: no stiffjob task and no stiffrun process remain on BensPC.

## Vast 4070 readers checksum (17:48Z, read-only, nothing deleted)
The Mac holds both ~2.1 GB reader models (I cannot see inside Vast box 52755827, so whether the box's files are these two is for the cleanup thread to confirm by comparing sha256):
- /Users/ben-hannan/premonition-models/lis319f-merged/model.safetensors, 2161290944 bytes, sha256 970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b
- /Users/ben-hannan/premonition-models/lis319-merged/model.safetensors, 2161290944 bytes, sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76
Same folders also hold tokenizer.json (lis319-merged sha 3e065a55...fed81) and config.json (sha 28edd4e3...6773). The Mac is a single copy: if it is the only other copy, back it up before deleting the box.

## 18:43Z Speed benchmark (bench_tps.py, PR #35 commit 9c3d86c36) on the Mac: Apple M1 Pro, 34 GB, MPS
Shown (fresh weights, so speed only; torch 2.14.1, transformers 4.57.6 -- the cloud used 5.17.0, not pinned here). Large batch 32. Raw: artifacts/bench-tps/mac-m1pro-mps.json.
- System (reader+core+exit, one answer token per question): short prompts (39 tok) 5.6 questions/s at batch 1, 19.6 at 16, 21.1 at 32 and 64; long prompts (67 tok) 5.0 at batch 1, 13.8 at 16, 11.0 at 32, 14.0 at 64.
- Bare LFM2.5-1.2B, 64 new tokens, batch 1: decode 25 tok/s fp32, 37 tok/s bf16 (prefill ~500-590 tok/s). Batch 32: decode 341-413 tok/s fp32, 475-484 tok/s bf16.
One local fix (not pushed): MPS cannot run adaptive_avg_pool1d when the length is not divisible by 8, so a shim (artifacts/bench-tps/run_bench_mps_shim.py) computes that pooling exactly with window slices on the device (checked: max diff 0.0 vs CPU). It adds a few small ops per row, so the system numbers may be slightly pessimistic. The batch-32 long-set figure (11.0) is below batch 16 (13.8), so the Mac numbers are noisy; one run, median of 10.
The BensPC 5070 Ti run is waiting for the English queue to finish.

## 19:46Z Cloud recipe (allptr + 8000 generated practice rows) on BensPC: 12 of 12 runs done. PASS for both arms (marks: PASS-MARKS-PTR-PC.md)
Shown (6 paired seeds, 192 fresh questions, exact match; fast lane, in-family test, fresh set not sealed). Bar = bare LM 8-shot on the same set = 75.0% (matches the cloud). Raw files: artifacts/ptr-pc/.
| arm | fresh mean (95% CI) | per seed | vs bar | new question kinds (bar 67.7) |
|---|---|---|---|---|
| S from scratch | 91.9 (90.0 to 93.8) | 92.7 94.3 92.7 92.2 89.1 90.6 | +16.9 | 79.9 |
| M from main2 skills checkpoint | 91.2 (90.0 to 92.5) | 91.1 89.6 92.2 92.2 92.2 90.1 | +16.2 | 88.1 |
- Both arms: every seed at least 14 points above the bar, so PASS (mark was bar + 5 = 80.0). Cloud's round 4 was 92.6% and round 5 new-kinds 79.9%; the PC from-scratch arm reproduces both (91.9, 79.9).
- M vs S on the fresh set: mean -0.7, CI -3.3 to +2.0, so no help and no harm (registered rule: no help). On the new kinds (read, not judged): M +8.2, CI -2.1 to +18.5, mostly one seed (+26.0, S seed 5 only 62.0); the other five seeds are -1.6 to +9.9. Suggested at most, untested: skills initialisation helps new kinds. Do not claim it.
- Read, not judged: contains 94.1 (S) / 93.9 (M); generated held-out panel 99.6 / 99.2; train fit 92.0 / 91.1; zeroing the core's 8 vectors gives 0.0% in all 12 runs.
- Limits: the test shares its six question kinds with the generator; the talker sees every prompt word (allptr), so the frozen LM does part of the reading; fresh set unsealed; toy English task, not the village model. This is not the earlier English pilot (which scored 2-7/48 on fresh comprehension): different recipe (all-words + pointer, 8000 generated rows), not comparable numbers.
Next: speed benchmark on the 5070 Ti.

## 19:56Z Speed benchmark on BensPC (RTX 5070 Ti, CUDA), bench_tps.py 9c3d86c36, large batch 128
Shown (fresh weights, speed only; torch 2.11.0+cu128; ran alone, GPU-BUSY held, nothing interrupted). Raw: artifacts/bench-tps/pc-5070ti-cuda.json.
- System (answer only): short prompts 18.5 questions/s at batch 1, 147 at 16, 212 at 64, 228 at 128; long prompts 18.1, 127, 160, 162.
- Bare LFM2.5-1.2B, 64 new tokens: batch 1 decode 73 tok/s fp32+tf32 (short), 55-73 bf16; batch 64 decode 4452-4669 tok/s fp32, 4256-4314 bf16; prefill 16.7-17.1k tok/s fp32, ~30k bf16 at batch 64.
- Versus the Mac (M1 Pro, MPS, entry above): about 3x faster at batch 1 for the system (18.5 vs 5.6 questions/s), about 10x at large batch (228 vs 21).

## 22:35Z START fix screen v2 on BensPC (plateau thread, spec artifacts/fix-screen-v2/PC-JOB.md @ 41371412f; marks in FIX-SCREEN-v2.md, fixed before running)
Staged the spec's skills_pretrain_v1.py (sha 96AA5B3D...) over the pipeline copy (old copy kept as skills_pretrain_v1.py.pre-fixscreen2.bak). Smoke passed (prefix-widened, SKILLS-RESULT). Queue running: Z (lesion, eval only) then X1-X3 (exit widened 32->256), one at a time; ~1.5 h. PC now has ~98 GB free (was 3.5 GB). No checkpoints written. Logs C:\Users\benja\fixscreen2-*.log, fixscreen2-queue.log.

## 23:04Z fix screen v2: Z (lesion) done; X1-X3 relaunched after my script bug
Z finished. My first X launch failed instantly (PowerShell variables are case-insensitive: loop variable $s overwrote the script path $S), and a second launch had a mangled output path, which I stopped by exact PID before it could overwrite anything (an empty stray folder artifacts/fixscreen2/X remains on the PC, no checkpoints). X1-X3 are now running correctly, ~25 min each.

## 00:03Z FINISH fix screen v2 on BensPC (plateau thread): Z core matters; X (exit 32->256) NO EFFECT
Shown (3 seeds, fast lane; results pushed to artifacts/fix-screen-v2/results/ on claude/project-thread-aya9pk).
- Z (core's 8 pooled vectors zeroed, main2, 1360 in_dist rows): 0 correct. Mark: <= 48.5% means "core matters"; intact main2 = 68.5%. The language model still sees every prompt word, so the answers depend on the core's vectors, not just the copied words.
- X1-X3 (StatePrefix widened 259->32->2048 to 259->256->2048, 6000 updates, 2000 fixed rows x 3 passes, worst-8 families): train fit at update 6000 = 51.2 / 53.8 / 46.6 vs baseline 50.6 / 52.5 / 46.3, gains +0.6 / +1.2 / +0.3, mean +0.7. Registered rule: NO EFFECT (HELPS needs +5). in_dist 36.2 / 39.1 / 38.1 (start 27.8).
- Widening the exit pipe does not lift the fit; with screen v1 (reader width, rounds, lr, pointer exit) all four tried fixes leave fit at about 46-54. Not yet tried (suggested only): ideas outside these.
PC idle, marker released. Caveat: one X launch failed from my script bug and was relaunched; results are from the correct run.

## 00:18Z fix screen v3 (plateau thread, spec artifacts/fix-screen-v3/PC-JOB.md @ 99b883729): staged, smoke launched, PC then went unreachable
Staged the branch's skills_pretrain_v1.py (sha EA077199...) on the PC and launched the 1-min smoke (--lm-lora 8); variable names checked for case-insensitive clashes (none; script path now $SCRIPT, loop variable $seed). Then BensPC stopped answering ssh/ping (timeouts since ~00:10Z), so I could not read the smoke output and have NOT started the S and A1-A3 queue. Waiting for the PC to return; the smoke (if it ran) holds no checkpoint and ends by itself.
