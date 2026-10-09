# Sakana's Continuous Memory Machines vs our thinker (Fri Oct 9, ~1:40 PM ET)

Ben shared a DAIR.AI post at 1:32 PM ET 10-09. Paper: "Continuous Memory Machines", Regan et al., Sakana AI, arXiv 2610.07907 (read via
the arXiv HTML; the last ~2% of the page was not read). Labels: **shown** (paper or our code), **suggested**, **untested**. Nothing was run.
Follows `running-summary-2026-10-08.md`, `fast-slow-2026-10-08.md`, `important-links-2026-10-09.md`. Small card experiments only; no village model.

## 1. What CMM is (shown, paper)

- Built on the CTM (Continuous Thought Machine): a recurrent model that "thinks" for a fixed number of internal ticks.
- Two memories: short-term = the last M_S states (4-20 ticks); long-term = a persistent matrix of M_L learned slots (4-128), starting
  from learned values. Each tick, a small transformer (2-4 layers best) reads and rewrites both together; the short-term one is then dropped.
- No learned stop: fixed ticks (50 on Maze); the answer is read at the "most-certain" tick (lowest output entropy).
- Sizes: 60K to 10M parameters. Toy tasks only.

## 2. Results that matter for us (shown, paper; 3 seeds)

| Task | CMM | No long-term memory (CMM-STM) | Plain transformer | RMT | CTM |
|---|---|---|---|---|---|
| Few-shot regression, K=20 | 30.63 | 13.03 | 29.75 | 30.46 | 8.78 |
| Maze action / board % | 96.3 / 61.6 | 87.0 / 43.8 | 41.4 / 0.7 | did not train stably | 88.8 / 37.4 |
| Associative recall (loss) | <1e-3 | | 2.7e-4 (better) | | 3.2e-2 |
| ImageNet-100 | 89.7 | | 89.5 | | 89.4 |

- The long-term memory clearly helps the CTM (few-shot 13.0 to 30.6). But RMT, which carries memory slots like our thinker, gets 30.46,
  and a plain transformer 29.75. Versus designs with slots, the few-shot gain is about 0.2.
- Maze is a big win over a plain transformer, but board accuracy ranges 22.8 to 90.7 across its 3 seeds.
- Cost: on Copy-100, 2.2x the CTM's step time and 22,330 MiB peak memory vs 634.5 MiB (35x), more than BensPC's 16 GB. Maze: 127.5 h
  per seed on one H100.
- No ablation isolates the two-way read/write.

## 3. Compared with our thinker (shown, `ledger.py`, `tool_h1.py`)

| CMM part | Ours |
|---|---|
| Long-term slots, learned start, rewritten by a small transformer each tick | The thinker's notes: 8 control + N_REG vectors (44 in the caps-fixed build), learned start, rewritten each round by self-attention + reading the words and workspace. Close match. |
| Separate long-term and short-term stores | One store: the same notes do scratch work and keep things. The workspace keeps exact calculator results, protected. |
| Short-term window of the last 4-20 ticks | None: each round sees only the current notes. |
| Per-neuron private models (CTM backbone; swapping it for an LSTM hurt Maze and few-shot badly) | None. |
| Fixed ticks, answer at the most-certain tick | H1: learns to stop when its answer settles (1-32 rounds). Ours saves rounds; theirs doesn't. |

## 4. Verdict (suggested)

- Not for the big run. Our notes already are CMM's main piece; the paper's few-shot edge over slot designs is ~0.2; the memory cost is
  far beyond our PC.
- Worth keeping for later: (a) a separate protected notebook beside the scratch notes; (b) letting the thinker look back at its last few
  rounds. Both are learned, so they fit the rules.

## 5. Cheapest test, if Ben wants one (proposed, not run; my pick: wait)

- B2 at 3M vs B2 + a separate notebook of 16 slots (written and read by the same rounds, kept apart from the scratch notes), 2 seeds
  (200, 201), same data and steps, Mac or PC after G1. Cost: $0, free machine time only.
- Marks, fixed now: pass = fewshot_number_rule +3.0 on both seeds AND pooled-5 drop no worse than -1.0 on either seed. Proved wrong if
  fewshot_number_rule gains under +1.0 on both seeds. Anything else is mixed, report only.
