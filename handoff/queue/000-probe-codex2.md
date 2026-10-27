COMMON RULES: READ-ONLY. Edit, stop, or delete nothing. No ssh. NEVER read, cat, list, or print anything under ~/.codex (auth, config, sessions) or any key/token. NEVER WebFetch. Finish within 10 minutes.
YOUR TASK (Director, 2026-09-27 03:34 UTC; Ben 03:25 "you can use unlimited luna"): find the exact GPT-6 Luna model id for the Codex CLI with tiny calls.
C="/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex"; D=$(mktemp -d)
1. `"$C" exec --help | head -80` (paste).
2. For each M in: gpt-6-luna, gpt-6.0-luna, luna, gpt-6-luna-codex: run `"$C" exec -m "$M" -C "$D" --sandbox read-only --skip-git-repo-check "Reply with exactly: ok" < /dev/null 2>&1 | tail -15` with a 90-second limit (e.g. run it in the background and stop only that exact child PID if it passes 90 s). Paste each result. If a flag above is rejected, drop it and note that.
3. Also once with no -m (default model) and paste the tail, including any line naming the model.
4. `rm -rf "$D"`.
Write to handoff/replies/000-probe-codex2.md with a top line: the first M that answered "ok" (or "none"), and the exact working command form.
PUSH: handoff/replies/000-probe-codex2.md
