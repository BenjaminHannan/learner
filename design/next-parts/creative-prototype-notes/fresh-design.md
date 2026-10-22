# Creative prototype: an independent design (2026-10-03)

Design only. Nothing was edited, trained, tested or run. Written without reading OLD-creative-prototype.md or
critic-report.md. Sources: FACTS.md, integrated-design-v6-text.txt ("v6 l.N"), pipeline_code/calculator_runtime_depth_compare.py
("runtime"), calculator_tools.py ("tools"), pr23-f1-report.md ("F1"), pr23-design.md sections 2 and 6, the 09-25 creative
roadmap, scaling plan, research notes B and C, PASSMARKS-blurt3 and VERIFY-blurt3r, and a skim of TEACHING_TO_TEST_CONTRACT.md.

Labels: **shown** = read in code, a checked result, or the v6 text. **suggested** = reasoning or literature. **untested** = a
guess nobody has measured. The old number-puzzle results (MiniCPM5-1B + LoRA) are a different model; they are cited only as
motivation and never as evidence about this system.

## 0. Summary for Ben

1. In today's word problems there is almost nothing for creativity to do. Most questions have one right calculator call
   out of about 3 possible results, so trying them all takes 3 tries (shown, from the tool code). The real failure is the
   last step: the model only says numbers from a shelf of about 27 training answers, and got all 64 off-shelf answers
   wrong (shown, F1). More guesses cannot reach a number the model cannot say.
2. Also, for word problems the calculator can only check the arithmetic, not whether 18-7 or 18+7 is meant (shown, v6
   l.165). So without the answer key every guess stays "unresolved". With the answer key, the loop is just ordinary
   supervised training with extra steps.
3. So I propose testing the idea on "make the target" puzzles written in short English: "Luna's cards show 12, 25, 8 and 6.
   Using adding and taking away, each card at most once, make 31." Same calculator, same 4 loops, same heads. There are
   many correct solutions, and a checker can prove a solution right without any answer key, by replaying the calls.
   This is new generated data, so it touches your rule against unrelated data. I think it is related (same interface,
   same skill of choosing calls), but I flag it (decision D1).
4. A "candidate" is the model's full list of calculator calls over the 4 loops. The variety comes from sampling the call
   heads instead of always taking their top choice. Turning up the talker's temperature cannot change the calls (shown).
5. Learning: the model is fine-tuned on its own checked solutions. Context reuse (the doc's first choice) has no slot to
   live in today, so this skips ahead in the doc's order (flag D3).
6. The test: on 256 fresh puzzles, does the trained model's sampling hit more often than (a) before training and (b) a
   placebo trained on the same number of its own rule-keeping but wrong tries? Pass marks are fixed below. A careful
   control shows whether the model can learn these calls at all, so a failure can be read.
7. Cost: about 1.5 to 3.5 GPU hours on your PC, $0 (untested estimate).

## 1. Facts that drive the design

- The call is chosen before the talker speaks. Each loop: action head = Linear(256,3) over the mean of (h+e) at question
  positions; two bilinear pointer heads score references (question literals plus earlier OK results); the runtime takes
  argmax; then the tool runs, the result is written into a reserved slot, and the core advances. After 4 advances the
  frozen LM decodes greedily from the 8-vector prefix and BOS only (shown, runtime; FACTS).
- So a complete call trajectory exists before any LM decoding. LM temperature can only change the final text (shown).
- The first call is a linear function of the mean of the initial state plus input features over the question (shown in
  the runtime and v6 l.84). PR #23 reads the v6 code as starting h at zero (suggested here; the panel core's begin_latent
  was not checked). If so, the loop-0 action is a bag-of-features linear choice, and 127/128 panel calls fired at loop 0
  (shown, pr23 section 2).
- Tool limits: NONE/ADD/SUB; exactly two distinct references; at most 8 literals and 3 prior results; at most 4 calls;
  results enter only if they are one canonical numeric token (shown, tools and runtime). The tool never reads labels and
  does not know which literal is the target (shown).
- Every candidate starts from a clean begin_latent; nothing carries across forward calls (shown, runtime).
- Readout: 113/113 wrong finals were training answers; 64/128 rows needed an off-shelf answer and all 64 were wrong;
  71/86 right calls still gave a wrong final (shown, F1 and FACTS).
- Trainable modules today: core, reader, prefix, tool. Training = final-answer loss plus averaged call cross-entropy
  (shown, FACTS and v6 l.80). About 0.41 s per optimizer update in the disposable benchmark (shown, other workload).
- The "40 calls, rescued 2 of 6" creative diagnostic has no receipt (shown, FACTS). Treat it as unverified.
- Context reuse is not available in this pipeline: the calculator path has no example slot (its 8 memo slots are the 4
  tool pairs), every digit literal in the question enters the registry and more than 8 is an error, and the question cap is about 48 tokens (shown, runtime,
  tools, pr23 section 2). PR #23's Workspace contract adds an example role, but it is untested and not built.

## 2. What the candidate is, and what can vary it

| Variation source | Changes calls? | Changes final text? | Verdict |
|---|---|---|---|
| LM sampling temperature | No (calls are fixed first) | Yes | Wrong lever for calls; samples the answer shelf (shown + suggested) |
| Sample action and pointer heads, softmax(logits/tau) per loop | Yes | Yes (state changes) | **Recommended.** Plain sampling of the model's own policy (flag A) |
| Noise in the latent state (multi-start) | Yes | Yes | Later; it is a reasoning-method change |
| The 8 terminal checkpoints as a population | Yes | Yes | Cheap extra baseline only |

The candidate is the full trajectory: for each of 4 loops, the sampled (action, left, right), the tool's status and
result, plus per-loop log-probabilities. For goal puzzles the trajectory is the solution (for example "25+12=37, 37-6=31").
That is a genuine derivation with many valid alternatives, which is the case v6 l.162 says diversity needs. Different
NONE placements and ADD operand swaps are the same solution (canonicalized, so they never count as variety).

## 3. Does today's word-problem domain give creativity anything to do?

- Call space: with 2 literals, loop 0 has 9 head combinations (NONE, or ADD/SUB times 2x2 pointer pairs); 4 are
  DUPLICATE_REFERENCE errors; the 4 valid calls give only 3 distinct values (a+b, a-b, b-a) (shown, tools). Exhaustive enumeration with
  the answer key finds the right call in at most 3 tries. Nothing to discover.
- With the answer key as checker, "sample, keep the hit, train on it" equals training on the gold call, which the
  existing recipe already does (shown, v6 l.80). No new information, so no creativity claim is possible (suggested).
- Without the key, the calculator cannot tell 18-7 from 18+7, so every candidate is unresolved (shown, v6 l.165-167).
- The final answer is capped by the shelf; sampling the talker draws from the shelf, so off-shelf rescues should be rare
  (suggested from F1; untested). Optional Stage 1 below checks this cheaply and replaces the unreceipted diagnostic.

Verdict: on word problems the prototype can only show known-answer filtering, which Ben's rules say is not learned
creativity or live verification. Keep word problems as the retention guard and a report-only transfer check.

## 4. Proposed task family: make-the-target puzzles (decision D1, flagged)

**Task.** Given 3 to 5 numbers and a target, written in one short English sentence, produce calculator calls whose last
call returns the target. Rules (the canonical form, fixed in advance):
- The answer is the result of the trajectory's last non-NONE call, which must be status OK.
- Its derivation tree uses each given number at most once (operand origin spans disjoint at every node; the tool already
  tracks origin spans, shown) and never uses the target literal.
- Every value in the tree is in 0..99 and qualifies as one canonical token. At most 4 calls (the existing limit).
- Calls outside the tree are allowed but use budget.

**Why it tests creativity honestly (suggested).** Many valid solutions exist; the checker needs no answer key, only the
goal stated in the problem, which v6 l.168 names as the deployable kind of check ("restricted formal tasks may provide
exact semantics and goal predicates"). Hits are exact, so lucky guesses cannot fool it.

**Why it is not "unrelated generated data" (judgment, flagged).** Same English reader, core, heads, calculator, loop
budget and result slots. It exercises multi-step composition and result pointers, which the protocol supports but no
experiment has tested (shown, v6 l.80 "establishes neither multi-step composition..."). Ben chose exact-answer puzzles
of this shape in the older project (shown, 09-25 roadmap). It follows v6 l.66's generator rule: canonical form first, lossless English renderings, oracle never
deployed. Recommended default: proceed. If Ben says no, run only Stage 1 and report that the word domain cannot show learned
creativity.

**Generator (fixed before any model run).** Numbers 1..99, target 10..99, target not equal to a given number. Mix by the
shortest solution: 1 call 25%, 2 calls 50%, 3 calls 25%; 3 numbers 30%, 4 numbers 40%, 5 numbers 30%. Keep problems with
1 to 20 canonical solutions and a uniform-policy hit chance between 0.2% and 10% (computed exactly, section 9). 10 English
templates with names and objects (cards, coins, stickers); 2 templates are held out for the transfer slice.

**Exhaustive enumeration baseline.** A host solver enumerates every trajectory and finds all solutions. For 5 numbers
there are about 24 million rule-respecting 4-loop sequences before merging equal values (41 x 61 x 85 x 113, from the
tool limits); a search that merges equal values is fast on CPU (untested estimate). p_u is computed by dynamic programming
over tool states, with 100k Monte Carlo samples per puzzle as the fallback. It solves 100% of problems, so
the claim is never "beats search". Its jobs: certify each problem solvable, count solutions S, compute chance floors and
the expected tries-to-first-hit of blind enumeration in random order, (T+1)/(S+1) for T canonical trajectories. It never
runs inside the loop and never gives hints (v6 l.158).

## 5. One round of the loop

1. Name the worker version V0 (parent checkpoint hashes).
2. For each practice puzzle: worker attempt (argmax). If the checker accepts, store it (source = worker).
3. Otherwise sample K = 32 candidates at the dev-chosen tau, each from a clean start (source = explorer). Store every
   candidate with its acceptance state. Accepted ones are "rescues" against V0.
4. Learning (section 10) uses accepted records only. Rejected and unresolved records stay as diagnostics.
5. Report the v6 l.161 explorer numbers: newly rescued puzzles, duplicate solutions, unresolved count, latency.

No candidate ever sees the checker's verdict or another candidate (clean restarts, shown). Rejected guesses never enter any
context (there is no context path).

## 6. Checker and the three acceptance states

- **Accepted**: both checkers find the predicate true.
- **Rejected**: a definite violation (wrong value, target literal used, number reused, last call ERROR or out of range,
  no call at all, more than 4 calls).
- **Unresolved**: the checkers disagree, replaying the logged actions through the stdlib tool does not reproduce the
  logged results, or the run crashed or was cut off. Unresolved counts as no hit and never enters positive replay.

Independence: checker A replays the action list from the canonical form with its own arithmetic and ignores the runtime's
logged values. Checker B is written by a different agent from the rules text alone and tests membership in the solver's
canonical solution set. Neither shares code with the generator or the runtime. The model has no access to either. Gate:
A and B agree on 100% of all enumerated trajectories for 500 random puzzles, and both reject 20 planted violations.
Word-problem checks (Stage 1 only) are labelled "accepted by known answer (training oracle)" and never "verified".

## 7. Splits and leakage

- Split key = the sorted multiset of given numbers. All targets and renderings of one multiset go to one split. This
  stops paraphrase and sub-result leakage, and it makes later hindsight relabelling (same numbers, new target) safe by
  construction.
- Splits: practice 1,024; dev 128 (tau choice, gates, noise; reusable, never a claimed score); test T1 256 (once); test
  T2 256 (once, persistence); transfer slice X 128 (held-out templates plus 5-number puzzles; report only).
- All panels are generated, checked by A and B, hashed and sealed before any model run. Raw outputs are frozen before
  scoring, as in the existing protocol.
- Goal puzzles cannot reveal word-problem answers. Reserved and consumed word panels are never opened. Optional: the
  parent screens goal instances against its private operand-pair exclusions without showing them to anyone.
- T1 and T2 are consumed after one use and never enter training, tuning or replay.

## 8. Experience record (fits the PR #23 section 6 Workspace contract)

One JSON line per candidate, append-only, plus a per-round manifest (counts, hashes, versions, split hashes).
Tensors are not stored; the fields let a future Workspace assembler rebuild tokens, (role, modality), coords and valid.

```
{"schema":"premonition.experience.v1","record_id":"<sha256 of content>","family":"make-target-addsub-v1",
 "instance_key":"<sha256(sorted numbers, target, rules v1)>","split":"practice",
 "problem":{"text":"...","template":"t03","canonical":{"numbers":[12,25,8,6],"target":31,"rules":"v1"}},
 "workspace":{"question":{"role":0,"modality":0,"token_ids":[...],"coords":"column=token index; row absent; time 0"},
   "registry":[{"id":"literal:0","value":12,"char_span":[a,b],"token_indices":[...]}],
   "steps":[{"loop":0,"action":"ADD","refs":["literal:1","literal:0"],"status":"OK","value":37,"token_id":123,
             "result_role":3,"arrival_loop":0,"logprob":-1.2}, {"loop":1,"action":"SUB","...":"..."},
            {"loop":2,"action":"NONE"},{"loop":3,"action":"NONE"}]},
 "final_text":null,
 "outcome":{"state":"accepted","claim":"last call result = target under rules v1","canonical_solution":"(25+12)-6",
   "checker_a":{"sha":"..."},"checker_b":{"sha":"...","agree":true},"reason_code":null},
 "provenance":{"worker_version":{"core":"sha","tool":"sha","reader":"sha","prefix":"sha","lm":"sha"},
   "source":"explorer","tau":1.5,"sample_index":17,"rng_seed":0,"runtime_sha":"...","generator_sha":"...","utc":"..."},
 "eligibility":{"positive_replay":true,"consumed_panel":false}}
```

Mapping (suggested): question tokens are role 0, modality text 0, column = token position; each tool result is role 3
with time = arrival. For later context reuse, an accepted record renders as role example 2, row = example index, column =
token position, with the derivation as text ("25 + 12 = 37 ; 37 - 6 = 31"); this is a checked derivation, not a
self-written explanation. Provenance is never an input feature (section 6 rule).

## 9. Metrics, floors and power

- **Luck (primary):** accepted explorer candidates per puzzle on T1 (K = 32), summed over 256 puzzles. This is the
  direct measure of "generates better candidates".
- **First try (secondary):** argmax worker accepted on T1. This is "the worker can now do it alone".
- **Variety and coverage (guards):** puzzles with at least one hit in 32; distinct canonical solutions per solved puzzle;
  pass@256 on a fixed 64-puzzle subset of T1 (training on own hits can narrow what the model can reach; Yue 2025 vs
  ProRL is disputed, research note B).
- **Report only:** value hit rate among rule-valid candidates (separates "keeps the rules" from "reaches the goal");
  rule-violation and error rates; loop of first call; tries-to-first-hit vs blind enumeration; X slice; latency.
- **Chance floors (exact, per puzzle):** p_u = hit chance of a uniform random policy over the same head choices
  (NONE/ADD/SUB times all candidate pairs, including the target literal and duplicates), computed by enumeration. Floor
  for luck = 32 x sum of p_u. Floor for first try = sum of p_u.
- **Unit of analysis:** the puzzle for intervals (cluster bootstrap over puzzles), the seed for arm decisions (hence the
  each-seed rules), following the contract's clustering rule.
- **Power (suggested):** 256 x 32 = 8,192 samples per arm and seed. A 1.5x luck ratio should stand at about 2.5 to 3
  standard errors if hits spread over 40 or more puzzles. First try +8 points has roughly 75 to 85% McNemar power at 256
  puzzles if the base is near 10%. Seed spread is unknown with 2 seeds. Noise rule fixed now: on dev, run the untrained
  sampler with two sampling seeds; if their hit totals differ by more than 15%, use K = 64 on T1.

## 10. Learning route (decision D3, flagged)

- Feasible today: a weight update of existing trainable parts with the existing call cross-entropy (shown). Context reuse
  needs an example slot that does not exist (shown, section 1). The adapter is not built or approved (shown, v6 l.98).
- Recommended default: treat this as an early, small replay step. Fine-tune core + tool; freeze reader, prefix and LM.
  Reason: calls depend on core state and heads; freezing the reader keeps the word-problem input path stable. Fresh Adam,
  LR 1e-4 (the existing lower LR), 512 updates, each batch = 8 goal trajectories (call cross-entropy on every loop,
  including the NONE targets after the answer) + 2 TRAIN32 word problems with the original full loss (retention mix,
  identical in every arm). No final-answer loss on goal puzzles: the target is not a talker output, and training it
  would only grow the shelf.
- Deviation from the v6 order (context, adapter, replay), flagged. A tool-only run (about 133k parameters, an adapter
  stand-in) is the later one-change follow-up if retention fails.
- Starting points: the two seed-0/static and seed-1/static terminal low-LR checkpoints (32/32 TRAIN at all checks, shown;
  static avoids LM forwards for features). Chosen now, before any goal-puzzle result.

## 11. Arms (one change: what the model is trained on)

| Arm | Trained on (same count, same updates, same retention mix) | Question it answers |
|---|---|---|
| N | Nothing (the parent) | Plain sampling baseline |
| W | Accepted own candidates: worker hits plus at most 2 distinct canonical rescues per practice puzzle | The prototype |
| P (placebo) | Own candidates from the same puzzles that keep every rule but reach the wrong value; same count per puzzle, matched on number of calls | Does the goal check add anything beyond rule-keeping and more multi-call practice? |
| PC (positive control, flag E) | Enumeration-solver solutions for the same practice puzzles W used, same count per puzzle | Can this model learn target-directed calls at all? |

P is the key control: random-reward studies show training on own outputs can help with no real signal (Spurious Rewards,
research note B, shown in its setting). W vs P isolates the checker's goal information. PC uses solver-made worked examples,
which CURRENT.json marks "new_worked_example_supervision_authorized: false" for the curriculum (shown). It is a control,
never a discovery claim. Default: include it, because without it a W failure cannot be read. A known-answers-only arm (the
old blurt C) is skipped: the untrained worker will probably solve almost nothing (untested), so it would have no data.

## 12. Pass marks (fixed before running; sealed by hash in a PASSMARKS file)

H(arm, s) = accepted explorer candidates on T1 for seed s. Means are over the 2 seeds.
- **Validity (else the run is void, not failed):** checkers A and B agree on 100% of T1 candidates; unresolved at most 1%.
- **Inconclusive:** fewer than 150 accepted practice records per seed (cold start), mean H(N) below 25, or the each-seed
  rules split. Then one extra seed, then the line stops (PR #23 rule).
- **P1 luck rises:** mean H(W) >= 1.5 x mean H(N), and H(W,s) > H(N,s) for both seeds.
- **P2 the goal check caused it:** mean H(W) >= 1.3 x mean H(P), and H(W,s) > H(P,s) for both seeds.
- **G1 variety:** puzzles with a hit, W >= N in each seed; distinct solutions per solved puzzle, mean W >= 0.8 x mean N.
- **G2 coverage:** pass@256 on the 64-puzzle subset, W >= N minus 2 in each seed.
- **G3 retention:** TRAIN32 word problems, calls drop at most 1 and finals drop at most 2 per seed (parents are 32/32).
- **PASS = P1, P2, G1, G2, G3.** Claim: "after training on its own checked solutions, the model proposes correct
  solutions more often on fresh puzzles, beyond a matched placebo". Not claimed: worker learning, persistence, transfer.
- **Sharpening only:** P1 and P2 pass but G1 or G2 fails. Claim "sharper but narrower", not creativity.
- **Proved wrong:** mean H(W) <= mean H(P), or mean H(W) <= mean H(N), with validity met and not inconclusive.
- **Unreadable null:** W fails and PC also fails both "luck >= 1.5 x N" and "first try >= N + 8 points". Then the limit is the model
  (heads or loop-0 timing), not the creative loop; write an outside-opinion prompt before any change.
- **S1 worker learned (secondary):** first try on T1, W minus N >= 8 points pooled over 512 seed-puzzles and positive in
  each seed. Falsifier: W first try <= P first try.
- **S2 persistent (secondary, v6 l.94 and l.187):** after an identical intervening block (256 updates of TRAIN32 only)
  applied to W and N and a process restart, on T2: mean (H(W') - H(N')) >= 0.5 x mean (H(W) - H(N)). Only then claim
  "persistent".
- **Floor check (report):** if H(N) is below the uniform floor, say so; the parent policy is then worse than blind.

## 13. Stages and gates

| Stage | What | Gate to start | Where, cost |
|---|---|---|---|
| S0 | Generator, renderer, canonical form, checkers A and B, solver, p_u calculator, splitter, store writer. Seal panels and PASSMARKS. | None (can start now) | CPU, $0 |
| S0b | Native tokenizer: every 0..99 value is one canonical token; all renderings fit 48 tokens with at most 8 literals | S0 tests pass | Windows CPU, $0 |
| S1 | Sampler patch in the runtime (tau > 0 samples; tau = 0 is argmax). Regression: tau = 0 reproduces the saved TRAIN32 traces and answers of both parents exactly | S0b | GPU, minutes |
| S1w | Optional word diagnostic (below) | S1 | GPU, minutes |
| S2 | Dev: tau in {1.0, 1.5, 2.0}, pick max dev hits (ties go lower); noise rule; cold-start gate: at least 5% of dev puzzles hit and at least 150 expected practice records | S1 | GPU, minutes |
| S3 | Explore practice with V0; build store; audit A/B agreement | S2 gate passes, else raise the 1-call share to 50% once (fixed rule), else stop and propose hindsight relabelling | GPU, about 10 to 20 min per seed |
| S4 | Train W, P, PC, 2 seeds each | S3 audit clean | about 4 min per run at 0.41 to 0.5 s per update |
| S5 | Frozen T1 outputs for N, W, P, PC; score; verdict | S4 done; PASSMARKS hash unchanged | GPU, 30 to 90 min |
| S6 | Intervening block, restart, T2 | P1 and P2 pass | GPU, about 30 min |
| S7 | Replication with new generator seeds and fresh T1 | S5 PASS | as S3 to S5 |
| S8 | Round 2 (new practice puzzles, worker V1) and the handoff | S7 PASS | as above |

S1w (optional, recommended because the old diagnostic has no receipt): 32 parent-supplied practice word problems (never a
panel), half with off-shelf answers. (a) Force each loop-0 call option, later loops greedy, greedy decode. (b) Greedy calls,
32 LM-temperature samples of the final. Predictions fixed now (suggested): off-shelf rescues by (b) at most 2 of 16; final
right given a forced right call at most 30% on off-shelf items. If off-shelf rescues reach 8 of 16, my reading of the
shelf is wrong and the word domain deserves its own creative test. Labelled known-answer acceptance throughout.

Order with the rest of the queue: S0 to S2 do not touch word panels or existing checkpoints and can run beside the fresh
terminal eval, the curriculum and the English pilot. New outputs go to new folders; parents are copied, never changed.
If the curriculum later yields a better worker, rerun S2 to S5 with that named version.

## 14. Compute (untested estimates except the update cost)

About 300k trajectories in total (explore 68k; T1 68k for 4 arms x 2 seeds x 256 x 33; pass@256 98k for N, W, P; T2 34k;
dev 33k). The runtime is batch-1 (shown), so at 10 to 30 ms each that is 50 min to 2.5 h. Training: 6 runs x 512 updates
+ 4 intervening blocks x 256 updates = 4,096 updates x 0.41 to 0.5 s, about 28 to 34 min. Goal-puzzle rows need no LM forward (calls only); the retention rows
do. Total about 1.5 to 3.5 GPU hours on the RTX 5070 Ti, $0, well inside 16 GB (the 9M core is small).

## 15. Flags: changes to architecture or reasoning method, with my defaults

| Flag | Change | Default |
|---|---|---|
| A | Sampling the call heads at inference (explorer only; worker stays argmax) | Do it; it is the "varied candidates" Ben approved |
| B (D1) | New generated task family (goal puzzles in English) | Do it; related, judgment call under Ben's rule |
| C | The solution is the executed call trace, not the talker's text, for this family | Do it; not forced copying, since no final text is used |
| D (D3) | Weight-update learning before context reuse | Do it; context reuse has no slot today |
| E | Positive control trained on solver solutions | Include as a control only |
| F | Hindsight relabelling (a miss that made 22 is a solution to "make 22") | Later rung, one change vs P; solves cold start |
| G | Latent noise, call-timing change, separate explorer network | Not in round 1 |

## 16. Handoff to sleep replay

The store is the handoff: accepted records with versions and checking method, deduplicated by (instance_key, canonical
solution), rejected and unresolved kept apart. Later sleep replay should draw balanced batches across solution depths and
mix old TRAIN32 data (keeping old data avoids collapse, research note C item 28, shown in its setting). A promoted change
needs S2-style persistence evidence on a fresh panel, and the core and any adapter are promoted together (v6 l.185-187).
Expect gains to stall after about 2 rounds without new puzzles (ReST-EM, shown in its setting).

## 17. What this design cannot claim, and the main risks

- It cannot show that goal-puzzle skill helps word problems; transfer is report-only (suggested: math gains often stay
  put, research note B).
- It does nothing for the answer shelf; that stays with PR #23's C1 and C3 lines.
- Cold start is a real risk: a 9M core over frozen embeddings has far weaker number sense than the old 1B (untested).
  The S2 gate, the 1-call share rule and hindsight relabelling are the planned answers, with no hidden hints.
- The loop-0 call is a linear choice over mean-pooled features (shown), so first-try gains may need the model to learn
  to wait a loop; the first-call-loop histogram will show it.
- An outside opinion (Astra, or GPT with tables pasted) on D1 and the placebo choice before S3 would be worthwhile.
