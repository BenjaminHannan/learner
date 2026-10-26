# Practice-1: let the model practise puzzles with tools, then sleep on its tries

Pre-registered 2026-10-25 (before any run). Requested by Ben (21:28Z, 21:29Z): give the model a harness with search, a
code runner and a picture tool, let it attack lots of puzzles found online, sleep on its tries, and test it before and
after on 100 diverse puzzles written by Claude Sonnet.

## Model and harness
- K2-Horizon-3.7B (small tier), fp16 on a Kaggle T4, thinking off, HF generate (code reused from sleep2/askonce).
- Tools, one call per turn, at most 8 turns per puzzle, then the last answer counts:
  - `python(code)`: runs code in a subprocess, 10 s, no network, output cut to 2,000 chars.
  - `search(query)`: offline search over a fixed reference library (Python docs for builtins, math, itertools,
    collections, re, fractions, and Wikipedia summaries of ~150 puzzle/math topics). No puzzle sites, no answer sites,
    no ARC or GitHub pages, so nothing can leak an answer. Same library in every arm.
  - `look(grid)`: K2 has no vision, so the picture tool turns a grid into a description: size, colour counts,
    connected objects with their boxes, symmetries. (A real image tool waits for a vision backbone.)
  - `answer(text)`: final answer.
- Grading is automatic and exact: integers, short strings and grids are normalised and compared to the stored answer.

## Puzzles (three separate sets, no overlap, checked by hash and by near-duplicate text)
- Practice pool, about 300 (the model may try these as often as it likes):
  - ARC-AGI-1 public TRAINING tasks with small grids (from github.com/fchollet/ARC-AGI);
  - puzzles made by code with known answers (logic grids, cryptarithms, sequences, mazes, counting);
  - a separate pool of Sonnet-written puzzles from a different batch and seed than the test set.
  (Project Euler was planned but projecteuler.net is blocked from our machines.)
- SEALED TEST, 100 puzzles (Ben's test): written by Claude Sonnet 5.5 through the Message Batches API, spread over
  kinds (grid/ARC-style, number, word, logic, sequence, cipher, ASCII picture). Each comes with a Python reference
  solver; a puzzle is kept only if the solver's output equals the stated answer and the answer is unique and short.
  The kind of each puzzle is recorded. Frozen with a sha256 before any model sees it; never used in practice.
- Sibling test, 60: held-out ARC-AGI-1 training tasks and code-made puzzles not in the practice pool
  (same kinds as practice), to tell "got better at practised kinds" from "got better at puzzles".

## Day and night
- Day: every practice puzzle, 2 tries at temperature 0.7 with the harness.
- Night: a fresh LoRA (r16, attention + MLP) on the base model, trained on all lessons gathered so far
  (expert iteration). Fixed size every night: 256 SFT examples x 2 epochs plus up to 64 DPO pairs (beta 0.1,
  weight 0.2), same optimizer steps in every arm. No lone negatives this time (Dopamine-1 lesson: penalising failed
  tool tries taught the model to stop using tools).
- Three day/night rounds (more self-practice nights was the only lever that helped in the multistep work).

## Arms (one change between them)
- A0 no practice: the base model. Measured twice (once per lane, different sampling seeds) to see the noise.
- P practice + sleep with the checker: SFT on solved tries, DPO pairs (solved try, failed try) on the same puzzle.
- C equal-compute control: same days, same night size, same losses and steps, but the checker is removed:
  SFT examples are drawn from all tries and DPO pairs are random (chosen/rejected picked without looking at
  the result). This tests whether learning from checked results matters, not just more puzzle training.

## Pass marks (fixed now). Test = the sealed 100, 2 tries each, score = mean per puzzle; paired sign-flip test over puzzles.
- T1 practice + sleep works: P (after night 3) >= A0 + 8 points and p < 0.05.
- T2 the checker matters: P >= C + 5 points and p < 0.05. A gap of 5+ with p >= 0.05 is "suggested", not shown.
- T3 practised kinds (label): sibling test P >= A0 + 8.
- T4 no harm: ARC-Easy 200 within 2 points of A0, and tool calls per puzzle >= half of A0's.
- Wrong if: P <= A0 + 2 on the sealed test after three nights, or P < C.
- Sanity: the two A0 runs should agree within 6 points; a bigger gap is reported as a noise warning.
- Reported per night (P1, P2, P3 on the sealed test) and per puzzle kind; kinds are descriptive only.

## Not claimed
One training seed. Small test (100 puzzles can only show gains of about 8+ points). Fixing failed tries with a
Sonnet critique (as in Skill-Sleep 1) is left out because Kaggle jobs cannot hold the API key; it is the next step.
Live web search is left out because answers to online puzzles are one search away.

## Compute
Free first: one Kaggle session with two T4s (lane 0 = P chain, lane 1 = C chain; both measure A0 first).
A timing pilot sets how many practice puzzles fit before the 11 h cut; the pool is shrunk for both arms equally.
Claude calls (test and pool writing) go through the Message Batches API.

## Addendum 1 (2026-10-25 22:40Z, before any GPU run; pass marks unchanged)
- Night size in code: 256 SFT x 2 epochs + 64 pairs packed into 32 optimizer steps per night (both arms). The pilot may
  raise steps for both arms equally if time allows. P has SFT on its wins alongside DPO, which acts as the NLL term that
  Iterative RPO (arXiv 2404.19733) found keeps the chosen answer from being pushed down.
- Pairs: both lanes always get 64 pairs; if P has fewer candidates it repeats them (it has 0 only if no puzzle has one
  solved and one failed try). Tries over 4,096 tokens are never lessons in either arm. The adapter is not merged.
- Tokenizer check: K2 splits space-separated digits one per token, but merges compact digit runs ("00000" -> "000","00").
  The practice ARC prompts use spaces. Some sealed-test grid puzzles use compact rows; they are left as written (same for
  every arm; the grader ignores spaces). Next version: one digit per token everywhere.
- Research while waiting (Haiku, search-level, unverified): ARC winners multiply data with 8 rotations/flips + colour
  swaps and keep answers that agree across views (arXiv 2505.07859); SOAR self-trains on its own verified search traces.
  Not added here (one change at a time); candidates for Practice-2.

## Addendum 2 (2026-10-26 ~01:30Z, after a failed timing pilot, before any result; pass marks unchanged)
- Pilot 1 (Kaggle T4, HF generate) hit its 1 h cap with no numbers: replies ran to 768 tokens (no stop at the end of a
  tool call) and generate kept OOMing at batch 12. Fixes, same for every arm: each reply stops at `</input>`; caps are
  now 512 new tokens per turn, 6 turns, 4,096 context; sticky batch size; vLLM backend (prefix cache, LoRA served
  without merging) with automatic fallback to HF.
- Evals run at A0, after night 1 and after night 3 (pass marks use night 3, as before). Sibling set: 1 try per puzzle.

## Addendum 3 (2026-10-26 ~02:00Z, Ben 01:30Z: run it on his Mac with real internet; before any result)
Practice-1M is the same design on the M3 Pro, with these differences (same in every arm; pass marks unchanged):
- Model K2-3.7B 4-bit through mlx_lm.server; nights are QLoRA on the 4-bit base (custom MLX loop, loss on assistant
  turns only, SFT + DPO as above), size 128 SFT x 1 + 32 pairs, 32 steps, lessons capped at 2,048 tokens (memory
  limit while Ben's assistant is resident).
- Tools add live `search` (DuckDuckGo) and `fetch` (web page text) in practice AND in the test evals, so A0, P and C
  have the same tools. Every result and page is blocked if it shares a 12-word run with a sealed test puzzle, comes
  from an answer/solution site (ARC repos, Kaggle, Hugging Face, Project Euler solution sites), or shows a practice
  puzzle's answer next to its title. All web calls are logged.
- Project Euler 1-100 joins the practice pool (answers only in the grader). Practice subset 120 puzzles.
- Day 1 tries are shared by P and C (both are the base model then). No ARC-Easy on the Mac (harm check = tool use).
- The Kaggle run stays as a second, offline-search replication.

## Addendum 4 (2026-10-26 01:55Z, Ben: results by 11:00Z; before any result)
To fit about 8 h on the M3: practice subset 80 puzzles x 2 tries, TWO day/night rounds (not three; self-training
papers report most of the gain within about 2 rounds), test evals only at A0 and after night 2 (test100 x 2 tries,
first 30 sibling puzzles x 1), day 1 shared by P and C. Pass marks are unchanged but read at night 2: T1 P2 >= A0 + 8
(p < 0.05), T2 P2 >= C2 + 5. If the Kaggle offline run (3 nights) finishes, it is reported alongside.

## Addendum 5 (2026-10-26 02:00Z, Ben: parallelise; before any result)
P and C run as two side-by-side processes on the M3 (own server, port and output dir, 6 streams each). Day 1 is no longer
shared: each arm runs its own base-model day 1 and its own A0 test. The two A0 scores give the noise estimate; T1 compares
P2 with the mean of both A0 runs (per puzzle), T2 compares P2 with C2.

## Addendum 6 (2026-10-26 ~02:40Z, before any result was used)
First Mac A0 tries: format parsed fine, but K2 (thinking off) answered at once with about 60 tokens and got 1 of 35
right, a floor where neither arm could show anything. Restarted all runs with one prompt change for every arm: think
step by step in plain text before the single tool call, and do not guess. The python sandbox limits are best-effort
(macOS rejects RLIMIT_AS, which broke every python call on the Mac). The first 35 tries are discarded.
