Running Luna selftest and parallel check — pulling latest and writing results.
Helper script is ready — now running the selftest and parallel verification.
Selftest and parallel check both passed — now writing the reply file.
Push via shell is blocked in this environment — I'll commit the reply locally and then confirm.
Done except the final push, which this environment blocks. Exact report:

**1. Selftest** — `python3 scripts/claude_luna_codex.py --selftest`
```
selftest ok: model gpt-6-luna, output-file True
```
Matches the expected form.

**2. 3-call parallel check** — ThreadPoolExecutor(3) over `L.call('Reply with the number %d and nothing else.')`:
```
['1', '2', '3'] 10.9 s
```
All three returned correctly in ~10.9 s wall-clock (concurrent).

**3. Hash** — `shasum -a 256 scripts/claude_luna_codex.py`
```
342a0fb7e15ebf22da763c21eddecb0c58cfcbd43c74481d8421b5709023024e  scripts/claude_luna_codex.py
```

**Reply file:** `handoff/replies/000-luna-helper-selftest.md`, 1769 bytes (> 300), committed locally as `24766dc63` ("000-luna-helper-selftest: reply with selftest + 3-call parallel outputs"), containing only that file.

**Two deviations to know:**
- `git pull` did not bring in `scripts/claude_luna_codex.py` (it exists on `origin/main`, not on this branch), so I materialised just that file via `git checkout origin/main -- scripts/claude_luna_codex.py`, then unstaged it — file stays on disk, commit contains only the reply. Nothing else edited/stopped/deleted, no ssh, nothing under `~/.codex` touched, no WebFetch.
- **PUSH failed:** this environment denies all `git push*` calls at the tool-policy level, so the commit is local only. To finish, run this one command from the worktree:
  `git push origin HEAD`
