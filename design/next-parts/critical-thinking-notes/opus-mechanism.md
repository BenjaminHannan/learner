# Reasoner mechanism: what to change inside the ~9M core (design only)

Angle: the internal mechanism of the latent reasoner. Written 2026-10-03. Nothing was trained or run. Labels: **shown** = I read it in this repo's code or results, or checked a cited abstract; **suggested** = literature or reasoning; **untested** = our guess. There are two rulers here and I keep them apart. The **puzzle ruler** is the few-example mazes, sums and grids (`claude_fewex_*`). The **assistant panel** is the 128 fresh calculator questions from the brainstorm thread, run on Ben's Mac. The village model is not used anywhere in this note.

## 1. What the core is today (read from code)

- **Shown (code).** The core is `AttentionReasoner` (`scripts/sol_spatial_attention_core.py:46-139`). It is built from the fewex loop: 2 shared width-256 attention blocks per round (`claude_fewex_net.py:22`). Each MLP (256 -> 1024 -> 256) is turned into 8 copied experts with top-2 routing, a router that starts at zero, and a small balance loss (`sol_spatial_attention_core.py:19-43`). That comes to roughly 9M stored weights, about 2.6M active (my arithmetic).
- **Shown (code).** There is **one state stream**. Each round computes `z = h + e`, runs the 2 blocks, then a LayerNorm (`claude_fewex_net.py:74-78`). The question positions and the context "notebook" positions share the same attention (`begin_latent`, lines 68-96). Only the **question positions** are exported (`read_latent`, lines 102-105). There is no separate place for a draft answer.
- **Shown (code).** The output path takes those question-position states and runs them through `256+3 -> 32 -> LM width`. It then **average-pools them down to 8 prefix vectors** (`sol_translator_english_v6.py:33-46`, `adaptive_avg_pool1d` at line 44). So a number the core computed at one position gets averaged with its neighbours before the LM sees it.
- **Shown (code).** On the assistant path, training uses a **fixed 4 rounds** (`DEPLOYMENT-V6-PLAN.json` `"rounds": 4`, batch 2). The loss is a PonderNet-style expected loss: survival × stop probability × (CE + ponder penalty × round), with full backprop through all 4 rounds (`sol_translator_grounding_v6.py:178-188`). The puzzle ruler is different. It trains on a random 1..16 rounds with gradient on the last ≤6 (`claude_fewex_net.py:154-161`) and reads up to 48 rounds.
- **Shown (lead sweep, verified there).** There is no augmentation, no voting, no verifier pass and no multiple starts anywhere.

## 2. What the evidence says the mechanism lacks

- **Shown (brief):** 86/128 had the right calculator setup but only 15/128 the right final answer. 71 made the right call and still got the final answer wrong. 38 picked the wrong operation.
- **Suggested.** Most of the loss happens *after* the right call. Three readings fit: (a) the core has the right number, but the 32-wide, 8-vector pooled prefix blurs it; (b) the core never writes the tool result into a place it keeps; (c) it is memorising the 32 practice problems. We cannot read the calculator code (it is on the Mac only), so how the tool result re-enters is **untested**.
- **Shown (cited, authors only).** In TRM, keeping two states (a running answer *y* and a scratch latent *z*) beat one or three states. Deep supervision with a detached carried state was the biggest HRM factor, and ACT halting added little (lead sweep §2, angle 1; TRM 2510.04871).
- **Shown (cited abstract).** Looping improves *knowledge manipulation*, not storage (~2 bits per weight either way) (Ouro 2510.25741). **Suggested:** that fits Ben's "skills first, facts later". In the skill phase, spend weights and compute on rounds and state, not on more experts. Experts mainly add storage. Sparse MoE also hurts on small data (MoE plan, citing ST-MoE and TRM).
- **Shown (cited abstract).** Not every looped step adds depth, and recursion can be "dead compute" (2511.16886). Huginn trains on a random depth with truncated backprop so it can think longer at test (2502.05171, as used in the Huginn plan). MoR gives each token its own number of rounds (2507.10524). Neither has been tested at 9M.

**Precondition for every test below (suggested).** No mechanism can win if the core memorises 32 problems. Every assistant-panel arm trains on the **same enlarged, checked TRAIN set** (Ben approved authoring one). It is scored on a **fresh 128-question panel**: written by an authoring subagent, checked by an independent checker, and sealed by hash before any run. The consumed panel is never reused.

## 3. Ranked mechanism changes (at most 5, each one change)

Ranked by (chance it helps critical thinking) × (how directly it hits the measured failure) × (does it keep paying as we scale rounds or width).

### 1. Draft-answer registers: a separate workspace stream read by the talker

- **What.** Add R = 8 learned register vectors (8 × 256 ≈ 2k weights). They are appended to the core state like notebook positions, using the existing neutral bias index `N.CLIP` that `begin_latent` already uses for appended positions. They run through the same blocks every round. The output prefix reads **only the 8 registers**, one register to one prefix vector, replacing the average-pool over question positions. Everything else stays the same.
- **Why it should help critical thinking.** It splits "what I currently think the answer is" (registers, TRM's *y*) from "the question and my working" (positions, TRM's *z*). The model then has a draft it can re-read, check and revise every round. It also gives the tool result one place to land and one way out to the talker, so it is not averaged with question tokens (suggested; TRM two-state ablation and ViT registers 2309.16588, authors). It scales cleanly: more rounds mean more revisions of the same draft, and more registers mean a bigger draft (untested).
- **Label.** Suggested (mechanism) / untested (here).
- **Cheapest test.** Two arms, 2 seeds each: baseline core vs core+registers. Same enlarged TRAIN set, same steps, same 4 rounds, same LM, same reader. Score on the fresh sealed 128-panel.
- **Fixed pass mark.** Right final answers at least **+12/128** over baseline in **both** seeds. +12 is about 2 SE at p ≈ 0.12. In addition, right-final answers among right-setup questions must rise by ≥ 10 points, and right-setup must not drop by more than 8/128.
- **Falsifier.** Final-answer gain ≤ +4 in both seeds. Or right-setup holds while right-final among right-setup is unchanged. Either means the drop is not caused by the state shape or the pooling, so look at the tool-return path itself.

### 2. Random-depth recurrence training with truncated backprop (Huginn/TRM recipe on the assistant path)

- **What.** Replace the fixed 4 rounds of full backprop with this: draw a total of 1..16 rounds per batch, run the early ones without gradient, and backprop through the last ≤4. This is the same recipe the puzzle ruler already uses (`claude_fewex_net.py:154-161`). Keep the PonderNet mass over the rounds that do get gradient.
- **Why.** A fixed 4 means the core has never learned to make use of round 5. With random depth, "think longer" becomes a dial at test, which is what makes a reasoner get better with compute (suggested: Huginn; Bansal et al. 2202.05826). It also lowers memory per step, so the same budget buys wider or longer training (suggested).
- **Label.** Suggested; untested on the assistant path.
- **Cheapest test.** One arm vs baseline, 2 seeds, same TRAIN set. Score the panel at 4, 8 and 16 rounds.
- **Pass mark.** 16-round right-final at least **+8/128** over the same net at 4 rounds, in both seeds. The 4-round score may be at most 5/128 below the baseline.
- **Falsifier.** 16 rounds ≤ 4 rounds in both seeds (dead compute, as in 2511.16886). Or the stop fires at round 1-2 on more than 80% of questions.

### 3. Latent hypothesis branching: several noisy starts plus agreement vote (training-free first)

- **What.** Start the state from K = 8 small random values instead of zeros, run each start, and take the plurality answer. Weights stay the same. Report how often the starts agree.
- **Why.** This is cheap "consider other hypotheses, then check they agree", which is self-consistency done inside the latent. Agreement can also become a stop signal that needs no label (suggested: lead sweep angle 3 and 4; path-independence 2211.09961, authors). It scales with test compute without new weights (suggested).
- **Label.** Untested here.
- **Cheapest test.** Puzzle ruler only, on saved practised-loop checkpoints and the 300 dev mazes. $0 on CPU, zero training. It can be added as columns to the queued per-round read (lead sweep test 2).
- **Pass mark.** The 8-start vote beats the single zero-start by **≥ +8 F_eq** on both seeds (the repo's noise bar).
- **Falsifier.** The starts agree on more than 95% of mazes (no diversity to vote over), or the vote gains < +2. Either way, branching needs training (noise during practice) before it can help, and that would be a separate change.

### 4. Process supervision of the operation choice (step-level credit inside the core)

- **What.** Add a small linear "plan head" on the pooled core state at every round. Train it to predict the correct calculator operation, with labels taken from the checked TRAIN set's known setups. It is an auxiliary loss only, and the tool interface is unchanged.
- **Why.** 38/128 picked the wrong operation. At the moment the core only learns about its choice through the final English answer, which is a weak signal routed through the frozen LM. Grading the intermediate step gives the core credit where the reasoning actually branches (suggested: Lightman et al. 2305.20050 shows process > outcome supervision, at large scale, authors).
- **Label.** Suggested at scale; untested at 9M.
- **Pass mark.** Wrong-operation count drops by **≥ 12/128** (from about 38) in both seeds, with no loss in right-final.
- **Falsifier.** Plan-head TRAIN accuracy above 95% while panel wrong-operation is unchanged (±4). That would be memorising, not a skill.

### 5. Keep MoE fixed during the skill phase; grow rounds and state, not experts

- **What.** A *holding* change. Freeze the expert count at 8, top-2, while changes 1 to 4 are tested. Add width or rounds first. Only grow experts once the TRAIN stream is large, following MoE plan step 2's big-data race.
- **Why.** Loops buy manipulation and experts buy storage (Ouro, shown abstract). MoE loses on small data (ST-MoE, TRM, shown per MoE plan). Ben's plan puts facts in later, which is when experts should pay off (suggested).
- **Label.** Suggested.
- **Test, pass mark and falsifier.** Already sealed as MoE plan step 2 (MoE-256 must beat the loop by ≥ 8 on held-out kinds in both seeds). I do not add a new one.

**Considered and not ranked.**
- Per-token adaptive depth (MoR) and fancier ACT: the HRM analysis found ACT worth little (lead sweep §2), and our stop already fails to fire on new mazes.
- Explicit backtracking or a critic pass: change 3 tests whether diversity exists before we build a critic on top of it.
- More scratchpad memory: the notebook already exists.
- Previous-state memory: already queued in the Huginn plan, idea 2.

## 4. Recommended first change

**Change 1, draft-answer registers.** It is the only change aimed at the largest measured loss (71 of 86 right calls lost before the final answer). It costs about 2k weights, makes one structural edit, and both rulers can carry it later. It also gives every later change (random depth, branching, a critic) a single draft to revise and to vote on.

Before training it, run one free read on the Mac's existing assistant checkpoints (report-only, $0). Fit a linear probe for the calculator result on (a) the core's final question-position states and (b) the 8 prefix vectors, using the right-call cases.
- If (a) ≫ (b): the pooled prefix is losing the number. Change 1 is squarely aimed; go.
- If both are low: the tool result never reaches the core. Fix the tool-return path first. That is a separate change, not a mechanism change.
- If both are high: the frozen LM is mis-reading a good prefix. Look at the talker before changing the core.

Seal those three readings, with the threshold "probe accuracy ≥ 0.8 vs ≤ 0.4", before running the probe.

## 5. What I could not verify

- How the calculator result re-enters the core (the code is on the Mac). The 128-panel numbers come from the brief, not a repo file.
- External numbers are from abstracts and search summaries only. Open the papers before any mark depends on them.
- Weight counts are my arithmetic from the code, not a printed count.

## Plain-language summary for Ben (a high-school senior)

1. Right now the reasoner has one "desk" where the question and its working are mixed together. The part that talks reads an *average* of that desk. So a number it worked out can get smudged on the way out (shown in the code; that this causes the errors is suggested).
2. In 71 of 128 fresh questions, the model asked the calculator the right thing and still gave the wrong final answer. That is the biggest leak.
3. First change: give the reasoner a small "answer notepad" of 8 slots. It writes its current best answer there and re-checks it every round, and the talker reads only the notepad. This is cheap, and tiny puzzle solvers like TRM do something similar (suggested).
4. It passes only if final answers go up by at least 12 of 128 on new questions in both runs. If they go up by 4 or fewer, the notepad wasn't the problem.
5. Next in line: train with a random number of thinking rounds so "think longer" actually helps; try several starting guesses and let them vote; grade the "which operation" step directly; and hold off on adding more experts until there is lots of training data.
6. None of this works if the model only memorises its 32 practice problems, so every test uses a bigger, checked practice set and a brand-new sealed quiz.

## Sources
- [Mixture-of-Recursions 2507.10524](https://arxiv.org/abs/2507.10524)
- [TRM 2510.04871](https://arxiv.org/pdf/2510.04871)
- [Latent reasoning / dead compute 2511.16886](https://arxiv.org/pdf/2511.16886)
- [Ouro 2510.25741](https://arxiv.org/abs/2510.25741)
- [Let's Verify Step by Step 2305.20050](https://arxiv.org/pdf/2305.20050)
- Huginn 2502.05171, ViT registers 2309.16588, Bansal 2202.05826 and path-independence 2211.09961, as cited in the repo research notes (not re-opened)
