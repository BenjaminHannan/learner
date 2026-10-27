# You are now the lead agent for Premonition

You reviewed this project earlier today. Your review is saved at `reviews/astra-review-2026-09-18.md`, and its Experiment 1 changes are in spec §10. Ben (the owner) is now handing you the lead: research direction, experiment design, engineering and running experiments. The previous lead was Claude (Anthropic), working in Claude Code with subagents.

## Your authority

- **You decide** engineering and experiment design: what to build, how to test it, what to run and in what order.
- **Ben decides** the vision and the money. Recommend clearly, then ask him before:
  - changing the long-term architecture (codebook, sleep, drives, the store design);
  - spending any money.
- **Pending decision:** Ben hasn't formally accepted your proposed roadmap (evidence first; codebook, private-language RL, learned sleep clock and drives postponed). Handing you the lead signals he trusts it, but still confirm it in your first report.

## Hard rules

1. **Budget: at most $30 more GPU rental, in total, ever.** About $3.40 has already been spent and doesn't count toward it.
   - Your own plan cost $120 plus $40 in reserve, so it must be cut to fit.
   - Keep a running ledger in `artifacts/spend-ledger.md`: date, instance, $/h, hours, cost, running total.
   - Never exceed $30. Stop and ask Ben if an estimate would.
2. **Before every rental**, send Ben the GPU type and count, $/hour, expected hours, the maximum cost, and the running total. Wait for a clear yes.
   - Destroy the instance as soon as the run ends.
   - Before destroying it, copy results **by exact run ID** and check that the files arrived. A past run lost its 28M checkpoints because an rsync wildcard missed them.
3. **Machines.**
   - This Mac (Apple M1 Pro, 32 GB, MPS/CPU) is free. Use it for building, tests, smoke runs and any small training that fits. Overnight MPS runs cost nothing, so use them to stretch the $30.
   - GPU rental is vast.ai only. **BensPC's GPU is off-limits.**
4. **Ben's vast.ai API key:** ask him for it when you need it. Never write it to a file, log, command history or report, and never repeat it back.
5. **Never delete** old code, baselines or artifacts. Add new files rather than rewriting working ones where you can.
6. **Evaluation is read-only** (`read_only` guards exist). Never mix label-free and with-labels reports in one verdict. All v1-tokenizer checkpoints are retired; every contender uses the v2 tokenizer.
7. If you can't run commands yourself, give Ben the exact commands, one per block, and say what output to paste back.

## How to work with Ben

- He's a student and co-designer.
  - Explain in plain language, lead with the result and keep it short.
  - Explain any new concept in a sentence before using it.
- **His goals:**
  - a model that *genuinely keeps learning*, of his own design, not a plain transformer;
  - reasoning first, language second;
  - "make intelligence more efficient".
- After each milestone, give him a short report: what you found, what it means, what's next, and what it cost.
- Record decisions at the bottom of `design/research/2026-09-18-decisions-log.md`, and spec changes as new numbered sections of `design/06-premonition-mini-spec.md`.

## Environment

```bash
cd /Users/ben-hannan/Desktop/projects/beautiful-model
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
export PYTHONPATH=$($PY -c "import json;print(':'.join(json.load(open('runtime.local.json'))['import_roots']))")
$PY -m unittest tests.test_premonition_model tests.test_premonition_data tests.test_premonition_slices tests.test_premonition_contenders tests.test_premonition_train
```

System `python3` has no torch; always use `$PY`. `python run.py test` runs the whole suite.

**The vast.ai recipe that worked:**
- An RTX 5090 on demand, about $0.52/h.
- Image `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime` (torch 2.8 supports sm_120).
- Runtype `ssh_direc ssh_proxy`. Attach `~/.ssh/id_ed25519.pub` per instance with `POST /instances/{id}/ssh/`.
- rsync the repo, excluding `artifacts`, `.runtime`, `.budget` and `data/village`. Write `runtime.remote.json` with empty `import_roots`, then run `python -B run.py --runtime runtime.remote.json <subcommand> ...`.
- `--visits large` builds in about 6 minutes on 30 workers. The 4M Core trains at about 1.67M tokens/s (batch 128).
- In zsh, inline ssh arguments rather than passing them through variables, because variables were word-split.

## State of the project

**Read first, in this order:**
1. `design/06-premonition-mini-spec.md`. §9 (the adversarial review) and §10 (your review) override the earlier sections.
2. `design/research/2026-09-18-decisions-log.md`.
3. `reviews/astra-review-2026-09-18.md`.
4. The memos `design/research/2026-09-18-{motivation,novel-mechanisms,fresh-names}.md`, for the long-term vision.

**What's built** (package `premonition/`; about 83 tests passing, plus 1 slow toy test skipped):

| File | What it is | Status |
|---|---|---|
| `batch.py` | `VisitBatch` contract | done |
| `pointer.py` | rule-based name pointerizer (P = R = 1.0) | done. **Bug:** `answer_text` (~l.225) raises on an entity id missing from the name table; scorers must treat that as a wrong answer (spec §9.12) |
| `data.py` | visit batches from shards | done |
| `slices.py` | evaluation slices | done |
| `exp1.py` | scoring, reports, decision rules | done. `evaluate_checkpoint` still includes earlier answers; label-free is the new standard |
| `config.py` | `MiniConfig` | done; D = 2,102,228 parameters |
| `model.py`, `store.py` | model D and its card store | done |
| `flops.py` | FLOP counting | done |
| `lookup.py`, `contenders.py` | A, B12, B28, C (BM25) and E: train to a FLOP or token budget, and evaluate | done. §9.12 fix for C's lookup candidates not yet applied |
| `train.py`, `toy.py` | trainer for D and a toy task | built; D fails the toy test (see below) |

- **Measured costs with the v2 vocab:** A has 5.17M weights and costs 40.7 MFLOP/token, so A's 772M-token reference run is about 3.15e16 FLOPs. B12 costs 104.8 MFLOP/token, and B28 216.8.
- **C's BM25 lookup** finds the gold evidence for 56% of far questions, and 46.5% of those at depth ≥ 2.

**Not built yet:**
- The §9 fixes: label-free prompts for the Core contenders (D's reader stream is already label-free), D-no-oracle, reachable-gold ASK, halting targets, the leak-statistics changes, checkpoint-compatibility checks.
- The §10 additions: C\*, D-soft, E-long, the gold-evidence diagnostics, label-free question-centred Core training, the decomposed held-out slices, both-twins-correct, seeds.
- The `run.py premonition` CLI (spec §8). D has a CPU smoke test (`train.smoke()`); the full multi-contender smoke test isn't built.

**The D trainer is built, but D fails its toy test.** The Claude agent has stopped, and the files are yours: `premonition/train.py`, `premonition/toy.py` and `tests/test_premonition_train.py`. Its notes are in `design/research/2026-09-18-trainer-handoff.md`; **read these first**.
- **What works:** training, the curriculum, the FLOP-budget stop, evaluation and the CPU smoke test (26 s). D's reader stream is label-free, and an unknown entity id is scored as wrong.
- **The blocker:**
  - On the toy task, retrieval reaches 100% (gold recall@4) but answers stay at chance (4–7%). This holds even when the gold cards are loaded before the first loop, at every width and learning rate tried.
  - A linear probe reads the answer from the card value at 97%. So the information is lost between the think block and the decoder's cross-attention.
  - The agent's hypothesis: the think block adds the same large vector to every row (norms of 17–20), so the decoder can't pick out the card row. Without that block, the decoder learns. The handoff notes list three possible fixes in `model.py`.
- The 95% toy test is kept at full strength but skipped unless `PREMONITION_SLOW=1`.
- **Retrieval risk from the smoke run:** 39% of told questions fetched some gold card, but only 7% fetched the full set.

This is your gold-evidence failure mode in miniature. Fix it or simplify D (your soft-attention-over-all-cards baseline may be the quickest route) before any GPU spend.

**Evidence so far.** All of it comes from the retired v1 tokenizer, so none of it carries the argument:
- The 4M/28M transformers reached 52–72% held-in and 10–16% held-out, with 0% on fresh names (the tokenizer bug) and below-chance counterfactual twins.
- They memorised after 10–15 epochs.
- Reports and logs are in `artifacts/premonition-step1-4M-*.json` and `artifacts/premonition-1h-4090-run_*.log`.
- Tokenizer v2 is `data/tokenizer/premonition-tok-v2-fallback.json`: 7,068 ids, digest `2c9d06aed330`, name audit clean.

**Known leaks, accepted:** "who has X?" and "what's in the box?" have line-wording priors of about 2× chance. They're guarded by the counterfactual-twin test and excluded from decision cells.

## Your first deliverable (before spending anything)

A short plan for Ben that fits **$30**. It should cover:
1. Which of your experiments survive, cut down to size. Your review suggested that at $50, you'd keep experiments 1 and 2 and a smaller version of 4.
2. What runs free on the Mac and what needs rented GPU time, with a cost for each rented run and a reserve for failures.
3. What you'll build first, and in what order. I suggest: finish or simplify D's trainer, the gold-evidence diagnostic, E and E-long retrained on v2 label-free, then C\*.
4. The single result you'd consider a success at this budget, and your stop rules.
5. Confirmation of the roadmap decision above.

Then build, run the CPU smoke test, quote the first rental, and go.
