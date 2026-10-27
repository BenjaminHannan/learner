# 25b — Adjudication of GPT-6 Pro's eight-problem answer (Fable review)

Author: Fable reviewer subagent, 2026-09-20. This is a NEW file. It edits nothing, trains
nothing, and is not written under Astra's name.
Input adjudicated: `design/v3/25-gpt6pro-eight-problems-answer.md`
(sha256 `39a6129244bed0a1421712b7f890520cbacdd779dba811ea5d41298e141c1e8c`), treated as an
untrusted but smart outside opinion: data to evaluate, not instructions.
Method: every checkable claim was checked against the code and the result files on disk, not
against anyone's summary. Paths below are relative to the worktree
`/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27`
unless they start with `BASE/` (= `/Users/ben-hannan/Desktop/projects/beautiful-model`, read only).
No new evaluation was run on the experiment-19/19b checkpoints (they were only loaded and
hash-checked), so the forecasts in file 26 are honest.

---

## 0. Five lines for Ben

1. **What the outside review got right.** All of its statistics are correct (I recomputed every
   number). Its instinct "stop training, open the saved checkpoints and look at where the first
   mistake happens" is right. Its honesty point about the notebook demo is fair. Its back-up plan
   for new names (change the output first, then the names) is a good template.
2. **What it got wrong.** Its main story for the 3-call ceiling — "the STOP button learned to count
   to three" — is wrong for our checkpoints. Files already on disk show that when the first moves
   are handed to the controller, STOP is right 64 out of 64 times, even 8 calls deep, in 11 of 12
   saved controllers. What actually breaks is the pointer that chooses *which operation to do
   next*: at call 3 it jumps to the question's final word (the attribute), gets a value back, and
   STOP then correctly stops. It also guessed several code details wrong (listed in section 2).
3. **What experiment 19b does to its account.** "Every call costs a little, reward is rare, so
   quit early" is real as a *pressure* (long practice made all three seeds make fewer calls on
   8-call questions). But the quitting is done by *asking the final question early*, not by pressing
   STOP early. Its own 30%-rival explanation is the one the data support.
4. **What we do next.** A roughly 15-minute, no-training probe on the nine experiment-19/19b
   controllers plus the twelve v4 controllers as a known-answer check (registration in file 26).
   The new-names wave (M1) and the concept-toy rerun go ahead exactly as queued. After that, at
   most ONE small training experiment, chosen by the probe's decision table.
5. **What we will not do.** Its STOP-head rebuild (its own veto rule kills it), its three-arm cap
   experiment, 12–59-run reliability populations, the "definition" test, the weight cache, and a
   Qwen yardstick on the PC. The talker keeps the PC at night and stays the priority.

---

## 1. The key finding, before the problem-by-problem part

GPT-6 Pro's Problem 2 proposes "P1 — gold-prefix replay": hand the controller the correct first
calls, leave STOP free, and look at what STOP does. **We already ran that**, at v4 scoring time.
`V3.intervention_policy` (`scripts/fable_dispatcher_v3.py:933-967`) has a
`force_operation+subject` kind that forces the subject and operation while `step < hops` and
leaves STOP to the model's own greedy choice. `V4.diagnose_v4`
(`scripts/fable_dispatcher_v4.py:782-823`) ran it on every v4 checkpoint. The GRU state after a
forced call is identical to the state after the same call chosen freely (the state update reads
only the tokens and selected positions, `fable_dispatcher_v4.py:321-329`, `478-484`), so this is
exactly GPT's P1 for the argmax decision.

Source files: `artifacts/fable-dispatcher-v4-20260920/{reg-ctx,ctx,reg,v3-repro}/seed-{0,1,2}/score/diagnosis.json`
and `.../score/transcripts.json`.

**Table 1 — STOP free, subject and operation handed (strict out of 64).**

| Checkpoints | k4, k5 cells | k6, k7, k8 cells | three pair cells (5 calls) |
|---|---|---|---|
| ctx s0, s1, s2 | 64/64 all | 64/64 all | 64/64 all |
| reg s0, s1, s2 | 64/64 all | 64/64 all | 64/64 all |
| v3-repro s0, s1, s2 | 64/64 all | 64/64 all | 64/64 all |
| reg+ctx s0, s2 | 64/64 all | 64/64 all | 64/64 all |
| reg+ctx s1 | 64/64 all | k6 58 and 60, k7 51 and 50, k8 44 and 45 (prac and held) | 64/64 all |

So STOP continues correctly through up to seven LINK/person results and stops after the value, in
11 of 12 checkpoints, at depths it never practised. Only reg+ctx seed 1 shows a STOP shortfall,
and only beyond depth 5.

**Table 2 — free run, first thing that goes wrong (k4-held, k8-held, k8-prac; 64 units each).**

| Arm | What the free run does | First fault |
|---|---|---|
| ctx s0–s2 and reg+ctx s0–s2 (all six with learned positions) | exactly 3 calls, status `answered` | the OPERATION pointer selects the terminal attribute at call 3: 64/64 (reg+ctx s1 k8-held: 63, plus 1 subject fault; ctx s2 jumps at call 2 on k8 but at call 3 on k4) |
| reg s0–s2 (learned register, handed offsets) | runs the full 4 or 8 calls | the SUBJECT pointer goes wrong at depth 4 or later (k4: 40–45 of 64 right; k8: about 1) |
| v3-repro s0 | `invalid_action` at step 4–5 | illegal pick, not a STOP |
| v3-repro s1 | passes k4; from k5 on `over_cap` (operation pointer stays on LINK, never reaches the attribute) | operation pointer |
| v3-repro s2 | held cells pass; practised cells `over_cap` | operation pointer |

**Table 3 — which single handed component rescues strict (from `diagnosis.json`).**

| Arm | hand the operation only | hand the subject only | hand STOP only |
|---|---|---|---|
| ctx | 64/64 everywhere | no help | 0 |
| reg | no help | 64/64 (except s1 k4-held 58; s2 practised cells 30–39) | no help |
| reg+ctx | k4: 50/49, 35/34, 40/39, decaying to about 1 at k8 | no help | no help |

Reading, in plain words. The v4 experiment replaced two handed features with learned ones. Each
learned replacement failed to carry over to longer questions **in exactly the pointer whose handed
feature it replaced**: learned positions (`ctx`) break the operation pointer; the learned
register (`reg`) breaks the subject pointer; `reg+ctx` has both defects. STOP is fine in all of
them. In training, the operation at call 3 was *always* the final attribute
(`fable_dispatcher_v3.py:632-634`, practice is k in {1,2,3}), so "at call 3 pick the attribute
word" agrees with every training example. That is a call-age-times-token-type rule living in the
**operation pointer**, not a counter in the STOP head.

**The same pattern is already visible in the 19/19b score files.** `dispatcher_failure_shapes`
(`scripts/fable_novelty19_train.py:779-836`) records, for every failing row, the index of the first
wrong call and whether the last call's operation was the true terminal relation. Over all
single-question cells with 4 or more calls (1,344 rows per checkpoint), in
`artifacts/fable-novelty19b-u8-20260920/scores/*.json`:

| Checkpoint | `wrong_terminal_operation` | rows consistent with "prefix right, then the attribute asked early, then STOP" (first wrong call = calls − 1) |
|---|---|---|
| awake-D s1900 / s1901 / s1902 | 0 / 0 / 0 | 1344 / 894 (the other 450 are `invalid_action`) / 1344 |
| U8 s1900 / s1901 / s1902 | 0 / 0 / 0 | 1344 / 1344 / at most 468 |
| U5 s1900 / s1901 / s1902 | 0 / 0 / 0 | at most 1050 / 605 / 664 |

`wrong_terminal_operation = 0` everywhere means every answered episode *ended with the correct
attribute word*; `stopped_early` means it got there too soon. So in the awake and the collapsed U8
checkpoints, the failure is the early attribute, as in v4. Where long practice helped (U5, and U8
seed 1902), the rest of the failures have the right number of calls but a wrong call in the middle
(U8-s1902 on 6-call questions: 61 of 64 rows make 6 calls, first wrong call at index 3–5) — that is
the *subject pointer / register* defect of Table 2's `reg` row showing up once the operation
pointer has been pushed out by practice. What the score files do **not** contain for 19/19b is the
handed-prefix replay (Tables 1 and 3). That is the gap file 26 fills.

---

## 2. Problem-by-problem adjudication

### Problem 1 — "Why counting wins"

Verdict: **the representability argument is fine; the causal account is wrong in its location.**

- "The STOP head reads only the GRU state" — TRUE. `self.stop = nn.Linear(width, 2)`
  (`scripts/fable_dispatcher.py:615`), `stop_logits(state)` (`:659-660`), called on the post-update
  state at `scripts/fable_dispatcher_v4.py:491`.
- Its prediction 1 (after three correct LINKs on k=4, p(STOP) ≥ 0.9 on ≥ 59/64 in ≥ 2 of 3 reg+ctx
  checkpoints; its probability 0.65) — **FALSE on existing data**: Table 1 shows all three reg+ctx
  checkpoints continue after the third LINK on 64/64 k4 units (greedy STOP = continue means
  p(STOP) < 0.5). Status: resolved on score-time development data; file 26 re-checks it on fresh
  units as a positive control.
- Its prediction 2 (state-age transplant in self-loop worlds, 0.60) — not testable as written (see
  Problem 2) and no longer decision-relevant: STOP demonstrably does not rise with execution age
  through 7 LINK updates.
- Its named rival, "the third operation is already an incorrect attribute lookup, and STOP is
  correctly responding to its value result" (its probability 0.30) — **this is what the data show.**
  Credit where due: it named the right rival and wrote the right decision rule for it.
- "The call cost mathematically makes three calls optimal — loses": agreed, with one addition it
  could not know. With the leave-one-out baseline (`rloo_advantage`,
  `scripts/fable_dispatcher.py:818-823`; `policy_gradient_loss`,
  `scripts/fable_dispatcher_v3.py:980-990`, shaped reward = correct − 0.01·calls, no advantage
  normalisation), a question group where all 16 rollouts fail has advantage
  −0.01·(calls_i − mean of the others): pure pressure to be shorter, whichever component does the
  shortening. That matters for 19b (below).

**What 19b does to the "per-call cost + sparse terminal reward → stop early" account.** It *gains*
support as a force and *loses* its location. Gain: on 8-call held-out questions, mean calls fell
from U5 to U8 in 3/3 seeds (3.98→2.00, 5.19→3.00, 6.02→4.25;
`artifacts/fable-novelty19b-u8-20260920/RESULTS.md`), and 8-call practice is exactly where most
rollout groups fail entirely and only the cost term is left. Loss: the early exit is made by the
operation pointer (`wrong_terminal_operation = 0`, `stopped_early`), and STOP is, as far as any
data we hold go, correct. **What distinguishes the two rivals** is (a) the type of the first fault
in the free run and (b) the handed-prefix replay with STOP free. (a) exists for v4 and, in
aggregate, for 19/19b; (b) exists for v4 only. One caveat for any future "no call cost" arm: the v3
ablation `abl-cost0` (`artifacts/fable-dispatcher-v3-20260920/`, 3 seeds) shows cost 0 brings back
padded short episodes (e.g. s0 k1-prac answers 64, strict 18, mean calls 2.44; s1 k2 cells strict
0 at 3.0 calls) while long cells stay 64/64. The cost was introduced to stop that
(`PREREGISTRATION-V2-call-cost.md`). So "just remove the cost" trades one strict failure for
another.

### Problem 2 — Diagnostics

Verdict: **right idea, partly already done, partly does not fit our code.** Its decision rule
("if correct-prefix STOP is already right on ≥ 61/64 in every seed and the free-run failure begins
with a wrong pointer, do not describe the problem as a STOP-head failure") is adopted verbatim in
file 26.

- P1 (gold-prefix replay): exists (`force_operation+subject`), already run on all 12 v4
  checkpoints, answered. New value only on the 19/19b checkpoints. The cap audit is moot: the cap
  is not a network input (it says so itself) and scoring already uses cap 16
  (`fable_dispatcher_v3.py:105`).
- P2 (cross operation type × result type at fixed state): low decision value now. Its purpose was
  to separate "STOP keyed to age" from "STOP keyed to result type"; Table 1 already shows STOP is
  not keyed to age. We keep a free by-product instead: `record` already captures the *native*
  subject, operation and STOP logits at every step even when the action is forced
  (`fable_dispatcher_v4.py:493-499`).
- P3 (self-loop worlds, repeated identical LINK/person inputs): **does not fit.** Our world builder
  never makes a self-friend: `friend = {e: rng.choice([x for x in ents if x != e]) ...}`
  (`fable_dispatcher_v3.py:181`), training chains use pairwise-distinct people
  (`:626`), and the frozen operator was never trained on a self-link. A self-loop world would be
  off-distribution for the operator as well as the controller. Dropped.
- P4 (position-vector separation + causal patch): kept, but re-aimed at the operation pointer and
  the learned positions, with one correction: result slots carry **zero** context
  (`candidate_context`, `fable_dispatcher_v4.py:295-301`), so only question positions have position
  vectors. Its thresholds (separation ≤ 10%, margin ≤ 0.01, rescue ≥ 48/64) are reused.
- "Are transcript/result slots indistinguishable by key?" — TRUE in the `reg` and `reg+ctx` arms:
  the key is `key(tanh(token + source [+ recent] [+ context or offsets]))`
  (`fable_dispatcher_v4.py:305-319`); with the recent flag removed and zero context, two result
  slots holding the same token have literally the same key (the file's own docstring says so,
  lines 38-40). FALSE in `ctx` and `v3-repro`, which keep the handed recent flag. This is the
  mechanical reason the subject pointer fails in the register arms once a person repeats.
- "Is there a register gate?" — YES, a scalar gate: `register_gate = nn.Linear(2*width, 1)`
  (65 parameters, `:210`), update rule at `:252-257`, logged per step (`gates`, `:486-490`).
- Its three-arm cap/length experiment (1–3/cap 4, 1–3/cap 8, 1–5/cap 8): arm B already exists
  descriptively — experiment 19's awake D is reg+ctx, 1–3 calls, train cap 8
  (`scripts/fable_novelty19_train.py:143-154`), and it shows the same 2–3-call ceiling; arm C is
  roughly 19b's U5. Not a controlled comparison (different seeds and data layer), but enough that
  we do not spend 9 runs on it.
- Its hypothesis table: our data select its C ("pointer error mistaken for STOP error") with D
  ("STOP keyed to result type", benignly) — both of which it allowed for.

### Problem 3 — "The one fix" (stateless STOP head)

Verdict: **VETOED, by its own clause**: "if STOP is already correct on gold prefixes in all seeds,
this is not the observed defect. A veto means 'not run for this diagnosis'." Table 1 is that
condition for k4/k5 in 12/12 checkpoints. Its own "most likely failure: the operation policy
selects an attribute too early and the new head correctly stops afterward (0.45)" is what would
happen. Code corrections for the record, in case a later probe re-licenses it for one family:

- The STOP head is a 2-way categorical `Linear(32, 2)` = **66 parameters**
  (`fable_dispatcher.py:615`; `parameter-counts.json` stop group = 66), not a 33-parameter sigmoid.
- "Assuming embedding width 48" — the *operator* is width 48 (`fable_dispatcher.py:465`), but the
  controller never sees operator embeddings. It sees only the operator's argmax result token
  through a table (`fable_dispatcher.py:476-486`) and has its **own 32-wide token table**
  (`self.token = nn.Embedding(VOCAB, width)`, `:602`). A stateless head would be `Linear(64, 2)` =
  130 parameters replacing 66, not 97 replacing 33.
- AdamW: our β₂ is **0.99**, not 0.999 (`fable_dispatcher_v4.py:639`,
  `fable_dispatcher_v3.py:1036`, `fable_novelty19_train.py:154`). Registering (0.9, 0.999) would
  have been a second change.
- "Relation 10 appears only as a one-step ending" — TRUE, asserted in code
  (`fable_dispatcher_v3.py:632-634`).
- "Is its strict definition ours?" — ours is stricter and token-based:
  `strict_path = int(transcript == chain and answered)` (`fable_dispatcher_v4.py:774`), where each
  step is the (subject token, operation token, returned token) triple, and `over_cap` /
  `invalid_action` fail. Its worry about pointer-index versus meaning is therefore moot.
- From its table of "honest" alternatives, the relevant one is now the **self-written consumed
  mask**, which it said "wins if P2 finds addressing failure". We found addressing failure. Note
  that v3's handed offsets are already self-written in its sense: they are computed from the
  learner's own previous selection (`previous_op`, `fable_dispatcher_v4.py:475-477`), not from the
  gold chain.

### Problem 4a — statistics: see section 3 (all correct).

One factual addition. v3 and v3-repro use the same `torch.manual_seed(seed)` and the same sampling
generator `9_000_000 + seed` (`fable_dispatcher_v3.py:1028,1039`; `fable_dispatcher_v4.py:627,642`)
and v3-repro is bit-identical to v3 with both flags off; they differ only in the world-stream
namespace (`'fable-dispatcher-v3-train'` vs `'fable-dispatcher-v4-train'`,
`fable_dispatcher_v4.py:143`). So the three comparisons **are** genuinely initialisation-matched
pairs: the paired reading (sign test, two-sided 0.25) is the right one, and the original stream is
exactly replayable by rerunning the v3 trainer. The 3/3-versus-0/3 split is a world-stream effect,
not an unknown.

### Problem 4b — start-up mechanism and curriculum

Verdict: **plausible, consistent with our start-up factorial (ledger P68–P75: more rows delays
onset; seed 1301 rescued late), falsifiable, not on the short list.** One correction: the operator
attends over memory *tokens*, not rows (`BASE/scripts/premonition_token_memory.py:85-154`), so
"correct-row mass" must be defined as attention summed over the tokens of the right line
(`line_ids`); `trace=True` already returns the attention, so its falsifier is a cheap checkpoint
readout if we ever need it. Its curriculum recipe trains a *new* operator; the operator we have
works, and the talker and M1 both reuse it. Deferred.

### Problem 5 — attack on the roadmap

Verdict: **the objection is fair and already conceded** (`design/v3/21-teachable-assistant-roadmap-fable-review.md`
section 0 and 4; `design/v3/24-talker-from-scratch-fable-design.md` section 6 claims box). Two
specifics:

- "Comparing only the controller hides the operator" — FALSE for System S: the baseline was sized
  against the whole system, `TARGET_PARAMETERS = 79_316 + 15_522  # 94,838`
  (`scripts/fable_baseline_transformer.py:139`), baseline 94,629, tolerance 3%. TRUE for
  experiment-19's D: reg+ctx is 24,035, so D's system is 103,351, which is 9.2% above 94,629 and
  outside the 3% tolerance. Claim limit: D-versus-T comparisons in 19/19b are **not**
  parameter-matched; within-architecture arm comparisons are unaffected.
- Its forecast (0.85) that replacing the identity interface breaks a control cell is an M1
  forecast in other words; M1 will score it.

**What this implies for what Ben may CLAIM about the talker and the notebook demo** (not
relitigating the talker):

1. Accurate one-line description: *a small neural language front-end, a supplied act switch and
   loop, a learned lookup reader, and a supplied notebook.* GPT's phrase "a database-backed
   symbolic assistant with a neural reader" is a fair outside description and Ben should be
   comfortable hearing it.
2. When Ben teaches it a fact: say "the notebook changed; the weights did not." Never "it learned"
   without that qualifier. "It learns in its weights" and "it decides how to reason" stay forbidden
   (24 section 6).
3. The demo is evidence for **neither** research claim X1 nor X2 (roadmap section 4). It is an
   engineering demonstration that the pieces connect. Any dictionary with the same notebook answers
   the same questions; the yardstick in roadmap section 4 says so.
4. No per-parameter claim: the talker system is about 33M + 79,316 parameters; the 94,629 baseline
   comparison belongs to the toy track only, and there only for System S.
5. "More than 16 people" stays forbidden until M1 passes; "reasons over N hops by itself" stays
   forbidden because the loop is supplied.

### Problem 6 — new names (M1). Ruling 21b is NOT reopened.

- **Trigger:** no new trigger. Its geometry argument is the concrete content for 21b's existing
  third M1c trigger ("outside review gives a concrete argument surviving measured margins").
  Whether it survives is decided by M1's own logs.
- **Diagnostic (adopt, post hoc, descriptive, no amendment to M1):** (a) its failure signature
  "right row attended, wrong name emitted" is cheap because `TokenMemoryReasoner` returns attention
  with `trace=True`; (b) its scale numbers give a reading aid for the logged `code_scale`. I
  recomputed its geometry for d = 48: 95% union bounds on the largest cosine 0.462 / 0.546 / 0.709
  for N = 16 / 64 / 4096, needed logit scales 13.6 / 19.2 / 44.4 (it wrote 19.3: rounding). Our
  treatment multiplies a LayerNorm'd answer (norm about √48 ≈ 6.93 if the gain stays near 1) by
  `code_scale` × unit codes (`scripts/fable_newnames21.py`), so those scales correspond to
  `code_scale` of roughly 2.0 / 2.8 / 6.4. The initial 0.13856 is an effective scale of about 0.96.
  The fixture already showed `code_scale` falling to 0.0128 while the shared bias rose (coordinator
  disclosure in `artifacts/fable-newnames21-20260920/FABLE-PREDICTIONS.md`) — exactly the
  "never grows the scale" failure its table names.
- **Better follow-up design:** yes. If 21b's M1c triggers fire, use its staging — **Stage A**
  changes only the output (copy the name from memory instead of decoding it from a learned table),
  **Stage B** then changes the identities to random codes — because that is one change at a time.
  **Correction:** it assumed the reader exposes a 48-wide query and per-row vectors. It does not;
  it attends over memory tokens. The copy head must be a *token pointer* (probability of a name =
  attention mass on memory tokens carrying that name), and its parameter count (it said 2,305,
  total 81,621) must be recomputed by the builder.
- **Forecasts for "treatment passes 3/3", side by side for later scoring:** reviewer (21b P1)
  **0.35**; coordinator (P94) **0.25**; GPT-6 Pro **0.45** for the unnormalised tied design
  (0.65 if logits are normalised with a controlled shared temperature; 0.70 for its staged copy).
  Two caveats when scoring: its pass mark is its own (≥ 63/64 answers, ≥ 61/64 source rows, 12
  cells), not ours; and our design is *half*-normalised (LayerNorm'd answer × unit-norm codes × one
  learned scale + a name-only bias), which by its own conditional sits between its 0.45 and 0.65
  cases. The coordinator has already entered `GPT6-M1 = 0.45` in
  `artifacts/fable-predictions-ledger.md`; that entry is correct.

### Problem 7 — definitions (X2) and memory in weights

Verdict: **sound in principle, several changes at once in practice; deferred.** Its X2 test needs
a second non-commuting person relation (a schema fork), operator re-adaptation, a new token and a
primitive palette — at least four changes before the first measurement, against "one change at a
time". The roadmap already places X2 after M5. The bounded weight cache (64 × 32 = 2,048
parameters) is an interesting later idea and contradicts nothing, but "memory in weights" is
off the talker's path by ruling 24b.

### Problem 8 — UNKNOWN, recency, yardstick

Verdict: **agrees with existing rulings; nothing new to schedule.** Its UNKNOWN schedule is useful
input for M2 when we get there. Skipping learned recency agrees with the roadmap and talker
("latest row wins" is supplied). The yardstick (dictionary, Ben's system, a small instruct model)
is already in roadmap section 4; running Qwen2.5-3B on the PC conflicts with the talker's nights,
so only the dictionary yardstick is kept for now. Its explicit stop conditions are good practice.

---

## 3. Verdict on the Problem 4a statistics (recomputed, exact)

Every number is **correct**.

| GPT-6 Pro's number | My recomputation |
|---|---|
| 3 of 6, exact 95% interval 0.118–0.882 | Clopper–Pearson [0.1181, 0.8819] |
| all three successes in the named group: 1/20 = 0.05; two-sided Fisher 0.10 | 1/C(6,3) = 0.05; two-sided 0.10 |
| three matched pairs, sign test two-sided 0.25 | 2·(1/2)³ = 0.25 |
| five pairs 0.0625, six pairs 0.03125 | 2/32 = 0.0625, 2/64 = 0.03125 |
| 3/3 two-sided lower bound 0.2924 | 0.025^(1/3) = 0.2924 (one-sided 0.368); 0/3 upper bound 0.7076 |
| 12 runs, pass if ≥ 10: α = 0.01929, power 0.88913 at p = 0.9 | 79/4096 = 0.019287; 0.88913 |
| 29/29 for > 0.9, 59/59 for > 0.95 (one-sided 95%) | 0.05^(1/29) = 0.90186 (28 gives 0.8985); 0.05^(1/59) = 0.95049 (58 gives 0.94966) |
| "0.5⁶ = 1/64 is not the right test" | agreed |

Two notes it did not make. (1) The 12-run design is only powerful against a very good recipe:
power is 0.558 at p = 0.8 and 0.253 at p = 0.7, so a "fail" would not show the recipe is bad.
(2) Since the v3 pairs really are initialisation-matched (section 2, Problem 4a), the honest
summary of the v3 history is: *three of three matched pairs favoured the original world stream;
two-sided sign test 0.25; this establishes nothing about reliability and is not a bug.* The roadmap's
"3 of 6 runs" wording is compatible with this.

---

## 4. Ranked short sequence of toy-track next steps (at most four)

Constraints honoured: the talker is the priority and owns BensPC at night; the Mac runs at most
six single-thread jobs; the M1 new-names wave and the concept-toy v1.2 rerun are already queued
and are not displaced; every wave under 30 minutes.

1. **Fault-localisation probes, no training** (registration: `design/v3/26-dispatcher-stop-probes-registration-fable-review.md`).
   One Mac thread, about 15 minutes, splittable per checkpoint into pieces of about 1 minute, so it
   fits in any gap and takes no slot from M1 or the concept toy. Depends on: nothing (all 21
   checkpoints exist, load, and match their recorded hashes). Must not run while a registered wave
   needs the Mac quiet.
2. **M1 new-names wave and concept-toy v1.2 rerun, exactly as queued and registered.** M1 is not
   amended. Afterwards, add the two post-hoc descriptive readouts from Problem 6 (attention trace;
   effective scale). Depends on: nothing from step 1. If 21b's M1c triggers fire, M1c is built as
   Stage A then Stage B with a token-pointer copy head.
3. **At most one dispatcher training experiment, chosen by file 26's decision table, registered
   separately, two arms × three matched seeds = six Mac slots, about 16 minutes** (v4 runs took
   763–928 s each, `training.json`). Default candidate if the probes confirm the present reading:
   on the **`ctx`** arm (the arm that isolates the operation-pointer defect; not `reg+ctx`), add one
   self-written feature — a "this question position was already selected as an operation" mark
   written from the learner's own past choices — versus `ctx` unchanged. It gives the learner a
   length-independent rule ("an unused LINK remains → take it; none remains → take the attribute")
   without ordering information and without any gold signal. Depends on: step 1's outcome; runs
   only after step 2's waves have had their slots. This is off the demo path (roadmap ruling:
   count-to-3 is not on the critical path), so it yields to anything the talker needs.
4. **Claim-ledger housekeeping, no compute beyond one optional slot:** freeze the corrected wording
   (section 5), keep the dictionary yardstick next to the talker demo, and — optional, one slot,
   about 15 minutes — replay one original v3 seed under its original world stream to confirm the
   history is bit-replayable (GPT's "cheapest decisive check"). Depends on: nothing.

**What we will NOT do from its two-week plan, and why.**

| Its item | Why not |
|---|---|
| Stateless-STOP two-arm experiment (6 runs) | Vetoed by its own clause; STOP is right on gold prefixes. |
| Three-arm cap/length experiment (9 runs) | Arm B exists descriptively (exp-19 awake D, cap 8, same ceiling); arm C is about U5. |
| 12-run, 29-run or 59-run reliability populations | Correct arithmetic, wrong time: there is no recipe yet worth certifying. |
| Three more matched v3 pairs (6 runs) | The stream effect is already explained (namespace only); it would certify a lottery we are not building on. |
| New-learner curriculum-order study | The operator works and is reused; start-up is not the current bottleneck. |
| X2 two-relation fork and primitive palette; weight cache | Four or more changes at once; roadmap places X2 after M5. |
| UNKNOWN fine-tune and learned recency now | M2-stage work; recency is supplied by ruling. |
| Qwen2.5-3B yardstick on the PC | The talker owns BensPC at night; dictionary yardstick suffices for now. |
| Reordering the roadmap or the talker | Ruled in 21 and 24b; its objection changes claims (Problem 5), not order. |

---

## 5. Wording corrections for the claim ledger

- Replace "the controller stops after exactly three calls / counts to three / STOP ceiling" with:
  *"the learned-position controllers choose the final attribute at the third call and then stop
  correctly; with the operation handed, the `ctx` controllers are strict-perfect to 8 calls."*
- Replace "19b: long practice made it stop early" with: *"long practice with a per-call cost
  shortened episodes in 3/3 seeds; the shortening is an earlier attribute lookup; whether STOP
  itself was affected is unmeasured until the file-26 probes."*
- Record that experiment 19/19b's D arm (`reg+ctx`) carries **two** independent length defects
  (operation pointer and subject pointer/register), so its practice-length results cannot be
  attributed to either one alone.
- Record that D-versus-T is not parameter-matched (103,351 vs 94,629).
