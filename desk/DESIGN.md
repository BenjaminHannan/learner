# Premonition Desk: design (v2)

Ben's own Mac assistant app. Ideas borrowed from OpenBot (desktop chat app with threads and tool cards)
and Meta's Muse agent (built-in browser, long autonomous multi-step tasks, acts for you), but every line
is written fresh here. No OpenBot/OpenCode code, no cloud agents (no Claude, OpenCode, Codex, etc.).
The only brain is the local Premonition gateway.

## Stack
- Electron 33, plain JavaScript (CommonJS in main, plain ES in renderer), no bundler, no framework.
- Built-in browser = an Electron `WebContentsView` inside the main window (see "Browser: cards and in-window panel"), persistent
  partition `persist:desk` (sign-ins survive restarts). Created lazily on first use, driven from the main process
  (executeJavaScript + sendInputEvent). There is no permanent browser pane: the window is just the chat.
- Screen control = `deskhelper`, a small Swift CLI (AXUIElement + CGEvent + NSWorkspace), compiled on the
  Mac with `swiftc`. Electron spawns it; it prints JSON.
- Model = OpenAI-compatible chat completions at `http://127.0.0.1:8090/v1` (models `qwen36-auto`
  default, `qwen36` thinking, `qwen36-fast`). Streaming SSE. The gateway already writes every call to the
  diary for sleep, so the app does not log separately.
- Diary memory = spawn `~/learner-ops/assistant/diary_mcp.py` (stdio MCP: tools diary_search, diary_read,
  diary_days). If the file or python is missing, the diary tool is simply left out.

## Speed rule (the big lesson from OpenBot: 36k tokens of setup per chat = minutes cold on the M1)
- System prompt + tool list are CONSTANT strings: no time, no paths, no per-chat text. Target under
  ~2k tokens total (test enforces < 9000 characters for system + JSON tool schemas; currently about 6.4k).
- Date/time goes into the user message as a one-line prefix, never the system prompt.
- Tool results are trimmed (page snapshot <= 3500 chars, page text <= 6000 chars per page, shell <= 4000).
- History is append-only so the server's prompt cache keeps hitting. Only when the estimated context
  passes ~24k tokens do we compact once: old tool results become "[older result omitted]".
- Self-warm (src/warm.js): the gateway's prompt cache makes a warm first token ~0.15 s, but the first Desk request
  after the model starts was 13 s because our system+tools prefix was not cached. So the app sends ONE non-streaming
  request (header `X-Premonition-Warm: 1`, model `qwen36-fast`, `max_tokens` 1, user message ".") built by the same
  `buildChatBody()` as real requests (same system string, same tools array and order, same `tool_choice`), so the
  prefix is byte-identical. When: at launch (after first paint), whenever the gateway goes from down to up (poll
  `/v1/models` every 5 s while down, 30 s while up), and after a model, gateway or tool-list change in Settings. It
  never blocks typing; the top bar shows "Warming up..." (Glim sleepy) then "Ready". Skipped if a run is in flight.
- Instant window: `show:false` + `backgroundColor`, shown on `ready-to-show`. Diary spawn, helpers scheduler, warm-up,
  status pill, global hotkey and any browser view are deferred until after first paint (the e2e checks the order).
  `agent:send` waits (max 3 s) for the tool list to be final so the first real request matches the warmed prefix.
- Stay ready: optional open-at-login (hidden), closing the window hides it (default; helpers keep running), Cmd+Q
  quits, global hotkey (default Option+Space) toggles the window and focuses the composer.
- Measure: time to first token is logged per request (`thread.requests[]`, and `ttftMs` on each assistant item) and
  shown on hover over the assistant's answer ("first word in 0.4 s").

## Agent loop (main process, agent.js)
User message -> loop: call model with tools -> stream text/reasoning to UI -> if tool calls, run them
(one at a time), append results, repeat. Stops when the model answers with no tool call, after
`maxSteps` (default 40) or when Ben presses Stop (AbortController cancels the HTTP request and tools).
Tool-call parsing: use `delta.tool_calls` when present; fallback parser for Qwen-style
`<tool_call>{"name":..,"arguments":..}</tool_call>` (and `<function=name><parameter=k>v</parameter></function>`)
inside content, in case the server's parser misses one.

Autonomy switch (top bar): "Ask first" vs "Hands-off".
- Ask first: shell commands and screen clicks/typing/keys need Ben's OK on an inline card (Allow once / Allow for
  this task / Deny). Typing into a password/payment field is never allowed for the agent in either mode: see "Sign-in hand-off".
- Hands-off: everything runs, except shell commands matching a danger list (rm -rf, sudo, diskutil,
  mkfs, shutdown, `> /dev/`, curl|sh, git push --force ...) and anything the model itself flags with
  ask_user. Stop is always one click (also Esc).

## Tools (17, short schemas)
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
open_app(name)                          Launch/focus a NON-browser Mac app. Refuses Safari/Chrome/Firefox/Arc/Edge/Brave/Opera/Vivaldi (use browser_go).
run_shell(command)                      zsh -lc, cwd ~, 60 s timeout.
diary_search(query)                     Search past chats (only when diary_mcp.py is available).
ask_user(question)                      Pause and ask Ben; his reply is the tool result.
agent_start(name, task, every?, at?)    Start a helper agent (see Helpers). agent_list(). agent_stop(name_or_id).

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

## UI v2 (its own look, not OpenBot's)
Ben's feedback on v1: ugly, hard to see, huge empty right pane, walls of repeated text. v2 is chat-first.
- Palette (theme.css): warm near-black "espresso" (`#16120f` bg, `#1f1a16` surface) and warm paper in light mode, one
  amber accent used sparingly, hairline borders as 10-16% overlays. Body text `#f7f1e9` on dark (16:1), secondary
  `#d2c5b6` (11:1), faint `#b9ab9b` (8:1); light mode `#241b14` / `#4f4237` / `#6a5c4f`. Every text pair is >= 4.5:1;
  `test/desk.test.js` checks the tokens and the e2e audits the rendered DOM in both themes. Appearance has a High
  contrast toggle (secondary text becomes primary, borders strong) and text size S/M/L (15 / 16.5 / 18.5 px, 1.5 line height).
- Chat column centered, max 760 px. Ben's messages are soft filled bubbles on the right; Glim's answer is plain text
  next to a small Glim avatar; steps are small pills (icon + one line, chevron next to the label, expandable).
- One **activity group** per task: all steps, plan, thinking and short narration fold into one block: while running
  "Glim is working . 3 steps" with a live line for the newest step; when done it collapses to "Did 6 things . 14 s"
  (expand to see every step: the audit trail). Repeated narration is dropped, narration is clamped to two lines, the plan is a
  slim checklist inside the group (never a sticky overlay), and lines like `[Action: ...]` are hidden. Only the final answer is prominent.
  Approval / question cards and the live cards sit at the top of the group, always visible.
- Composer: one line growing to ~6 lines, Send / Steer / Stop. Typing a message that looks like a password
  ("my password is", "password:", "pw is", one-time codes) shows "Don't paste passwords here; I'll open a sign-in window
  instead" with Send anyway / Cancel.
- New chat: Glim, a greeting and four suggestion chips that fill the composer.
- Chrome text (top bar, buttons, labels, pills, placeholders, drawer) is `user-select:none`; message text stays selectable.
- Threads drawer slides over the chat from the left. Settings is a full sheet (Cmd+,), see below.
- Glim is alive but calm: blink, an occasional glance while idle, sleepy after 5 min idle; he never pops up
  except for errors, "waiting for Ben" and finished helper results.

## Browser: cards and in-window panel
Ben's feedback on the popup: "It should be in a browser thing in the app, not just in its own window. Everything should be built into
the original window." So there is no browser window any more; the only other window is the status pill.
- Browser off by default. When the agent uses a browser tool, a **live browser card** appears in that task's activity
  group: favicon, title, host, a live thumbnail (`capturePage`, 360 px JPEG q55, refreshed after every action and every
  1.5 s while the run is going) and a pulsing "Glim is browsing". The thumbnail is stored with the thread. Screen control gets the
  same kind of card. Cards, a link in an answer, a sign-in hand-off and the pill's "Open browser" all open the panel.
- **Panel** (renderer/panel.js + #bpanel): wide windows (>= 1000 px) get a right-hand split, default 58% of the width (min 420 px, chat
  keeps >= 360 px), with a draggable divider (width remembered; double-click resets) and the chat column reflowing to its left. Narrow windows get
  a full-window sheet under the top bar with a Chat (back) button. Chrome rendered by the main renderer: favicon + title, who is in control, **Take over / Hand back to Glim**,
  close (x), back / forward / reload, address field, and the sign-in banner ("Sign in here yourself; Glim can't see what you type." + Done / Not now).
  A top-bar **Browser** button appears once the open thread has a browser and toggles the panel. The panel shows the open thread's browser;
  switching threads switches (or closes) it.
- Take over really pauses Glim: the agent's browser tools wait (`holds` in main.js, abortable with Stop) until Hand back or close.
- **One browser view per thread** (chat threads and helper threads alike, key = thread id, same `persist:desk` partition). Idle chat-thread browsers are
  kept up to 4 besides the active one (oldest dropped); a helper's is dropped when its run ends; deleting a thread drops its browser. A card whose browser is gone opens a fresh one at the card's URL.
- **Stacking** (main.js): the window's `contentView` holds `[idle browser views ..., UI view, the open browser view]`. The UI view fills the window and is
  above every browser view that is not on show; it has a transparent view background (its page paints opaque) and the app starts with
  `--disable-backgrounding-occluded-windows`. Without those two things Chromium treats a view that is fully covered by the UI as occluded and stops painting it:
  measured under xvfb, a covered view had 0 animation frames and `capturePage` failed ("Current display surface not available"), and an off-window view was no better.
  With them, a closed browser stays attached at the panel's full size (same viewport as when open), so agent browsing, `sendInputEvent`/`insertText`, snapshots and
  card thumbnails all work with the panel closed. Nothing is parked off-screen or in another window.
- The renderer measures the content rect (#bSlot) and reports it with `browser:layout`; main sets every browser view's bounds to it and lifts the open
  one above the UI. The slide is a short JS animation: each frame moves the chrome and reports a shifted rect, so the page slides with it. While the divider is dragged,
  Settings / the screen viewer / Permissions are open, or the narrow drawer is out, the view drops below the UI (those overlays live in the UI view).
- "Closing" the window with keep-running on a Mac makes it see-through, click-through and unfocusable (not hidden) while browsers exist, because a hidden window stops painting its pages.
- Known gap: not verified on macOS hardware (only Linux under xvfb); `sendInputEvent` mouse moves for the divider are not delivered as pointer moves under xvfb, so the e2e drives the divider with synthetic pointer events.

## Permissions card (drag the app into System Settings)
A sheet inside the main window (renderer/perms.js, src/perms.js, no extra window): shown on first launch (Mac), from Settings > Screen control > Permissions,
and when a screen tool is refused for permissions (at most once a minute). One row each for Accessibility
(`x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension?Privacy_Accessibility`, falling back to the old `com.apple.preference.security` form), Screen Recording
(`?Privacy_ScreenCapture`) and an optional Automation row (no status; macOS asks per app). Each row: a status dot (deskhelper `check` combined with Electron's
`isTrustedAccessibilityClient(false)` / `getMediaAccessStatus('screen')`; polled every 2 s while the card is open and re-checked when the window regains focus), an Open Settings
button (`shell.openExternal`), and turns green when the permission flips. Below: a draggable tile with the real app icon and name, "Drag this into the list, then switch it on";
dragging calls `webContents.startDrag({file: <the .app bundle>, icon})` (IPC accepted only from the main window's webContents); clicking it calls `shell.showItemInFolder`.
The bundle is found by walking up from `app.getPath('exe')` to the `.app` directory (dev: the Electron executable). If deskhelper still reports "no" while the app itself is allowed, macOS is
listing the helper binary separately, so a second tile for deskhelper appears.

## Sign-in hand-off (no passwords in chat)
- `browser_type` into a password or payment field never types: the tool returns "Login needed: Ben is signing in
  himself" semantics: the browser panel opens with the banner "Sign in here yourself; Glim can't see what you type. Click Done
  when finished.", the chat card turns "Sign-in needed", the pill shows "Waiting for you: sign in", and the agent waits
  (abortable, holds no run slot). Done -> the panel closes, the tool result is "Login needed: Ben is signing in himself. He
  clicked Done. Fresh snapshot ...". "Not now" tells the model not to type credentials. Snapshots mask password values.
- The prompt says: never ask Ben for passwords or codes in chat; for sign-in, 2-step or passkey pages just act and the app hands off.

## Loop guard (agent.js)
The same tool call with the same arguments 3 times in a row is refused ("Stuck: ... Do NOT repeat it"); a second
identical click that leaves the page unchanged gets a "nothing changed" note. The next stuck event in the same run pauses and escalates
(`onStuck`): on a sign-in / passkey / 2-step page it opens the same sign-in hand-off, otherwise it asks Ben with an `ask_user`-style card. Scrolling is exempt.

## Status pill (src/pillstate.js, src/pillwin.js, renderer/pill.*)
Our own design of an always-on-top status pill: a small frameless transparent window pinned top-center under the menu bar,
on all Spaces and over full-screen apps, never focusable, click-through everywhere except the pill itself
(`setIgnoreMouseEvents(true,{forward:true})`, toggled on hover). One state source (`PillState`, priority error > waiting for
Ben > working > done) feeds the pill, the top-bar Glim and the dock badge so they never disagree.
- Collapsed (~236x38): Glim in the current mood + one line ("Opened gmail.com", "Waiting for you", "Done: weather report", sad Glim + "Something went wrong") and elapsed time.
- Hover (after a 150 ms intent delay) expands with a small spring (280 ms), collapses in 190 ms: agent, current step, time, error text,
  other agents, and buttons: Open (goes to that thread), Stop, Allow once / Deny for approvals, Open browser for sign-in, Dismiss.
- Shows while any agent/helper is active or has news; "done" fades after 8 s; errors and waiting stay until seen (opened or dismissed). Hidden while the chat window is in front.
- Appearance > "Status pill" turns it off.

## Settings (every key in store.js)
Model (gateway URL, default mode Auto/Think/Fast, Test connection with latency), Autonomy (main agent and helpers Ask first / Hands-off,
max steps, read-only danger list), Helpers (runs at once), Memory (diary on/off, diary_mcp path, python path), Screen control (deskhelper
path, Check permissions, Ask macOS, Open Accessibility / Screen Recording settings via `x-apple.systempreferences:` deep links), Vision, Appearance
(theme System/Light/Dark, text size, high contrast, status pill), Startup (open at login, keep running when closed, global hotkey recorder).
Changes apply immediately and persist (`settings.json`, values validated in `store.sanitize`). Gateway/model changes re-warm; diary changes
rebuild the tool list (and re-warm); theme drives `nativeTheme.themeSource`; the hotkey is re-registered.

## Files
desk/package.json, desk/main.js (window, views, IPC), desk/preload.js (+ preload-pill.js), desk/src/{agent,warm,perms,pillwin,pillstate,cards}.js,
desk/src/llm.js (SSE + tool-call parsing), desk/src/prompt.js (system prompt + tool schemas),
desk/src/helpers.js (schedules, scheduler, run slots, screen lock, notices), desk/src/tools/{browser,screen,shell,web,diary,agents}.js, desk/src/store.js, desk/renderer/{index.html,pill.html,*.css,app.js,panel.js,perms.js,md.js,guard.js,mascot.js,pill.js},
desk/helper/deskhelper.swift, desk/build-mac.sh (npm ci, swiftc, @electron/packager darwin arm64,
ad-hoc codesign, copy to /Applications/Premonition Desk.app), desk/test/*.test.js (node:test),
desk/test/e2e.js (xvfb: fake gateway drives the real browser, panel, permissions card, pill and UI against a local page; screenshots to test/out and docs/img/ui-v2-*.png).

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

## Helpers (sub-agents, including recurring ones)
The primary agent can delegate with `agent_start(name, task, every?, at?)`: no schedule = run once now;
`every` ("30m", "2h", "1d", minimum 5m) = run now, then at that interval; `at` ("08:00") = daily at that local
time (first run at the next 08:00). `agent_list()` shows status (idle / queued / running / waiting-for-Ben /
stopped), schedule, next run and the last result; `agent_stop(name_or_id)` aborts and removes the schedule
(the helper and its thread stay, as "stopped", until Ben deletes it). One prompt line tells the model to use them.
- Same prompt, same tool list: a helper is the same Agent class with the same system prompt and tool schemas
  (so the gateway's prompt cache is shared). The agent_* tools just answer "helpers can't start helpers" for a helper.
- A run's user message: `[date] You are helper '<name>'. Task: <task>. Finish with a short report.` Recurring
  helpers also get the previous report (<= 600 chars) so they can say what changed. Each run starts with fresh
  model history (the report carries over); the visible step trail keeps growing (last 400 items).
- Own thread per helper (`helper: id`, saved like any thread, listed under Agents, not Threads). Ben can open it and
  watch live. Typing in it steers a running helper; it cannot start a run (use Run now).
- When a run finishes: a UI-only "notice" item goes into the thread that started it (not in model history), a
  macOS notification shows the summary, and the queued notices are prepended to Ben's next message as one line,
  `[helper updates] name: summary; ...`, then cleared.
- Scheduler (`src/helpers.js`, state in `userData/helpers.json`): ticks every 30 s while the app is open. A helper
  whose time passed while the app was closed runs once on startup (its next run is a single time, then recomputed
  from now), never once per missed slot. Paused helpers are skipped.
- Concurrency: setting `maxParallel` (default 2; the M1 gives ~30 tok/s each at 2). Primary and helpers share one
  FIFO limiter; extra runs queue ("Waiting for a free slot"). A run waiting for Ben's answer gives its slot back.
- Autonomy: helpers use setting `helperMode` (default Hands-off) with the same danger list. An approval card or
  ask_user sets the helper to waiting-for-Ben, shows a notification, and the card waits in the helper's thread
  (replayed when Ben opens it).
- Browser: one `Browser` per agent (constructor takes a `WebContentsView`), attached under the UI like any thread browser (see "Browser: cards and in-window panel"; same `persist:desk` partition, so sign-ins are shared), created at run start and
  destroyed at run end. webRequest listeners are one per session, so a single dispatcher keys on webContents id.
- Screen control: `screen_*` and `open_app` take a global FIFO lock, taken by an agent's first screen tool and held
  until its run ends; others wait (abortable).
- UI: threads drawer has an Agents section above Threads: status dot, name, schedule ("every 2h", "daily 08:00",
  "once"), next run, last result, and Run now / Pause (Resume) / Delete.
