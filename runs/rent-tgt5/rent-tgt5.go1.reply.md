Renting the 5090 for your tgt-5 run — fetching the latest and checking gates first.
Credit 9.78 — above the $3 gate, proceeding with rental checks.
No duplicate — renting the cheapest fast 5090 now.
Instance is running — setting up the run tree.
Setup done — fetching the base model snapshot now.
Selftest passed — launching the main run detached.
Strong early signal (W seed 1: 97/120) — continuing to poll.
Run finished in ~11 min with a PASS signal — copying results back.
Instance destroyed and confirmed gone — writing the artifacts.
Verdict: PASS — the registered tgt-5 GPU run completed and meets both PASS conditions; nothing was patched.

Run numbers (from gpu/tgt5_summary.json, recorded verbatim in artifacts/claude-tgt5-20260926/RESULTS-gpu.md):
- Base: 81/120 pairs D>0 masked (79/120 raw), mean D 0.5069 (raw 0.3849)
- W seeds: 97/120, 97/120, 100/120 — each ≥ 84 (PASS condition 1 met)
- W−base mean: 1.3956 nats (≥ 0.20), 98.33% bounds [1.0099, 1.797], lower bound > 0 (PASS condition 2 met)
- Proved-wrong clause NOT triggered (upper bound 1.797 > 0); conclusive (179 won practice puzzles ≥ 20, 20 own greedy-correct ≥ 10)
- Secondary: E 109,103,102/120; C 89,87,81/120; DEV temp rule chose 1.5 (44 vs 41 lucky blurts on 58 missed)

Integer counts:
- Credit gate: 9.78 (≥ 3.00, proceeded)
- Duplicate gate: 0 gpu dirs on origin/main or origin/builder-outbox, 0 live rent-tgt5 instances (1 unrelated live instance rent-dl2 left alone)
- Rentals used: 1 of 3 max (instance 52674236, RTX 5090, $0.49444/h, ~0.38 h ≈ $0.19 of $1.00 budget)
- Selftest: `selftest ok`, 1 run; main run 10.7 min wall, 120 pairs / 60 hands, exit clean, no traceback
- Files copied back before destroy: 4 (tgt5_summary.json 1363 B, pairs.jsonl 120 lines, contrasts.json 50358 B, log.txt 71 lines); instance destroyed and confirmed gone (0 rent-tgt5 live)
- Files staged (force-add, artifacts/ is git-ignored): 6 — gpu/ ×4, RESULTS-gpu.md ×1, ledger ×1 (modified)
- Weights pushed: 0; code edits: 0; repo-root notebook/ writes: 0

Every deviation (task vs rent-kit/routine):
1. Skipped the rent-kit's second model fetch (all-MiniLM-L6-v2) and the fable_self122 smoke check — the task ordered MiniCPM5-1B only, never any other model (model commit 87179e5c1f455ef22e6223592d2d61351b525bfc, matches expected).
2. Installed `peft` alongside the rent-kit's package list (env-only; proved unnecessary since blurt2's LoRA is plain torch — no code touched).
3. Built the GPU tree via the task's exact 8-path `git archive origin/main` list instead of the rent-kit's builder-outbox+main+self122 recipe.
4. First ssh launch command hit my own 120 s client timeout; the run survived via setsid, reconnect showed it healthy — no impact, no re-rent.

PUSH (staged, watcher to push): artifacts/claude-tgt5-20260926/gpu, artifacts/claude-tgt5-20260926/RESULTS-gpu.md, artifacts/fable-predictions-ledger.md.
