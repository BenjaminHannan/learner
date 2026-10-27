COMMON RULES: Edit, stop, or delete nothing. No ssh. NEVER read, cat, list, or print anything under ~/.codex. NEVER WebFetch. Finish within 10 minutes.
YOUR TASK (Director, 2026-09-27): run the Luna helper's selftest and a 3-call parallel check, and report exactly what happened.
In the worktree (git pull first so scripts/claude_luna_codex.py is present):
1. `python3 scripts/claude_luna_codex.py --selftest` (paste output; expect "selftest ok: model gpt-6-luna, output-file True/False").
2. `python3 -c "import sys,time;sys.path.insert(0,'scripts');from concurrent.futures import ThreadPoolExecutor as T;import claude_luna_codex as L;t=time.time();r=list(T(3).map(lambda i:L.call('Reply with the number %d and nothing else.'%i,timeout=180),[1,2,3]));print(r,round(time.time()-t,1),'s')"` (paste output).
3. Report `sha256sum scripts/claude_luna_codex.py` (or shasum -a 256).
Write all of it to handoff/replies/000-luna-helper-selftest.md; make sure the reply file is over 300 bytes.
PUSH: handoff/replies/000-luna-helper-selftest.md
