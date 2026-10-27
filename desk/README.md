# Premonition Desk

Ben's own Mac assistant app (the assistant is called Glim): just a chat window. When Glim uses the web, a live browser
card appears in the chat; click it to open the real page in a browser panel inside the same window (a split on the right, or a full-window sheet on narrow windows) that you can use too (sign-ins included). A top-bar Browser button shows or hides it.
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

The e2e writes screenshots to `desk/test/out/` (git-ignored) and copies them to `desk/docs/img/ui-v2-*.png`: chat (light/dark), welcome, running with a live browser card, the in-window browser panel (wide, light/dark, and the narrow sheet), the sign-in banner, the Permissions card, the password guard, Settings, and the status pill (collapsed/expanded/working, light/dark).

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

Gear icon in the top bar or **Cmd+,**. Everything applies immediately and is saved in `settings.json` in the app's userData folder.

| Group | Setting | Default | Notes |
| --- | --- | --- | --- |
| Model | Gateway URL | `http://127.0.0.1:8090/v1` | `/chat/completions` is appended; **Test connection** shows the latency |
| Model | Default mode | Auto (`qwen36-auto`) | Auto / Think (`qwen36`) / Fast (`qwen36-fast`), same as the top-bar pills |
| Autonomy | Main agent | Ask first | Ask first or Hands-off |
| Autonomy | Helpers (`helperMode`) | Hands-off | same choice for helper agents |
| Autonomy | Max steps | 40 | model calls per task (1 to 200) |
| Autonomy | Danger list | fixed | shown read-only; these shell commands always need your OK |
| Helpers | Runs at once (`maxParallel`) | 2 | primary plus helpers; extra runs queue (1 to 4) |
| Memory | Use my diary | on | adds/removes the `diary_search` tool right away |
| Memory | diary_mcp.py path, Python path | `~/learner-ops/...`, venv or `python3` | |
| Screen control | deskhelper path | bundled | **Check permissions**, **Ask macOS**, and buttons that open System Settings > Privacy > Accessibility / Screen Recording |
| Vision | Send screenshots to the model | off | newest image only |
| Appearance | Theme | System | System / Light / Dark |
| Appearance | Text size | M | S / M / L |
| Appearance | High contrast | off | stronger text and borders |
| Appearance | Status pill | on | the floating pill at the top of the screen |
| Startup | Open at login | off | starts hidden |
| Startup | Keep running when the window is closed | on | closing hides the window; helpers keep going; Cmd+Q quits |
| Startup | Global shortcut | Option+Space | shows/hides Glim from any app and focuses the composer; click the button and press the keys, Backspace turns it off |

Changing the model, gateway or diary setting re-warms the model (see below).

Autonomy switch in the top bar:
- **Ask first**: shell commands and screen clicks/typing/keys need your OK on an inline card (Allow once / Allow for this task / Deny).
- **Hands-off**: everything runs, except shell commands on the danger list (`rm -rf`, `sudo`, `diskutil`, `mkfs`, shutdown, writes to `/dev/`, `curl | sh`, force push, ...). The model is also told to call `ask_user` before sending, buying, paying or deleting.

Passwords: the agent never types into a password or payment field. The browser panel opens with "Sign in here yourself; Glim can't see
what you type. Click Done when finished." and Glim waits. The composer warns if a message looks like it contains a password.

Stop (button or Esc) cancels the request and any running tool. Typing while a task runs queues a steer note that is injected before the next model call (shown once, as a "Steer" bubble).
If the model repeats the same call three times, the app stops the loop; if it happens again it asks you (or opens the sign-in hand-off on a sign-in/passkey page).

## Status pill

A small pill pinned top-center on every Space (our own design): Glim plus one line ("Opened gmail.com", "Waiting for you",
"Done: weather report", or a sad Glim and "Something went wrong"). Hover for the agent, current step, time, error text and
buttons (Open, Stop, Allow/Deny). It fades 8 s after a task finishes; errors and "waiting" stay until you look. Turn it off in Settings > Appearance.

## First reply speed

On launch, whenever the gateway comes back (checked every 5 s while down, 30 s while up) and after a model/gateway change, the app sends one tiny
request (`X-Premonition-Warm: 1`, model `qwen36-fast`, `max_tokens` 1, user ".") with exactly the same system prompt and tools as a real request, so the
gateway's prompt cache is warm before you type. The top bar says "Warming up..." then "Ready"; typing is never blocked. The window opens before the
diary, helper scheduler, warm-up and browser start. Hover over an answer to see its time to first token.

## Helpers (sub-agents)

Ask Premonition to hand off a long or repeating job ("every morning at 8, check X and tell me what changed").
It starts a helper with `agent_start` (one-off, `every` 30m/2h/1d, or daily `at` 08:00). Helpers run with the same
prompt and tools, in their own browser (the card shows in the helper's thread) and their own thread, listed under **Agents** in the threads drawer
(Run now / Pause / Delete). When one finishes you get a notification and a note in the chat that started it, which
the assistant also sees with your next message. Schedules live in `helpers.json` and only fire while the app is
open (or running in the background: closing the window only hides it); a missed run happens once at launch. Details in `DESIGN.md`.

## How it talks to the gateway

- `POST {gatewayUrl}/chat/completions` with `stream: true`, `model`, `messages`, `tools` (18 tools, 17 without the diary; `stream: true`, `tool_choice: auto`).
- The system prompt and tool schemas are constant (about 6.4k characters; a test keeps them under 9000). The date goes in a `[Tue 2026-10-27 14:05]` prefix on each user message.
- Streamed `delta.content`, `delta.reasoning_content` / `delta.reasoning` and `delta.tool_calls` (by index) are accumulated. If the server fails to parse a Qwen-style call, `<tool_call>{json}</tool_call>` and `<function=name><parameter=k>v</parameter></function>` in the text are parsed instead.
- History is append-only. Past ~24k estimated tokens (chars / 3.5) old tool results are replaced once by `[older result omitted]`.
- The gateway already logs every call to the diary, so the app does not.

## Layout

`main.js` (window, browser views and panel stacking, IPC, wiring), `preload*.js`, `src/agent.js` (loop, approvals, loop guard, compaction), `src/llm.js` (SSE, shared request builder),
`src/warm.js` (self-warm), `src/perms.js` (Permissions card helpers), `src/pillwin.js` + `src/pillstate.js` (status pill), `src/cards.js`,
`src/prompt.js`, `src/store.js`, `src/helpers.js`, `src/tools/{browser,web,screen,shell,diary,agents}.js`, `renderer/`,
`helper/deskhelper.swift` (Swift CLI for screen control), `test/`.
Threads are JSON files in `userData/threads/`.

## Browser panel and Permissions card
The browser is not a separate window. The main window holds a stack of native views: the app UI (a transparent-background
`WebContentsView` filling the window) and one browser view per thread. A closed panel keeps the browser view attached at the panel's
full size *underneath* the UI, so the agent can keep browsing and the card thumbnails keep updating; opening the panel lifts that one
view above the UI over the panel's content rect. Only the status pill is a second window.

The Permissions card (first launch on a Mac, Settings > Screen control > Permissions, or when a screen tool is refused) has one row per
macOS permission with a live status dot, an Open Settings button, and a draggable tile of the app icon to drop into System Settings.
