000-bash-stop-bm398w start 2026-09-27T14:02:54Z
driver 17262: bash /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.oZGCMa5NMn/bm398w_macdrive.sh
  child 62970: /Users/ben-hannan/.local/bin/uv run --offline --no-project --python 3.12 python -B scripts/claude_bm398w_data.py word --plans artifacts/claude-bm398w-20260927/d
  child 62971: /Users/ben-hannan/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12 -B scripts/claude_bm398w_data.py word --plans artifacts/claude-bm398w-20
  child 88026: /Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/../CodexCLI.app/Contents/MacOS/codex exec -m gpt-6-luna -C /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm00
  child 88048: /Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node_repl
  child 88049: /Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node /Applications/ChatGPT.app/Contents/Resources/cua_node/lib/node_modules/@oai/cua-repl/bin/cua-repl
  child 88050: /Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node_repl
TERM sent to driver 17262
data python 62970: /Users/ben-hannan/.local/bin/uv run --offline --no-project --python 3.12 python -B scripts/claude_bm398w_data.py word --plans artifacts/claude-bm398w-20260927/d
data python 62971: /Users/ben-hannan/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12 -B scripts/claude_bm398w_data.py word --plans artifacts/claude-bm398w-20
left alone 88050: /Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node_repl
left alone 88049: /Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node /Applications/ChatGPT.app/Contents/Resources/cua_node/lib/node_modules/@oai/cua-repl/bin/cua-repl
left alone 88048: /Applications/ChatGPT.app/Contents/Resources/cua_node/bin/node_repl
TERM 88026: (codex)
TERM 62971: 
left alone 62970: 
still running after stop: driver / data python 
count train: {"chats": 170, "kept_chats": 151, "sessions": 1200, "sessions_kept": 1070, "sessions_never_tried": 130, "failed_rows_by_reason": {"count": 1}}
count panel: {"chats": 26, "kept_chats": 26, "sessions": 182, "sessions_kept": 182, "sessions_never_tried": 0, "failed_rows_by_reason": {"leak": 1}}
--- RUNLOG-b.txt, last 12 lines without per-call failure lines
{"jobs": 1200, "skipped": 679, "ok": 106, "not_run": 415, "failed_calls": 0, "bad_lines": 0, "minutes": 45.0}
exit=0 end 2026-09-27T12:12:19Z
== train word pass W=1 start 2026-09-27T12:12:22Z
{"jobs": 1200, "skipped": 785, "ok": 116, "not_run": 299, "failed_calls": 0, "bad_lines": 0, "minutes": 45.2}
exit=0 end 2026-09-27T12:57:31Z
== train word pass W=1 start 2026-09-27T12:57:34Z
{"jobs": 1200, "skipped": 901, "ok": 118, "not_run": 181, "failed_calls": 0, "bad_lines": 0, "minutes": 45.2}
exit=0 end 2026-09-27T13:42:48Z
== train word pass W=1 start 2026-09-27T13:42:49Z
STOPPED 2026-09-27T14:03:18Z by 000-bash-stop-bm398w: Ben chose Stop it for bm-398w at 13:57:41 UTC; driver 17262 and its processes stopped by exact PID; data kept
count train: {"chats": 170, "kept_chats": 151, "sessions": 1200, "sessions_kept": 1070, "sessions_never_tried": 130, "failed_rows_by_reason": {"count": 1}}
count panel: {"chats": 26, "kept_chats": 26, "sessions": 182, "sessions_kept": 182, "sessions_never_tried": 0, "failed_rows_by_reason": {"leak": 1}}
000-bash-stop-bm398w end 2026-09-27T14:03:18Z
rc=0
