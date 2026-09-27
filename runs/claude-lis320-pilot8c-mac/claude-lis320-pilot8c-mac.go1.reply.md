touched stop file for lis320-pilot8b-mac 2026-09-27T08:44:41Z
ORPHAN wording run found (left running, waiting):
54153 /usr/local/bin/opencode run --model opencode/muse-spark-1.3-contributor-free --auto --dir /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27 --ti

RUNNER NOTE (Director, 09-27): your builder model is rate-limited, so every tool call counts. To wait for a long background run, use ONE blocking command (e.g. while pgrep -f <exact script> >/dev/null

COMMON RULES (the "Fix: reading facts from chat" thread, Claude, wrote this task on 2026-09-27; re-queue of lis320-pilot8-mac, whose two builders died on "Rate limit exceeded" at 03:27-03:30 local bef
GPU: no (Mac CPU; 60 GPT-6 Luna wording calls plus 1 selftest call through Ben's Codex plan via scripts/claude_luna_codex.py; $0). No reader, no rental, no BensPC, no OpenRouter, no opencode. Label: l
LOAD-LIGHT: yes
CODEX RULES: never read, print, copy or commit anything under ~/.codex or any key or auth file. The helper runs each call in a fresh empty temp dir with a read-only sandbox; do not change that.
PYTHON: run every script as `uv run --offline --no-project --python 3.12 python -B <script> ...` (standard library only).
WHY: Ben (03:47 UTC 09-27): "just have luna rewrite all the training data". lis-320's writer moves from GLM (opencode plan at its usage limit since about 00:57 UTC) to GPT-6 Luna. The prompt, seeds, c

0. ORPHAN CHECK (before step 1): run `pgrep -fl "claude_lis320_luna2.py --seeds"`. The first attempt (lis320-pilot8-mac) may have left a nohup'd wording python running. If one is found: record its PID
1. TREE: git fetch -q origin main; D=$(mktemp -d); git archive origin/main scripts design/v3/60-listener artifacts/claude-lis320-20260926 artifacts/claude-chatdev-20260926 artifacts/claude-e2e331-dev-
2. SEALS (all OK or stop, run from $D): shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-6.sha256.txt; shasum -a 256 -c artifacts/claude-lis320-20260926/SEAL-ADDENDA-8.sha256.txt; shasum
3. SELFTESTS (each must end ok/OK, else stop): scripts/claude_lis320_luna2.py --selftest; scripts/claude_lis320_seed_cr.py --selftest; scripts/claude_lis320_check_we3.py --selftest; scripts/claude_lis
4. SEEDS: scripts/claude_lis320_seed_cr.py --seed 328 --n 60 --ask-back --avoid-names artifacts/claude-lis320-20260926/avoid_names_dev.txt --avoid-hashes artifacts/claude-lis320-20260926/avoid_test.sh
5. WORDING (3 workers, the Director's share): record `date -u` and `uptime`; scripts/claude_lis320_luna2.py --seeds $O/seeds.jsonl --out $O/raw.jsonl --workers 3 --max-minutes 40 > $O/glm.log 2>&1 ; r
6. scripts/claude_lis320_rawcheck2.py --raw $O/raw.jsonl --seeds $O/seeds.jsonl --models gpt-6-luna   (record the line; ROUTE-FAIL: still do steps 7-8, and say so first in RESULTS.md)
7. scripts/claude_lis320_check_we3.py --seeds $O/seeds.jsonl --raw $O/raw.jsonl --out $O/kept.jsonl --drops $O/drops.jsonl > $O/check.json ; scripts/claude_lis320_style.py --kept $O/kept.jsonl --out $
8. Copy $O (seeds.jsonl, raw.jsonl, kept.jsonl, drops.jsonl, check.json, style.json, glm.log) into artifacts/claude-lis320-20260926/pilot8/ of your worktree and write RESULTS.md there: every printed c
PUSH: artifacts/claude-lis320-20260926/pilot8
STOP: orphan still running after 15 min; no new run started 2026-09-27T08:59:43Z
rc=3
