# Sleep ideas, round 2: getting the reasoner to learn rules (2026-09-25)

Read-only research. I checked the claims about this repo against `scripts/claude_rsn294_core.py` (the LoopThinker model, its output heads and its puzzle generator), `scripts/claude_rsn294_run.py`, `scripts/claude_rsn296_gen.py`, `design/v3/30-modes/353-loop-no-step-embedding.md`, `design/v3/30-modes/360-sleep-plan.md` and `design/v3/30-modes/sleep-research-2026-09-24.md`. Labels: SHOWN = a paper's result, SUGGESTED = argued, UNTESTED = my idea.

**Plain summary for Ben:** Sleep has one resource the daytime doesn't: the exact code solver can show every step of every practice puzzle for free. The best ideas below use those steps to teach the reasoner "one step per thinking pass, then hold still", and use one-change twin puzzles to punish shortcuts. Each idea is tested by training on short chains only and scoring on longer ones.

**Repo facts that shape these ideas (checked):**
- The loop reasoner only answers from its final pass.
- The "support rows" target (`sup`) is a set of rows with no order, so nothing tells the model which hop to do on which pass.
- The number of passes is random, 2 to 12, no matter how many hops the question has.
- The generator already includes one kind of broken chain (30% of "missing" items).
- Swapping in fresh names for people, relations and values every episode (half of MLC) is already done (rsn-294).

---

## Card experiments (30M loop reasoner only)

### 1. Progressive loss with input recall: extra passes shouldn't hurt
- **What:** Run a random number of passes with no gradient, then a few more passes with gradient, and apply the loss only at the end. The block can't count passes, so it has to learn a step it can repeat safely. The existing `inject` of the input on every pass already plays the "recall" role.
- **Evidence:**
  - Bansal et al., NeurIPS 2022 (arXiv 2202.05826), SHOWN: recurrent networks trained this way solve much larger prefix-sum, maze and chess problems than they were trained on, and stop getting worse as passes are added ("overthinking").
  - Kuo et al. 2026 (arXiv 2606.29983), SHOWN: looped transformers can contain a computation that generalizes, but training often fails to find it. A random loop count breaks the false link between input length and loop count and makes out-of-range results stable. They also train a learned stochastic stop with RL, which is relevant to Ben's thinking-stop token.
- **Fit:** No labels needed, same compute as 353, roughly $2 like 296. It is the cheapest direct attack on "extra passes don't help yet". It depends on 353's loop training at all.
- **First experiment:** 353 loop plus progressive loss, against 353 as the twin.
  - Pass: blind 2-step score at 20 passes ≥ score at 12 passes minus 1/30. Blind 2-step ≥ twin. 0 checked inventions. ≤ $4.
  - Proved wrong if: accuracy falls ≥ 5 points from 12 to 20 passes, as it may for the twin.
- **Could fool us:** Stable but wrong. The model could reach a fixed point on a shortcut. So stability can only count alongside the accuracy marks.

### 2. Sleep writes step-by-step traces: one hop per pass, then hold
- **What:** The exact solver already walks the chain. Sleep saves which row each hop uses, and trains the existing row-pointer head at every pass: pass t points at the row for hop min(t, k), where k is the question's hop count. The answer is supervised at every pass from k on, so extra passes must leave it unchanged. The thinking-stop label is the first pass where the chain is finished.
- **Evidence:**
  - Neural algorithmic reasoning trains on intermediate "hints" (CLRS, arXiv 2205.15659; Ibarz et al., arXiv 2209.11142). SHOWN that hints help on some tasks and not others.
  - Looped transformers whose loop count grows with problem size generalize to longer inputs (Fan et al., arXiv 2409.15647, SHOWN).
  - Recurrent networks trained on easy instances solve harder ones by running more passes (Schwarzschild et al., arXiv 2106.04537, SHOWN).
  - The "hold" part is my way of avoiding the loop-count link that Kuo et al. warn about (UNTESTED).
- **Fit:** Only a loss change. The heads run on each pass, and the labels come free from the solver, so no model makes any data. This also gives the thinking-stop token a meaning (SUGGESTED).
- **First experiment:** Different from the planned C1 ladder, because it trains on **1-2 hops only**.
  - Twin: the same model and data without the per-pass loss.
  - Panel: fresh blind items at 3, 4 and 5 hops, 30 each, made after the recipe is frozen.
  - Pass: 3-step ≥ 15/30 and 4-step ≥ 10/30. 2-step ≥ 27/30. The learned stop pass rises with hop count on 5-hop items (Spearman ≥ 0.5).
  - Proved wrong if: pointer accuracy on practice hops is ≥ 95% while blind 3-step is ≤ 5/30.
- **Could fool us:** The model might just count the relation slots in the question to guess k instead of following the chain. Check with a panel where a hop's row is missing (the right answer is UNKNOWN). Traces must never be written into the notebook. They are practice-only labels.

### 3. Minimal-pair twins (counterfactual practice)
- **What:** Every practice episode comes with 2-4 twins made by code. Each twin changes one row:
  - delete the hop-j row, so the answer becomes UNKNOWN;
  - change the hop-j value, so the answer changes;
  - add a near-miss row (same relation, different person), so the answer stays the same;
  - reorder the rows or the time stamps, so the answer stays the same.

  The twins train in the same batch. A shortcut gives the same answer across the pair and loses reward on one of them.
- **Evidence:**
  - Kaushik et al., ICLR 2020 (arXiv 1909.12434), SHOWN: counterfactually edited data made models less reliant on spurious cues and more robust out of domain.
  - Huang et al. 2020 (arXiv 2010.04762), SHOWN: for NLI it did no better than the same amount of ordinary data. The evidence is mixed.
  - Contrast sets expose large drops on minimal edits (Gardner et al., arXiv 2004.02709, SHOWN).
  - Reordering premises hurts LLMs (Chen et al., arXiv 2402.08939, SHOWN).
- **Fit:** The generator and `solve()` already exist. This puts twins at every hop depth, not only the existing broken 2-step chain (UNTESTED).
- **First experiment:** Same data size as the twin, which gets unpaired extra episodes.
  - Pass: false-answer rate on blind missing-hop items ≤ half the twin's. Blind "flip consistency" ≥ twin + 15 points; this counts both answers of a pair right, on 2-hop pairs made with edit types never practised. Blind 2-step not below the twin.
  - Proved wrong if: pair accuracy on practice is ≥ 95% but blind flip consistency is within 5 points of the twin.
- **Could fool us:** Twins made by the same code share its quirks, which is practice shaped to our own style. Keep at least one edit type out of practice, only for the panel.

### 4. DreamCoder-style dreams over question operators (compositional recombination)
- **What:** Treat each solved puzzle as a small program: hop, then count, who, yes/no, compare, or before/after (the 7 kinds). A Stitch-like step finds sub-programs that recur in wins and practice. Dreams are new compositions sampled from that library, answered by the solver, and trained into the reasoner.
- **Evidence:**
  - DreamCoder (arXiv 2006.08381, PLDI 2021), SHOWN: ablations indicate both the abstraction step and the dreaming step matter.
  - Stitch (arXiv 2211.16605) makes abstraction search far faster, SHOWN.
  - LILO (arXiv 2310.19791) adds language names for the abstractions, SHOWN.
  - Against: learned libraries are rarely reused, and the gains came from self-correction instead (Berlot-Attwell et al., arXiv 2410.20274, SHOWN).
  - MLC (Lake & Baroni, Nature 2023) generalizes systematically but reportedly not to longer sequences (SUGGESTED, from later reviews). So this targets new combinations, not longer chains.
- **Fit:** The 30M net can't call library functions, so the library only shapes what it practises (UNTESTED). Its real payoff is in the village model, where creative wins become programs.
- **First experiment:** Hold out 2 operator pairs from all practice (for example count after a hop, and yes/no after 2 hops; extend the question frame if needed).
  - Pass: held-out pairs ≥ 70% of the accuracy on practised pairs.
  - Proved wrong if: held-out pairs < 30%.
- **Could fool us:** The dream mix drifting toward the panel's pairs. Freeze the held-out list before building the generator.

### Low priority: grokking and weight decay
Grokking is a finite-data effect (Power et al., arXiv 2201.02177). This training makes fresh data every step. In Wang et al. (arXiv 2405.15071, SHOWN), out-of-distribution composition stayed at zero even after grokking, though that was with facts stored in the weights. Don't spend money on "train longer with high weight decay" to get longer chains. Just log blind-dev curves in the runs above to catch any late rise, which costs nothing.

## Village / agent model (separate)
- Solution steps in wins should be saved as solver-checkable programs (for idea 4) and as traces (for idea 2). They train the reasoner only, under the 40% cap for model-made data.
- Sleep's self-check should add the flip-consistency test (idea 3) as a gate that catches shortcuts: a night is rejected if flip consistency drops.

**Suggested order:** 1, then 2, then 3, one change each. Idea 2's per-pass targets should be registered as the thinking-stop token's supervision before any RL on the stop token.

Sources: [Bansal 2202.05826](https://arxiv.org/abs/2202.05826), [Kuo 2606.29983](https://arxiv.org/html/2606.29983v1), [Berlot-Attwell 2410.20274](https://arxiv.org/abs/2410.20274), [MLC productivity limits (review)](https://arxiv.org/html/2509.20074)