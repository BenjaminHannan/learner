# Sealed card: ShinkaEvolve trial, card write rule for keeping the person

Sealed 2026-10-20 (Stage 0), before any evolve run. Do not edit after the GO. Any later change goes in a dated "Amendments" section at the bottom, with the reason.

## 1. Task

**Mechanism evolved:** the card write rule of PremonitionMini. This is the module that turns one line's reader states into one memory card, a retrieval key plus a value. In the model it is `CardWriter` in `premonition/model.py`. Nothing under `premonition/` is touched.

**Why this one.** It is where "the value is kept but the person is lost" happens:
- answer-only training puts 0.979 of the single pool on the value token (`premonition/card_pools.py`);
- the person is readable from the cards in only 116/2048 cases (`design/research/2026-09-18-decisions-log.md`);
- answers follow the value word, not the card (`reviews/opus-milestone-03-probe-binding.md`).

The other candidate mechanisms were ruled out:
- Read: it depends on what the write puts in the key.
- Halting: it has no link to binding.
- Eviction: it only matters when more than 16 cards are fetched.
- Consolidation: it does not exist in this model.
- The `Think.bind` slots: they are measured as unused.

**The toy (`task/toy.py`, CPU, about 2–3 minutes for 3 seeds, 1 thread each).**
- A visit has 8 lines, each stating one fact (person, relation, value). The 3 content tokens sit at random positions among 7 filler tokens.
- Each visit has 4 people and 4 relations.
- The asked card always has decoys: at least one card for the same person with another relation, and at least one for the same relation with another person.
- A frozen random "reader" mixes neighbouring tokens weakly, so the person signal at the value token is weak.
- The candidate writer makes one card per line.
- A fixed question encoder turns "person relation" into a query. Cards are scored by κ·cos(query, key). The soft-read value is decoded into a value guess.
- Writer, query encoder and decoder are trained jointly from scratch with **answer-only** cross-entropy for 700 steps.

**Score.** The mean of held-out answer accuracy on **familiar names** and on **novel names**. Novel names are 8 entity tokens never seen in training. Each is measured on 1024 visits, and the score is averaged over the seeds.

**Validity check of the toy (shown, table in section 4).** On the toy, the PremonitionMini baseline reproduces the project's failure. On novel names:
- it picks the right card 54% of the time;
- 45% of all novel-name questions go to the same relation of another person;
- errors to another relation of the same person are rare.

The "address told" oracle reaches 0.97.

**What the toy is not.** It is a synthetic stand-in. The reader is frozen and random rather than trained, retrieval is soft rather than hard top-4, and there are no think loops. A winner here is a candidate for PremonitionMini, not a result about it (untested there).

## 2. Seed program (baseline)

`task/initial.py`: PremonitionMini's writer, re-implemented on the toy interface.
- One `Linear(d,1)` softmax pool over the line gives p.
- key = W_k p; value = W_v p.
- 1,617 parameters at d=32, dk=16.

Interface (fixed): `CardWriter(d, dk)`, with `forward(states [B,C,L,d], mask [B,C,L]) -> keys [B,C,dk], values [B,C,d]`. At most 20,000 trainable parameters.

Sandbox, two layers:
- **Process isolation** (`task/worker.py`, `toy.IsolatedWriter`). This is the real boundary.
  - The writer runs in its own child process, which receives reader states and nothing else: no token ids, facts, questions or answers.
  - The child sends back keys and values as raw bytes in a fixed format. The parent never unpickles child data, and inputs go over as copies, not shared memory.
  - The child receives the gradient of the parent's loss and steps its own optimizer.
  - On every call the parent shuffles the B×C lines across visits with a secret permutation, and un-shuffles the cards afterwards. A writer that mixes lines therefore mixes unrelated ones.
    - The permutation is seeded from a salt file that is not committed, plus the run seed, so runs can be reproduced.
    - The noise table in section 4 was measured with fresh random shuffles. That can only add variation: the baseline's seed-100 score is identical (0.478) under both.
  - The parent keeps the frozen reader, the answerer, the loss, the metrics and the checks.
  - API keys and tokens are stripped from the child's environment. The child dies with its parent.
  - Each seed has a 150 s limit, from writer start-up to the end of eval, transfers included. The training data is generated before the clock starts.
  - The parent's behavioural checks run on both eval splits, at the eval batch size:
    - f(x1), f(x2), f(x1) must give the same f(x1) twice (no state kept between calls; this also catches mixing, because the shuffle differs between calls);
    - changing 16 random lines must leave every other card unchanged;
    - outputs must be finite and have the right shapes.
  - Every number the writer stores counts against the 20,000 cap. It is counted after `__init__` and again after training, using torch's own methods.
    - A tensor counts its whole storage, so a small view of a big tensor counts big.
    - Also counted: parameters, buffers, containers (dict keys too), helper objects, class attributes along the MRO, method attributes, defaults and closures, the `.grad` of non-parameters, Python numbers (big ints by size), and the candidate module's namespace.
    - State nested too deeply to count is rejected.
    - The child does the counting.
- **Static check** (`task/evaluate.py`, first line of defence). Applied on the syntax tree:
  - only imports, definitions and literal constants at top level;
  - imports limited to math, torch, torch.nn and torch.nn.functional;
  - an allow-list for every `torch.`/`nn.`/`F.` path, with no module used as a value;
  - no attribute assignment on the file's classes or functions or on torch modules (use `self.x = ...`);
  - no `_`-names (except `__init__`), no getattr/type/exec/open, no generators and no match statements.
- `confirm.py` applies both layers.
- Finalists' code is also read by hand before confirmation.
- Residual risk (stated, not fixed): the child is not OS-confined (same user, files and network), and the data seeds are public. A candidate that got past the static check could read the harness from disk and replay the data. The static check and the hand-reading are the defence against that.

## 3. Scorer and seeds

- `task/evaluate.py` gives `combined_score` = the toy score averaged over **evolution seeds 0, 1, 2**.
- It also returns text feedback (per-split accuracy, pick rate and error types).
- It also returns a behaviour descriptor: the share of key movement and value movement caused by swapping the person, relation, value or filler token (8 numbers, with no accuracies).
- Noise seeds: **100–104**, used only for section 4.
- **Fresh confirmation seeds: 1001 and 1002.** They are never used before `confirm.py`.
  - Disclosure: a plumbing test of `confirm.py`, run before the GO, already ran the **baseline and the multi-head reference** on these seeds. Results: baseline 0.411 and 0.471; multi-head pool 0.751 and 0.741. No evolved program has seen these seeds, and nothing is selected on them. The baseline's fresh-seed scores are low next to its noise-seed mean (0.497), which makes the BETTER mark slightly easier to reach. It is reported here so the reader can weigh that.

## 4. Measured seed noise (shown; `results/noise/SUMMARY.md`, seeds 100–104)

| writer (all known) | score mean | sd | range | acc novel | person-lost errors (novel) |
|---|---|---|---|---|---|
| **baseline single pool (seed)** | **0.497** | **0.020** | 0.046 | 0.388 | 0.448 |
| mean pool | 0.345 | 0.018 | 0.044 | 0.272 | 0.391 |
| two pool (separate key/value pools) | 0.616 | 0.033 | 0.079 | 0.458 | 0.403 |
| multi-head pool, 4 heads (PMA) | 0.773 | 0.021 | 0.053 | 0.565 | 0.430 |
| oracle address (illegal: told the roles) | 0.972 | 0.013 | 0.035 | 0.945 | 0.055 |

These numbers come from the final harness, with the writer isolated in a child process. The baseline runs exactly as a candidate does.

Note (shown): known methods already beat the seed by a wide margin. Multi-head pooling gets most of the familiar-name headroom (0.98) but little of the novel-name headroom (0.56 against an oracle of 0.95). So "better than the baseline" is easy. What matters in this trial is better **and** not known, and the novel-name gap is where a new idea would show.

## 5. Fixed budget

- **Model: `claude-opus-5-5` for every LLM role** (mutation, ShinkaEvolve's novelty-rejection call, novelty judge), at effort medium. Ben asked for this on 2026-10-20; it replaces the brief's "prefer Haiku/Sonnet".
- Evolve run:
  - up to **150 generations**, 2 islands;
  - ShinkaEvolve's cost cap: nominally $2.15. After the smoke spend, `run_evo.py` lowers it to about **$2.02** (see the backstop below), and this cap is what will end the run. Calls already in flight when the cap is reached can add a little; the backstop bounds it;
  - mutation calls are capped at 12,000 output tokens (Opus 5.5's thinking is always on); at about $0.05–0.08 per Opus mutation, expect roughly 25–35 generations (suggested; measured after the run);
  - each evaluation: 3 seeds, at most 150 s per seed from writer start-up to the end of eval (data generation excluded). ShinkaEvolve's job limit is 60 minutes, counted from the start of the proposal (sampling included), so in practice it does not bind before the per-seed rule. Training batches are cached per seed.
- Novelty judge: cap **$1.60**, reserved before the evolve run.
  - Each finalist gets up to 2 requests (one resume after `pause_turn`) of at most 2 web searches each. A finalist still searching after that is NOT JUDGED. The resume is budget-checked too, and its worst case is large (about $1.5), so in practice a finalist whose first reply pauses is NOT JUDGED. That affects only that finalist; later ones are still judged.
  - A turn starts only if its worst case still fits. The worst case assumes the input is billed again at every step (2 passes per search), with 20k tokens of results per search, plus a full 12k-token output. That is about $0.64 for a first turn.
  - So roughly the first 4 finalists in the fixed order are likely to be judged (suggested).
  - The judge runs once. It refuses to run again on an existing output file, and its earlier spend counts against its cap.
  - A reply cut off at max_tokens is NOT JUDGED.
  - Every outcome that is not a verdict (budget, refusal, error, unparsed, truncated) is recorded as "NOT JUDGED" and counts as **known**. Once a finalist is skipped because its first turn does not fit the budget, no later finalist is judged.
- Whole trial:
  - every paid call goes to `results/TRIAL_LEDGER.jsonl` (`ledger.py`). All prices come from the bundled catalog plus `shinka_local.patch` (ShinkaEvolve's live price fetch is off);
  - backstop: a mutation call is refused if the trial total, plus the calls already in flight (each reserved at $0.36: 30k input plus a full 12k output), plus the judge reserve, could pass **$4.50**, out of the $5.00 hard limit. That point is 4.50 − 0.155 − 1.60 − 2 × 0.36 = $2.025 of evolve spend. It is below the nominal $2.15, so `run_evo.py` sets ShinkaEvolve's cap to it.
    - ShinkaEvolve counts a proposal's cost only when the proposal finishes. So the backstop can fire first, by up to one unfinished proposal's spend. When it does, it also drops ShinkaEvolve's cap so the run stops cleanly.
    - Either way, evolve spend stays at or below $4.50 − $1.60 − the spend before the run.
    - Known gaps (stated):
      - a request that is billed but never returns (a client timeout or a cancelled call) is not in the ledger;
      - a judge request that runs more internal search passes than estimated can cost more than its pre-check allowed;
      - if the backstop fires before ShinkaEvolve has counted any cost, the run keeps proposing, but every call is refused, so it spends nothing more.
    - The $0.50 between the $4.50 stop and the $5.00 limit is the margin for these.
- Spent before the card, in the ledger: **$0.155**, all smoke tests (limit $0.25).
  - $0.0029 on the bundled sine example smoke test (3 Haiku 5.5 calls).
  - $0.0181 on the first plumbing test of `run_evo.py` (2 calls, before the switch to Opus).
  - $0.1340 on the final plumbing test with Opus 5.5 (2 calls, about $0.067 each: about 3k input and 2.5–3k output tokens). Its programs are discarded and were not looked at beyond the summary table.
- CPU only, in this container. No GPU.

## 6. Finalists (rule fixed now)

After the run, the finalists are at most 6 programs:
- (a) the top 4 distinct correct programs by evolution score;
- (b) the 2 correct programs whose behaviour descriptor is farthest from those 4 (z-scored Euclidean distance), among programs scoring at least 0.497 − 0.06 = 0.437. These are the "novel but maybe not better" candidates.

Each finalist's code is read by hand for sandbox evasion. Any evasion disqualifies it and is reported.

## 7. Pass marks (fixed now)

Each finalist is run on fresh seeds 1001 and 1002 (`confirm.py`, 3 parallel jobs like the evolve run), together with the baseline and the multi-head pool on the same seeds. Comparisons are paired by seed: the same data and the same initialisation stream.

- **BETTER** needs both of these:
  - on **both** fresh seeds, finalist − baseline > **0.06**. This is more than the baseline's 5-seed range (0.046) and more than 2 × its sd (0.039);
  - the finalist's novel-name accuracy, summed over the two fresh seeds, is above the multi-head pool's. This is the section 9 rule: a gain that is only on familiar names does not count.
- **BETTER THAN BEST KNOWN** (reported, not required): on both fresh seeds, finalist − multi-head pool > **0.045** (max(2 × 0.021, 0.03), rounded up).
- **NOT KNOWN**: the novelty judge (section 8) returns "NOT FOUND". I also check its reasoning against KNOWN.md and the code. If I disagree, both verdicts are reported and the finalist counts as **known**.
- **WINNER = BETTER and NOT KNOWN.**

Results are reported in four groups:
- both (winners);
- better but known;
- novel but not better;
- neither.

## 8. Novelty machinery

1. **ShinkaEvolve's code-novelty rejection, as designed.** Every proposal is embedded and compared by cosine to the programs on its island. Above **0.95**, the novelty LLM decides whether it is meaningfully different; if not, the proposal is resampled (up to 2 attempts).
   - Deviation: there is no OpenAI key here, so embeddings come from `local_embed_server.py`. It produces a hashed bag of code tokens and bigrams, with comments, strings and numbers stripped.
   - Calibration (shown): a temperature tweak of the seed scores 0.993 and an added LayerNorm 0.973, so both are rejected. Two-pool, mean-pool and multi-head writers score 0.70–0.83 against the seed, so they pass.
2. **Known-ideas list.** `KNOWN.md` (about 60 items: the project's own ideas from `design/research/`, `reviews/`, `design/v3/`, plus the standard literature). Its short form, `KNOWN_SHORT.md`, goes into the system message as "do not reproduce these".
3. **Novelty judge** (`novelty_judge.py`). A separate Opus 5.5 call per finalist, in this fixed order: 6(b)-1, 6(a)-1, 6(b)-2, 6(a)-2, 6(a)-3, 6(a)-4. If the budget runs out, the finalists last in that order are the ones left "NOT JUDGED", and they count as known. It sees the code and KNOWN.md but **no scores**, and searches the web. It answers "KNOWN: X" or "NOT FOUND: closest is Y" and gives a confidence. Every verdict is reported verbatim, including "known".
4. **Strange slot** (`run_evo.py`). On **25%** of parent draws, the parent is not chosen by score. It is chosen at random from the 3 correct programs (score ≥ 0.437) whose behaviour descriptor is farthest from the island's current top scorers. Each such draw is logged in `strange_slot.jsonl`.
   - ShinkaEvolve makes one child per generation, so this works out to about 25% of all parents over the run, not a per-batch quota.

Each finalist gets a one-paragraph description in the report, saying whether it is a known method (named) or not.

## 9. What would prove the trial a failure

- **Failure:** no finalist is both BETTER on the 2 fresh seeds and judged NOT KNOWN.

Partial outcomes are reported for what they are:
- every better program is a known method (for example rediscovered multi-head pooling or role-specific projections): the process re-derives the literature;
- every "novel" program fails the BETTER mark.

These also count as failure, whatever the evolution-seed scores look like:
- a result that only holds on evolution seeds 0–2;
- a winner whose gain is all on familiar names, with novel-name accuracy on the fresh seeds no better than the multi-head pool's on the same seeds.

## 10. What a pass would and would not show

- **A pass would show:** the toy contains a writer mechanism that is new to the judge's search and to this project, and that keeps the person better than the PremonitionMini writer on held-out seeds.
- **A pass would not show:** that it helps PremonitionMini on the ladder or the village. That needs a separate pre-registered run under `premonition/`, outside this trial (untested).

## Files

| path | role |
|---|---|
| `task/toy.py` | fixed harness: data, frozen reader, training, metrics |
| `task/initial.py` | seed program (EVOLVE block = `CardWriter`) |
| `task/evaluate.py` | ShinkaEvolve scorer and sandbox |
| `task/references.py`, `task/calibrate.py` | known writers and noise runs |
| `run_evo.py` | evolve run: ledger hook, budget stop, strange slot, known-ideas prompt |
| `ledger.py`, `results/TRIAL_LEDGER.jsonl` | whole-trial spend |
| `local_embed_server.py` | embedding server for code-novelty rejection |
| `novelty_judge.py`, `confirm.py` | Stage 1 judge and fresh-seed confirmation |
| `shinka_local.patch` | local patch to ShinkaEvolve: pricing rows and no temperature for Haiku/Sonnet/Opus 5.5. Upstream commit 8adc053 |
| `KNOWN.md`, `KNOWN_SHORT.md` | known ideas |

## Amendments

### 2026-10-20: two clarifications to section 6 (after the evolve run, before finalist selection)
The sealed section 6 leaves two choices open. Both are fixed here before any finalist was selected or confirmed. No pass mark, threshold, descriptor, novelty test or fresh-seed rule changes.
1. **Finalists are evolved programs (generation 1 or later).** The seed is the baseline that every finalist is compared with, so it is not a candidate itself. "Distinct" means different code after comments, strings and spacing are removed (the same tokenisation as the code-novelty embedding).
2. **The z-score reference set for 6(b) is the strange slot's** (`run_evo._strange_parent`): correct programs scoring at least 0.437 that have a valid descriptor. "Farthest" in 6(b) therefore means the same thing it meant during the run.

Why: a code review of `select_finalists.py` found that the card did not pin either choice.
