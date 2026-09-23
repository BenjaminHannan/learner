---
name: mimo-skill
description: "2026-09-21 — DEFAULT agent model = opencode-go/muse-spark-1.3-contributor (Muse on OpenCode Go, opted in, unlimited per Ben); cheap Go models glm/qwen as fallback; free Zen models rate-limit; recipe, limits, verification rule"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-22T02:55:00.000Z
---

Ben set up `.claude/skills/mimo/SKILL.md` in the main repo (`/Users/ben-hannan/Desktop/projects/beautiful-model`) and said "Here's how you can do it yourself."

**Model ruling (2026-09-21):** "use muse spark. I don't like your proposal" → `--model opencode/muse-spark-1.3-contributor-free` for all agent runs; fallback `opencode/mimo-v2.6-flash-free` only if Muse runs out (empty reply). No model bake-off proposals.

**Usage ruling (2026-09-21, latest):** "You can use the muse 1.3 spark agents as much as you want. If they run out, use the v2.6 flash again. But your agentic use between the two is unlimited" and "if there's anything that would benefit from an agent, do the agent. Also, you can run them in parallel I believe. I had seven going at once just now." → Delegate freely (research scouts AND builds); run tasks in PARALLEL (the earlier one-at-a-time rule is dropped — Ben ran 7 concurrently). My own Claude usage stays minimal ([[minimize-usage]]).

Recipe: one task file per agent in scratchpad `mimo/queue/NN-name.md`; runner `mimo/run1.sh <task>` = `/usr/local/bin/opencode run --model <id> --auto --dir <repo> "$(cat task.md)" < /dev/null > NN.reply.md`, nohup-backgrounded, writes `NN.done` with the model used; `log.txt` has start/done lines. Read-only tasks: prefix "You are in read-only mode…". Each task text starts with the common rules block pointing at `design/v3/30-modes/48-parallel-build-brief-20260921.md`.

**OpenCode Go (2026-09-21 ~22:45, latest):** free Zen models (`opencode/*-free`) hit unpublished per-minute rate limits ("Rate limit exceeded… opencode go") with several agents at once. Ben bought OpenCode Go ($10/mo) and registered his key himself via `opencode auth login` (provider "OpenCode Go"); I never store the key (it leaked into one transcript — Ben should rotate it). Go models are `opencode-go/<name>`; verified answering: `glm-5.3-flash` (cheapest, $0.15/$0.50 per 1M), `qwen3.8-flash`, `kimi-k3`, `gpt-5.6-luna`, `minimax-m3`. `deepseek-v4-flash`/`v4.1-flash` and `muse-spark-1.3-contributor` need opt-ins on Ben's dashboard (he said he'd opt in). `opencode/<paid>` (non-free Zen) → "Insufficient balance" — never use. **Budget rule ("you're eating my 5 hour"):** six Go agents burned 12.8 % of the 5-hour window in ~1 min → keep ≤ 2 Go agents at once, only on glm-5.3-flash / qwen3.8-flash, until Ben says otherwise; Muse/MiMo free sessions don't count. Runner `mimo/rungo2.sh <task> [model]` (cheap chain only; killed run or `NN.stop` file = no fallback, no done marker — old rungo.sh fell through to pricier models after a kill and wrote spurious `.done` files).

**Muse on Go (2026-09-21 22:56, LATEST):** Ben opted in; `opencode-go/muse-spark-1.3-contributor` answers. Ben: "Try using all the muse 1.3 contributor agents you want" → default model for every agent, cap: Ben lifted the 10 cap at 23:10 ("ball out of the extra agents") but corrected me: the 5-hour bar is ONE total — at 100 % every Go model stops, no switching to another model. Rule: hold ≤ ~15 Muse agents (measured 23:17: ~$1.7/h ≈ 14 %/h of the bar with 15–18 agents) and keep the projected bar < 90 % at the window reset; 0.1 %/min ≈ 10 agents; the ≤ 2 rule applies only to the non-Muse Go models. `rungo2.sh <task>` now chains muse-go → glm-5.3-flash → qwen3.8-flash.

**Watching the Go budget (calibrated 2026-09-21 23:07 from Ben's dashboard):** `opencode stats --days 1 --models` prints $ per model (matches the dashboard within ~15 %). Dashboard 5-hour bar = SUM of per-model percentages; per-model 5-hour quotas: Muse Spark $12, GLM 5.3 Flash $12, MiniMax M3 $12, Qwen3.8 Flash $6, Kimi K3 $3, GPT 5.6 Luna $3. 1 % of the bar ≈ $0.12 of Muse spend; ~10 agents ≈ 0.1 %/min ≈ 6 %/hour; 18 agents ≈ 11 %/hour. The window RESETS (not rolling) — plan spend against the reset time shown on the dashboard. Kimi's $0.60 in one minute (20 %) is why the pricey models are banned.

**Limits:** never pass secrets/ARMED files/notebook personal data; `timeout` binary doesn't exist on the Mac — use the Bash tool timeout; agentic runs take minutes to an hour. Flash-class models over-claim: verify every RESULTS.md (seal, re-run scorer, claims ≤ numbers) before reporting to Ben. Related: [[ben-runs-mimo-agents]], [[subagents-gpt-xhigh]] (superseded for delegation: opencode agents replace GPT-xhigh for builds; GPT bridge still OK for web scouts).
