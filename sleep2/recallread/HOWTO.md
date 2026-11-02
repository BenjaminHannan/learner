# Recall-then-read, stage 1: how to run it

Spec: `/mnt/project-files/mechanism/INVENT-1.md`, "Pick 2". Scope: K2-Horizon-3.7B, Week-2 world only (not the village model, not the card experiments).
Run from the repo root (`python -m sleep2.recallread.<module>`). Tests: `python -m pytest sleep2/recallread/tests -q`.

## What is reused (not rewritten)
- Sleep code and world: branch `claude/project-thread-cqc4bi`, commit `a7ed69d79d9ca928bc77b577c2912c6655474ad0`: `backbone/sleep/brain/sleepb.py` (recipe `ab_ob_b4_nb`,
  K2 port: `--tok-budget 1024`, thinking-closed prompts, names pass with thinking), `backbone/train.py`, `backbone/sleep/sleep1.py`, and
  `backbone/sleep/brain/data/week2.json` (sha256 `70db7146...`; checked on every load). `train_sleep.py` only builds addendum 11's k2s_bf16 command line.
- The job needs that code next to `sleep2/`: merge `a7ed69d` into the branch you push (sleep2/ is a new directory, so it should merge cleanly), or rely on the job's
  fallback, which `git fetch`es the pinned commit and checks the sha256 of `sleepb.py` and `train.py`.
- `paired.py` exists there but is tied to sleepb result JSONs; `stats.py` has its own exact McNemar (same formula).

## Order (nothing below has been submitted; every API script defaults to a dry run)
1. `python -m sleep2.recallread.items plan` (no API): 132 cross-day chains, 75 W, 30 dev, 200 one-hop, 50 never-taught.
2. Dry runs (counts + cost, recorded in `data/recallread/api_cost_estimates.json`; submit refuses if the recorded total exceeds $5):
   `items requests --dry-run`, `alias_table requests --dry-run`, `alias_table requests --dry-run --w`, `grade requests --dry-run --assume-rows 7100 --results <dir>`.
3. Submit (needs `LEARNER_ANTHROPIC_API_KEY`; do a pilot first with `--limit 5`): `items requests --submit`, then `items collect`; `alias_table requests --submit` and `--w --submit`,
   then `alias_table collect` and `collect --w` (needs `items.json` for the W deleted turns, so run `items freeze` once with `--no-claude` before the W table; then freeze again).
4. `items freeze` (validates Claude's wording: ends with '?', has the start name, no bridge/answer; lexical-gap check; falls back to the template wording and counts it) ->
   `data/recallread/{items.json, items.sha256, week2.json, week2.json.sha256}`. Add `alias_table_full.json` and `alias_table_W.json` (from step 3).
   `python -m sleep2.recallread.make_condition_w` re-checks the W deletion and writes `index_W.sqlite`.
5. Copy `data/recallread/` to `/mnt/project-files/recallread/frozen/` (the job's `needs=`). Fill `commit=` in `gpuq-recallread.sh`, copy it to your gpuq-drafts folder.
6. After the job: copy the results back, then `grade requests --submit`, `grade collect`, `python -m sleep2.recallread.report --results <dir>` (writes `REPORT.md`, `summary.json`).
   Without a key you can still get exact-match numbers: `grade exact-only` then `report`.

## What the GPU job does (gpuq-recallread.sh, 1 x RTX 4090)
1. Private venv with transformers 5.20.2 / peft 0.21.2 / accelerate 1.15.0 (the versions sleepb ran against).
2. `train_sleep.py`: ab_ob_b4_nb on K2-Horizon-3.7B bf16, seeds 1 and 2, adapter saved under `$GPUQ_OUT/sleep/s<seed>/adapter`. About 2.5-3.5 h each (a 5090 took 1.75 h).
3. `run_eval.py`: a 20-item smoke, then all arms: D0, D1, D2, D3, D4, R, RD3, R_tau, on 589 rows per seed (twohop_nat 132, twohop_gap up to 132, W_nat 75, onehop 200, never 50;
   `twohop_tmpl` is frozen but not run unless you pass `--splits`). Baseline arms have no LoRA and run once (`*_s0.jsonl`). Estimate 1-2 h. Estimated total 6.5-9 h, limit 11.
   Output: `$GPUQ_OUT/results/recallread/{arm}_{seed}.jsonl` plus `ledger_R_vs_D3_<seed>.json`, run logs, sleepb result JSONs.

## Design choices to check (all fixed before any result)
- Diary = the 1,043 USER turns of the world (as `sleepb.Diary`), FTS5 with porter stemming, BM25. Context = fused ranking trimmed to 1,500 tokens (depth 50 per query so the budget binds).
- Same reader prompt for every arm: "Answer with just the name. If the notes do not say, answer: unknown." (the project's diary prompt has no abstain option; pass mark 4 needs one).
- Ledger (`arms.assert_equal_budget`): R and D3 have equal key-pass count (1), key decode budget (40), read count (1), answer budget (20) and final k_tokens (1,500) on every item.
  "Rounds" is read as model passes (key pass + read = 2 for both). D3 additionally has a second retrieval round and a larger prefill (favours D3, as the spec says); R does one retrieval.
- Condition W: for the 75 W chains every user turn mentioning the hop-1 fact (and any turn holding both start and bridge name) is deleted from the index, the D3/D4 inputs and the D4 table;
  `check_deletion` asserts no hop-2 turn is lost and no start-bridge link survives. The LoRA saw the whole diary.
- Pass marks 1-4 and the proves-wrong rule are in `stats.py`; mark 5 (Mac) reports "NOT RUN". Pooled McNemar stacks both seeds (baseline arms appear twice, so pooled p is optimistic); per-seed signs are also required.
- R_tau: tau tuned on the 30 dev chains from R's logged key logprobs (ablation, no pass mark).

## Deviations from the spec
- 132 two-hop chains, not 150: the world supports only 132 clean cross-day chains (mentor->lives, owner->born, sibling->works; 44 each). 75 of them are W. If the lexical-gap filter rejects Claude's wording, that chain has no `twohop_gap` row.
- One-hop items are 200 of the world's own forward tests (no Claude); Claude only rewords them. Never-taught names are invented syllable mixes, grep-checked absent from the diary, then reworded by Claude.
- Optional 50 Ben-written items: not built. Mac latency (`mac_latency.py`): a later step.
- Sonnet 5.5 requests use `thinking: {"type": "between_tools"}` (thinking off); Haiku uses `disabled`. If the pilot batch rejects this, change `batchlib.params`.
