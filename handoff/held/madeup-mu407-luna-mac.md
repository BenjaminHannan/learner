COMMON RULES (the "Making things up about you" thread, Claude, wrote this task on 2026-09-27). Follow the first 13 lines of origin/main:handoff/queue/lis-302-gpu.md (additive only, fictional names, TEST-ONLY panels never read, report in your final reply). Get files with `git fetch -q origin main` and `git archive`; never check out or push a branch yourself (the watcher pushes PUSH paths).
GPU: no (Mac CPU; GPT-6 Luna through Ben's Codex plan via scripts/claude_luna_codex.py: a pilot of 4 calls, then about 75, ONE at a time (--workers 1: this thread's share of Luna is 2 parallel calls for two jobs, Director 03:54 UTC); no opencode, no GLM, no rental, no BensPC, no OpenRouter). Label: madeup-mu407-luna. TIME CAP: 150 minutes. DISK: 1.
CODEX RULES: never read, list, print, copy or commit anything under ~/.codex. The helper runs each call in an empty temp folder with a read-only sandbox; do not change that.
PYTHON: run every script as `uv run --offline --no-project --python 3.12 python -B <script> ...` (standard library only).
SHELL LIMIT: your shell tool stops any single command after 80 minutes. The one long step (6) runs in the background as written; every other command is short.
WHY: mu-407 tests whether a clear "reply to this message now" label stops the plain 1B treating its memory of earlier chats as the present (artifacts/claude-mu407-20260927/PASSMARKS.md). Ben ruled at 03:47 UTC 09-27 that Luna may write this data (ADDENDUM-1). Luna words fresh DEV chats around code-picked facts and the four input pieces the talker sees. Nothing is trained.

1. TREE (your worktree is not on main, so work only from main's archive): git fetch -q origin main; D=$(mktemp -d); git archive origin/main scripts artifacts/claude-mu407-20260927 | tar -x -C $D; cd $D; O=artifacts/claude-mu407-20260927/prep; mkdir -p $O. Record `git rev-parse origin/main`, `date -u` and `uptime`.
2. SEAL (run from $D): `shasum -a 256 -c artifacts/claude-mu407-20260927/SEAL-prep.sha256.txt` and `shasum -a 256 -c artifacts/claude-mu407-20260927/SEAL-luna.sha256.txt` must print OK on every line. Else stop and report.
3. SELFTESTS (each must print ok, else stop): scripts/claude_mu407_prep_luna.py selftest-luna ("mu407 prep-luna selftest 11/11 ok"); scripts/claude_mu407_prep_luna.py selftest ("mu407 prep selftest 8/8 ok"); scripts/claude_luna_codex.py --selftest ("selftest ok: model gpt-6-luna ...").
4. PILOT, recording `date -u` before and after and every printed line verbatim:
   scripts/claude_mu407_prep_luna.py facts --out $O/facts_all.jsonl
   scripts/claude_mu407_prep_luna.py smokefacts --facts $O/facts_all.jsonl --out $O/smoke_facts.jsonl
   scripts/claude_mu407_prep_luna.py frames --out $O/frames.json
   scripts/claude_mu407_prep_luna.py write --facts $O/smoke_facts.jsonl --out $O/raw.jsonl --workers 1 --max-minutes 20
   scripts/claude_mu407_prep_luna.py pilot --frames $O/frames.json --raw $O/raw.jsonl   (record its JSON line and exit code)
   Exit code 1 = pilot FAIL, exit code 2 = pilot REVIEW: in either case skip steps 5-7, go to step 8, and say "pilot FAIL" or "pilot REVIEW". Never reword any prompt.
5. (nothing: numbering kept for the report)
6. FULL WRITE in the background. Start it with one command:
   nohup uv run --offline --no-project --python 3.12 python -B scripts/claude_mu407_prep_luna.py write --facts $O/facts_all.jsonl --out $O/raw.jsonl --workers 1 --max-minutes 45 > $O/write.log 2>&1 & echo $! > $O/write.pid ; date -u
   Then check it with separate short commands, each under 10 minutes: `sleep 300; tail -2 $O/write.log; kill -0 $(cat $O/write.pid) && echo alive`. Repeat until it is no longer alive. If it is still alive 70 minutes after it started, stop it by exact PID only: `pgrep -P $(cat $O/write.pid)` gives its python child; kill that PID, then the PID in write.pid, record both and `date -u`, and go on (raw.jsonl keeps every finished row). Record the last line of write.log.
7. SELECT AND CHECK, recording every printed line and exit code:
   scripts/claude_mu407_prep_luna.py select --facts $O/facts_all.jsonl --raw $O/raw.jsonl --out-panel $O/panel/items.jsonl --out-facts $O/facts.jsonl
   python -B scripts/claude_mu405_check.py --panel $O/panel/items.jsonl --facts $O/facts.jsonl
   scripts/claude_mu407_prep_luna.py scan --frames $O/frames.json --raw $O/raw.jsonl
8. Copy $O (facts_all.jsonl, smoke_facts.jsonl, frames.json, raw.jsonl, write.log, panel/items.jsonl, facts.jsonl; whichever exist) into artifacts/claude-mu407-20260927/prep/ of your worktree and write RESULTS.md there: the origin/main commit, uptimes, every `date -u`, seal and selftest lines, every printed line, the pilot JSON and exit code, the check line and the scan JSON, and the line "writer: Luna (gpt-6-luna), helper sha256 <shasum of scripts/claude_luna_codex.py>". Counts only in RESULTS.md: do not paste chat or frame text into it. Then rm -rf "$D" (exact path) and confirm it is gone.
If stopped by the time cap: still do step 7 with what exists (if the pilot passed), then step 8, and say "partial".
PUSH: artifacts/claude-mu407-20260927/prep
