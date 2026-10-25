# Sleep mode (v1 design)

Ben's request (2026-10-25 21:34Z): he clicks **Sleep**; the assistant trains for as long as it is free, even for days.
Every hour it wakes, scans email and calendar read-only, tells Ben if something needs him, and goes back to sleep.
When sleep stops paying off, it switches to **practice**: it works out what kinds of jobs Ben uses it for (e.g. spreadsheets),
looks up new tricks (web pages, YouTube transcripts), and practises them in a sandbox with automatic checks.
Ben clicks **Wake** (or starts the assistant) and it stops and leaves a morning summary.

Runs on the MacBook. Pure stdlib Python 3.9+ (the Mac's assistant venv is 3.12; tests run on Linux). No pandas required.

## Layout

```
sleepmode/
  DESIGN.md        this file
  README.md        how to use it (Ben-facing, short)
  __init__.py
  __main__.py      python -m sleepmode ...
  config.py        Config dataclass; defaults overridden by ~/learner-ops/sleepmode/config.json
  state.py         paths, status.json, events.jsonl, notified-ids store, wake flag
  plateau.py       marginal-returns rule
  workers.py       sleep workers: FakeWorker, CommandWorker
  mlx_worker.py    reference real worker for the Mac (mlx_lm LoRA on diary + practice data, NLL quiz)
  checkin.py       hourly read-only check-in: scanners -> triage -> notify
  notify.py        macOS notification, inbox.md, optional ntfy push (off by default)
  scheduler.py     the main loop (state machine)
  cli.py           start | wake | status | summary | once
  install_mac.sh   Desktop launchers "Sleep Mode.command" / "Wake Up.command", copies to ~/learner-ops/sleepmode/app
  tools.py         ToolBox: web_search, fetch_page, python, diary_search, diary_read
  dreamcheck.py    check dreams against the diary (with tools) before a trainer uses them
  practice/
    __init__.py
    habits.py      what kinds of work Ben uses the assistant for (from the diary)
    research.py    trick cards: built-in seeds + web pages + YouTube transcripts, distilled by the model
    tasks.py       task families with exact automatic checkers (v1: spreadsheets on CSV)
    sandbox.py     run an attempt in a throwaway copy, no network, no writes outside it
    model.py       OpenAI-compatible chat client (+ FakeModel for tests)
    agent.py       tool-using loop (native tool calls or `TOOL: name {json}` text lines)
    loop.py        one practice round -> SFT examples + DPO pairs + pass rate
  tests/           unittest, all offline, no MLX needed
```

## Files on the Mac (`~/learner-ops/sleepmode/`, override with env SLEEPMODE_HOME)

- `config.json` optional overrides
- `status.json` live state: mode, since, hours slept, last quiz, last check-in, pid
- `events.jsonl` one JSON line per event (chunk_done, checkin, switch, practice_round, wake, error)
- `WAKE` presence = wake request (Wake launcher / `python -m sleepmode wake` writes it)
- `SLEEPING` presence while the loop runs (pid inside); the assistant's serve.sh can treat it like PAUSE_OTHERS
- `inbox.md` notifications, newest first
- `notified.json` ids already notified (no repeats)
- `practice/YYYY-MM-DD/{sft.jsonl,pairs.jsonl,rounds.jsonl}` practice output; `practice/tricks/<kind>.json` trick cards
- `worker/` the worker's own data (adapters, quiz history)

## Scheduler (scheduler.py)

State machine, modes `sleep` and `practice`. One loop iteration = one "hour" (config `hour_s`, default 3600; tests use tiny values).

```
start: write SLEEPING; event start; mode = sleep
loop:
  if wake requested -> break
  if pause file (~/learner-ops/PAUSE_OTHERS) exists or memory pressure >= warn -> skip work this hour (event paused), still check in
  mode sleep:    r = worker.run_chunk(budget_s = hour_s - checkin_reserve_s, practice_data=list of sft/pairs files, stop=should_stop)
                 plateau.add(r.quiz, r.elapsed_s);  if plateau.flat(): mode = practice (event switch, reason)
  mode practice: alternate: practice hour (loop.run_round with budget) then consolidate hour (worker.run_chunk on the new practice data).
                 After each consolidate chunk, plateau is fed too; practice data is what keeps sleep useful.
                 If no practice kind has a checker (habits found nothing practicable) -> stay in sleep mode with a long idle (event idle).
  every hour (wall clock, at least once per hour_s): checkin.run() (read-only), even during practice/paused
  sleep until the next hour mark if the work finished early, polling for wake every poll_s (default 5 s)
on wake / SIGTERM / SIGINT: stop the running worker (SIGTERM, then SIGKILL after 30 s), write summary.md, remove SLEEPING, event wake.
```
Wake triggers: `WAKE` file; `~/learner-ops/ASSISTANT_RUNNING` appears (Ben started the assistant); signal.
`should_stop()` is polled during chunks, so wake takes effect within `poll_s` (the child is terminated; the worker is
expected to checkpoint on SIGTERM; CommandWorker reports `interrupted`).
Keep-awake (cli.keep_awake, foreground run, so also the background start): `caffeinate -ims -w <pid>`. Lid closed on battery is not supported (the Mac sleeps).
Memory pressure (macOS): `sysctl -n kern.memorystatus_vm_pressure_level` (1 normal, 2 warn, 4 critical); >= 2 stops the chunk and pauses. Non-mac: treated as normal.

## Marginal returns (plateau.py)

Each sleep chunk reports a quiz score (higher = better, any scale; the MLX worker uses -NLL x 100 on held-out diary turns).
Noise-aware slope rule: from the 3rd point on, fit OLS to the last `plateau_window` (default 4) points (cumulative hours, quiz).
SE of the slope comes from the residuals but is never below `plateau_noise` (default 0.5 quiz points) / sqrt(sum((t-tbar)^2)).
A check is flat when `b + 0.84*SE < plateau_min_gain_per_hour` (upper 80% bound; default 0.5). Switch to practice after
`plateau_patience` (default 2) flat checks in a row AND at least `min_sleep_hours` (default 2). Missing quiz (None) never counts and breaks the streak.
Simulation test (sigma 1, 8 points): a true 1.0/h slope trips it in <10% of trials, a flat curve in >80%.
Forgetting guard: the worker may put `general` (a general-skills score, higher = better) in `ChunkResult.info`; the scheduler passes it
to `add(quiz, hours, general)`. If it is more than `plateau_general_drop` (default 1.0) below its best on 2 checks in a row, `flat()` is
True at once (reason "general skills dropping"). `reset()` when new practice data arrives (a new source of learning).

## Workers (workers.py)

```python
@dataclass
class ChunkResult: quiz: float|None; elapsed_s: float; steps: int; interrupted: bool; info: dict
class SleepWorker:  def run_chunk(self, budget_s, practice_files, should_stop) -> ChunkResult
```
- `FakeWorker(curve)`: quiz follows a diminishing-returns curve (e.g. 50 + 30 (1 - exp(-h/1.5))); sleeps a tiny time. For tests and `--fake` demos.
- `CommandWorker(cmd)`: runs `cmd` (list) with env `SLEEPMODE_BUDGET_S`, `SLEEPMODE_OUT` (json path to write),
  `SLEEPMODE_PRACTICE` (os.pathsep-joined files), `SLEEPMODE_WORKDIR`. Polls should_stop; on stop sends SIGTERM, waits 30 s, SIGKILL.
  Reads `{"quiz": float|null, "steps": int, ...}` from SLEEPMODE_OUT. Also kills it at budget_s + 120 s.
  Any experiment sleep (e.g. a port of backbone/sleep/brain/sleepb.py) plugs in through this contract.
- `mlx_worker.py`: reference real worker, run as `python -m sleepmode.mlx_worker` (CommandWorker target). Builds chat-format
  data from the diary (`~/learner-ops/diary/raw/*.jsonl`, record schema below) + practice sft.jsonl, keeps a fixed held-out
  quiz split (5 % of conversations by hash, at least 20 turns, frozen in worker/quiz.jsonl on first run), times one step,
  sets `--iters` to fit the budget, runs `mlx_lm.lora` with `--resume-adapter-file` (LoRA on top of the q4 base, so nothing
  is re-quantized), then `mlx_lm.lora --test` on the quiz split and reports quiz = -test_loss*100. Model from config `mlx_model`
  (default K2 small tier; Qwen3.6 trains ~6x slower on MLX). Adapter saved to worker/adapters/. Not tested here (no MLX on Linux):
  tests cover data building, iters planning and output parsing only.

Diary raw record (written by the assistant gateway, branch claude/project-thread-ipiiv2):
`{"ts": iso, "model", "conv_id", "messages": [{"role","content"}...] (system content replaced by {"$blob": hash}),
  "response": {"content": str, "tool_calls": [...]}, "status": int, ...}` in `raw/YYYY-MM-DD.jsonl`.
User text: messages with role user (content may be a string or a list of {type:text,text}).

## Check-in (checkin.py, notify.py)

Read-only. Scanners return `Item(id, source, sender, subject, when, snippet, flags)`:
- `MailAppScanner`: osascript against Mail.app. No `whose` over the whole inbox and no message bodies (either can force IMAP
  downloads): takes the first `mail_max_scan` (default 150) inbox messages, loops, skips read ones and ones older than `mail_lookback_h`
  (default 24), collects id/sender/subject/date only (snippet empty), max 50. Wrapped in `with timeout of 90 seconds`. Read-only.
- `CalendarScanner`: osascript Calendar.app events starting within `calendar_ahead_h` (default 12), same timeout wrapper.
- `run_osascript` maps stderr `-1743` (not authorized) to `NotAuthorized(PermissionError)` and `-1712` to a timeout RuntimeError.
  On `PermissionError` the check-in marks the scanner "needs permission" (`status.json` `needs_permission`, event `checkin_needs_permission`),
  adds it to the scheduler's `blocked_scanners` (not called again this run) and writes one `inbox.md` line asking Ben to allow access.
- `python -m sleepmode preflight`: runs each enabled scanner once in the foreground (triggers the Automation prompts while Ben is
  present), checks `detect_isolation()` and a tiny `run_python`, prints an OK/FAIL table (exit 1 on any FAIL).
- `ImapScanner` (optional; host/user/password-env in config): `EXAMINE` (read-only select), UNSEEN SINCE.
- Scanners that fail (no permission, not mac) log an event and are skipped, never crash the loop.
Triage (rules, offline): notify if sender matches `vip_senders`, subject/snippet hits `urgent_words`
(urgent, asap, today, deadline, due, overdue, action required, payment failed, security alert, verify, interview, ...),
or a calendar event starts within `event_soon_h` (default 2). Optional LLM triage via `triage_url` (OpenAI-compatible) if set.
Each notified id is stored; never notify twice. Notify = macOS `display notification` + prepend to inbox.md;
optional `ntfy_topic` push (off by default: it would send subjects to ntfy.sh).
Check-in also writes a heartbeat line (event checkin: counts per source, n notified).

## Practice (practice/)

`habits.py`: scan diary user turns, keyword-classify into kinds (spreadsheet, email, writing, code, scheduling, research, math, other);
returns counts + share. Kinds with a registered task family are practicable (v1: spreadsheet). If Ben never used spreadsheets
we still practise the top practicable kind only if its share >= `practice_min_share` (default 0.05) else none.

`research.py`: `get_tricks(kind)` -> list of trick cards `{title, how, example, source}`.
Sources in order: built-in seed cards per kind (offline, ~15 for spreadsheets: SUMIFS, XLOOKUP, pivot, dedupe, TEXTSPLIT, date bucketing...),
then optional web (`research_web` default true): DuckDuckGo HTML search (`https://html.duckduckgo.com/html/?q=`) for
"<kind> tips tricks", fetch top pages, strip HTML; YouTube: same search with `site:youtube.com`, video ids from links,
transcript via `youtube_transcript_api` if installed (skipped otherwise). The model distills fetched text into cards.
Cached in practice/tricks/<kind>.json with fetch date; refreshed at most once a day. Fetched text is untrusted: it only becomes
hint text in prompts, is never executed, and never decides pass/fail.

`tasks.py`: task families with exact checkers. A task = `{id, kind, family, instruction, files: {name: text}, expected: {name: text}}`
plus `check(sandbox_dir) -> (ok, why)`. v1 spreadsheet families on generated CSV tables (seeded random: sales, expenses, contacts,
grades): sum by group, average by group, filter rows, dedupe by key, join/lookup two tables, computed column, sort by two keys,
monthly totals from dates, top-N per group, percent change, fill missing, split full name. The model writes a Python script that
reads the input CSV(s) and writes `output.csv`; the checker parses output.csv and compares to the reference result
(numbers rounded to 2 dp, header names exact, row order exact only where the task says sorted).
`generate(kind, n, seed)` -> tasks. Registry so new kinds (formulas via an xlsx engine, email drafting with rubric) plug in later.

`sandbox.py`: `run_python(code, files, timeout_s=30) -> RunResult(ok, stdout, stderr, files_out, dir)`. Fresh temp dir with copies of the
task files only (never Ben's real files), `python -I attempt.py`, cwd = sandbox, env = {PATH, HOME=sandbox, LANG}, no proxy vars;
rlimits CPU 30 s, file size 20 MB, nproc where supported. On macOS wrapped in `sandbox-exec -p <profile>`: deny network,
deny file-write outside the sandbox dir (and /dev), deny file-read-data (not file-read*, so stat/realpath of parent dirs still work) under $HOME except the sandbox and the python prefix; every path in the profile is realpath'd; TMPDIR = the sandbox dir.
On Linux uses `unshare -rn` when available for no network. Output files copied out; dir deleted.

`model.py`: `ChatModel(url, model, api_key=None).chat(messages, max_tokens, temperature) -> str` (urllib, OpenAI-compatible
/v1/chat/completions). `FakeModel(fn)` for tests.

`loop.py`: `run_round(kind, model, budget_s, out_dir, seed, n_tasks)`:
for each task: ask the model (system: "write a Python script ...", user: instruction + file previews + one trick card as a hint when relevant),
extract the code block, run in sandbox, check. Fail -> up to 2 retries with the error/diff fed back. Records:
- pass on first try -> sft example (prompt WITHOUT the hint, the passing code)
- pass after retry -> sft example + DPO pair (chosen = passing code, rejected = first failing code), prompt without hint
- never passes -> negative only (pairs file with chosen null is skipped; logged in rounds.jsonl)
Writes sft.jsonl / pairs.jsonl in chat format (`{"messages": [...]}` and `{"prompt": [...], "chosen": str, "rejected": str}`) and a
rounds.jsonl line `{kind, n, pass1, pass_any, tricks_used, elapsed_s}`. pass1 over rounds is Ben's "is practice working" line.
Stops early at budget_s. For practice the scheduler needs a model server: config `practice_model_url`; if `practice_server_cmd`
is set the scheduler starts it (e.g. mlx_lm.server on port 18082) before the round and stops it after, to free memory for sleep.

The format matches skillsleep (good -> SFT, fixed bad -> DPO) so its trainer can consume practice output, and the puzzle-practice
thread's checked-correct tries.

## Tools while sleeping (tools.py, practice/agent.py, dreamcheck.py)

Ben's request: the model gets the best tools while asleep, for practice and for checking dreams before training on them.

`ToolBox(diary_dir, *, web=True, fetch, searcher, sandbox_files)`: `schemas()` (OpenAI function JSON) and `call(name, args) -> str`
(always a string, errors as `ERROR: ...`, clipped to ~4000 chars). Tools: `web_search` (DuckDuckGo html: title, url, snippet),
`fetch_page` (http/https only; localhost, private/link-local IPs and non-http schemes are refused before any fetch; output is labelled
untrusted web text), `python` (practice.sandbox with the current task's files, `toolbox.sandbox_files`), `diary_search` (read-only:
`diary.sqlite` FTS5 table via a `mode=ro` URI if present, schema inspected defensively; else term-overlap scan of `raw/*.jsonl`),
`diary_read(date, conv_id)`. `web=False` removes the two web tools. Nothing is written except sandbox temp dirs.
`fetch_page` checks the requested URL and every redirect hop (`tools.safe_fetch`). Remaining gap: a hostname that resolves to a private address only at fetch time (DNS rebinding) is not caught.

`practice/agent.py`: `run_agent(model, messages, toolbox, max_steps, budget_s) -> (final_text, transcript)`. Native mode uses
`model.chat_tools` (tool results as role `tool` messages). A reply with a line `TOOL: name {json}` is also a call (result goes back as a
user message `RESULT name: ...`), and a server that rejects `tools` drops to this text mode. At the step or time cap the model is asked
once more for a final answer without tools.

Practice: `run_round(..., toolbox=, use_tools=)` (default on when a toolbox is given). The model may test its script with `python`, look up
tips, or see how Ben phrases things, then give the final ```python block. The block is still graded by the exact checker in a fresh
sandbox; tools never decide pass/fail. Training records are unchanged (final prompt and answer, no tool transcript, no hint);
`rounds.jsonl` gains `tools`, `tool_calls` (per tool) and `tool_calls_total`. Config `practice_tools` (default true); web follows `research_web`.

Dream check: `python -m sleepmode.dreamcheck IN.jsonl --out DIR --model-url URL [--model NAME] [--diary DIR] [--no-web] [--keep-unknown] [--max N]`.
Input items are `{"id","question","answer","source"?}` or chat items `{"messages": [...]}` (last user turn = question, final assistant turn = answer).
For each item the agent checks the answer (mostly `diary_search`; `python` for arithmetic; web only if allowed) and ends with
`VERDICT: SUPPORTED|CONTRADICTED|UNKNOWN` plus `FIX: ...` when contradicted. SUPPORTED also needs `EVIDENCE: "<quote>"` line(s): quote >= 12 chars (whitespace/case normalized) that appears in a diary_search/diary_read result of the transcript, else the verdict is downgraded to UNKNOWN (reason "no evidence"). An item with `hops` (list of strings) is verified hop by hop, one valid EVIDENCE line per hop. `--plant N` adds N corrupted copies (a number or capitalized name in the answer swapped for another from the input; items with neither skipped), reports `planted_false_accept_rate` in stats, and never writes planted items to the outputs. Output in DIR: `kept.jsonl` (SUPPORTED; CONTRADICTED with the fix
written in as the answer and `fixed: true`; UNKNOWN too with `--keep-unknown`), `quarantine.jsonl` (UNKNOWN, with `reason`, for browsing weird-but-maybe-true dreams; not with `--keep-unknown`), `dropped.jsonl` (with `reason`), `stats.json`. Items keep their
shape plus `verdict`, `fixed`, `tool_calls`. A model error or missing verdict counts as UNKNOWN. A CommandWorker-style trainer calls this on its
dreams before training and trains on `kept.jsonl`.
