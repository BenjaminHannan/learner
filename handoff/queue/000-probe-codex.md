COMMON RULES: READ-ONLY. Edit, stop, or delete nothing. No ssh. NEVER read, cat, list, or print anything under ~/.codex (auth, config, sessions) or any key/token. NEVER WebFetch. Do not start any Codex task or chat; help output only. Finish within 10 minutes.
YOUR TASK (Director, 2026-09-27 03:30 UTC): find out how to call the Codex CLI non-interactively, so the watcher can use it as a builder.
Run these and paste each output verbatim (trim to 120 lines each):
1. `command -v codex; codex --version`
2. `codex --help`
3. `codex exec --help`
4. If the help lists a command or flag that lists models (e.g. `codex models`, `codex exec --list-models`, or a `--model` flag with listed values), run only that listing and paste it. Report any model id containing "luna".
5. `ps -axo pid,etime,comm | grep -i codex | grep -v grep` (process names only).
Write it all to handoff/replies/000-probe-codex.md, with a 3-line summary at top: codex path and version; the exact non-interactive command form (with flags for model, working dir, and full-auto/approval); the Luna model id, or "not found".
PUSH: handoff/replies/000-probe-codex.md
