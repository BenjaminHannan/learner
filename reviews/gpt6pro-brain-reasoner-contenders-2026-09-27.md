# GPT-6 Pro prompt: brain-inspired contenders for the reasoner (Thread manager, 2026-09-27T19:46:16Z)

Ben asked at 19:45 UTC for a prompt he can paste into GPT-6 Pro to come up with brain-inspired reasoner designs. Everything below the line is the prompt. The numbers come from TM-verified results on main: rsn-358i3 (recount 23dbe806b), rsn-358u (56a1d3a74), rsn-358e3/e4/e5/e6 RESULTS.md, and scripts/claude_rsn358e_moe.py. Check the reply's factual claims against the code and papers before acting on them.

---

# Invent brain-inspired "reasoner" networks that could beat a looped transformer on puzzles, learning, and memory (no code or file access needed)

You are an expert in computational neuroscience and in machine-learning architectures for reasoning: recurrent and iterative inference, energy-based and predictive-coding models, cortical microcircuits, fast weights, and complementary learning systems. You have **no access** to my code, files or machine. Everything you need is below. Do not ask me to run anything before you answer. If a fact you need is missing, say exactly what it is and how it would change your answer.

Mark every claim as **shown** (by published results or the data below), **suggested**, or **untested**. When you say an idea is new, say what the closest published work is and what exactly differs.

I am a high-school senior building this with AI help. Please end with a plain-language summary I can follow (details at the bottom).

**Scope:** only the **reasoner**, a small network trained from scratch on code-made puzzles. My project has other parts: a reader and a talker that are small off-the-shelf language models, small synthetic "card" experiments, and a simulated "village" world. Do not mix those in or borrow numbers from them.

## 1. What I'm building and why

The project is an assistant meant to copy the brain's strengths and improve on them where it can. The **reasoner is the model**: a reader turns a chat message into a puzzle, the reasoner solves it, and a talker puts the answer into words. The reader and talker are standard language models, and that's fine (they are eyes and a mouth). **The reasoner is where the new idea must live.** Right now it is a looped transformer, which is published work (universal transformers, tiny recursive models), so it is not novel. I want contenders that are genuinely brain-inspired and new, and that could beat it.

What I care about, in order:
1. **Learning a new kind of puzzle from few examples**, compared with a fresh net and a plain net of the same size. This is my main measure.
2. **Keeping old kinds while it learns new ones during "sleep"** (offline training between uses). The net may grow.
3. **Solving bigger puzzles than it practised on**, by thinking longer.
4. It **decides for itself when to stop thinking** (a learned stop, with variable depth). It is never told which kind of puzzle it is seeing, and it runs no hand-written rules.
5. Its size is judged by total weights, against same-size rivals.

## 2. The current reasoner (the one to beat)

- Each puzzle is a grid of cells; each cell is one token. Input = token embedding + cell-position embedding.
- A **looped transformer**: 2 blocks. Each block is attention (with learned row and column position biases) plus an MLP (d -> 4d -> d), with LayerNorms. The same 2 blocks are applied again and again to a carried state ("rounds"). In training it runs 1-16 rounds, with gradient through the last 1-6. At test time a learned stop head ends the thinking (at most 48 rounds). An output head predicts every cell's answer at once.
- Main size: width 512, about 6.4M weights. A smaller version (width 256, about 1.65M weights) is used for cheap CPU tests.
- Training: AdamW, lr 1e-3, warm-up then cosine, code-made puzzles only.

## 3. The puzzles

- **Grids:** Latin-square-style grids with a symbol legend. Practised at 4x4 and 5x5; tested at 5x5, 6x6 and 7x7.
- **Sums:** multi-digit addition, laid out as cells. Practised at short lengths (1-4 digits in the small version); tested at 6, 8, 10 and 12 digits, all longer than practised.
- **Mazes:** 5x5 and 7x7 practised; 7x7 tested (9x9 and 11x11 in a transfer test).
- **Number puzzles** (reach a target from a few numbers, like the 24 game).
- Scores are puzzles fully right, out of 200 or 300.

## 4. Results so far

### 4a. Loop vs a plain (non-looped) transformer of the same size
Main size, about 6.4M weights each: loop = 2 blocks x width 512, looped; plain = 8 blocks x width 256, one pass. Same data and steps, 4 seeds. Numbers are the mean of loop minus plain, out of 300. Practised sizes are level.

| test | loop - plain (told the kind) | loop - plain (not told the kind) |
|---|---|---|
| sums 6 digits | +124.00 | +144.50 |
| sums 8 digits | +185.75 | +220.25 |
| grids 6x6 | +52.00 | +41.50 |
| grids 7x7 | +67.75 | +36.75 |
| number puzzles | both nets 0-5 of 300 | both nets 0-3 of 300 |

So looping helps a lot on bigger puzzles (shown, small scale, 4 seeds). Neither net learns the number puzzles at all.

### 4b. Learning kinds one after another (small version, 1.65M weights)
Grids, then sums, then mazes, each learned in turn. T = grids5 + sums4 + maze7 after the last phase, out of 600. Six seeds, equal total size, with old kinds replayed in later phases.
- **Plain dense loop + replay:** T 470.17. It learns every new kind (sums 200, mazes 150) and keeps grids at 128 of about 197.
- **Freeze old parts, add new "expert" parts:** T 239.83. It keeps grids best (164) but barely learns new kinds (sums 76, mazes 3).
- **Same, with the shared layers still learning:** T 321.17. It learns new kinds (sums 199, mazes 99) but the frozen experts break (grids 42).
- With no replay at all, the dense net forgets grids completely (199 -> 0).
- Running now: new experts that can also read the frozen old ones (lateral connections); a dense net that grows new neurons each sleep; an 8-layer loop.

### 4c. Few-example learning (not yet measured reliably)
The one early few-example test was hit by a training bug that has since been fixed, so there is no trustworthy result yet. A new few-example maze test is running.

### 4d. Designs already queued for a first race (don't just re-propose them; improve on them or beat them)
Same size as the small loop, same puzzles:
- predictive coding / energy settling;
- local-only recurrent message passing between neighbouring cells (neural-cellular-automaton style);
- fast weights / Hebbian working memory.

## 5. Constraints

- Compute: CPU at $0 (a 1.65M-weight run takes about 1.5 h on one thread), or rented GPUs at up to $4 per job.
- PyTorch; weights trained from scratch; code-made training data only.
- One change per experiment. Pass marks and a "proved wrong" result are fixed before the run, with at least 2 seeds.
- No hand-written rules or task labels in the final design. A disclosed stand-in is allowed only as temporary scaffolding.

## 6. What I want from you

1. **8-10 contender designs, ranked.** For each one give:
   - the brain mechanism it borrows, with the neuroscience evidence labelled shown / suggested;
   - how it works, in plain words and then precisely (equations or short PyTorch-style pseudocode);
   - how it decides when to stop thinking;
   - why it might beat the looped transformer on each of the 5 goals in section 1, and where it will probably lose;
   - the closest published work, and what exactly is new;
   - how to build it at about 1.65M and about 6.4M weights so it fits the constraints.
2. **The top 3 for a first race**, each as one sealed test against the looped transformer at the same size. Give the pass marks, the result that would prove it wrong, and the cost in CPU runs. Prefer designs that target my main measure (few examples) and forgetting, not just bigger puzzles.
3. **Honest check:** which ideas are really a transformer in disguise, and which would fail at this tiny scale, and why.

## 7. Plain-language summary for me

End with 6 to 10 short sentences with no jargon. Say which 3 designs you'd try first, what brain idea each copies, and what result would tell me it's worth keeping. Use everyday comparisons. Keep "shown", "suggested" and "untested" visible in the summary too.
