COMMON RULES (the "Making things up about you" thread, Claude, wrote this task on 2026-09-27). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply). Get files with `git fetch -q origin main` and `git archive`; never check out or push a branch yourself (the watcher pushes PUSH paths).
GPU: no (Mac CPU; about 80 GLM 5.3 Flash calls, at most 235 with retries, plus 1 leak-check call through Ben's opencode subscription, at most 3 at a time under the Mac-wide cap W = min(3, 16 - running opencode processes); $0). No reader, no rental, no BensPC, no OpenRouter. Label: madeup-mu407-prep. TIME CAP: 105 minutes. DISK: 1.
OPENCODE RULES: never read, print, copy or commit any opencode config, auth file or key. The scripts delete only the sessions they create; never delete any other session.
PYTHON: run every script as `uv run --offline --no-project --python 3.12 python -B <script> ...` (standard library only).
THINKING SETTING: reasoning effort "low" (`--variant low`), set inside scripts/claude_lis320_glm_oclow.py (called by scripts/claude_mu407_prep.py). Do not add or change any flag.
WHY: mu-407 tests whether a clear "reply to this message now" label stops the plain 1B treating its memory of earlier chats as the present (artifacts/claude-mu407-20260927/PASSMARKS.md). This job has GLM word the fresh DEV chats (code picks every fact) and the four input pieces the talker sees. Nothing is trained. DEV data only.

1. TREE: D=$(mktemp -d); git archive origin/main scripts artifacts/claude-mu407-20260927 | tar -x -C $D; cd $D; O=artifacts/claude-mu407-20260927/prep; mkdir -p $O. Record `git rev-parse origin/main` and `uptime`.
2. SEAL (run from $D): `shasum -a 256 -c artifacts/claude-mu407-20260927/SEAL-prep.sha256.txt` must print OK on every line. Else stop and report.
3. SELFTESTS (each must print ok, else stop): scripts/claude_mu407_prep.py selftest ("mu407 prep selftest 8/8 ok"); scripts/claude_lis320_glm_oclow.py --selftest (last line "lis320 glm_oclow selftest ok ...").
4. LEAK CHECK (one call): scripts/claude_glm_leakcheck.py --worktree <absolute path of your worktree>. Record its JSON line. Exit code 2 (ROUTE-FAIL) or 3 (LEAK): stop and report.
5. SHARE: N=$(pgrep -f "opencode run" | wc -l | tr -d ' '); W=$((16 - N)); if W > 3 then W=3. If W < 1, wait 2 minutes and count again (at most 15 times, then stop and report). Record `date -u`, `uptime`, N and W.
6. RUN, recording `date -u` before and after and every printed line verbatim:
   scripts/claude_mu407_prep.py facts --out $O/facts_all.jsonl
   scripts/claude_mu407_prep.py frames --out $O/frames.json
   WRITE runs in the background, because your shell tool stops any single command after 80 minutes (it did so to job madeup-g406-2-mac at 02:06 UTC 09-27). Start it with one command:
   nohup uv run --offline --no-project --python 3.12 python -B scripts/claude_mu407_prep.py write --facts $O/facts_all.jsonl --out $O/raw.jsonl --workers $W --max-minutes 45 > $O/write.log 2>&1 & echo $! > $O/write.pid ; date -u
   Then check it with separate short commands, each under 10 minutes: `sleep 300; tail -2 $O/write.log; kill -0 $(cat $O/write.pid) && echo alive`. Repeat until it is no longer alive. If it is still alive 70 minutes after it started, stop it by exact PID only: `pgrep -P $(cat $O/write.pid)` gives its python child; kill that PID, then the PID in write.pid, record both and `date -u`, and go on (raw.jsonl keeps every finished row). Record the last line of write.log.
   scripts/claude_mu407_prep.py select --facts $O/facts_all.jsonl --raw $O/raw.jsonl --out-panel $O/panel/items.jsonl --out-facts $O/facts.jsonl
   python -B scripts/claude_mu405_check.py --panel $O/panel/items.jsonl --facts $O/facts.jsonl   (record its line and exit code)
   If frames fails (exit 1), still run the rest and say so.
7. Copy $O (facts_all.jsonl, frames.json, raw.jsonl, write.log, panel/items.jsonl, facts.jsonl) into artifacts/claude-mu407-20260927/prep/ of your worktree and write RESULTS.md there: the origin/main commit, uptimes, every `date -u`, seal/selftest/leak-check lines, N and W, every printed line, and the check line. Counts only in RESULTS.md: do not paste chat or frame text into it. Then rm -rf "$D" (exact path) and confirm it is gone.
If stopped by the time cap: still do step 6's select and check with what exists, then step 7, and say "partial".
PUSH: artifacts/claude-mu407-20260927/prep
