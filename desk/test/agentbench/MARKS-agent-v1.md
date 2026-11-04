# MARKS-agent-v1: make Glim better at doing things (track AGENT1, 2026-11-04)

Registered before the first scored run. Do not edit after the baseline starts. Any change to the bench gets a new MARKS file.

## What is measured
- **Bench:** `test/agentbench/` has 20 tasks (`tasks.js`) on fake local sites (`sites.js`). The sites are served inside the test browser's own session by intercepting http/https, so nothing reaches the internet and no real account is touched. Every host is `*.test`, plus a fake `duckduckgo.com` for the browser's search fallback.
- **Real loop:** `run.js` drives the real `src/agent.js` with the real browser tool, system prompt, tool list (`buildTools({diary:true})`, 24 tools), memory module, verify step, think cap and steer handling. It talks to the real gateway on 8090: `qwen36` (thinking) for steps and `qwen36-fast` for the self-check, exactly as the app sends them. The gateway serves Nanbeige4.2-3B 8-bit through glim_mlx_server.
- **Settings:** Ben's M1 settings (verify on, hands-off, vision off, contextTokens 12000, maxToolChars 8000).
- **Stubs:** only where a person or the Mac is needed.
  - `ask_user` answers come from the task script: "yes" by default; per task otherwise.
  - Sign-in waits answer "not now".
  - Shell, screen and app tools return "not available".
  - `web_search` reads a fake index.
  - The browser runs offscreen. On-screen windows lose every click on this M1, whose display sleeps.
- **Test-only tagging:** every request carries `test: true` / `X-Test`, so sleep never trains on bench chats.
- **Bounds:** at most 240 s and 25 model steps per task (bench-only; the app has no step limit). A task that hits the cap fails.
- **Per task we record:**
  - success (automatic scorer: final site state plus Glim's visible words);
  - model calls, tool calls;
  - replans: visible replies holding a numbered plan or "Plan:", plus plan cards;
  - tool-name leaks: a tool id in visible text or an ask_user question;
  - repeated identical actions: same tool and args as the previous call, scroll excepted;
  - wall time;
  - the largest request estimate (`context-budget.requestTokens`, chars/2.5) and how many requests went over 8192.

## Runs
- 3 runs per version.
- Sampling as the app uses it: the app sends no temperature or seed, so the server's default sampling applies. The 3 runs are 3 independent samples. No fixed seed is possible through the app path.
- Each run is 3 waves of 6–7 tasks (`wave.sh`), each < 30 min. Every wave runs under `/tmp/aon/realmodel-lock.sh`, and only when memory pressure is 1 and load ≤ 8.
- Control = baseline at HEAD `f28dd458c` (branch always-on), same bench, same settings.

## Pass marks (fixed now)
A version is **accepted** only if both hold:
1. **Gain:** its mean over 3 runs of the number of tasks passed (of 20) is at least **2.0 higher** than the last accepted version (the baseline at first).
2. **No regression:** no task that passed in ≥ 2 of 3 runs in the last accepted version fails in ≥ 2 of 3 runs of the new version.

**Secondary (reported, not gating):** mean model calls, replans, leaks, repeats, time and largest request. The context-diet version also states its own size goal: every request ≤ 8192 estimated tokens.

**What proves a version wrong:** a mean gain < 2.0, or any regression as defined above. Then it is not accepted: it is reverted (or left off behind its setting), and the next version is measured against the last accepted one.

**Limits:**
- At most 5 versions, one change each.
- No weight training. Harness only: prompt, tools, page format, context, menus, checks, thinking per step.
- Good/bad step examples may be written to a file for a later sleep; nothing is trained here.

## Noise
The baseline's 3 runs give the per-task spread. With 20 tasks and 3 runs, a 2.0-task mean gain is about the smallest gain this bench can tell from noise. That is why the mark is 2.0 and not 1.
