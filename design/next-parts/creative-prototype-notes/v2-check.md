# Independent check of creative prototype design v2 (2026-10-03)

Diagnosis only. No repo file was edited. Nothing was trained, tested or run on a GPU, and no money was spent.
GOLD-PRIVATE-v1.json, eval panel files and reserved or blind panels were not opened. On the branch
`claude/critical-thinking-data-128-outputs` I read only `README.md` and `pipeline_code/audit_fresh_core_comparison.py`.
I ran three small CPU scripts in my scratchpad, listed in section 9.

Labels: **shown** = read in a named file or line. **computed** = output of my own script. **suggested** = my
reasoning. **untested** = a guess nobody has measured.

Sources: **v2** = `design/next-parts/creative-prototype.md`. **v6** = `integrated-design-v6-text.txt`, "l.N" = line N.
**C.json** = the CURRENT.json copy. **runtime**, **tools**, **eval** = the three pipeline_code files of those names.
**audit** = `audit_fresh_core_comparison.py` on the branch above. **maths** = `math-report.md` and its JSON files.
**PR23** = `pr23-design.md` and `pr23-f1-report.md`.

## 0. Summary for Ben

The plan gets the big things right. It adds randomness to the calculator choices (the only place it can change the
solution). It uses puzzles whose checker needs no answer key. It has a no-training baseline, a look-alike placebo and a
positive control, with pass marks fixed before anything runs. Most numbers I checked match their sources.

Five things must be fixed before the pass marks are sealed:

1. **The model could pass without ever looking at the target number.** Learning only the puzzle's rules (use every
   number once, feed the first answer into the second step, never use the target, then stop) and then picking plus or
   minus at random already solves about 1 try in 7. "Always add all three numbers" solves 26% of the puzzles on the
   first try. The placebo never learns those rules, so the test would credit "it learned to aim at the target" for
   what may only be "it learned the rules". Fix: test twin puzzles that share the numbers but have different targets.
2. **Training on a saved two-step solution needs code that does not exist.** Today's training always runs the model's
   own calculator choices, not saved ones. A replay mode must be built, tested and flagged.
3. **The rule for a correct answer is written two different ways.** One version allows wasted or broken steps before
   the answer and the other does not, and the chance floors used the looser one.
4. **The "the skill lasts" test is too weak.** The in-between training is more practice on 32 questions the model
   already answers perfectly and practises in every training step anyway, so it barely changes the model.
5. **Some outcomes have no verdict, and "proved wrong" is too trigger-happy.** It would fire about 1 time in 7 even if
   the idea really helps a little (+5 points).

Also: the GPU time is probably 2.5 to 3.5 hours, not 1 to 2. Each training step in the plan does 10 examples, and the
measured 0.41 seconds was for 1.

## 1. Must-fix list

| # | Issue | Where | Fix (short) |
|---|---|---|---|
| M1 | A policy that ignores the target can pass L1, L2, S1 and the readable gate | v2 sections 4, 8, 9 | Twin-target goal-use mark, format-valid reporting, balanced sign patterns, narrower claim words |
| M2 | Training on stored multi-call trajectories has no code path. The current recipe executes predicted calls (v6 l.80) | v2 section 7 | Specify forced replay of stored calls in every trained arm, add a regression test, flag it (new F7) |
| M3 | STRICT and the trajectory "shape" are defined inconsistently. The floors used a looser STRICT | v2 sections 5, 6, 8 | Write one definition. Define the training form, R's shape and PC's loop placement from it |
| M4 | S2 "persistent" uses an intervening block that barely changes the model, and applies it to W only | v2 sections 9, 10 | A real intervening block that moves the weights, applied identically to W, R and N |
| M5 | The outcome rules have gaps, overlaps and a weak "proved wrong" | v2 section 9 | An ordered decision list with a "not shown" verdict and a proved-wrong rule based on an upper bound |

Details and evidence follow.

## 2. Factual claims and numbers

Every claim I could trace. "OK" means it matches the cited source.

| v2 claim | Source check | Verdict |
|---|---|---|
| Action head `Linear(256,3)` over the mean of h+e at question positions; two bilinear pointer heads; argmax; four loops; result into a reserved value/status slot; then advance (section 2) | runtime l.27-29, 47-62, 117-150 | OK (shown) |
| "frozen LM decodes the final answer from 8 prefix vectors and BOS (shown, code)" | Not in runtime, tools or eval. PR23 section 2 says the 8-vector pool is v6-code behaviour and "Still open: does the panel pipeline export through v6's 8-vector pool?" | **Minor mismatch.** Label it "suggested (v6 code, PR23)" |
| "Producing it touches the LM only through the embedding of each result token" | runtime l.64-77 is right for result tokens. Question features also come from the LM (cached static embeddings or contextual states, eval l.414-418) | Minor. True for a cached static parent. Say so |
| Tool limits: two distinct refs, at most 8 literals, at most 3 prior results, at most 4 calls, one canonical numeric token | tools l.10-13, 165; runtime l.67-71, 94 | OK |
| Every integer 0..999 is one LFM2.5 token, no negative is | maths A1 (computed from the public tokenizer) | OK as cited |
| "Trainable modules: core, reader, prefix, tool. Loss: final-answer CE plus averaged call CE ... (shown, code and v6 l.80)" | eval l.42 (components). audit l.325-329: total = numeric CE + action CE + pointer CE. "Averaged" and "until it succeeds, then NONE" are v6 l.80 only | OK, labels slightly generous |
| "Calls fired at loop 0 in 127 of 128 consumed-panel outputs (shown, PR23 section 2)" | PR23 section 2 says "Every panel call fired at loop 0". C.json `current_science.observational_complete_program_recount.all_active_calls_loop0_no_later_superseding_calls: true`. The branch README lists "1 omitted call" | **Minor.** The number is right, but it comes from C.json plus the README, not from PR23. Fix the citation |
| C.json: curriculum `TRAIN_launch_authorized: false`, `new_worked_example_supervision_authorized: false`; `checkpoint_selection_authorized: false` for the terminal panel | C.json `separate_approved_curriculum` and `current_science` | OK |
| v6 creativity bullets (plain sampling baseline, later improvement, replay not evidence, clean restarts, rejected guesses not context, cold start, checks match claim, goal predicates, context then adapter then replay) | v6 l.151-152, 155, 158, 161, 163-168, 51, 235 | OK |
| "v6 says 'two-digit' results" | v6 l.77 | OK |
| Word problems: 9 head combinations, 4 duplicate errors, 4 valid calls, 3 distinct values; "1 time in 6"; pass@8 76.7%; pass@32 99.7% | maths Part 2 | OK, but the paragraph mixes two random policies. The 9-combination count assumes independent pointer heads, and "1 in 6" assumes distinct pairs. Under independent heads (what sampling the real heads gives) it is 1 in 12, pass@8 50%, pass@32 94%. The conclusion (luck saturates) holds. **Minor** |
| "a random policy hits 0.54% per try on 3-number puzzles" | maths tier P 0.544% | OK |
| Looser rule at 4 numbers: 0.016% to 0.60% | maths 1b (k = 4, 2..60: 0.0160% vs 0.604%) | OK |
| Tier table (3,283 / 33,670 / 2,318,380; 6.51 / 0.544 / 0.0161%; pass@8 37.1 / 4.24 / 0.128%; pass@32 75.0 / 15.6 / 0.513%) | maths 1d and part1_tiers.out | OK. My own independent enumeration also gets 33,670 P puzzles (computed) |
| "floors fall 3 to 20% at 3 or 4 numbers" if results up to 999 are accepted | maths 1b | OK |
| "97 to 100% of puzzles have exactly one sign pattern" | maths 1a (97.1% to 100%); tier P 98.98% | OK |
| Power: "false-pass 1.9%, real 15-point gain 85% at seed spread 5 (3 seeds, every W seed beats the control mean)" | part3_rules.json `sd5 S3 n256 R2 M10` = [0.0186, 0.848] | Number OK. But it comes from the **greedy binomial** simulation with **3 control seeds**, not the "normal model checked by simulation" (that check was for pass@8 with 2 seeds and the other clause). It covers one comparison, not the joint PASS. **Minor label; see M5 and section 5** |
| "A real 10-point gain passes only about half the time" | Computed only for 2-seed rules (47 to 50%). For 3 seeds, pass@8 and the older clause it is about 41% (part3_power.json). Not computed for the v2 clause | Minor. Roughly right |
| Warning rule "R's seeds spread by more than 16 points" | maths 3d derived 16 for **two** control seeds | **Should-fix** (section 5) |
| "constant LR 1e-4 (the terminal low-LR value)" | eval l.33 (`low_lr` 0.0001) | OK |
| Parent seed-0/static low-LR is 32/32 TRAIN at all three checks | v6 l.374-376 | OK for finals. Calls at 5120 are not stated in v6 (v6 l.289 gives 32/32 calls at 4096). Minor: cite the recount |
| "the measured 0.41 s per update" and "9 runs x 512 updates x about 0.45 s" | C.json `partial_benchmark.mean_complete_control_update_seconds` 0.413. audit l.364, 387: one teacher-forced example per optimizer update. C.json timing: four-loop core 0.028 s, LM teacher forcing 0.015 s, optimizer about 0.11 s per step, the rest guards and fsync | **Should-fix.** 0.41 s is for a 1-example update, and v2's updates hold 10 examples (section 4) |
| "Copy the calculator recipe" | The recipe is 1 example per update and executes predicted calls (audit, v6 l.80). v2 uses 10 rows per update and must replay stored calls | **Must-fix M2** plus a should-fix flag |
| Section 1 row 3, row 4, row 6, row 10 | PR23 F1 table; maths Part 2; runtime l.102-108; FACTS | OK |
| Example puzzle "Use 14, 9 and 30 ... to make 35": 14+30=44, 44-9=35 | Valid tier-P puzzle: no pair makes 35, target not a given number | OK (computed) |
| Section 12 Workspace mapping (question role 0, tool result role 3 with arrival time, example role 2, row = example index) | PR23 section 6, l.117-122 | OK |
| Kept from v1: "fresh sets ... by a separate author" | v2 S0 makes every split with one generator | Minor inconsistency. Say which one holds |

## 3. Validity of the experiment

### M1 (must-fix). A target-blind policy can pass

**What I found (computed, `v2check/blind.py`).** On tier P (my enumeration reproduces the 33,670 puzzles):
- A policy that has learned only the **format** (each given number used once, the first result fed into the second
  call, target literal never used, then NONE) and picks the operation and order at random hits **14.4% per try**,
  **pass@8 66.9%**, **pass@32 97.5%**. That is about 26 times the uniform floor of 0.544%.
- The same, but also avoiding negative or out-of-range intermediates: **25.7% per try, pass@8 85.4%**.
- Sign patterns over (smallest, middle, largest) in tier P: all plus 26.4%, (-,+,+) 25.6%, (+,-,+) 24.1%, (+,+,-)
  13.0%, (-,-,+) 10.9%. So the fixed argmax policy **"ADD the first two literals, then ADD the third"** never reads
  the target and **solves 26.4% of P puzzles at the first try**. It does not even need to compare sizes.

**Why this breaks the design (suggested).**
- R is matched only on the number of OK calls. It is not matched on the format, so it does not learn the format. W
  learns the format from every accepted row. So W minus R of 10 points or more (L2) can come from format alone, and
  L2's label "the checker caused it" would be read as goal-directed search, which section 0 item 8 and section 4
  imply.
- L1 (W minus N of 10 or more) and S1 (first try plus 10) pass the same way. The readable gate (PC beats N by 10)
  passes trivially, because PC also learns the format. A failed goal-use would then still be called "readable".
- The fresh-design report had both a rule-keeping placebo and a "value hit rate among rule-valid candidates" report
  line. v2 dropped both.

**Fix (concrete).**
1. Make T1 twins: 128 number sets x 2 targets with **different sign patterns**, same template and same number order,
   only the target changed. 99.6% of P number sets have 2 or more valid targets (computed, `v2check/twins.py`), so this
   is easy.
2. Add a fixed mark **G4 goal use**: for each twin, own-target hit rate minus cross-target hit rate. The cross-target
   rate is the share of the twin prompt's samples that form a STRICT-valid tree (numbers mapped by value) reaching this
   puzzle's target. A target-blind policy scores 0 in expectation. Require GU(W) minus GU(R) of at least a fixed margin
   (for example 5 points), every W seed above the R mean, and a bootstrap over number sets that excludes 0. Without G4
   the claim is capped at "learned the puzzle's rules from checked experiences".
3. Report, for every arm, the format-valid rate and the hit rate among format-valid candidates next to the exact
   format-only floor for each puzzle.
4. Balance sign patterns in T1 and practice, so no fixed sign rule beats about 20%.
5. Put G4 in the readable gate too: PC must show goal use, not just format.
6. Optional, if a second placebo is wanted: R' = value-blind random picks among **format-valid** own samples (hits
   included at their natural rate), drawn from an enlarged sample pool (section 3, R availability).

### M2 (must-fix). There is no code path to train on a stored multi-call trajectory

- **Shown.** v6 l.80: "Training and evaluation execute predicted calls without gold-result injection. Initial checked
  supervision requests the correct calculation until it succeeds, then targets no call." `CalculatorPath.forward` always
  executes argmax calls (runtime l.119-124) and has no argument for forced actions. audit l.364 and l.387 count one
  teacher-forced example per update. In that recipe, teacher forcing is the final-answer tokens, not the calls.
- **Consequence (suggested).** W, R and PC rows are fixed two-call trajectories. If training executes the model's own
  loop-0 call and it differs from the stored one, the stored loop-1 target ("result:1 minus literal:1") refers to a
  result that was never made. W's rows are sampled at tau above 1, so argmax will usually differ. "Copy the calculator
  recipe" therefore cannot work as written. Relabelling on-policy with a solver would turn W into PC.
- **Fix.** Add flag **F7: forced replay of stored calls during training** (all trained arms equally), which departs from
  v6 l.80. Specify the per-loop targets (the stored action and pointer indices at every loop, NONE after the last OK
  call). Add an S1 regression: forced replay of a free-run argmax trajectory gives bit-identical logits and results.
  W0 (a) "force each possible first call" needs the same path, so build it once.

### M3 (must-fix). STRICT and "shape" are not one definition

- maths STRICT (common.py l.13-15 and `exact_random_strict`): NONE or ERROR may fill any other loops, before, between
  or after the tree. Only extra OK calls break it. All floors and STOP numbers use this.
- v2 section 5: "NONE fills the remaining loops". v2 section 6 rejects "an ERROR or out-of-range call in the tree", but
  an ERROR call produces no result, so it cannot be in a tree. Whether a leading NONE or ERROR loop, or an ERROR after
  the finish, is accepted is unclear.
- This decides what W trains on. An accepted row with an ERROR loop would teach the model to make an erroring call.
  It also decides what "same shape" means for R ("same number of OK calls, then NONE": at the same loops? are ERROR
  loops allowed?) and where PC's calls go.
- **Fix.** Write one rule. Suggested: acceptance = maths STRICT (keeps the floors valid). Training form = OK calls at
  loops 0 to k-2, then NONE. Drop accepted trajectories that are not in training form (do not edit them, because forced
  replay of an edited trajectory changes later states), and report how many were dropped. R's shape = OK calls at the
  same loop positions and no ERROR loops. PC = one solver trajectory per kept W row, in training form.

### R placebo: defined, always buildable, but it can collapse onto W (should-fix)

- It can be built for every puzzle W uses, because W's own accepted rows have the required shape. That is also the
  weakness. The parent was trained to call once and then choose NONE, so two-OK-call samples may be rare. If they are,
  R's pool is mostly W's own hits and R becomes nearly W (suggested). Under the uniform policy, a two-call-then-stop
  sample occurs roughly 1 time in 35, so a W puzzle's 33 samples hold about one hit plus about one other (suggested,
  rough).
- R is not "value-blind, so it avoids training on mistakes". At natural hit rates, 80 to 99% of R rows are rejected
  trajectories, which is "distilling known mistakes" (v6 l.184) in a control arm. That is acceptable for a
  never-promoted control, but v2 section 8 presents R as escaping the v1 flaw #5 conflict, and it does not.
- **Fix.** Draw R from an enlarged inference-only pool (for example up to 512 extra samples per W puzzle at the same
  tau, stopping once 10 shape-matched samples exist). Fix now: report R's accepted share and its overlap with W rows,
  and if more than 25% of R rows are accepted or identical to a W row, call L2 inconclusive. Say plainly that R trains
  mostly on rejected tries and is never promoted.

### Positive control (minor)

Well defined in purpose. Say which solver trajectory is used (for example uniform among the solver's solution
trajectories in training form), the per-puzzle count (equal to W's count for that puzzle) and the loop placement.

### Hidden second changes (should-fix)

Between W and R the only intended difference is which trajectories are used. I found no hidden difference beyond M1
(format), M3 (shape) and the overlap risk above. Relative to the existing recipe, three changes are shared by all
trained arms and are unflagged or misdescribed: forced replay (M2), **10 rows per update instead of 1** (audit), and a
full-weight update of all four parts (see section 6). Flag them.

### Leakage (should-fix)

- The split is by canonical form (sorted numbers plus target), so the same **number set** can be in practice and T1
  with a different target. In one random draw, 18 of 256 T1 puzzles shared a number set with practice (computed,
  `v2check/twins.py`). That is not an answer leak, but TEACHING_TO_TEST_CONTRACT.md l.99 says "Operands used in test
  queries never appear in any training query". The hindsight-relabelling branch (section 13) would also turn a practice
  miss on set S into "make t from S", which can be an exact T1 or T2 puzzle.
- **Fix.** Split by number set (the fresh design did this, and the 9,139 P sets are plenty). Seal **T1b** for the S7
  replication now (v2 says "a fresh T1" but lists no such split).
- DEV, practice, T1, T2 and X are otherwise disjoint as written. TRAIN32 is a different family. No consumed panel is
  touched. OK.

### Is STRICT checkable from the runtime trace? Yes (shown)

Each loop records `refs` and `resolved_references` as ids, `candidate_ids`, `status`, `error_code`, and for OK calls a
`result` with id `result:N` and `operand_references` (tools l.176-180, runtime l.124-126). Literal ids are `literal:k`
in text order (tools l.77). Two notes: the target literal's id must come from the generator's char span, never from
value matching; and on `UNSUPPORTED_NUMERIC_TOKEN` the runtime sets `result` to None but keeps `resolved_references`
(runtime l.130-131), so checkers must treat that loop as ERROR.

## 4. Feasibility on the real code

| Item | Finding | Severity |
|---|---|---|
| Sampling the heads | Easy patch at runtime l.119 and l.122. Use a private `torch.Generator`, because the eval runner fails if inference changes the global RNG (eval l.494-497). For common random numbers, pre-draw uniforms per (puzzle, sample, loop, head) and sample by inverse CDF, otherwise draws will not line up across arms | Minor |
| Trajectories without LM decode | Yes. `forward` returns the trace before any decode (runtime l.168-171). Result tokens need the LM embedding table and the reader | OK |
| Batch-1 runtime | `forward` refuses batch above 1 (runtime l.81-84). Sampling is sequential. C.json: four-loop core about 28 ms. S3 (about 34k forwards) at about 15 min and S5 (about 82k forwards) at 30 to 60 min look right | OK |
| Training cost | 0.41 s is one 1-example update including guards and fsync (C.json timing block; audit). Each v2 update has 8 puzzle rows (core only, cheap) plus 2 TRAIN32 rows (with LM teacher forcing), so likely 1.0 to 1.3 s (suggested). S4 is then about 75 to 100 min, not 35. S1 to S6 come to about 2.5 to 3.5 h, plus S7 | **Should-fix** (section 0 item 9, section 10) |
| Question cap and literal limit | eval l.127: at most 48 tokens plus EOS. A tier-T question has 5 literals (at most 8 allowed). S0b checks both. Name the 48 | Minor |
| Target literal in the registry | Yes. `build_registry` takes every integer literal (tools l.45-52). STRICT handles it | OK |
| Result range | S0b check is right. If 100..999 are accepted, tier-T intermediates above 99 become legal, and those token embeddings were never seen in training | OK |
| Final-answer CE weight 0 | Feasible: the logged loss is a sum of three terms (audit l.328). Puzzle rows can skip `read_latent`, prefix and LM entirely. Then the prefix gets gradient only from TRAIN32 rows | OK |
| Training 4 components | Matches eval l.42. See section 6 for the v6 rung issue | OK |
| Checker gate "agree on every enumerated trajectory of 500 random puzzles" | Under the tool limits a P puzzle has about 25 x 41 x 61 x 85, roughly 5 million, four-loop sequences, and a T puzzle about 24 million (fresh-design section 4 gives 41 x 61 x 85 x 113). 500 puzzles means billions of checks per checker in Python | **Should-fix.** Exhaustive on about 50 P puzzles with NONE/ERROR placements collapsed, plus 1 million random trajectories over 500 puzzles, plus every solver solution |
| Checker B "tests membership in the solver's solution set" | That shares the generator's solver, which contradicts "Neither shares code with the generator" | **Should-fix.** B builds its own enumerator from the rules text |
| Cold start | The parent was trained to choose NONE after a successful call. Tau of 1.0 to 2.0 may not overcome that, so two-call samples may be rare (suggested) | Minor. On DEV, measure P(second OK call) per tau before fixing the grid |
| S3 fallback | "else add 256 W-tier puzzles to practice once" does not say whether the DEV gate is re-run (DEV has no W-tier items) | **Should-fix** (see M5) |
| GPU hold | C.json `new_Premonition_GPU_dispatch_allowed: false`; v6 l.6 says dispatch is on hold. FACTS says the GPU is now Premonition's. v2 is silent (critic m12 not carried over) | Should-fix: state that GPU stages wait for the hold to be released |

## 5. Statistics

### M5 (must-fix). Outcome rules have gaps and overlaps

Computed with `v2check/noise.py` (per-seed SD 5 points plus puzzle noise, 3 vs 3 seeds, unpaired, so cautious):

| True W minus R | P(mean W at most mean R) = "proved wrong" | P(0 < W minus R < 10) = no verdict defined |
|---|---|---|
| 0 | 50% | 48% |
| +3 | 26% | 67% |
| +5 | 14% | 71% |
| +10 | 1.6% | 48% |
| +15 | 0.1% | 14% |

Problems:
- "Proved wrong" (mean W at most mean R) fires 14% of the time when the idea really adds 5 points. That is a
  falsifier with a high false-alarm rate.
- W minus R between 0 and 10 has no verdict. That is the most likely outcome under a small real effect. Section 9 says
  small gains "read as not shown", but no row says so.
- Other gaps: L1 fails but L2 passes; G2 fails; G3 fails; W below N while R is below W. No verdict for any of them.
- Overlaps: "Inconclusive (fewer than 100 accepted practice puzzles)" and "Proved wrong" can both be true. No order is
  given.
- Remedy mismatch: Inconclusive says "then one more seed per arm", but more seeds cannot fix too little practice data.
- Gate mismatch: the S2 cold-start gate is 5% of DEV puzzles, while inconclusive is 100 of 1,024 (9.8%). A DEV rate of
  5 to 9.8% passes S2 and then fails by construction.
- Loophole: if the W-tier fallback runs, 256 easy 2-number puzzles (random pass@32 75%) alone can meet the 100-puzzle
  count while P-tier hits stay near zero.
- The readable gate blocks a W pass: if PC fails, v2 stops even when W passes. On-policy rows can be easier to fit than
  solver orderings, so this can happen.
- "the seed rule below splits" is undefined.
- One extra seed after a split is a second look at the data. Say how it is scored.

**Fix: one ordered decision list, sealed in PASSMARKS.**
1. Invalid run: stop, report, no verdict.
2. Fewer than 100 **P-tier** practice puzzles with an accepted candidate: "no data, stop" (no extra seeds). Align S2 to
   at least 10% of DEV (13 of 128) and do not count W-tier puzzles.
3. R overlap above 25% (section 3): L2 inconclusive.
4. PASS (with G4 from M1).
5. Otherwise, if PC fails the readable mark: "unreadable", outside-opinion prompt.
6. "Proved wrong" only if the upper end of the seed-aware 95% interval of W minus R is below +5 points.
7. Everything else: "not shown", with the effect and its interval reported.

Add named rows for G2-only and G3-only failures ("stopping only", "passed with harm"). State how the extra seed is
scored if one is added.

### Other statistics issues (should-fix)

- **Warning rule.** maths 3d derived 16 points for the gap between two control seeds. With three R seeds the 95th
  percentile of the max-minus-min spread is about 19 points, and a 16-point line triggers about 12% of the time even
  when the seed SD really is 5 (computed). Use 19 for three seeds. Measure the spread on DEV, not T1, so no T1 score is
  read before the rule fires.
- **Bootstrap.** The interval is over puzzles only, for a mean of 3 seeds. It ignores seed-to-seed variation, so as a
  "95% interval of W minus R" it is too narrow. Use a two-level bootstrap (seeds within arm, then puzzles; number sets
  if twins are used), or call it a puzzle-only interval.
- **Power claim scope.** 1.9% and 85% hold for L2 alone, under the greedy binomial model, with 3 control seeds. The
  joint PASS (readable, L1, L2, G1, G2, G3 and G4) has lower power. L1 is against N, which is one model with no seed
  spread, so its false-pass chance is below 1.9%. Say both.
- **G1 noise.** "Coverage W at least N minus 2 in every W seed" fails by chance about 74% of the time when coverage is
  truly unchanged (computed, seed SD 5). That sends real gains into "sharper but narrower" by noise. Use the seed mean
  with an interval lower bound above -2 points.
- **Seeds versus the repo contract.** TEACHING_TO_TEST_CONTRACT.md l.316 uses 5 seeds with 4 of 5. v2 uses 3 with
  "every seed beats the control mean". The maths shows that clause works (4 seeds: 0.8% and 87%), but v2 should cite
  the contract and say why 3 seeds are enough.
- **Chance passes and trivial routes.** By noise alone, about 2% at most. "Learn to emit NONE after two calls" is
  matched by R and checked by G2. OK. "Bias toward one ordering or sign pattern" is **not** controlled (M1).

## 6. Consistency with v6 and Ben's rules; overclaims

| Point | Source | Severity and fix |
|---|---|---|
| Updating all four parts is v6's last rung (consolidation into a candidate core). v6 orders context, then an adapter with the core frozen, then replay, and says "A future adapter or overnight replay needs separate approval" | v6 l.16, 51, 92, 233, 285 | Should-fix: F3 should name the full-weight update, not only "before context reuse" |
| Training executes stored calls, not predicted ones | v6 l.80 | Must-fix M2 (flag F7) |
| R trains mostly on rejected tries | v6 l.174, 184 | Should-fix: state it. R is a never-promoted control |
| "Persistent" requires surviving intervening learning | v6 l.94, 187 | **Must-fix M4**, below |
| G3 is called retention, but TRAIN32 is rehearsed in every update (2 rows per update) | v2 section 7 | Should-fix: rename it "no harm on rehearsed items". It cannot show retention of anything un-rehearsed |
| Generator rule "A later **approved** generator" | v6 l.66 | Fine: D1 is flagged. Note that the generator itself is part of what Ben approves |
| Answer-hidden checker | v6 l.168 | OK, scoped: the generator only emits puzzles its solver certifies as solvable. Claim "goal predicate on certified-solvable puzzles" |
| "creative here means finding that answer more often by search" | v2 section 0 item 8, section 4 | Overclaim until G4 (M1) passes |
| "Copy the calculator recipe" | audit; v6 l.80 | Overclaim: 10-row updates and forced replay are changes |
| "Stopping" (STRICT needs NONE after the answer; G2 "finding, not just stopping") versus Ben's "learned stopping is out of scope" | FACTS | Minor: say that NONE after the answer is the existing call recipe (v6 l.80), not learned halting |
| Parent choice by a no-score rule | C.json `current_science.all8_endpoint_results` | OK and stronger than stated: seed-0/static is not the consumed panel's best (seed-0/contextual scored 3/16, seed-0/static 2/16), so the choice does not track the panel. Worth one line |
| "Ask before spending 0.50 dollars or more; nothing irreversible" | FACTS | OK ($0, copies only) |

### M4 (must-fix). S2 cannot show persistence as written

- The intervening block is "256 TRAIN32-only updates". The parent already fits TRAIN32. At update 4096, two of the
  three stable branches had last-256 output CE of 0.000155 and 0.000733 (v6 l.360; the order is not stated, but
  seed-0/static had 0 answer switches). TRAIN32 is also rehearsed in every W update. So the block changes the weights
  very little (suggested), and passing S2 would say little about surviving intervening learning (v6 l.187).
- v2 does not say the block is applied to N or R, so "W minus N" on T2 also mixes in the block's own effect.
- **Fix.** Use an intervening block of genuinely new learning that measurably moves the weights. Examples: a fixed block
  of a different generated family, or the admitted curriculum once it exists. Fix its size now and record the
  parameter distance moved. Apply the identical block to W, R and N. Require that W minus R, not only W minus N, keeps
  at least half its T1 value on T2.

## 7. Section 0 in plain language (should-fix)

Good: short numbered points, honest limits (item 8), a clear "failed" statement (item 7), a cost line.

Problems for a high-school senior:
- It opens with "v1 had five fatal flaws", but Ben never read v1 (FACTS: "Ben has not read it"). Lead with what the
  test is and why.
- Undefined jargon: talker, calls, reader, core, four loops, heads, trajectories, inference-only, v6, restricted formal
  tasks, shelf, placebo, positive control, solver-made answers, pass marks.
- No numbers for the bar. Say "the trained model must solve at least 10 more puzzles in 100 than the placebo, on
  puzzles it has never seen".
- No list of what Ben must decide: D1 (new puzzle family), F1 (sampling), F3 (weight update), F4 (solver-made
  control), F5 (parent), F6 (no final-answer training), plus new F7 (replay) and the 10-row update.
- After M1, add one line on the format-versus-aiming risk and the twin test.
- Cost: say 2.5 to 3.5 GPU hours on his PC, $0.

Suggested opening (plain): "We give the model small number puzzles like 'use 14, 9 and 30 once each, adding or
subtracting, to make 35'. A checker can tell if an answer is right without an answer key, by redoing the steps. The
model tries each practice puzzle 32 times, keeps its right answers and practises on them. Then we test on puzzles it
has never seen, against the same model with no practice and against a copy that practised on random tries of its own.
It counts only if the trained model wins by at least 10 points and also does better when we change only the target
number, which proves it is aiming and not just following the rules."

## 8. What checks out (no need to re-check)

- The core diagnosis that LM temperature cannot vary the calls (runtime l.117-150).
- Puzzles as the test family, their tiers, counts and floors (independently reproduced: 33,670 P puzzles).
- STRICT by literal id is checkable from the recorded trace.
- Three checker states, two independent checkers, planted violations.
- No in-context arm (runtime l.102-108, 8 memo slots = 4 tool pairs).
- Parent choice not driven by the consumed panel.
- Experience-store fields match v6 l.56 and l.180 and the PR23 section 6 contract.
- Exploration and scoring times (S3, S5).
- The CPU stages (S0, S0b) can start now and touch no checkpoint or panel.

## 9. Computations (all CPU, in my scratchpad)

Folder: `/tmp/claude-0/-home-user-learner/d373121d-85b9-59b3-9420-0d9a2b02a919/scratchpad/v2check/`

- `blind.py`: re-enumerates tier P (33,670 puzzles, matching maths). Format-only floor 14.4% per try, pass@8 66.9%,
  pass@32 97.5%. With valid arithmetic 25.7%, pass@8 85.4%. Sign-pattern shares 26.4 / 25.6 / 24.1 / 13.0 / 10.9%.
- `twins.py`: 9,100 of 9,139 P number sets (99.6%) have 2 or more P targets. With a canonical-form split, 18 of 256 T1
  puzzles shared a number set with practice in one random draw.
- `noise.py` (run with the maths venv): three-seed spread above 16 points 11.8% (95th percentile 19.0; two seeds
  15.9). Proved-wrong and no-verdict rates (table in section 5). G1 every-seed false-fail 74%.

Assumptions in `noise.py` (suggested): seed SD 5 points, pass@8 puzzle variance 0.8 of the bound at a 50% level,
n = 256, arms unpaired. Pairing by puzzle would shrink the puzzle part. The seed part dominates.
