# Premonition Desk: design (v1)

Ben's own Mac assistant app. Ideas borrowed from OpenBot (desktop chat app with threads and tool cards)
and Meta's Muse agent (built-in browser, long autonomous multi-step tasks, acts for you), but every line
is written fresh here. No OpenBot/OpenCode code, no cloud agents (no Claude, OpenCode, Codex, etc.).
The only brain is the local Premonition gateway.

## Stack
- Electron 33, plain JavaScript (CommonJS in main, plain ES in renderer), no bundler, no framework.
- Built-in browser = an Electron `WebContentsView` beside the chat, persistent partition `persist:desk`
  (sign-ins survive restarts). Driven from the main process (executeJavaScript + sendInputEvent).
- Screen control = `deskhelper`, a small Swift CLI (AXUIElement + CGEvent + NSWorkspace), compiled on the
  Mac with `swiftc`. Electron spawns it; it prints JSON.
- Model = OpenAI-compatible chat completions at `http://127.0.0.1:8090/v1` (models `qwen36-auto`
  default, `qwen36` thinking, `qwen36-fast`). Streaming SSE. The gateway already writes every call to the
  diary for sleep, so the app does not log separately.
- Diary memory = spawn `~/learner-ops/assistant/diary_mcp.py` (stdio MCP: tools diary_search, diary_read,
  diary_days). If the file or python is missing, the diary tool is simply left out.

## Speed rule (the big lesson from OpenBot: 36k tokens of setup per chat = minutes cold on the M1)
- System prompt + tool list are CONSTANT strings: no time, no paths, no per-chat text. Target under
  ~2k tokens total (test enforces < 9000 characters for system + JSON tool schemas).
- Date/time goes into the user message as a one-line prefix, never the system prompt.
- Tool results are trimmed (page snapshot <= 3500 chars, page text <= 6000 chars per page, shell <= 4000).
- History is append-only so the server's prompt cache keeps hitting. Only when the estimated context
  passes ~24k tokens do we compact once: old tool results become "[older result omitted]".
- The gateway warms a stable prefix at startup; since ours never changes, the first reply is fast.

## Agent loop (main process, agent.js)
User message -> loop: call model with tools -> stream text/reasoning to UI -> if tool calls, run them
(one at a time), append results, repeat. Stops when the model answers with no tool call, after
`maxSteps` (default 40) or when Ben presses Stop (AbortController cancels the HTTP request and tools).
Tool-call parsing: use `delta.tool_calls` when present; fallback parser for Qwen-style
`<tool_call>{"name":..,"arguments":..}</tool_call>` (and `<function=name><parameter=k>v</parameter></function>`)
inside content, in case the server's parser misses one.

Autonomy switch (top bar): "Ask first" vs "Hands-off".
- Ask first: shell commands, screen clicks/typing/keys, and browser typing into password/payment fields
  need Ben's OK on an inline card (Allow once / Allow for this task / Deny).
- Hands-off: everything runs, except shell commands matching a danger list (rm -rf, sudo, diskutil,
  mkfs, shutdown, `> /dev/`, curl|sh, git push --force ...) and anything the model itself flags with
  ask_user. Stop is always one click (also Esc).

## Tools (14, short schemas)
web_search(query)                       DuckDuckGo HTML results, top 8 (title, url, snippet). Main-process fetch.
browser_go(url)                         Navigate; returns snapshot.
browser_click(id)                       Click element [id] from the last snapshot; returns snapshot.
browser_type(id, text, enter?)          Focus, replace text, optional Enter; returns snapshot.
browser_scroll(direction)               up|down one screen; returns snapshot.
browser_back()                          History back; returns snapshot.
browser_read(page?)                     Main readable text of the page, 6000-char pages.
screen_look(app?)                       Front app (or named app): windows + numbered UI elements (from deskhelper).
screen_click(id? | x?,y?, double?)      Press element [id] from the last look, or click a point.
screen_type(text)                       Type into the focused control.
screen_key(keys)                        e.g. "cmd+t", "return", "cmd+shift+4".
open_app(name)                          Launch/focus a Mac app.
run_shell(command)                      zsh -lc, cwd ~, 60 s timeout.
diary_search(query)                     Search past chats (only when diary_mcp.py is available).
ask_user(question)                      Pause and ask Ben; his reply is the tool result.

Snapshot format (browser): first line `URL: ... | Title: ...`, then up to ~120 visible interactive
elements as `[12] button "Add to cart"`, `[13] input(text) "Search" value=""`, `[14] link "Docs" -> /docs`,
then `Text: <first ~800 chars of visible text>`. Elements get `data-desk-id`; ids reset each snapshot.
While the agent acts, a small amber badge flashes on the element it clicks (Ben can watch).

## deskhelper (Swift CLI, JSON on stdout, exit code 0/1, errors as {"error": "..."})
deskhelper check                         {"accessibility":bool,"screenRecording":bool}
deskhelper ask-permissions               triggers both macOS prompts
deskhelper look [--app NAME] [--max 150] {"app","pid","windows":[{"title","frame"}],"elements":[{"id","role","title","value","frame":[x,y,w,h]}]}
                                         also saves id->element info to ~/Library/Caches/premonition-desk/last_look.json
deskhelper press ID                      AXPress on that element (re-found by path), else click its center
deskhelper click X Y [--double] [--right]
deskhelper type TEXT                     CGEvent unicode strings in chunks of 20 chars
deskhelper key COMBO                     cmd/shift/alt|opt/ctrl + key name or letter (return, tab, esc, space, delete, up, down, left, right, f1..f12)
deskhelper scroll DY                     lines, negative = down
deskhelper open-app NAME                 NSWorkspace launch or activate
deskhelper screenshot PATH [--max 1280]  JPEG of main display, scaled (shown to Ben in the chat; not sent to the text-only model)

## UI (its own look, not OpenBot's)
Warm dark "espresso" palette with an amber accent (light mode follows the system):
bg #14110f, surface #1c1815, raised #25201c, line #3a322b, text #efe7de, muted #a89a8c, accent #f5a524,
danger #ef6b5b, ok #7cc68b. Font: -apple-system / "SF Pro Text"; tool details in ui-monospace.
Layout:
- Top bar (draggable, leaves room for the traffic lights): threads button, thread title, model picker
  (Auto / Think / Fast pills), autonomy switch (Ask first / Hands-off), status dot for the gateway.
- Left: chat column (resizable, default 460 px). Messages as plain text blocks (assistant) and amber-
  edged bubbles (Ben). Agent steps are a vertical "trail": small round icon + one-line summary
  ("Opened amazon.com", "Clicked [12] Add to cart"), click to expand args/result. Thinking text is a
  collapsed "Thought for 6 s" line. Composer at the bottom: multiline, Enter sends, Shift+Enter newline,
  Stop replaces Send while running.
- Right: work pane with two tabs, Browser (address pill, back/forward/reload, the live view) and Screen
  (latest deskhelper screenshot + the element list). Ben can use the browser himself at any time.
- Threads drawer slides over the chat from the left: new thread, list by recent, rename, delete.
- Settings sheet: gateway URL, default model, max steps, diary_mcp path, python path, helper path,
  "Check permissions" button (runs deskhelper check / ask-permissions).
Threads are saved as JSON in app.getPath('userData')/threads/.

## Files
desk/package.json, desk/main.js (window, views, IPC), desk/preload.js, desk/src/agent.js,
desk/src/llm.js (SSE + tool-call parsing), desk/src/prompt.js (system prompt + tool schemas),
desk/src/tools/{browser,screen,shell,web,diary}.js, desk/src/store.js, desk/renderer/{index.html,app.css,app.js},
desk/helper/deskhelper.swift, desk/build-mac.sh (npm ci, swiftc, @electron/packager darwin arm64,
ad-hoc codesign, copy to /Applications/Premonition Desk.app), desk/test/*.test.js (node:test),
desk/test/e2e.js (xvfb: fake gateway drives the real browser view against a local page).

## Vision (when the gateway can see)
The deployed 3-bit model is text-only today; an image-capable server (mlx-vlm) is being added on the M3.
Setting `vision` (off | on, default off). When on, screen_look and browser snapshots also attach a JPEG
(max 1280 px) as a follow-up `user` message with an `image_url` data URL right after the tool result,
and screen_click accepts x,y from what the model sees. Only the newest image is kept in history (older
ones become "[older screenshot omitted]") so context stays small. Off = text-only accessibility list.

## Ideas taken from Muse (feature level only)
- Asks before sensitive actions (send a message/email, buy, submit a payment form, delete): the prompt
  tells the model to call ask_user first, and the danger list backs it up in Hands-off mode.
- Audit trail: every action is in the step trail of the thread and saved with it.
- Plans: for multi-step jobs the model first writes a short numbered plan in its reply (prompt rule);
  the UI shows the latest plan pinned above the trail.
- Steer while running: Ben can type while the agent works; the message is queued and injected as a user
  message before the next model call (like a "steer"), instead of waiting for the task to end.
