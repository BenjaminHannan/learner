---
name: web-search-tool-idea
description: "2026-09-21 Ben wants the model to search the web / use tools like Claude Code does; parked as a SEARCH act after talker S2"
metadata:
  type: project
---

Ben said (2026-09-21) the model should be able to search the web, "use tool use in claude code or something". Plan I gave him: add a SEARCH act to the typed thought; our own small harness executes the search (model never touches the net); results are read into notebook facts tagged source=web, separate from Ben-taught facts. Obstacle: a ~33M simple-English model can't read real pages — either a big-model translator (Qwen/Claude rewrites pages into simple fact sentences; claim must say the big model did the reading) or Simple English Wikipedia only. Our model can't be the brain inside Claude Code, but we can copy the tool loop (~100 lines) or expose our model as a tool Claude Code calls.

**Why:** part of Ben's vision for the [[teachable-assistant-goal]]; pairs with [[dreamer-checker-idea]] (checker verifies against notebook + web).
**How to apply:** parked until the talker does TELL/ASK/UNKNOWN reliably (S2 of [[talker-route-b]]); keep the act alphabet extensible so SEARCH can be added; keep web facts provenance-tagged; claims ≤ evidence about who did the reading.

**Correction 2026-09-21 (Ben was right):** our model CAN be the model behind the Claude Code CLI — point `ANTHROPIC_BASE_URL` at a small shim server that speaks the Anthropic Messages API, drops Claude Code's huge system prompt, passes only the user's text to our model, and maps our acts to its formats (reply → text, SEARCH act → a web-search tool_use block that Claude Code executes; tool result simplified and fed back). Claude Code then serves as the harness, so no separate tool loop is needed. Claim limit: our model talks through Claude Code's interface with a translator; it does not do Claude's coding/planning work.

**2026-09-21 — Ben's bar: "if it can't emit simple tool calls it's a shit model."** Agreed. Tool calls are native to the typed thought (act = SEARCH/other tool, slots = arguments; no free-text JSON to botch). Registered intent: a "tool-call exam" talker milestone after TELL/ASK/UNKNOWN — 3–5 tools described in simple English, pick right tool (or none) + right arguments, pass mark fixed beforehand (~≥95% on held-out wordings), 33M first. Integration route: Claude Code is closed-source, so don't patch it — use the Claude Agent SDK (own short system prompt, restricted tool list) + base-URL pointing at our model; the 20k-token stock prompt is the only real obstacle, not tool emission.

**2026-09-21 — Ben: "then use codex".** Decision: the harness of first choice is a fork of OpenAI's open-source Codex CLI (Apache-2.0; custom `model_providers` + `base_url` in its config, OpenAI chat-completions wire format with tool_calls). We trim its prompt to simple English, replace its shell/patch tools with web search + notebook lookup, and serve our model behind an OpenAI-compatible endpoint. Order: talker TELL/ASK/UNKNOWN → tool-call exam → Codex fork. Claude Agent SDK is the fallback.
