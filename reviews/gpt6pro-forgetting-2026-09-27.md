# GPT-6 Pro prompt: why the small puzzle reasoner forgets, and how it could keep learning (Thread manager, 2026-09-27T18:56:57Z)

Ben asked at 18:55 UTC for a prompt he can paste into GPT-6 Pro. Everything below the line is the prompt. Every number was checked against these files on main: artifacts/claude-rsn358e-20260926/, claude-rsn358e3-20260926/RESULTS.md, claude-rsn358e4-20260927/RESULTS.md, claude-rsn358e5-20260927/RESULTS.md, claude-rsn358e6-20260927/RESULTS.md, claude-rsn358e7-20260927/PASSMARKS.md, codex-autoroute-20260927/PASSMARKS.md, RESULTS.md and hard_replay/RESULTS.md, and scripts/claude_rsn358e_moe.py. Check the reply's factual claims against the code before acting on them.

---

# A small looping reasoner forgets old puzzle kinds when it learns new ones. Why, and what should I test next? (No code or file access needed.)

You are an expert in continual learning (catastrophic forgetting, replay, parameter isolation, growing networks) and in looped / weight-shared transformers. You have **no access** to my code, files or machine, so everything you need is below. Do not ask me to run anything before you answer; reason from what is here. If a fact you need is missing, say exactly what it is and how it would change your answer rather than guessing.

Mark every claim as **shown** (by the data below), **suggested**, or **untested**.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow (details at the bottom).

**Scope:** only the **small puzzle reasoner** described here (about 1.65 million weights, trained on CPU). My project has other parts: a 1-billion-parameter language model that reads and talks, small synthetic "card" experiments, and a simulated "village" world. Do not mix those in or borrow numbers from them.

## 1. What I want

The reasoner is meant to be the part of an assistant that keeps learning. During "sleep" (offline training between uses) it should learn a new kind of puzzle and keep the kinds it already knows, again and again over many sleeps. The net is allowed to grow. The final design must work out the puzzle kind by itself (no hand-given task labels). Hand-written rules are allowed only as disclosed temporary stand-ins.

The bar I care about: after several sleeps it keeps the old kinds nearly as well as when it first learned them, **and** it learns each new kind about as well as a normal net would. It should do that at no more total weights than a normal net it is compared with.

## 2. The network (in words)

- Each puzzle is a grid of cells; each cell is one token. The input for a cell is a token embedding plus a cell-position embedding plus a **puzzle-kind embedding** added to every cell. (The kind input is a disclosed stand-in. A separate test showed the looping net keeps its lead over a plain net without it, but every forgetting test below had it, except the two by the second agent in Table 4, which used a small learned front end instead.)
- A **looping transformer**: 2 blocks, width 256, 8 heads. Attention has learned row and column position biases. Each block has an MLP (256 -> 1024 -> 256) and LayerNorms. The same 2 blocks are applied again and again to a carried state ("rounds"). In training it runs 1-16 rounds, with gradient through only the last 1-6. At test time a learned stop head decides when to stop (at most 48 rounds). An output head predicts each cell's answer.
- About **1,646,750 weights** in the plain ("dense") version. fp32 on CPU, batch 64, AdamW, lr 1e-3, 100-step warm-up then cosine to 0, **a fresh optimizer at the start of each phase**.

## 3. The test protocol

Kinds are learned one after another. All training data is made fresh by code.

- **Phase A:** grids (Latin-square-style 4x4 and 5x5 with a symbol legend), 2,500 steps.
- **Phase B:** sums (addition, 1-4 digits), 2,500 steps.
- **Phase C:** mazes (5x5 and 7x7), 1,500 steps.

After each phase it is scored on dev sets of 200 puzzles each: grids5, grids6 (bigger than practised), sums4, sums6 (longer than practised), maze7. A score is puzzles fully right, out of 200. **T** = grids5 + sums4 + maze7 after phase C, out of 600. The dev sets were reused across these tests, so they are not held-out.

**Replay** means mixing batches of earlier kinds into later phases.
- "B replay": 250 of the 2,500 phase-B steps are grids batches (1 in 10). No replay in C.
- "Full replay": B replay, plus 75 grids and 75 sums batches among the 1,500 phase-C steps (1 in 20 each).

**The freeze-and-grow ("experts") layouts.** Each block's MLP is replaced by several experts with a learned top-1 router per cell. After each phase, the old experts, their router rows, the attention, the embeddings, the LayerNorms and the output head are **frozen**. New experts are added with zero-started router rows, and only they (plus their router rows) train.

## 4. Results

### Table 1: no replay at all (seeds 1 and 2)
- Dense: grids5 199 / 198 after A, then **0 / 0** after B.
- A same-size 4-expert version (nothing frozen): 0 / 0 after B.
- Freeze-and-grow at 1.64x the dense size ("moe-grow"): grids5 **40 / 70** after B; sums4 after B 139 / 124; maze7 after C 3 / 3.
- Diagnostic: the old experts' weights were byte-identical after B, and forcing old-only routing brought grids5 back to 187 / 188. **Shown:** the router, trained on sums only, stopped sending grids to the old experts.

### Table 2: B replay, 1.64x freeze-and-grow vs dense (seed 1 / seed 2)

| | moe-grow, no replay | moe-grow + B replay | dense + B replay |
|---|---|---|---|
| grids5 after A | 187 / 188 | 187 / 188 | 199 / 198 |
| grids5 after B | 40 / 70 | **191 / 188** | 184 / 172 |
| sums4 after B | 139 / 124 | **136 / 67** | **200 / 200** |
| sums6 after B | 83 / 68 | 94 / 32 | 194 / 196 |
| maze7 after C | 3 / 3 | 9 / 0 | 150 / 136 |
| grids5 after C (no replay in C) | 32 / 47 | 185 / 160 | 0 / 0 |
| trainable weights in B | 1,054,728 | 1,054,728 | 1,646,750 (all) |

An equal-size version (12 narrow experts per block, 4 opened per phase, 352,944 trainable weights per later phase) with B replay learned sums4 to only **0 / 59**.

### Table 3: equal total size, full replay, 6 seeds (seeds 3-8, means)

All four layouts have about 1.65M total weights.

| layout | grids5 after A | grids5 after C | sums4 after B | maze7 after C | T (of 600) |
|---|---|---|---|---|---|
| dense (all weights train) | 196.50 | 128.00 | 200.00 | 150.33 | **470.17** |
| frozen experts | 170.17 | **164.33** | 76.33 | 3.33 | 239.83 |
| frozen experts + "warm routing" | 170.17 | 161.50 | 84.50 | 5.67 | 251.83 |
| experts, shared attention + norms train again | 170.17 | **42.33** | 199.17 | 98.83 | 321.17 |

- Frozen experts: trainable weights in B and C were 352,944. The new experts received the new kind on only 3 of 6 seeds. Where they did receive it, they still learned little. T was lower than dense on 6 of 6 seeds.
- Warm routing: for 10% of new-kind batches, the code forced them to the new experts (a hand-given assignment, disclosed). The new experts then took the new kind on 6 of 6 seeds, and learning barely moved (sums4 84.50 vs 76.33).
- Shared layers train: the attention (qkv, output, row and column biases) and all LayerNorms train again in B and C, giving 882,640 trainable weights. New kinds are learned (sums 199.17, mazes 98.83), but the frozen grid experts **break**: grids5 after C falls to 42.33, below both other layouts on 6 of 6 seeds. It still trails dense on T on 6 of 6.

### Table 4: dense + full replay, replay scheduling (a second agent, Apple GPU, fp32, 6 seeds each)

Same net, same phases and steps. This agent used a small learned front end instead of the kind embedding. Every comparison is paired against its own locally rerun baseline.

| test | arm | grids5 after A / B / C | sums4 after B | maze7 after C | T |
|---|---|---|---|---|---|
| later replay (seeds 41-46) | baseline (250 grids in B; 75 grids + 75 sums in C) | - / - / 138.83 | 200.00 | 136.83 | 468.67 |
| | late: same 325 grid replay batches, 125 in B and 200 in C | - / - / 167.00 | 200.00 | 135.00 | 498.67 (wins 6 of 6) |
| targeted replay (seeds 61-66) | baseline (grid replay split between 4x4 and 5x5) | 197.00 / 178.00 / 143.67 | 200.00 | 138.00 | 475.50 |
| | targeted: all grid replay slots on 5x5 only | 197.17 / 189.83 / 155.83 | 200.00 | 136.17 | 484.33 (wins 3 of 6) |

Neither reached the pre-set bar of mean grids5 after C at least 180, with every seed at least 160.

## 5. What is being tested right now (please predict these; don't just re-propose them)

1. **Lateral connections** (2 seeds): the 1.64x moe-grow + B replay layout from Table 2. Each new expert also reads the sum of the frozen old experts' outputs, through a zero-started matrix, as in Progressive Neural Networks (Rusu et al. 2016). Old weights stay frozen. Pass = grids5 after B at least 150 and sums4 after B at least 150 on both seeds. Proved wrong = sums4 after B no better than 146 / 77. The size control is a dense net of the grown size (3,229,868 weights, all trainable).
2. **Grow the dense net wider each sleep** (queued; details not fixed yet): dense + replay, but at each new phase every layer gains new hidden units. The owner's literal idea is 1 new unit per layer per sleep, plus a larger version. Old weights are frozen and only the new units' weights train. The new units' outgoing weights start at zero, so the net starts identical.

## 6. Constraints

- Compute: CPU in a container at $0 (a 2-seed, 4-run test takes about 1.5-2 hours), or rented GPUs at up to $4 per job.
- One change per experiment, pass marks and a "proved wrong" result fixed before the run, at least 2 seeds (6 for a graded claim).
- Training data must be code-made. No LLM-written training data.
- No hand-given task labels in the final design.
- Size is judged on total weights against a dense net of the same size.

## 7. Questions

1. **Dense + replay forgetting.** With 1 grids batch in 10 during B, dense keeps most grids (Table 4: about 178-190 after B). With 1 in 20 during C it falls to about 139-156 by the end of C. Which explanation best fits: the replay ratio, the new kind's gradients dominating shared weights, the fresh optimizer each phase, something specific to looping (e.g. the carried state or stop head drifting), or something else? Give the cheapest experiment that tells the explanations apart.
2. **Freeze-and-grow.** Why do the frozen layouts learn new kinds so badly even when the routing works (warm routing)? And why does letting the shared attention train wreck the frozen experts? What does the literature say about these two failures? Consider Progressive Nets, PackNet, HAT, dynamically expandable networks, SupSup, adapter or LoRA-per-task, EWC/SI, LwF and distillation, dark experience replay, GEM/A-GEM, and generative replay. Which of these suit a looped, weight-shared net, and which don't?
3. **The two tests in section 5.** Give your chance that each passes, and why. For the grow-wider test, say what "1 unit per layer" can and cannot do at this size.
4. **Next experiments.** Rank the 3 best next experiments. Each should be one change against dense + full replay (the current best, T about 470). The target is mean grids5 after C at least 180 with every seed at least 160, while sums4 after B stays at least 195 and maze7 after C stays within 10 of the baseline. For each one, give the pass marks fixed in advance, the result that would prove it wrong, and its CPU cost in runs.
5. **Pitfalls.** Is anything in this setup likely to make the numbers misleading? Examples: reused dev sets, mazes never replayed, different phase lengths, 2-seed tests.

## 8. Plain-language summary for me

End with 5 to 8 short sentences with no jargon. Say what is going wrong, whether freezing-and-growing is worth continuing, and the single first thing to try. Use everyday comparisons. Keep "shown", "suggested" and "untested" visible in the summary too.
