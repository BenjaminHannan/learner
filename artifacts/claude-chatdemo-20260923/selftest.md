# chat-demo selftest (2026-09-23 builder run)

Port: **8765** (127.0.0.1; 8766 fallback never needed).
Base: exp 260 (138m + openers), loaded exactly as scripts/claude_openers260_run.py
(M.load_agent / load_base_cfg / make_daemon), STATE = ~/premonition-chat/state.
Start-up: daemon build 1.22 s (first smoke), `daemon ready in 1.0 s` (shell),
`daemon ready in 0.4 s` (launchd). Per-turn seconds below are the server's
measured turn times (machine was under load from sibling agents).

## 1. Direct 5-turn smoke (temp folder, uv run)

```
BUILD_SEC 1.22
TURN 0 (0.01 s) "Hi! My name is Ana."   -> 'Saved: your name is Ana.'
  saved: (USER, name, Ana); why: ears_stage=loop173b-name score=1.0
TURN 1 (0.00 s) "Ana lives in Lima."    -> 'Saved: your city is Lima.'
  saved: (USER, city, Lima); why: ears_stage=loop173-xhead score=1.0
TURN 2 (0.00 s) "Where does Ana live?"  -> 'your city is Lima.'
  saved nothing; answer OK trail F00002
TURN 3 (0.00 s) "Who lives in Lima?"    -> 'your city is Lima.'
  saved nothing; why: ears_stage=loop190-reverse score=1.0 records=[clarify]
  (weak spot: reverse lookup not answered as a who-question)
TURN 4 (0.00 s) "What is my name?"      -> 'Your name is Ana.'
  saved nothing; answer OK trail F00001
```

## 2. HTTP smoke on the launchd server (turn_index 5-9)

```
"Hi! My name is Ana."  -> 'Saved: your name is Ana.'  added=[[USER,name,Ana]]  0.022 s
"Ana lives in Lima."   -> 'Saved: your city is Lima.' added=[[USER,city,Lima]] 0.012 s
"Where does Ana live?" -> 'your city is Lima.'        saved nothing            0.128 s
"Who lives in Lima?"   -> 'your city is Lima.'        saved nothing            0.064 s
"What is my name?"     -> 'Your name is Ana.'         saved nothing            0.017 s
GET /notebook -> {"notebook": [["USER","city","Lima"],["USER","name","Ana"]]}
```

## 3. Flag -> push (exactly one line)

- `POST /flag {turn_index:3, note:"BUILDER TEST reverse-lookup weak spot check"}`
  -> `{"ok": true, "push": "queued (never pushed yet)"}`, then
  `GET /notebook` showed `"push_status": "pushed just now"`.
- `wc -l ~/premonition-chat/flags/flags.jsonl` -> **1**
- `git show origin/chat-flags:flags.jsonl | wc -l` (via flags-repo) -> **1**
- `git ls-remote origin chat-flags` -> `9cacb3d... refs/heads/chat-flags`
- flags-repo log: one commit `9cacb3d chat flag`; `ls-tree HEAD` -> only `flags.jsonl`.
- Flag line contains: time, user turn, reply, added, removed, why
  (ears_stage/ears_score/records), the BUILDER TEST note, and the 3 prior
  turns as context. Nothing else was pushed (no transcript, no state).
- No further flags were made after this test. The single flag line is the
  builder's own test (note prefixed BUILDER TEST).

## 4. New notebook (POST /reset), twice (nohup server + launchd server)

- `POST /reset` -> `{"ok": true, "moved_to": ".../old/state-<time>"}`.
- `GET /notebook` after -> `{"notebook": []}` (empty).
- `ls ~/premonition-chat/old/` shows the moved `state-*` folders with
  daemon.log.jsonl, done, inbox, notebook, outbox intact (moved, not deleted).

## 5. Restart via launchctl keeps the notebook

- Before: notebook `[["USER","city","Lima"],["USER","name","Ana"]]`.
- `launchctl kickstart -k gui/$(id -u)/com.premonition.chat` -> rc 0,
  `/ready` true again within ~2 s.
- After: `GET /notebook` -> same 2 facts; `POST /turn "Where does Ana live?"`
  -> `'your city is Lima.'` (0.009 s, answer OK trail F00002).

## 6. Page + start.sh

- `GET /` serves the page (title "Premonition Chat (exp 260 demo)").
- Header line present verbatim; flag-disclaimer line present verbatim.
- `./scripts/claude_chatdemo_start.sh` while serving -> exit 0, no-op.

## 7. launchd problems found and fixed (honest report, 2 deviations)

1. `uv run ...` as a launchd job **hangs forever at 0.00 CPU** (sampled 8+ min:
   main thread stuck in `getcwd -> open`, no child spawned, nothing logged).
   Same command works fine in a login shell.
2. Deeper cause (proven by probe): launchd-spawned processes get
   `Operation not permitted` on the worktree: `/bin/pwd` with
   WorkingDirectory=/tmp prints fine, with WorkingDirectory=<worktree> prints
   `pwd: .: Operation not permitted`. This is macOS TCC: ~/Desktop is
   protected; the interactive shell has access, launchd children (uv, python)
   do not. CPython itself hangs in `_Py_wgetcwd` during interpreter init.
   So the server **cannot run with its working directory in the worktree**
   under launchd.
3. Fix: `~/premonition-chat/runtime/` holds a verbatim copy of the runtime
   files (scripts/*.py + page, loop260 config, ltt_summary.json,
   relation_table_v1.json; all diff-verified identical except the config's
   single `tau_hat_path`, repointed at the copy). An audit hook over daemon
   build + 8 turns proved these are the ONLY repo files the daemon reads
   (besides .py imports). launchd runs persistent-venv python
   (`~/premonition-chat/chatdemo-venv`, CPython 3.12 + torch + numpy installed
   offline from uv's cache -- the same stack start.sh's uv command resolves)
   with WorkingDirectory=`~/premonition-chat/runtime`. The plist copy in this
   folder documents this in a NOTE comment. start.sh is unchanged (uv command,
   works in a login shell). Model behaviour is unchanged: same code, same
   config values, same mailbox turn path.
4. `handoff/kit/mimo/watcher.sh` named in the task does not exist (only
   `watch.sh`, which has no outbox-repo setup); the flags push was implemented
   per the task's inline description instead (git init, same remote url,
   branch chat-flags, fetch + reset if exists, commit "chat flag", push
   HEAD:chat-flags, retry-on-next-flag with "push pending" status).

## Handover state

- Test STATE moved to `~/premonition-chat/old/`; server restarted; Ben starts
  with an EMPTY notebook. Transcript (11 builder turns) kept on disk for
  provenance; flags file keeps the 1 BUILDER TEST line (on chat-flags too).
- Desktop: `Premonition Chat.webloc` opens http://127.0.0.1:8765.
