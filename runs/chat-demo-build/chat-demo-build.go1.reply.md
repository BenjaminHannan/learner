Building your Premonition chat demo — wiring up exp 260 for live testing.
Disk looks good and I've mapped the base setup — now digging into the daemon mechanics.
Base config confirmed — now running a smoke test to verify the model loads.
Smoke test passed — now building the chat server and page.
Server is live — now putting it through its paces over HTTP.
Core flows check out — now making it survive reboots and restart-proof.
The relaunched server isn't answering yet — checking what's happening.
The launcher process is stuck with no output — inspecting its log and looking for contention.
Venv server works — swapping the stuck launcher to use it directly.
Same hang with the venv binary — sampling the stuck process to pin it down.
No symlinks or odd mounts — probing launchd directly to see if the worktree path itself is the trigger.
Probes never ran (missing RunAtLoad) — fixing and rerunning.
Many of those are just CLI defaults — tracing actual runtime file opens to get the exact set.
Only three data files beyond scripts — checking layout, then staging the runtime copy.
Runtime staged — repointing its config at the local tau file.
Layout fix needed — nesting the scripts copy properly.
Launchd server is up and ready — running the full self-test suite against it.
Restart keeps the notebook — now verifying the page, start script, and reset on this server.
All green — writing the Desktop shortcut and the self-test record.
Final handover — fresh empty notebook, restart, and opening the page.
Chat demo built, tested, running. Report:

**Smoke (exp 260 base, direct, temp folder; build 1.22 s):** "Hi! My name is Ana." → 'Saved: your name is Ana.' (0.01 s) / "Ana lives in Lima." → 'Saved: your city is Lima.' (0.00 s) / "Where does Ana live?" → 'your city is Lima.' (0.00 s) / "Who lives in Lima?" → 'your city is Lima.' (0.00 s, reverse-lookup weak spot: clarify record, no who-answer) / "What is my name?" → 'Your name is Ana.' (0.00 s).

**Port 8765** (127.0.0.1; 8766 never needed). Start-up: daemon ready in 1.0 s (shell) / 0.4 s (launchd). HTTP smoke on launchd server reproduced all 5 replies (0.022/0.012/0.128/0.064/0.017 s).

**Self-tests (all pass):** flag → `flags.jsonl` exactly 1 line, `origin/chat-flags` exactly 1 line, one commit `9cacb3d chat flag`, branch contains only `flags.jsonl`; reset → notebook `[]`, old state moved to `~/premonition-chat/old/state-*` (2 dirs, nothing deleted); `kickstart -k` restart → both facts back, "Where does Ana live?" → Lima (0.009 s); `GET /` serves page with both required verbatim lines; `start.sh` exits 0 no-op while serving.

**Two problems, both fixed with documented deviations (see plist NOTE + selftest.md §7):** (1) `uv run` hangs at 0 CPU forever under launchd (sampled, getcwd/open); (2) launchd children get EPERM on the worktree — `/bin/pwd` probe: /tmp fine, worktree → `Operation not permitted` (macOS TCC protects ~/Desktop). So launchd runs `~/premonition-chat/chatdemo-venv` python (CPython 3.12 + torch + numpy, offline from uv cache) against diff-verified verbatim runtime copy `~/premonition-chat/runtime/` (only the config's `tau_hat_path` repointed; audit-hook proved these are the only repo files the daemon reads). `start.sh` unchanged (uv command, works in login shell). Model behaviour unchanged. Also: `handoff/kit/mimo/watcher.sh` doesn't exist (only `watch.sh`); flags push implemented per the task's inline spec.

**Handover state:** test STATE moved to `old/state-20260922-235816-handover`, server restarted, Ben's notebook verified empty (`[]`); transcript keeps 11 builder turns on disk; flags file/branch keep only the 1 BUILDER TEST line; page opened via `open` (rc 0); `Premonition Chat.webloc` on Desktop; plist loaded (`launchctl list` PID active, KeepAlive + RunAtLoad). No existing repo file edited; `git push` not run by me (denied) — 5 new files staged for the watcher.

**Exact file list (staged):** scripts/claude_chatdemo_server.py, scripts/claude_chatdemo_page.html, scripts/claude_chatdemo_start.sh, artifacts/claude-chatdemo-20260923/com.premonition.chat.plist, artifacts/claude-chatdemo-20260923/selftest.md.

CHAT-DEMO-READY
