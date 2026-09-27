# Reply: 000-luna-helper-selftest (Director task 2026-09-27)

Worktree branch: `claude/card-experiment-handoff-7c5b27` (worktree at `.claude/worktrees/card-experiment-handoff-7c5b27`).
Note: `git pull` alone did not bring in `scripts/claude_luna_codex.py` (it lives on `origin/main`, not on this branch), so the script was materialised with `git checkout origin/main -- scripts/claude_luna_codex.py` (no other files touched). Date (UTC): 2026-09-27.

## 1. Selftest

Command: `python3 scripts/claude_luna_codex.py --selftest`

Output (verbatim):

```
selftest ok: model gpt-6-luna, output-file True
```

Matches the expected form `selftest ok: model gpt-6-luna, output-file True/False` (here output-file True).

## 2. Three-call parallel check

Command: `python3 -c "import sys,time;sys.path.insert(0,'scripts');from concurrent.futures import ThreadPoolExecutor as T;import claude_luna_codex as L;t=time.time();r=list(T(3).map(lambda i:L.call('Reply with the number %d and nothing else.'%i,timeout=180),[1,2,3]));print(r,round(time.time()-t,1),'s')"`

Output (verbatim):

```
['1', '2', '3'] 10.9 s
```

All three parallel calls returned the requested numbers (`1`, `2`, `3`) in ~10.9 s wall-clock, so the calls ran concurrently and correctly.

## 3. Script hash

Command: `shasum -a 256 scripts/claude_luna_codex.py`

Output (verbatim):

```
342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e  scripts/claude_luna_codex.py
```

## Summary

- Selftest: PASS (`selftest ok: model gpt-6-luna, output-file True`).
- Parallel 3-call check: PASS (`['1', '2', '3']` in 10.9 s).
- SHA-256: `342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e`.
- Nothing else was edited, stopped, or deleted; no ssh; nothing under `~/.codex` was read; no WebFetch.
