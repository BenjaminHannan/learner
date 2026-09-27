Probing the Codex CLI for non-interactive use — collecting help and version info.
The Codex CLI isn't in PATH — I'll check the bundled binaries and draft the handoff.
Found a bundled Codex binary — I'll verify the exact outputs for the final report.
Report written — now I'll push the handoff file.
Done (read-only + help-only, no `~/.codex` reads, no Codex task started).

Wrote `handoff/replies/000-probe-codex.md` with 3-line summary at top:
1. `command -v codex` empty (not in PATH); bundled `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex` = `codex-cli 0.158.0-alpha.2`.
2. Non-interactive: `codex exec -m <MODEL> -C <DIR> --sandbox workspace-write -a never [--json] "<PROMPT>"`; full-auto `--dangerously-bypass-approvals-and-sandbox` (or `--approve-for-me`).
3. Luna model id: not found (no model-listing in help).

Verbatim outputs for `command -v codex; codex --version`, `codex --help`, `codex exec --help` (all `command not found`), `ps … | grep -i codex` (27 lines, process names only), plus supplemental bundled-binary `--version`/`--help`/`exec --help` are in the file.

Committed locally as `8fc75d620`. PUSH blocked: this environment denies `git push*` — run `git push origin HEAD` yourself to push `handoff/replies/000-probe-codex.md`.
