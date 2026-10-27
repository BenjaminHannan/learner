# Premonition Desk

Ben's own Mac assistant app: a chat on the left, a built-in browser and a screen view on the right.
The only brain is the local Premonition gateway (OpenAI-compatible chat completions). Everything the
assistant does shows up as a step trail you can expand, and the whole thread is saved.
The spec is in `DESIGN.md`.

## Run in development

```
cd desk
npm install
npm start          # electron .
npm test           # unit tests (node:test, no Electron needed, runs on Linux)
npm run e2e        # real Electron under xvfb: fake gateway drives the browser view (Linux)
```

The e2e writes a screenshot to `desk/test/out/ui.png` (git-ignored) and prints its path.

## Build and install on the Mac (Apple silicon)

```
cd desk
./build-mac.sh
```

It runs `npm ci`, compiles `helper/deskhelper.swift` with `swiftc -O` (skipped with a warning if
`swiftc` is missing, install the Xcode command line tools with `xcode-select --install`), packages
with `@electron/packager`, ad-hoc signs (`codesign --force --deep -s -`) and copies the app to
`/Applications/Premonition Desk.app`. If macOS complains on first launch, right-click the app and choose Open.

## Permissions to click once

Screen control needs two macOS permissions for "Premonition Desk" (System Settings > Privacy & Security):

1. **Accessibility** (to read UI elements, click and type)
2. **Screen Recording** (for screenshots)

Open Settings in the app and press **Ask for them** (triggers both prompts), then **Check permissions** to confirm.
If you rebuild and re-sign the app, macOS may ask again.

## Settings

Gear icon in the top bar. Saved in `settings.json` in the app's userData folder.

| Setting | Default | Notes |
| --- | --- | --- |
| Gateway URL | `http://127.0.0.1:8090/v1` | `/chat/completions` is appended |
| Default model | `qwen36-auto` | top bar pills: Auto = `qwen36-auto`, Think = `qwen36`, Fast = `qwen36-fast` |
| Max steps | 40 | model calls per task |
| Parallel runs | 2 | model runs at once, primary plus helpers; extra runs queue |
| `helperMode` (settings.json only) | `hands-off` | autonomy for helper agents |
| Vision | off | when on, screen looks and browser snapshots also send a JPEG (newest only) |
| diary_mcp.py path | `~/learner-ops/assistant/diary_mcp.py` | stdio MCP server, tool `diary_search` |
| Python path | `~/learner-ops/.venv/bin/python` if present, else `python3` | |
| deskhelper path | bundled in the app's Resources | falls back to `desk/helper/deskhelper` or `desk/build/deskhelper` in dev |

The diary tool is included in the tool list only if the diary server starts at app launch. The tool
list is then fixed for that run (changes need a restart) so the model's prompt cache keeps hitting.

Autonomy switch in the top bar:
- **Ask first**: shell commands, screen clicks/typing/keys, and typing into password or payment fields need your OK on an inline card (Allow once / Allow for this task / Deny).
- **Hands-off**: everything runs, except shell commands on the danger list (`rm -rf`, `sudo`, `diskutil`, `mkfs`, shutdown, writes to `/dev/`, `curl | sh`, force push, ...). The model is also told to call `ask_user` before sending, buying, paying or deleting.

Stop (button or Esc) cancels the request and any running tool. Typing while a task runs queues a steer note that is injected before the next model call.

## Helpers (sub-agents)

Ask Premonition to hand off a long or repeating job ("every morning at 8, check X and tell me what changed").
It starts a helper with `agent_start` (one-off, `every` 30m/2h/1d, or daily `at` 08:00). Helpers run with the same
prompt and tools, in their own hidden browser and their own thread, listed under **Agents** in the threads drawer
(Run now / Pause / Delete). When one finishes you get a notification and a note in the chat that started it, which
the assistant also sees with your next message. Schedules live in `helpers.json` and only fire while the app is
open; a missed run happens once at launch. Details in `DESIGN.md`.

## How it talks to the gateway

- `POST {gatewayUrl}/chat/completions` with `stream: true`, `model`, `messages`, `tools` (18 tools, 17 without the diary).
- The system prompt and tool schemas are constant (about 5.3k characters; a test keeps them under 9000). The date goes in a `[Tue 2026-10-27 14:05]` prefix on each user message.
- Streamed `delta.content`, `delta.reasoning_content` / `delta.reasoning` and `delta.tool_calls` (by index) are accumulated. If the server fails to parse a Qwen-style call, `<tool_call>{json}</tool_call>` and `<function=name><parameter=k>v</parameter></function>` in the text are parsed instead.
- History is append-only. Past ~24k estimated tokens (chars / 3.5) old tool results are replaced once by `[older result omitted]`.
- The gateway already logs every call to the diary, so the app does not.

## Layout

`main.js` (window, IPC), `preload.js`, `src/agent.js` (loop, approvals, compaction), `src/llm.js` (SSE),
`src/prompt.js`, `src/store.js`, `src/helpers.js`, `src/tools/{browser,web,screen,shell,diary,agents}.js`, `renderer/`,
`helper/deskhelper.swift` (Swift CLI for screen control), `test/`.
Threads are JSON files in `userData/threads/`.
