# Re-check of creative prototype design v2 (2026-10-03)

Fifth review pass: an independent Opus subagent re-checked the revised v2 against v2-check.md, the maths, the facts pack
and the code copies. Read-only; nothing trained or run on a GPU; no panel opened. Its scripts are in `v2recheck/`.

**How it was applied (by the thread, after the report):** MF-1, MF-2, MF-3, SF-1 to SF-8 and nearly all NITs are in
`../creative-prototype.md`. The `wins.jsonl` claim the reviewer could not open was checked by the thread and is shown
(`artifacts/claude-blurt2-20260925/*/wins/wins.jsonl` rows store free-text expressions such as `"(4 * 8 + 7)"`). The
power cell the reviewer cited (`part3_rules.json` "sd5 S3 n256 R2 M8" = 0.0447 / 0.9150) and the simulation outputs in
`v2recheck/*.out` were read back by the thread before use. Not applied: the NIT that G0 cannot tell crude magnitude
heuristics from exact aiming needs no change, because the claim words stay "aims at the target".

The report follows as returned.

---

This was a read-only check. No repo file was edited. Nothing was trained, tested or run on a GPU. GOLD-PRIVATE-v1.json,
panel files and reserved or blind panels were not opened. I ran CPU scripts in `scratchpad/recheck/` (section 6). One
attempted repo read, to check that `wins.jsonl` rows use free-text steps, was blocked by the permission system, so that
claim is unchecked.

Labels: **shown** = read in a named file, or produced by a named script under the stated assumptions. **suggested** =
reasoning. **untested** = nobody has measured it.

## 0. For Ben (plain)

- Most of the five big fixes landed. The twin-target test now really checks that the model aims at the target number.
  Training on saved steps is now planned, built and tested.
- Three things still need fixing before the pass marks are sealed:
  1. The error bars come out too narrow with only 3 training runs per arm. "Proved wrong" could then fire wrongly about
     1 time in 6 to 10 when the idea really helps a little.
  2. If too few practice puzzles get solved, the plan only finds out after it has used up the one-time test set. Its
     backup step cannot help.
  3. The "does it last" test has no defined training data. With 3 runs it would usually read "failed" even if the skill
     fully lasts.
- GPU time is about 2.5 to 4 hours, plus 1 to 2 hours for the "does it last" test.

## 1. Status of the earlier must-fixes and should-fixes

| Item | Status | Where in v2 | Residue |
|---|---|---|---|
| M1 target-blind pass | **Resolved** (shown) | §5 "Twin targets", §9 "Aiming (goal use)", G0, PC gate, verdict 5 | v2 averages goal use over both twins. Algebraically this is identical to v2-check's G4: both equal ½[P_A(t_A) − P_A(t_B) + P_B(t_B) − P_B(t_A)]. Sign balance is feasible: a greedy draw filled 445 of the 448 pairs needed (DEV + T1 + T1b + T2), 170 to 180 per pattern (`balance.py`). NIT: also report each arm's hit rate among rule-valid runs |
| M2 replay path | **Resolved** | §7 F7 and its regression test, §10 S1 | none |
| M3 one STRICT definition | **Resolved** | §5 "Acceptance rule STRICT", "Training form"; §8 R and PC use training form | SF-5 (loop numbering), NIT (one rejection reason missing) |
| M4 persistence | **Partly** | §9 "S2 persistence ... 512 updates of new single-call word problems ... applied to W, R and N" | MF-3 |
| M5 decision list | **Partly** | §9 "Ordered verdicts" 1 to 11 | MF-1, MF-2, SF-8 |
| Warning rule 16 → 19, measured on DEV | Resolved | §9 seed-spread rule | NIT on how 19 was derived |
| 0.41 s is a 1-row update; S4 75 to 100 min | Partly | §10, §0 | SF-1 (S3, S6 and 5 seeds not costed) |
| R can collapse onto W | Resolved | §7 step 2 (pool up to 256), §8, verdict 3 | SF-7 (natural-rate number). The "half" threshold, not 25%, is right, because a uniform rule-learner already hits about 26% |
| Hidden second changes flagged | Resolved | F3, F7, F8 | none |
| Leakage: number-set split, T1b sealed | Resolved | §5 "Splits, by number set" | none |
| Checker gate feasible | Resolved | §6 "500 puzzles ... 100,000 ... 20 planted" | NIT (which tiers) |
| Checker B independent | Resolved | §6 | none |
| S3 fallback unclear | **Not resolved** | §10 S3 gate | MF-2 |
| GPU hold stated | Resolved | §2, §10 | none |
| Two-level bootstrap | Partly | §9 "bootstrap that resamples seeds within each arm and then puzzles" | MF-1 |
| Power claim scope | Resolved | §9 "Power (provisional)" | SF-3 |
| G1 noise | Partly | G1 is now on the seed mean | SF-2 |
| Seeds vs the test contract | Resolved | §8 | none |
| F3 names the full-weight update; R trains on rejected tries; G3 renamed | Resolved | §7, §8, §9 | none |
| Positive control details | Resolved | §8 "one drawn at random (fixed seed) per W record" | none |
| §0 plain language | Mostly | §0 | NIT (decision list misses F5, F6, F8) |
| Minor items | 8-vector prefix label, loop-0 citation, word-problem policy mix, P(second OK call) on DEV: resolved. LM-touch wording, "separate author", 48-token cap, private RNG, stopping vs Ben's rule: not resolved | | NITs |

## 2. Findings, ranked

### MUST-FIX

**MF-1. With 3 seeds per arm, the interval method undercovers. "Proved wrong" then fires 10 to 16% of the time at a
real +5 gain.** (shown, `marks_sim.py`; assumptions: seed SD 5 points, Beta(1) puzzle spread, paired puzzles, 256
puzzles, 32 tries)
- v2 §9 says: "intervals come from a bootstrap that resamples seeds within each arm and then puzzles". Resampling 3
  seeds from 3 shrinks the seed variance by about 2/3 and uses normal quantiles where 2 to 4 degrees of freedom apply.
- Simulated coverage of the nominal 95% interval is **77 to 83%**. A seed-level Welch t interval covers 96 to 97%.

| True W − R (luck) | Luck clause of "proved wrong" fires (upper end < 5), bootstrap | Same, Welch |
|---|---|---|
| 0 | 49 to 62% | 15 to 24% |
| +3 | 23 to 32% | 4 to 8% |
| +5 | **10 to 16%** | 2 to 3% |
| +8 | 3% | 0.5% |

- Verdict 10 also needs the goal-use clause, so the joint rate is lower. But when the luck gain is +5 and the goal-use
  gain is small, the joint rate approaches the luck-only rate. This brings back the false alarm that M5 was meant to
  remove.
- The same interval is used in L2, G0, the PC gate and S2. In L2 it changes almost nothing (L2 with and without the
  interval differ by under 1 point), because the 8-point mark dominates.
- The resampling unit is also wrong for twins: v2 says "then puzzles", but the twin pair is the natural unit.
- **Replacement text (§9, the sentence after "Arm differences are paired by puzzle"):** "Intervals are 95% seed-level t
  intervals. The seed is the unit; each seed's score is its mean over T1. For W − R, R − N or PC − N use Welch's
  interval on the seed means. For one arm, or for W − N, use a one-sample t interval over the seeds' paired
  differences. A bootstrap that resamples twin pairs (number sets) is reported beside it as a check and decides
  nothing. With 3 seeds a seed-resampling bootstrap covers only about 80% (computed). With t intervals, 'proved wrong'
  fires only about 15 to 24% of the time even when the true effect is 0, so 'not shown' is the expected null outcome."
- This will lower G0 power, because a one-arm t interval with 2 degrees of freedom is wide. S0's power re-run (SF-3)
  must use these intervals. That may correctly push seeds to 5.

**MF-2. The cold-start and placebo verdicts are applied only after T1 is spent, and the W-tier fallback cannot rescue a
cold start.** (shown from the design's own text, plus `gates_sim.py`)
- Verdict 2 says: "fewer than 100 tier-P practice puzzles with an accepted training-form run ... Remedy: the fixed
  fallback in S3". The S3 gate says: "add 256 W-tier puzzles to practice and re-run the gate on 64 W-tier DEV puzzles".
- **Problem 1:** this is a one-round design. V0 alone produces the P-tier hit count in S3, so adding W-tier puzzles
  cannot change it, and W-tier puzzles are excluded from the count. The fallback leads to verdict 2 by construction. The
  W-tier gate is also vacuous: random calls already reach 75% of W-tier puzzles in 32 tries.
- **Problem 2:** "64 W-tier DEV puzzles" is not in the §5 split list.
- **Problem 3:** verdicts 2 and 3 can be decided at the end of S3, but the list is applied after S5. T1 ("main test,
  once") and S4 to S5 are spent on a run already known to be inconclusive.
- **Problem 4:** §13 gives a different remedy for cold start ("Hindsight relabelling") than verdict 2 does.
- Near the boundary, the DEV gate (13 of 128 or more) passes while practice falls below 100 of 1,024 with probability
  22% at a true coverage of 8%, 29% at 9% and 20% at 10%.
- **Replacement text:**
  - §10, S3 gate cell: "The S2 gate passes. Otherwise stop: T1 stays sealed, verdict 'Inconclusive, cold start'.
    End-of-S3 stop gate, before any training: at least 100 tier-P practice puzzles have an accepted training-form run in
    W's pool, and at most half of R's selected records are accepted. If either fails, stop before S4; T1 stays sealed;
    verdict 2 or 3."
  - Delete the W-tier fallback.
  - Verdict 2 remedy: "None in this run. Decided at the end of S3; T1 stays sealed. Next experiment: hindsight
    relabelling against R." Give verdict 3 the same wording.

**MF-3. M4 residue: the S2 intervening block cannot be run as written, its weight-change rule is unspecified, and a
fail mostly reads noise.** (shown for the C.json fields and the power numbers; suggested for the rest)
- **Source:** v2 says "from the approved curriculum bank if admitted, else the E2 practice pool". C.json has
  `dataset_instantiation_and_all_row_token_audits_pending: true`, and one curriculum arm is "exact TRAIN32
  numbers-and-names-only skeletons", which is near-rehearsal. E2 is a sketch with no pool. §10 also runs GPU stages
  "after ... the curriculum". By F5, a curriculum-trained worker would then become the parent, so a block drawn from the
  curriculum bank would be rehearsal, and S2 would be "not scored".
- **Recipe:** rows per update, LR, TRAIN32 mix and the "weight change" norm are undefined, yet the "at least half of the
  main training's" rule depends on them.
- **Supervision:** the block is gold-call supervision on new word problems. C.json has
  `new_worked_example_supervision_authorized: false`, and no flag covers it.
- **Power:** with a calibrated interval and full retention, S2 passes only 24% (true W − R +8), 35% (+10), 47% (+12) and
  65% (+15) of the time, given L2 passed. Yet §13 maps "PASS, S2 fails" to "Hand to the sleep-replay design
  (retention)".
- **Replacement text (§9, S2):** "Q2 persistence (stage S6). One block, applied identically to every W and R seed and to
  N: 512 updates of 10 rows each, constant LR 1e-4, fresh Adam, all four parts, the original recipe (predicted calls
  executed; final CE plus call CE). Rows come from 2,048 new single-call ADD/SUB word problems made and sealed in S0.
  They share no number pair with TRAIN32, the curriculum bank or any panel, and no parent trained on them. Flag F9:
  gold-call supervision on these items, for this block only. Then a process restart, then T2. Weight change = L2
  distance over core, reader, prefix and tool from the start of the block. If its median over runs is below half the
  median distance moved by W's training, Q2 is 'not scored'. Outcomes: 'kept' if T2 W − R is at least half its T1 value
  and the interval's lower end is above 0; 'loss shown' if the interval's upper end is below half the T1 value;
  otherwise 'persistence not shown'. Only 'loss shown' goes to the sleep-replay hand-off."
- Add F9 to §15, add the item generator to S0, and update §13 to match.

### SHOULD-FIX

**SF-1. The run-time and cost figures are low.** (suggested; `cost.py`, using the forward rate implied by v2-check's own
S5 figure: 82k forwards in 30 to 60 min, so 22 to 44 ms per forward)
- S3 is 1,024 × 65 = 66,560 forwards, so **24 to 49 min**, not "15 to 30", plus R top-ups.
- S6 is 7 runs × 512 updates (0.41 to 1.3 s each) plus 59,136 scoring forwards, so **46 to 121 min**, not "about 30".
- S1 to S5 total **2.5 to 4.0 h**. Going to 5 seeds adds **73 to 110 min**.
- Replace the cost line in §0 with: "Cost: about 2.5 to 4 GPU hours for S1 to S5, plus 1 to 2 hours for the persistence
  test if it runs, plus a replication. About 1.5 hours more if seeds go to 5. $0 (untested estimates)." Correct the S3
  and S6 cells in §10 to match.

**SF-2. G1 false-fails 26% of the time when coverage is truly unchanged** (seed SD 5; 16% at SD 3; shown,
`gates_sim.py`). That sends real gains to "Sharper but narrower" by noise. Replace G1 with: "G1 coverage: fails only if
the upper end of the 95% interval of W − N coverage is below −2 points."

**SF-3. Power.**
- §9 says "the 8-point L2 mark were not computed". It was: `part3_rules.json` cell "sd5 S3 n256 R2 M8" gives **4.5%
  false pass, 91.5% power at +15** (greedy, unpaired). The paired simulation gives 0.2 to 0.7% false pass and 93% power
  at +15, and 53 to 60% power at +10.
- The quoted 1.9% / 85% cell is a 3-seed vs 3-seed comparison with a 10-point mark. L1's control N has no seed spread,
  so that cell describes neither mark exactly.
- G0 has no power model. The maths scripts do not model goal use, and "power at a 15-point gain" is undefined for a
  5-point mark.
- Add: "S0 adds a goal-use simulation: paired twins, an assumed seed SD for goal use, the MF-1 intervals, alternative =
  a real +8 goal-use gain. G0 must meet false pass ≤ 5% and power ≥ 80% at that alternative, or seeds go to 5."

**SF-4. Name clash.** The secondary marks "S1 first try" and "S2 persistence" (§1 row 11, §9, §13) share names with
stages S1 and S2 (§10). Rename the marks Q1 and Q2 everywhere.

**SF-5. Loop numbering is mixed.** §2 and §13 say "loop 0", while §5's training form says "loops 1 to m". Read 0-based,
§5 would select runs whose first loop is NONE. Replace with: "OK calls in the first m loops (code `loop_index` 0 to m−1,
i.e. `call_index` 1 to m), then NONE."

**SF-6. The scoring temperature is not fixed in the pass marks.** §9 never says at what tau T1, T2, DEV and X are
sampled. Add: "All scoring uses the DEV-chosen tau and the same pre-drawn uniforms for every arm. The worker attempt is
tau 0."

**SF-7. Wrong label on the natural R hit rate.** §8 says "R keeps hits only at their natural rate among rule-valid runs
(about 14% to 26%, computed)". The 14.4% figure counts runs that error in the denominator, and those are not rule-valid.
Among rule-valid trees, a uniform choice hits **25.7%** (`blind.py`: c/v = 0.257, c/48 = 0.144). Replace with: "about
26% if the choice among rule-valid trees were uniform (computed); V0's real rate is measured in S3."

**SF-8. The failure table (§13) is missing rows** for Void, "placebo too close", "stopping only" and "Q2 not scored".
Suggested rows:
- Void: fix the cause and re-score the frozen outputs.
- Placebo too close: stopped before S4; register a separate R design.
- Stopping only: no claim; report the G2 gap.
- Q2 not scored: a larger block, as one change.

### NIT

- §5 rejection reasons lack "an intermediate result used more than once" (for example, a third call reusing result 1).
  Add it, and plant 20 such violations.
- §2 says producing a trajectory "touches the LM only through each result token's embedding". The question features
  also come from the LM: cached static embeddings or contextual states (eval l.414-418). Write: "...through the cached
  question features and each result token's embedding".
- §0 says "it can only say numbers from a shelf of 27 (shown)". What is shown is that all 128 finals were among the 27
  training answers. "Can only" is suggested.
- §1 "Kept from v1" says "by a separate author", but S0 builds every split with one generator. Write: "drawn by the
  certified generator from number sets disjoint from practice, sealed before any GPU stage; a separate agent audits the
  split".
- §0:
  - Add F5, F6 and F8 to the list of choices.
  - Write "3 per arm (5 if S0 or DEV says 3 are too few)".
  - Change "proves it is aiming" to "shows it uses the target".
  - Change "tries picked at random" to "rule-following tries picked without checking the answer".
- "Seed spread 5 points" (§9 power, §14) means SD, while "spread by more than 19" means max minus min. Say "seed SD" in
  the first case.
- The 19 threshold was derived with each seed scored on different puzzles. On the shared DEV set the 95th percentile at
  seed SD 5 is about 17. The 19 line fires 2% / 7% / 14% of the time at seed SD 5 / 6 / 7 (`gates_sim.py`). It is a
  weak warning; say so.
- §9 says "Marks (means over the 3 seeds...)". Write "over the seeds". State whether 5 seeds keep "every W seed" or the
  contract's 4-of-5 rule.
- G2 uses "STOP-rule luck", which is never defined. Add: "share of tries accepted when loops after the finishing call
  are ignored (maths STRICT-STOP)".
- The tier W rule omits "target not a given number" (maths 1d). The 3,283 count assumes it.
- §4 says "4 valid calls give 3 distinct values". One of those values is negative, which the runtime turns into ERROR
  (no negative is a single token), so only 2 results are usable.
- W0 has no stage or gate. "Supplied by the parent" is ambiguous, and off-shelf items cannot come from the parent's
  training set. Name the source.
- §6 checker gate: include W-tier and T-tier puzzles, because the X split uses T-tier and the fallback used W-tier.
- The sampler must not touch the global torch RNG: the eval runner raises if inference changes it (eval l.494-497).
- Name the 48-token question cap (eval l.127). Ten templates "with names and objects" and 5 literals may exceed it; S0b
  checks this.
- §7: say what happens if R still lacks enough rule-valid runs after 256 samples (drop that puzzle from all arms and
  report it). Make R pick distinct trajectories, as W does.
- F5's "no-score rule" fits six stable branches. Name the tie-break: static input, low LR, lowest seed.
- G0 cannot tell crude magnitude heuristics ("big target → add") from exact aiming. The claim words "aims at the target"
  are fine; "plans" would not be.

## 3. Numbers checked against the maths, v2-check and the JSON outputs

| v2 number | Source | Verdict |
|---|---|---|
| Tiers: 3,283 / 33,670 / 2,318,380 puzzles; hit per try 6.51 / 0.544 / 0.0161%; pass@8 37.1 / 4.24 / 0.128%; pass@32 75.0 / 15.6 / 0.513% | maths 1d, `part1_tiers.out` | OK |
| 0.54% per uniform try (§4) | maths tier P | OK |
| Rules-only floor 14.4% (pass@8 66.9%), 25.7% (pass@8 85.4%); "add all three" 26.4% | `blind.py`, re-run | OK |
| 99.6% of number sets have 2 or more targets | `twins.py` re-run: 9,100 of 9,139 | OK |
| 97 to 100% have one sign pattern | maths 1a (97.1% to 100%) | OK |
| Floors fall 3 to 20% if results up to 999 are accepted | maths 1b sensitivities (3.2 to 20.1%) | OK |
| Word problems: 1 in 12 (1 in 6 as a pair); pass@32 94% to 99.7% | maths Part 2 | OK (see NIT on negative values) |
| R natural rate "14% to 26%" | `blind.py` | **Mismatch: about 26%** (SF-7) |
| Power: 1.9% false pass, 85% power | `part3_rules.json` sd5 S3 n256 R2 M10 = 0.0186 / 0.848 | Number OK; scope SF-3 |
| "8-point L2 not computed" | `part3_rules.json` M8 = 0.045 / 0.915 | **Mismatch: it exists** (SF-3) |
| Seed-spread threshold 19 | v2-check `noise.py` (95th percentile 19.0, unpaired) | Matches its source; about 17 on shared DEV (NIT) |
| DEV gate 10% ≈ 13 of 128 vs 100 of 1,024 | arithmetic | Aligned, but see MF-2 |
| 0.41 s per update | C.json `mean_complete_control_update_seconds` 0.4134 | OK |
| S4 75 to 100 min | 9 × 512 × 1.0 to 1.3 s = 77 to 100 min | OK |
| S3 15 to 30 min; S6 30 min; total 2.5 to 3.5 h | `cost.py` | **Low** (SF-1) |
| S5 30 to 60 min | 84,480 forwards | OK |
| 127 of 128 calls at loop 0 | C.json l.322 `all_active_calls_loop0_no_later_superseding_calls` | OK |
| C.json flags and the 11:44 UTC time | C.json l.139, 310, 2586, 2594 | OK |
| v6 l.66, 77, 80, 165, 184, 187, 374-376 | v6 text | OK |

## 4. Probes for new defects introduced by the fixes

- **Twin targets leaking target information:** none found (suggested). Both twins sit in the same split. The twin's
  target is used only by the scorer. A target-blind policy scores exactly 0 in expectation on the pair-averaged measure.
- **Placebo R distinguishable by a trivial cue:** none found (suggested). R self-trains value-blind on its own
  rule-valid samples, which carries no anti-target signal. The puzzle set, per-puzzle count, shape, tau and pool size
  distribution are all matched. Small asymmetries: W picks distinct call orders while R may pick duplicates, and R's
  top-up has no defined shortfall rule. Both are NITs above. W can learn the practice sign-pattern prior, which is
  target-blind; that inflates L1 and L2 but not G0, which is why G0 is required.
- **Forced replay training on something the evaluation measures:** none (shown from the design text). Replay touches
  practice rows only. TRAIN32 runs the original protocol and G3 is already labelled "rehearsed".
- **S2 confounded:** yes. See MF-3: undefined or unavailable source, possible rehearsal, unflagged supervision, low
  power.
- **Split used for two purposes:** none. DEV is used only for tuning-type choices, T1 / T1b / T2 / X once each, and
  hindsight relabelling is outside this run. The only gap is the missing W-tier DEV split (MF-2).
- **Verdicts that never fire or overlap:**
  - The list is strictly ordered, so no two verdicts conflict.
  - "Stopping only" can fire only if R finds the answer but keeps calling 4 or more points more often than W. That is
    rare but possible.
  - "Proved wrong" with calibrated intervals fires 15 to 24% of the time at a true 0. It is reachable but rare; say so
    (MF-1).
  - "Sharper but narrower" will fire by noise until SF-2 is applied.

## 5. Claims vs the facts pack

- Code claims in §2, §3 and §6 match the code copies: argmax at runtime l.119 and l.122; clean `begin_latent` at l.107;
  single-token results at l.64-71; tool limits and `operand_references` at tools l.10-13 and l.176-180; components at
  eval l.42; low LR at eval l.33; greedy decode with 32 tokens at eval l.280 and l.492.
- The prefix is correctly labelled as coming from v6.
- One-row updates are cited second-hand, via v2-check's read of the audit script, which is not among the code copies.
  That is acceptable as cited.
- One overstatement: "touches the LM only through each result token's embedding" (NIT above).
- The "40 calls / 2 of 6 rescued" diagnostic appears only in §1 row 10 as "Not cited as evidence" and in §11 as "the
  unreceipted figure" that W0 replaces. It is not used as evidence anywhere.
- The `wins.jsonl` free-text claim in §12 is not verified (repo read blocked; untested by me).

## 6. Scripts (CPU only; copies in `v2recheck/`, run with the maths venv's numpy and scipy)

- `blind.py`, `twins.py`: copies of the v2check scripts, re-run with identical output (not duplicated here).
- `balance.py`: sign-pattern availability per number set; a greedy balanced twin draw (445 of 448 pairs, 170 to 180 per
  pattern); natural rule-valid hit rate (0.257 vs 0.144 per try).
- `marks_sim.py` → `marks_sim.out`: per-puzzle paired model. Bootstrap coverage vs Welch; proved-wrong rates; L2 false
  pass and power.
- `gates_sim.py` → `gates_sim.out`: cold-start boundary, G1 false fails, S2 power under full retention, 3-seed range on
  shared DEV.
- `cost.py` → `cost.out`: stage run-time arithmetic.

## Verdict

Not yet. The design is close, but three must-fixes remain: the intervals (MF-1), stopping at the end of S3 instead of
after T1 is spent (MF-2), and a defined and powered persistence block (MF-3). Each needs only the replacement text given
above.

Once MF-1 to MF-3, SF-1 and SF-3 are applied, it can be handed over as "as good as it can be". The other items are
wording.
