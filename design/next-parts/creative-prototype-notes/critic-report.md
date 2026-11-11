# Critic report: OLD creative prototype design (review of OLD-creative-prototype.md)

Date 2026-10-03. Diagnosis only. Nothing was edited in the repo, trained, run, tested or bought. No GPU was used.
GOLD-PRIVATE-v1.json, eval panel files and reserved or blind panels were not opened.

Labels on every claim: **[shown]** = read in a named file or code line; **[suggested]** = my reasoning or arithmetic
from shown facts, or literature quoted in the repo; **[untested]** = a plan or a guess nobody has measured.
"OLD l.N" = line N of OLD-creative-prototype.md. "v6 p.N" = line N of integrated-design-v6-text.txt (one paragraph per
line). "runtime l.N" = pipeline_code/calculator_runtime_depth_compare.py. "tools l.N" = pipeline_code/calculator_tools.py.
"eval l.N" = pipeline_code/eval_terminal_fresh_windows_v2.py. The small card experiments and the village model play no
part here; the MiniCPM5 number-puzzle ("blurt") results are a different model and are cited only as such.

## 0. Plain-language summary for Ben

The old plan says: let the model try a practice problem many times, each time a little differently, keep the tries a
checker says are right, and practise on them. The problem is how this model actually works. The part that picks the
calculator step (add or subtract, which numbers) always picks its single favourite; nothing random happens there today.
The randomness the old plan turns on only affects the very last step, where the talker says the final number. So the
"many different tries" are really the same calculation with the final number re-rolled, like spinning a wheel of numbers
until it lands on the answer the checker already knows. A kept try then contains exactly the answer key, nothing more.
Practising on it is the same as practising on the answer key for the problems where the wheel happened to land right.
That cannot show the model learned to come up with better ideas; it can only show that extra answer-key practice helps.
On top of that, on the last test the model only ever said numbers it had seen as training answers (27 of them). The wheel will mostly land on
those, so any later gain could just be "it learned a few more numbers to say", not "it learned a better method".

Fixable, but the fix changes the core of the plan: make the randomness reach the calculator choice, make the problems
big enough that guessing cannot win, score the calculator choice separately from the final number, compare against
"answer key on randomly chosen problems", and add a check that the training recipe can learn anything new at all.

## 1. Verdict

The old design is **not runnable as a valid test of its own claim** [suggested]. Three defects are fatal: the variation
source cannot vary the method (D1), every accepted experience is identical to the gold trace so arm B equals arm D (D2),
and the answer-shelf effect from PR #23 F1 makes any gain uninterpretable (D3). Twelve major and twelve minor defects
follow. Much of the process scaffolding (fresh set after TRAIN is frozen, separate checker author, hash pins, proved-wrong
and inconclusive clauses, gold-is-not-live-verification wording) is good and should be kept (section 5).

## 2. Defects

### Fatal

**D1. The variation source (LM decode temperature) cannot produce varied candidate solutions.**
- Old claim: "the model writes many complete solutions, each a little different, because we let the talker pick words
  with some randomness" (OLD l.20-21); "frozen LM writes a trace with calculator calls and a final answer" (OLD l.76);
  "V1 LM decode temperature (and top-p) | existing sampler | No: inference setting" (OLD l.82); first run uses V1 only.
- Evidence [shown]: calls are chosen by heads, not by the LM. runtime l.119: `action=ACTIONS[int(action_logits.argmax(-1).item())]`;
  runtime l.122: both pointers by `argmax`. The four loops (decide, execute, write result, advance) all finish before
  `read_latent`; the LM then decodes from the prefix plus a constant BOS only (repo `scripts/sol_translator_english_v6.py` docstring: "Inference consumes FinalLatent only, plus generated history and constant BOS"; pr23-design.md section 2, Output row). eval l.492 raises unless there is a
  "normal single greedy generation", and eval l.499 raises if inference "changed RNG". The v6 English decoder calls
  `generate(..., do_sample=False, ...)` (repo `scripts/sol_translator_english_v6.py`, generate method).
- Consequence [suggested]: under V1, all k candidates for one problem share one call trajectory and one latent. They differ
  only in the sampled final-number tokens. A "rescue" is the sampler landing on the gold number while the model's internal
  state is unchanged from the failed greedy attempt. OLD l.49-50 ("Accepted candidates are exactly examples where it did
  not lose it") is therefore wrong: the prefix that "lost it" is the same; only the dice differ. v6 p.162: "Multiple
  spellings of one correct number are artificial diversity."
- Also [shown]: "existing sampler" is false for this pipeline; the sealed runner enforces greedy decoding and an unchanged
  RNG (eval l.492, l.499). A sampling runner is new code.
- Fix [untested]: vary the method, not the number. Add an inference-only sampling mode to the call heads (seeded
  multinomial over action and pointer logits at a fixed temperature, final answer decoded greedily), with a regression
  test that temperature 0 reproduces the argmax trace bit for bit. Keep LM-temperature sampling only as a separate readout
  diagnostic, never as the creative variation. This is new runtime code; flag it to Ben as a judgment call under his
  10-03 12:09 autonomy note (it is plain stochastic sampling of the worker's own policy, which v6 p.152 names as the first
  baseline, but it is not "nothing wired differently"). Rewrite the summary for Ben (OLD l.18-25) to describe the real
  mechanism.

**D2. In a single-call add/subtract domain, accepted traces are the gold traces, so B equals D and gold does reach B.**
- Old claims: "Gold answers reach training only in arm D" (OLD l.126); arm D = "gold reference traces for the same
  problems B won, same count", purpose "do own hits add anything over the answer key?" (OLD l.175); "D >= B ... creative
  loop matters only where no key exists" (OLD l.242); "D is compared, not marked" (OLD l.213).
- Evidence [shown]: acceptance requires final answer = reference answer (OLD l.101-102) and, after reconciliation, call
  operation and bindings equal to the oracle canonical form (OLD l.300-301). Tool equivalence is "ADD commutative
  equivalence; SUB ordered strict" (CURRENT.json `current_science.tool_equivalence`). All panel calls were at loop 0 with
  no later calls (CURRENT.json l.322, `all_active_calls_loop0_no_later_superseding_calls: true`). The recipe targets "the
  correct calculation until it succeeds, then ... no call" (v6 p.80).
- Consequence [suggested]: an accepted row is (question, the one correct call, NONE, NONE, NONE, gold number), which is
  the gold training row up to ADD operand order. B and D train on the same problems with the same targets, so B minus D
  is zero or seed noise (with shared seeds and identical rows the two runs could even be bit-identical, and a tie
  already counts as "D >= B"); the branch's reading ("answer key teaches as well") is a tautology. The statement "Gold answers reach training only in arm D" exceeds the evidence: every accepted final
  number in B is the gold number, selected by consulting the key. The only thing that differs between B and plain answer-key
  training is **which problems** get labels (those where search happened to land right). Under V1 the call targets in B
  are calls the parent already makes, so B's effective signal is final-answer cross-entropy toward the gold number on
  right-call problems: a readout curriculum, not creativity.
- Fix [untested]: drop D as an arm; replace it with a free CPU check that B's targets equal oracle targets (expect 100%
  up to ADD order). Add the control that tests the only real difference, selection: **G-rand** = oracle labels on the
  same number of practice misses drawn at random, same updates. State the claim as "learning from search-selected,
  key-checked labels" (v6 p.181: experiments may use an oracle; v6 p.175: a check that consults gold must not be called
  answer-hidden). If call sampling (D1 fix) lets accepted traces differ from canonical ones in call timing or extra calls,
  D becomes meaningful again as a later, separate one-change test of "own trace format vs canonical format".

**D3. Answer-shelf confound: sampling-based rescue selects shelf numbers, and any gain may be vocabulary, not method.**
- Old claims: the "71" correct-call-wrong-final rows are the natural teaching signal (OLD l.49-51); primary measures
  L (pass@k) and G (greedy) on FRESH with no stratification by answer value (OLD l.190-198).
- Evidence [shown]: pr23-f1-report.md: wrong finals equal to a training answer 113 of 113; the model uses 24 of 27
  training answers; "Right answers that are NOT a training answer: 64 of 128 rows, all 64 wrong". v6 p.171: in the depth
  comparison "63 of 64 final numbers matched its training targets", but "three expected values and tokens were already
  present in training ... This weakens an unseen-output-vocabulary-only explanation". v6 TRAIN diagnosis rows show
  p(top choice) up to 0.96 on wrong TRAIN numbers.
- Consequence [suggested]: under V1, rescues need (greedy call right) AND (sampler draws the gold number). The sampler's
  mass sits on the shelf, so rescues will be mostly problems whose answer is on the shelf. Two outcomes, both confounded:
  (a) rescues are on-shelf only, so B adds no new output values and any FRESH gain is sharpening on familiar numbers
  (the Yue 2025 pattern in reviews/creative-research-2026-09-25/B-feedback-kinds.md); (b) some rescues are off-shelf, so
  B widens the answer vocabulary, and FRESH gains on those values are target exposure (PR #23's C3 data change), not
  better candidate generation. Neither reading supports "learned to generate better candidates".
- Fix [untested]: (1) make the primary creative measure **call level** (operation + ordered binding, ADD order-free),
  which the shelf does not touch; report final-answer measures separately, as v6 p.80-81 asks ("Evaluate call validity,
  semantic choice, final accuracy ... separately"). (2) Stratify every final-answer measure on FRESH by answer value:
  S1 in the parent's training answers, S2 new in some arm's training rows, S3 in no arm's training rows. A method claim
  needs a gain in S3 or a gain over a vocabulary-matched control. (3) Match G-rand (D2 fix) to B in the share of
  off-shelf answer values, or add a vocabulary-matched gold arm.

### Major

**D4. The training recipe and pipeline are misdescribed; the plan would change the recipe as a hidden second change.**
- Old claims: "Trainable: reader, core, prefix only ... Same loss the current pipeline already uses: next-token loss of
  the frozen LM on the target trace" (OLD l.152-153); same optimizer, LR schedule, batch and steps "as the English pilot"
  (OLD l.155); summary says "never the talker" and lists reader, core, prefix (OLD l.24).
- Evidence [shown]: trainable components are `('core','reader','prefix','tool')` (eval l.42). Loss is "Final-answer loss
  and averaged call cross-entropy" (v6 p.80). The English pilot has not run natively ("English model understanding,
  output quality and training gains remain unmeasured", v6 p.420, and the native 64/48 qualification is pending).
  The known calculator recipe is the LR-fork recipe (1024-update forks at LR 0.001 or 0.0001 from 4096 parents, v6 p.71).
- Fix [untested]: copy the calculator recipe exactly (all four components, final CE + call CE, the LR and update count
  of the terminal forks) and name the config hash. Freezing the tool heads or borrowing an English config would be a second
  change.

**D5. Chance floors are ignored; several pass marks are mis-set or redundant.**
- Old claims: L1 B >= 1.5 x A on diversity-adjusted accepted samples; L3 B coverage >= A coverage; inconclusive if "A has
  fewer than 10 covered FRESH problems" (OLD l.202-211); k = 32 for evaluation (OLD l.91, l.191).
- Evidence and arithmetic [suggested, computed with 1-(1-p)^k; per-problem assumptions untested]: see the table in
  section 3, Q4. A policy that guesses the final number uniformly over about 90 two-digit values reaches pass@32 = 30%,
  that is about 58 of 192 FRESH problems, far above the "fewer than 10" inconclusive line. A guesser restricted to the
  27-value shelf reaches 70% on shelf answers at k = 32. If calls are sampled (D1 fix) with two literals, a uniform policy
  over the four valid binary calls is right 50% (ADD) or 25% (SUB) per sample, so pass@16 is about 99 to 100%: the call
  search is exhaustive enumeration and "luck" saturates.
- Further [suggested]: under V1, diversity-adjusted accepted samples equal coverage (one distinct call sequence per
  problem), so L1 implies L3 and L3 adds nothing. A ratio mark (1.5x) is unstable when A is small and can be unreachable
  near the ceiling (A at 70% needs B at 105%). STaR's own warning applies directly: "settings with a high level of chance
  performance (e.g. binary decisions) yield many poor rationales, confounding the STaR approach"
  (B-feedback-kinds.md, STaR entry) [shown in that file].
- Fix [untested]: compute an exact per-problem chance floor from the registry (number of literals, ADD/SUB, ordered
  pairs) and from the measured readout distribution; report chance-corrected measures; use expected pass@1 under the
  sampler (per-sample correct rate) and pass@k only at k small enough that the uniform floor stays below about 30%;
  make the program space larger than the sample budget (distractor literals: with four literals the uniform per-sample
  floor is 1/12 for ADD and 1/24 for SUB). Use the old "lucky-unsupported" count as an empirical guessing-rate estimate.

**D6. C1 (train on wrong candidates) is not a placebo; it is harm training that deepens the shelf.**
- Old claim: "C1 placebo, wrong | same problems, same count, rejected candidates (wrong or invalid trace) instead of
  accepted | is it just practice on own text?" (OLD l.173).
- Evidence [shown]: under V1, rejected candidates on right-call problems are right call + wrong number, and F1 shows wrong
  numbers come from the shelf (113 of 113). v6 p.174: "Preserve failed attempts as diagnostics ... but do not relabel them
  as successful experiences"; v6 p.184: "Do not ... distill known mistakes". In the blurt-2p placebo the wrong guesses were
  rule-keeping expressions of a free-text LM and gave +1.5 over S0 (VERIFY-blurt2p.md), a different mechanism.
- Consequence [suggested]: C1 trains final-answer CE toward wrong shelf numbers, so B > C1 is near certain and says
  nothing about "practice on own text". It also makes the proved-wrong clause "mean B <= mean C1" (OLD l.208) close to
  vacuous.
- Fix [untested]: drop C1 from the marks (keep at most as a labelled harm probe outside the verdict). The fair
  "spurious reward" analogue here is G-rand: same label source, random selection. Keep C2 as the plain-practice control.

**D7. No positive control, so a null result for B would be uninterpretable.**
- Old claim: D is "optional" and "compared, not marked" (OLD l.175, l.213); no arm checks that the recipe can turn new
  labelled problems into FRESH gains at all.
- Evidence [shown]: TEACHING_TO_TEST_CONTRACT.md section 4: "A negative result on any research test is uninterpretable
  until the controls below pass." The 8-vs-32 coverage test added TRAIN examples and scored fresh 1/16 and 1/16 versus
  controls 1/16 and 0/16, 0/8 pairs everywhere (v6 p.42, p.229). Generalization is unproved (CURRENT.json
  `generalization_proved: false`).
- Fix [untested]: add **G-all** (oracle labels on all practice misses, same update budget) as a required positive
  control with its own mark on FRESH call-level accuracy. If G-all does not beat A, the creative run is reported
  "uninformative", not "proved wrong".

**D8. Arm E (in-context experiences) is not feasible with today's pipeline.**
- Old claim: "add arm E (accepted experiences supplied as in-context examples at inference, no weight change) as a cheap
  extra control" (OLD l.311-312).
- Evidence [shown]: the calculator forward builds the notebook as exactly 8 reserved tool positions,
  `memo=inputquery.new_zeros((1,8,256))` with `notebook_mask=torch.ones((1,8))` (runtime l.102, l.108); literal references
  must lie inside the query (runtime l.100: "literal reference must belong to original query tokens"); fresh generation
  "receives question-only inputs" (v6 p.414). The "example" role id exists only in the untested PR #23 Workspace proposal
  (pr23-design.md section 6, "v1, untested"). `interface_changes_authorized: false` (CURRENT.json
  `separate_approved_curriculum`). v6 p.90: "Merely placing examples in a prompt does not demonstrate that the model
  learned to use them"; it asks for an episodically trained context-only worker.
- Fix [suggested]: remove E from this run. Say plainly that the persistent update departs from v6's context-first order
  (v6 p.16, p.51) as a judgment call, because context reuse needs an interface change plus episodic training. Store
  experiences in a form that can later be rendered as Workspace example tokens (row = example index), so context reuse
  can be tested as its own later change.

**D9. The diversity adjustment and the per-problem cap are meaningless here; the primary luck mark is left undefined.**
- Old claims: diversity adjustment "a problem's hits count only up to its number of distinct accepted call sequences"
  (OLD l.192-194); cap of 2 "whose call sequences differ most" (OLD l.146); section 11.3 then says the adjustment breaks,
  proposes 2-call FRESH "if the generator supports it, otherwise say luck measures coverage only", and keeps "L1-L3 ... as
  written" (OLD l.303-306).
- Evidence [shown]: argmax calls (runtime l.119, l.122); one correct call per problem with ADD order treated as
  equivalent (CURRENT.json). v6 p.162 on artificial diversity.
- Consequence [suggested]: under V1 every accepted candidate of a problem is identical, so the adjustment turns L into
  coverage, the cap is just dedup to 1, and "variety collapse" cannot be seen through distinct traces. A pass mark whose
  definition depends on a later "if" is not pre-registered.
- Fix [untested]: replace with coverage, per-sample correct rate, entropy of the call distribution and of the
  final-number distribution, and the number of distinct wrong final values (to see collapse onto the shelf). Fix the
  definition before hash-pinning.

**D10. The checker does not implement v6's three states, and its arithmetic checks are vacuous here.**
- Old claims: four acceptance rules including re-executing each expression with an independent evaluator, "No invented
  numbers" with a constants list (1, 2, 10, 100, 60, 1000), units stripped, rounding rule (OLD l.100-112); 11.2 adds
  "three states" but defines only that unresolved rows are not trained on (OLD l.300-302).
- Evidence [shown]: the host executes exact integer arithmetic (tools l.165 onward); operands can only be registry
  references to question literals or earlier OK results (tools `_validate_registry`; runtime l.100); there are no
  constants; the domain is integer ADD/SUB with single-token results (runtime `_numeric_value`, UNSUPPORTED_NUMERIC_TOKEN
  at runtime l.131). v6 p.165-167: arithmetic validity is not interpretation (Mira 18-7 vs 18+7); "Accepted ... Rejected
  ... Unresolved means the available check cannot establish correctness."
- Consequence [suggested]: rules 3 and 4 can never fail for an OK call, so they check the one thing that cannot be wrong.
  Interpretation is decided only by the gold oracle. With a full oracle nothing is ever "unresolved", so the three states
  are a label without content.
- Fix [untested]: define the states concretely: **accepted (oracle)** = call matches oracle canonical form and final
  equals the call result; **unresolved (arithmetic only)** = an OK call whose result equals the final answer but no
  oracle is consulted (what a key-free checker could certify); **rejected** = definite violation (ERROR call, final
  differs from every call result, or oracle mismatch). Report the Mira gap: the share of arithmetic-only-acceptable
  candidates that the oracle rejects. Drop the units, rounding and constants rules.

**D11. Parts of the FRESH set are infeasible or leaky.**
- Old claims: F4 = 64 problems from a family not in TRAIN, "for example a rates or unit family" (OLD l.186-188); a third
  of FRESH from 2-call composition (OLD l.305-306); near-duplicate guard "no TRAIN problem shares template and all numbers
  with any FRESH problem" (OLD l.149); Luna problems as a source (OLD l.130-131).
- Evidence [shown]: actions are NONE/ADD/SUB only (runtime l.16, tools l.138); results must be one canonical numeric token
  (runtime `_numeric_value`); the model has only ever made one call at loop 0 (CURRENT.json l.322) and v6 p.80 says the
  curriculum "establishes neither multi-step composition ..."; v6 p.42: "Reserved numerical-pair exclusion coverage
  remains unknown" and the terminal panel needed a parent eligibility certificate (v6 p.413-416). The 16 Luna questions
  are the now-consumed terminal panel (CURRENT.json `current_science`, 128 outputs, recount PASSED).
- Consequence [suggested]: a rates family needs multiplication or division the tool does not have. 2-call FRESH items sit
  at floor for every arm and cannot separate them. The guard lets the same arithmetic fact (same operation and operand pair)
  through under a new template, which carries the answer value straight across splits. Without the parent's eligibility
  process, FRESH cannot be shown free of reserved pairs, and we may not open reserved panels to check.
- Fix [untested]: keep F4 inside ADD/SUB single-call (for example a new wording family or distractor-literal problems);
  no 2-call items until a recipe trains composition; exclude by (operation, ordered operand pair) and by the existing
  operand-pair exclusion lists; route FRESH through the parent's scoped eligibility review as the terminal panel was.

**D12. Practice pool, parent checkpoint and their interaction with other approved work are undefined.**
- Old claims: "TRAIN problem", "TRAIN-side DEV slice" without a source or size; "Same parent checkpoint" without naming it
  (OLD l.75, l.89, l.155).
- Evidence [shown]: six of eight terminal branches are 32/32 on TRAIN32 (v6 p.10), so TRAIN32 yields almost no misses.
  `checkpoint_selection_authorized: false` (CURRENT.json `current_science`); v6 p.413: "Select no winner or earlier
  checkpoint". The 512-pair curriculum is approved but not admitted (`TRAIN_launch_authorized: false`) and has its own
  two-arm experiment.
- Fix [untested]: name the practice pool, its size and author, keep it disjoint from the curriculum banks (or wait for
  the curriculum result and re-baseline), and either run all eight terminal parents (cheap at about 0.41 s per update,
  FACTS) or pre-register one parent by a rule that uses no consumed-panel score, stating it as a judgment call.

**D13. Feasibility leans on the unreceipted "40 calls, 2 of 6 rescued" sentence.**
- Old claim: "This is the baseline evidence for generation: it shows sampling can rescue some failures" (OLD l.313-315).
- Evidence [shown]: the only source is a sentence in v6 p.48 and p.152; a repo search finds the figure only in the old
  design itself (`design/next-parts/creative-prototype.md`, identical to the OLD file) and an unrelated "40 calls of 6"
  dialog script (`scripts/claude_rd378g_teacher.py` l.9); FACTS says the execution owner has no record. Its mechanism is
  also unexplained: with argmax calls, "varied complete candidates" could not have varied the calls through temperature.
- Consequence [suggested]: nothing numeric in the old plan is derived from it, but the cold-start question (v6 p.157-158:
  "If no explorer proposal ever passes a sound checker, there is no positive discovery signal") is unanswered, and the
  inconclusive line "fewer than 40 TRAIN misses won" (OLD l.210) has no basis.
- Fix [untested]: do not cite it as evidence. Run a pre-registered DEV probe on TRAIN-side practice problems first
  (rescue rate, per-sample call accuracy, lucky-unsupported rate, Mira gap) and set k, temperature and the inconclusive
  lines from it before FRESH is written.

**D14. Retention after context reset and intervening learning is missing.**
- Old claim: one no-harm check on "a regression panel the current pipeline already uses" (OLD l.198, l.206).
- Evidence [shown]: v6 p.187: "Test a saved skill after context reset and intervening learning"; v6 p.51: "Each
  persistent update needs its own evidence of transfer and retention"; TEACHING_TO_TEST_CONTRACT.md "Benefit and damage,
  reported separately" (signed paired change on earlier items).
- Fix [untested]: report signed paired change on TRAIN32 (retention) and re-score FRESH-type DEV items after one
  intervening, unrelated update (for example a matched C2-style block), as v6 asks.

**D15. More than one change is bundled.**
- Old design adds at once: a new sampling runtime, a new practice-data pool, a recipe change (D4), new FRESH families
  including 2-call and F4, and (11.4) an in-context arm [shown, OLD sections 2, 4c, 6a, 11].
- Fix [suggested]: the single change under test is "train on accepted own candidates" versus controls; everything else
  (sampler, practice pool, FRESH, recipe) must be fixed and shared by all arms and validated beforehand on DEV.

### Minor

- **m1.** V5 "dropout left on at inference ... only if dropout exists" (OLD l.86): the reader is LayerNorm, Linear,
  GELU, Linear with no dropout (`scripts/sol_translator_grounding_v6.py` l.42-49), and no dropout appears in
  `claude_fewex_net.py`, `sol_spatial_attention_core.py` or `sol_spatial_poc_ordered_v2.py` [shown for the repo copies;
  the PC pipeline is untested]. Drop V5.
- **m2.** "extra depth is forbidden" (OLD l.87) contradicts the header note that Ben's 12:09 message allows extra loops
  (OLD l.12-15) [shown]. Reword: out of the first run to keep one change.
- **m3.** Checker rule 1 (units stripped, exact rationals, "to the nearest" rounding) does not apply to integer ADD/SUB
  single-token answers [shown, runtime `_numeric_value`]. Replace with exact integer-token match.
- **m4.** Statistics. Two seeds versus the contract's five with a 4-of-5 rule (TEACHING_TO_TEST_CONTRACT.md section 4,
  "Thresholds, uncertainty, stopping") [shown]; seeds are cheap here. Ratio marks on pooled sample counts instead of signed
  paired per-problem differences with a cluster bootstrap, as the contract asks for stochastic scoring ("Clipping"
  paragraph) [shown]. With 2 versus 2 seeds, "each B seed beats each C seed" passes by chance 1 time in 6 under a null
  [suggested, 2!2!/4!]. Use common sampling seeds per problem across arms [suggested].
- **m5.** The power note (OLD l.215-220) computes the two-arm SE as if arms were independent; arms are paired on the same
  problems, so the true SE depends on discordant pairs [suggested]. "a real +6 point gain can still miss G1" understates
  it: +6 points is 11.5 problems, below the +13 bar, so it misses more often than not (about 59% under the stated SE)
  [suggested].
- **m6.** The template-nearest shortcut (OLD l.227-229) computes the final answer exactly from the looked-up call, so it
  has no readout defect; on new instances of TRAIN templates its final accuracy could be far above A's 12%, making "B's
  G1 gain must exceed that predictor's gain over A" nearly unreachable [suggested]. Score the shortcut at call level, and
  add an answer-shelf baseline and the magnitude shortcut v6 p.65 names [shown that v6 names it].
- **m7.** The no-harm "regression panel the current pipeline already uses" is unnamed (OLD l.198); every such panel is
  consumed, and reuse of consumed evaluation needs Ben's OK (FACTS) [shown]. Use TRAIN32 retention instead.
- **m8.** Pass marks were "adopted" at 12:14 (OLD l.273) while 11.3 already says the luck definition breaks [shown].
  Nothing has run, so rewriting them before the hash pin is allowed; say so in the record.
- **m9.** The experience record (OLD l.136-141) lacks the acceptance state, the claim each check established
  (oracle interpretation versus arithmetic only), evidence versions and the parent version that v6 p.56 and p.180 ask for
  [shown]. The sleep-thread key compatibility is untested: old wins.jsonl rows have keys answer, checked_by, problem,
  rows_used, source, steps, tries, turn_id with free-text steps such as "(4 * 8 + 7)" (artifacts/claude-blurt2-20260925/
  cpu-3/wins/wins.jsonl, 151 rows) [shown]; typed calls do not fit "steps" without a converter.
- **m10.** v6 p.161 asks explorer comparisons to count "newly solved problems, duplicate attempts, unresolved checks and
  latency" [shown]; the old measures omit duplicates, unresolved and latency.
- **m11.** The "Seeds split" branch (OLD l.243) does not require a new FRESH set for the replication; re-evaluating the
  same FRESH after seeing results breaks "touched once" [suggested]. The DEV slice used for temperature choice should be
  disjoint from rows that become training data [suggested].
- **m12.** Fact-pack notes: FACTS lists the 16-question Luna terminal panel as "pending", but CURRENT.json shows it scored
  and consumed (128 outputs, `independent_recount_status: PASSED`) [shown]. CURRENT.json (11:44 UTC) still has
  `new_Premonition_GPU_dispatch_allowed: false`, while FACTS says the GPU is now Premonition's full time [shown]; check
  before dispatch.

## 3. Answers to the eleven questions

1. **Can LM temperature produce varied complete candidates?** No. Calls are argmax per loop before the LM speaks
   (runtime l.119, l.122), so temperature only re-rolls the final number token(s) [shown for the code; consequence
   suggested]. See D1.
2. **Are B's accepted traces different from gold? What does B vs D measure?** Not different: one correct call, then NONE,
   then the gold number, equal to the gold row up to ADD order [suggested from shown recipe and tool equivalence]. B vs D
   measures seed noise; the only real difference from answer-key training is which problems get labels, which B vs D
   cannot see because D copies B's problem set. See D2.
3. **What does sampling-based rescue select given F1?** Mostly right-call problems whose gold number is on the 27-value
   shelf, plus rare off-shelf lucky draws [suggested]. Confound: a FRESH gain could be vocabulary widening (target
   exposure) or sharpening on familiar values, not method learning. See D3.
4. **Chance floors.** [suggested, computed as 1-(1-p)^k; the uniform policies are reference points, not measured
   distributions; "two literals per problem" is inferred from the Mira example and the matched ADD/SUB pairs and is
   untested for every family, so count literals per problem from the registry before fixing marks]

   | Random policy | p per sample | pass@1 | pass@4 | pass@16 | pass@32 |
   |---|---|---|---|---|---|
   | Final number uniform over ~90 two-digit values, call fixed (V1 world) | 1/90 | 1.1% | 4.4% | 16.4% | 30.1% |
   | Final number uniform over the 27-value shelf, answer on shelf | 1/27 | 3.7% | 14.0% | 45.3% | 70.1% |
   | Same, answer off shelf | 0 | 0% | 0% | 0% | 0% |
   | Call uniform over 4 valid binary calls, 2 literals, ADD | 1/2 | 50% | 93.8% | ~100% | ~100% |
   | Same, SUB | 1/4 | 25% | 68.4% | 99.0% | ~100% |
   | Call uniform over 9 head combinations (NONE/ADD/SUB x 4 pointer pairs), ADD | 2/9 | 22.2% | 63.4% | 98.2% | ~100% |
   | Same, SUB | 1/9 | 11.1% | 37.6% | 84.8% | 97.7% |
   | 4 literals (one or two distractors), valid binary calls, ADD | 1/12 | 8.3% | 29.4% | 75.1% | 93.8% |
   | Same, SUB | 1/24 | 4.2% | 15.7% | 49.4% | 74.4% |

   The old marks do not account for any of this: the inconclusive line (A under 10 of 192 covered) is below the
   uniform-number floor at k = 32 (about 58 of 192), and nothing is chance-corrected. See D5.
5. **Are the controls right?** A (plain sampling, no training) is right [suggested]. C2 (practice on known items) is a
   fair no-new-information control [suggested]. C1 is harm training, not a placebo, and conflicts with v6 p.174 and
   p.184 (D6). D duplicates B (D2). Missing: a positive control G-all (D7), a selection null G-rand (D2), and a
   vocabulary-matched control or answer-value stratification (D3).
6. **Is arm E feasible?** No, not without an interface change and episodic training (runtime l.100, l.102, l.108;
   CURRENT.json `interface_changes_authorized: false`; v6 p.90) [shown]. See D8.
7. **Is the diversity adjustment meaningful?** No. Under V1 every accepted candidate of a problem is the same call
   sequence; even with call sampling there is one correct program per problem (ADD order equivalent) [suggested]. See D9.
8. **Does the checker match v6's three states and the Mira problem?** No. Two working states; "unresolved" is never
   defined; the arithmetic checks cannot fail on an OK call; interpretation is settled only by the gold oracle, and the
   Mira gap is not measured [shown for code and v6 text; consequence suggested]. See D10.
9. **Are the pass-mark numbers and power statements right?** The arithmetic is right as written: SE of one arm about
   2.3 points or 4.5 of 192 at 11.7%, two-arm difference about 6.3 problems (the old 6.4 rounds 4.5 x 1.414), 192 x 32 =
   6,144, blurt figures match VERIFY-blurt2/2p/3/3r [shown]. The problems are in the design of the marks: paired arms
   treated as independent, the 1-in-6 null pass of the seed rule, unstable ratio marks, L3 implied by L1, a shortcut bar
   that cannot be met, and no chance correction (D5, m4, m5, m6) [suggested].
10. **Does anything rest on the unverified "40 calls, 2 of 6"?** Yes, the feasibility premise and section 11.5's
    "baseline evidence for generation"; no number is derived from it, but the cold-start risk is unaddressed (D13).
11. **TEACHING_TO_TEST_CONTRACT.md violations** [shown for the contract text; the mapping to this design is suggested,
    as the contract was written for a different memory design]: no positive controls before a negative result can be
    read (section 4) (D7); stochastic scoring scored by ratios instead of signed paired differences, and fewer seeds than
    the 5-seed, 4-of-5 rule (m4); "nothing taught contains an answer to a scored query" is not enforced at the level of
    arithmetic facts or answer values (D3, D11); the shortcut baseline is mis-specified (m6); benefit and damage are not
    reported as signed paired changes on earlier items (D14). Kept correctly: touched-once evaluation, choices made on
    DEV not FRESH, a shortcut baseline in principle, and benefit/damage reported separately in principle.

## 4. A valid first version (sketch only; every line untested)

Question, one change: does training on the worker's own sampled, oracle-accepted call programs improve its fresh,
worker-only call choice more than plain practice (C2) and more than no training (A)? Secondary: is search selection worth
more than random answer-key labels (G-rand)?

- Variation: call-head sampling at a fixed temperature (D1 fix), final answer greedy. Clean restart per candidate.
- Problems: ADD/SUB single-call word problems with one or two distractor literals, so the program space (24 programs at
  four literals) exceeds the sample budget and the uniform floor stays low. A DEV probe first checks the parent is not at
  zero on these (cold start, v6 p.157-158).
- Checker: three concrete states (D10); Mira gap reported.
- Arms (same parent or all eight parents, at least 3 seeds, matched updates, calculator recipe copied exactly): A, C2,
  B, G-rand (same label count as B, matched off-shelf share), G-all (positive control).
- Primary measure: FRESH per-sample correct-program rate under the same sampler, chance-corrected per problem, paired by
  problem with a cluster bootstrap. Secondary: greedy program accuracy, coverage at small k, final-answer accuracy
  stratified S1/S2/S3, pair completion, lucky-unsupported rate, Mira gap, retention on TRAIN32, duplicates, latency.
- Marks shape (numbers set from DEV before FRESH is written): positive control G-all beats A, else "uninformative";
  PASS needs B - A and B - C2 above fixed margins with the bootstrap interval above zero in at least 3 of 3 (or 4 of 5)
  seeds; G-rand is reported, not required.
- Proved wrong: B <= C2 on the primary measure with G-all passing. That would mean verified own experiences add nothing
  over plain practice here.
- Claim ceiling if it passes: "learning from search-selected, key-checked labels improves fresh call choice". Not
  answer-hidden verification, not learned creativity in the v6 sense. A later rung can test an answer-hidden family whose
  goal predicate is checkable by substitution ("which number added to 18 gives 25?"), as OLD 3b already suggests.

## 5. What the old design gets right (keep)

- Honest framing: "Sampling alone is not learned creativity" (OLD l.77-78) and "Gold scoring is not unknown-live
  verification" (OLD l.114-118) [shown in the OLD file; consistent with v6 p.175].
- FRESH written after TRAIN is frozen, by a separate author, double-checked, hash-pinned, touched once per arm; temperature
  and k chosen on DEV, never on FRESH (OLD l.120-131, l.182-184, l.226) [shown].
- Consumed panels block-listed; reserved and blind panels never opened; split by semantic instance (OLD l.127-129,
  l.320-322) [shown].
- Pass marks fixed before running, with proved-wrong and inconclusive clauses and verdict words (OLD l.200-213) [shown].
- Both luck and first try measured; pair completion; the "71" correct-call-wrong-final count as a secondary; lucky
  answers without valid support counted as wrong and reported (OLD l.110-112, l.196-198) [shown].
- Template-nearest shortcut predictor in principle (OLD l.227) [shown]; needs re-specification (m6).
- One round only; second round is a separate step (OLD l.159) [shown].
- Positive targets are typed calls plus final answer, never free-text rationale (OLD l.318-319) [shown; matches v6 p.174].
- Checker test set of known-wrong traces before the hash pin (OLD l.248-249) [shown].
- Old-model evidence correctly labelled as a hint from a different model, numbers matching VERIFY-blurt2, -2p, -3, -3r
  [shown]. The lesson that practising only known answers collapsed variety is worth keeping as a reason for C2.
- Failure-branch table with one next change per outcome (OLD l.232-245) [shown]; update rows that depend on D, C1 or V1.
- $0 on Ben's PC; learned stopping, compressed notes and n-grams out of scope (OLD l.177, l.270) [shown].
