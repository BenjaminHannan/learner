## Skeptic check of the sleep round 2 synthesis

I checked every arXiv id against its abstract page or a WebSearch hit. All of them exist, including Kuo 2606.29983 and Popescu 2607.20519. I checked the repo claims in `scripts/claude_rsn294_{run,core}.py`, `claude_rsn296_gen.py`, `claude_rsn296_run.py`, `claude_rsn353_run.py`, the 294/296/353 artifacts, plan 360, and round 1.

### Repo claims

- **claim:** `COPY_KINDS`/`ALL_KINDS` leave out `value3`, which appears only in dev scoring (run.py:42-43, 219). 296 and 353 reuse the runner via runpy.
  **verdict:** ok
  **fix:** It holds for all of them. `value3` appears in no other reasoner runner (296b, 299, 350).

- **claim:** "Big finding / code check that changes the ranking": 0/30 is zero-shot.
  **verdict:** overstated (as a novelty)
  **fix:** This was already known and deliberate. The 294 docstring says three-step is dev-only. `artifacts/claude-rsn296-20260924/VERIFY-director.md` D2 says "Three-step is 0/30 (never practised, as designed)". Round 1 (Job C, C1) already cites it. Reword it as a reminder, not a finding.

- **claim:** `MAX_HOPS = 3` with a separate slot per hop, so 4-step cannot be encoded. The answer head reads only the last pass.
  **verdict:** ok
  **fix:** Confirmed at core.py:45, 407, 420-421 and 496-503.

- **claim:** "Until those change, extrapolation means train on 1-2 steps, test on 3."
  **verdict:** wrong
  **fix:** The hop-3 slot embedding `S[1+MAX_WHO+2]` only gets gradient when a question has 3 relations. No training kind has 3 relations: `missing` has at most 2. So in every checkpoint that slot is still its N(0,1) random start, added to a d=640 or d=1024 token. The 1-2 → 3 test is broken by the input encoding, the same way the 4-step case is, so it cannot measure "rule vs template". A shared hop-role embedding (or relative hop encoding) must come **before** #2, #3 and the 363 extrapolation arm, not only before 4-step tests. A $0 check: compare the norm of that slot row with the trained rows in the Mac checkpoint.

- **claim:** GRPO advantage is zero when all 8 tries fail (run.py:110).
  **verdict:** ok
  **fix:** When the fact is present, wrong and "I don't know" both score -0.1 (core.py:527-529), so the spread really is zero.

- **claim:** Stop head: "an honest I don't know pays +0.3", so a pass cost could teach dodging.
  **verdict:** overstated
  **fix:** +0.3 is paid only when the gold is UNKNOWN. With the fact present, "I don't know" = wrong = -0.1. The dodging risk is smaller than stated. The design stays.

- **claim:** #1 twin type "reorder rows (answer stays)".
  **verdict:** wrong (no-op)
  **fix:** Rows have no position embedding (they all share `S[-1]`) and the encoder has no positional encoding, so row order cannot change the output. The Book class also already shuffles rows (core.py:130). Drop this twin type.

- **claim:** #1 twin types "delete a hop row" and "add near-miss row".
  **verdict:** overstated (as new)
  **fix:** Unpaired versions already exist: `missing` makes a broken 2-step chain 30% of the time (core.py:183), and the `near_miss` knob is in `_style`. Only the **pairing** and "change a hop value" are new.

- **claim:** #1 Step A: a bandit over about 8 `_style` knobs.
  **verdict:** overstated
  **fix:** There are 8 knobs, confirmed. But 296 was trained over exactly those ranges, so a flat result is expected and does not show "distractors aren't the weakness". Search outside the training ranges (size up to 48, `about_chain` > 5, `reuse` > 0.6). Also, the 296 checkpoints are on Ben's Mac, not in this container.

- **claim:** #1 Step B pass mark: "false answers on missing-hop items ≤ half the twin's".
  **verdict:** gameable
  **fix:** Checked inventions are already 0 (missing_fact 30/30), and half of 0 passes trivially. Score raw inventions before the fact-check, on broken-chain items, with n ≥ 60.

- **claim:** #4 skeletons are "the order of relations plus final operation"; held-out skeletons are ones never seen; "relation pairs never put next to each other" (#2).
  **verdict:** wrong (void design)
  **fix:** `encode` gives relations fresh random ids **every episode** (core.py:308, 318-321). The model never sees which relation is which, so held-out skeletons look the same as trained ones at the input. For 3-step items the final operation is always a value lookup. The "≥ 50% of in-skeleton at dose 16" mark would pass at dose 1. Redefine the families on features the model can see: which hop holds a correction, a missing row, a multi-valued relation or a near-miss; name reuse or cycles; whether the final value is a number or a thing.

- **claim:** #4 is "also the plain add-3-step baseline".
  **verdict:** repeats round 1
  **fix:** This is round-1 C1 and step 2 of plan 363's ladder. Say so. The new part is only the dose-response over families.

- **claim:** Section 4: "held-out structure types hashed from kind + relation path + step count".
  **verdict:** wrong
  **fix:** Relation path is invisible to the model (see above). Hash on the visible structure features instead.

- **claim:** Section 4: report pass@1 and pass@64.
  **verdict:** gameable / meaningless here
  **fix:** Each try is **one** categorical action. A value answer is a pick among up to 48 rows, so 64 samples cover almost the whole action space and pass@64 is about 1 for any policy. Use pass@2 or pass@4, or the probability mass on the gold answer.

- **claim:** #5 win injection with a capped ratio (LUFFY-style).
  **verdict:** overstated
  **fix:** In a one-action bandit, injecting the gold action amounts to cross-entropy on gold, i.e. putting `value3` in `COPY_KINDS`. On cards it is the same as #4's baseline. Drop it on cards and keep it for the village model only.

- **claim:** #2 "the block cannot count passes" is the benefit.
  **verdict:** overstated
  **fix:** 353 already removes the step embedding, and 294 already trains with random 2-12 passes (run.py:75-76). The new parts are only the no-gradient prefix and the perturbed start.

### Citations

- **claim:** Kaushik 1909.12434, Huang 2010.04762, PAIRED 2012.02096.
  **verdict:** ok
  **fix:** The claim that Step A follows PAIRED is only SUGGESTED. A plain knob bandit has no regret or antagonist.

- **claim:** Bansal 2202.05826 (mazes, prefix sums, no overthinking).
  **verdict:** ok
  **fix:** Bansal's progressive loss does **not** start from a perturbed state. The random start comes from Anil. The combination is UNTESTED.

- **claim:** Anil 2211.09961, Geiping 2502.05171, Schwarzschild 2106.04537, Fan 2409.15647, CLRS 2205.15659.
  **verdict:** ok
  **fix:** None.

- **claim:** Ibarz 2209.11142: "hints help on some tasks, not others".
  **verdict:** overstated
  **fix:** Its biggest single gain came from **not** teacher-forcing the ground-truth hints: feeding them in training hurt generalisation. For #3, supervise the pointer head but never feed the solver's row back in as input. Add Rodionov 2306.13411 (no hints were competitive) as counter-evidence.

- **claim:** Wang 2405.15071: transformers fail OOD composition. SHOWN.
  **verdict:** overstated for this repo
  **fix:** The paper is about composing facts stored in the weights, in a regime where it only works after grokking. Here the facts are in the input with anonymous per-episode ids. For this repo it is SUGGESTED at best. It also sits oddly next to dropping grokking.

- **claim:** RFT 2308.01825, Online Difficulty Filtering 2504.03380 (bound on variance of success), DART-Math 2407.13690.
  **verdict:** ok
  **fix:** For 2504.03380, label it SHOWN (theory + LLM experiments).

- **claim:** LUFFY 2504.14945: "+7.0 across 6 benchmarks".
  **verdict:** wrong (number)
  **fix:** The current abstract says "over +6.4". Use that figure.

- **claim:** CALM 2207.07061, Thinkless 2505.13379, Spurious Rewards 2506.10947, 2507.10532, Yue 2504.13837, B-STaR 2412.17256.
  **verdict:** ok
  **fix:** Thinkless is "decoupled GRPO": it balances the loss on the control token against the answer tokens. It is not really a separate normalisation. The placebo arm will probably show about 0 on a 30M model trained from scratch, because Qwen's gain came from its pretrained habits. Keep the arm anyway; it is cheap.

- **claim:** Shrink-and-perturb (Dohare, Nature 2024).
  **verdict:** overstated
  **fix:** The method is Ash & Adams (1910.08475). Dohare only tested it as a baseline; its own method is continual backprop.

- **claim:** Kuo 2606.29983, Popescu 2607.20519.
  **verdict:** ok (exist)
  **fix:** Titles and authors match looped-transformer stopping work. Popescu supports "fit the stop gate on frozen trajectories", as the stop-head item already says.

### Pass marks, budget, leakage

- **claim:** #2 pass mark: "3-step ≥ 12/30 at *some* pass count".
  **verdict:** gameable (best of 4)
  **fix:** Fix one scoring point in advance (12 passes), with "48 ≥ 12" as a separate mark. Use 2 seeds: 294's loop seeds differed a lot (copy-only 45 vs 107).

- **claim:** Costs of about $2 per arm.
  **verdict:** ok
  **fix:** 294 runs took 30-40 min at $0.47/h. All experiments fit the $4 cap with 2 seeds.

- **claim:** Blocked on 353.
  **verdict:** ok
  **fix:** 353 has pass marks and no results yet.

### Corrected top 5

0. **Prerequisite (one change, $0 CPU plus a small job):** replace the per-position hop slots with a shared hop-role embedding. The $0 part is confirming on the Mac checkpoint that the hop-3 slot is untrained. Without this, every 1-2 → 3 test is invalid.
1. **#1 minimal-pair twins.** Drop the reorder twin. Probe knobs beyond their training ranges. Hold out "change a hop value" for the panel only. Score raw inventions before the fact-check.
2. **#4, reworked** as held-out **visible-structure** families, run as the dose arm of round-1 C1 rather than as a new idea.
3. **#5, $0 zero-spread count and middle-band sampling only.** No win injection on cards.
4. **#3 per-pass hop labels,** after steps 0 and 353. Supervised, never teacher-forced.
5. **#2 path-independent loop training,** after steps 0 and 353. Score at fixed pass counts, 2 seeds.

**For Ben:** two of the planned tests can't work as written. The model gets new random labels for the kinds of link in every puzzle, so "new kinds of chain" look the same to it as old ones. The slot for the third step of a question has never been trained, so testing "learn 2 steps, try 3" mostly measures that untrained slot. Fix the input first, then run the twins test.

Sources: [2211.09961](https://arxiv.org/abs/2211.09961), [2209.11142](https://arxiv.org/abs/2209.11142), [2106.04537](https://arxiv.org/abs/2106.04537), [2606.29983](https://arxiv.org/html/2606.29983). Other ids were checked on export.arxiv.org abstract pages.