COMMON RULES (the "Answering from memory" thread, Claude, wrote this task on 2026-09-27 03:51 UTC). Follow the first 14 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, at most 4 parallel processes, report in your final reply). Get files with `git fetch -q origin main builder-outbox` and `git archive`; never check out or push a branch yourself (the watcher pushes PUSH paths).
GPU: no (Mac CPU; up to 60 GPT-6 Luna calls through Ben's Codex plan via scripts/claude_luna_codex.py, $0 extra). No opencode, no OpenRouter, no reader, no rental, no BensPC. Label: y1t-luna-pilot. TIME CAP: 70 minutes. DISK: 1.
KEY RULES: never read, print, copy or commit anything under ~/.codex, any config or auth file, or any key. The helper never touches them.
DUPLICATE GATE: stop with DUPLICATE if origin/builder-outbox already has artifacts/claude-y1t-20260926/luna/RESULTS-luna-pilot.md.
WHY: artifacts/claude-y1t-20260926/ADDENDUM-5-luna-writer.md (on origin/main, sealed in SEAL-y1t-add5.sha256.txt). Ben 03:47 UTC: Luna may write training data. This pilot words the first 60 of the 315 redo dialogs GLM could not reach; nothing is trained, checked or judged here.

1. TREE: D=$(mktemp -d); git archive origin/main scripts design/v3/60-listener artifacts/claude-lis320-20260926 artifacts/claude-y1t-20260926/ADDENDUM-5-luna-writer.md artifacts/claude-y1t-20260926/SEAL-y1t-add5.sha256.txt | tar -x -C $D; git archive origin/builder-outbox artifacts/claude-y1t-20260926/glm/raw.jsonl artifacts/claude-y1t-20260926/topup/raw_new.jsonl | tar -x -C $D; cd $D; O=artifacts/claude-y1t-20260926/luna; mkdir -p $O.
   PY means `uv run --offline --no-project --python 3.12 python -B` (no torch needed); under zsh write it out in full. export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1.
2. SEAL: `shasum -a 256 -c artifacts/claude-y1t-20260926/SEAL-y1t-add5.sha256.txt` (every line OK, else stop with SEAL-MISMATCH and run nothing).
3. SEEDS: $PY scripts/claude_lis320_seed.py --seed 4027 --n 2400 --avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sha256 --out $O/seeds.jsonl
   $PY scripts/claude_y1t_topup.py split --seeds $O/seeds.jsonl --raw artifacts/claude-y1t-20260926/glm/raw.jsonl --out $O/split
   $PY scripts/claude_y1t_luna.py pick --redo $O/split/seeds_redo.jsonl --done artifacts/claude-y1t-20260926/topup/raw_new.jsonl --out $O/luna_seeds.jsonl
   Check with `shasum -a 256`: $O/seeds.jsonl = 42b344fba2dad802fa3109295dd3548c8aa7bdd5c947a356ba1c61c480360f43, $O/split/seeds_redo.jsonl = e80e84156cb2ac003711c97ad8d9d4761962c6c42b83d3730477dad8abc4ef8b, $O/luna_seeds.jsonl = 6184cd224078ad2eb71cdd606129cb29fc14e513960c26c0ee0b295f57b483de. Any mismatch: stop with SEED-MISMATCH and run nothing. Record pick's printed line (expected "left": 315).
4. CHECKS: $PY scripts/claude_y1t_luna.py --selftest (ends "y1t luna selftest ok (no network)") and $PY scripts/claude_y1t_routefilter.py --selftest. `uptime`, `df -g /`.
5. PILOT (W=3 unless the Director's current Luna share says otherwise; record W and why):
   $PY scripts/claude_y1t_luna.py --seeds $O/luna_seeds.jsonl --out $O/raw_luna.jsonl --workers $W --batch 20 --max-minutes 50 --max-failed 10 --limit 60 > $O/luna_pilot.log 2>&1
   Its last line is the totals JSON. Record it verbatim. Do not rerun. Report the first line of each distinct "[y1tluna] call failed" error.
6. ROUTE FILTER: $PY scripts/claude_y1t_routefilter.py filter --raw $O/raw_luna.jsonl --out $O/raw_luna_rf.jsonl; record its counts line verbatim.
7. COUNT: line count of raw_luna.jsonl, rows with "parsed" not null, rows with parsed null, distinct dialog ids (counts only).
8. Copy $O/raw_luna.jsonl, $O/raw_luna_rf.jsonl and $O/luna_pilot.log into artifacts/claude-y1t-20260926/luna/ of your worktree (force-add; artifacts/ is git-ignored) and write RESULTS-luna-pilot.md there: every printed line verbatim, W and why, wall time, the counts, any error. Keep it to counts; Luna's text may not be summarised in it. Then rm -rf "$D" (exact path) and confirm it is gone.
PUSH: artifacts/claude-y1t-20260926/luna
