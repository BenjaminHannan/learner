# OpenBot prompt-size findings

Repo: /tmp/claude-0/-home-user-learner/e2cbeab6-ff63-5408-a99c-383b597f7517/scratchpad/openbot (HEAD f91535f, v0.51.1; Ben has ~0.50, so line numbers may differ).
Upstream OpenCode: .../scratchpad/oc (HEAD of anomalyco/opencode, newer than 2.1.4; native-runtime.lock.json:106-110 pins 2.1.1 in this OpenBot HEAD).
Labels: [shown] = seen in code, [suggested] = inference or untested.

## 1. `<openbot-developer-instructions>`

- [shown] Built in `src/backend/agent/developer-instructions.ts:210` `developerInstructions()`. It joins about 40 long static strings: persona, the 11 `openbot.*` tools, teammate/delegation rules, memory rules, `<agent_profile>` (line ~268), paths, computer-use, automation. No `<outcome>` tag exists in this HEAD (grep found none), so Ben's 0.50 build differs; expect the same builder.
- [shown] Called from `src/backend/agent/thread-lifecycle.ts:1044-1058`. Memories and teammates go into the user turn only when `client.provider === "claude"` (lines 1041-1042); for opencode they stay inside the instructions.
- [shown] Attached in `src/backend/acp-client.ts:1730-1744`. It does `blocks.unshift({type:"text", text:"<openbot-developer-instructions>..."})` onto the user prompt, because ACP has no system channel for it. It is meant to go once per session: sent only if `thread.instructionsSent !== thread.developerInstructions`, or if `thread.contextUsed === null` and more than `ACP_INSTRUCTIONS_REFRESH_PROMPTS` (=10, line 214) prompts passed.
- [shown] Why it repeats on every message in Ben's log: `acp-client.ts:2128` sets `instructionsSent = null` whenever a turn ends `failed` ("agent may not have kept a prompt that failed"). Ben's six turns all failed, so each retry re-sent it. Also reset on compaction (`#compacted`, line ~700) and on session reload (line 1323).
- [shown] `contextUsed` only fills from an ACP `usage_update` (line 1884-1886). [suggested] If OpenCode reports no usage for the gateway, it stays null and the block repeats every 11th prompt even on healthy turns.
- [shown] No setting or env var sends it once or shortens it (no `process.env` in developer-instructions.ts or thread-lifecycle.ts). Only fix is source. Patch 0004 returns a ~1.5k-char version for `opencode` agents on `premonition/*` models.
- [suggested] Biggest lever: stop the failure re-sends (fix the underlying failure; gateway side: make sure every request returns a clean completion). Second: patch 0004. Because prior user messages stay in history, each re-sent block costs 21.5k chars (~5k tokens, ~20 s of prefill at 230 tok/s) again.

## 2. Code Mode and `<system-update>`

- [shown] Not in OpenBot. It is OpenCode (2.x): `oc/packages/core/src/codemode/{instructions,catalog,tool}.ts`, `oc/packages/core/src/tool.ts:258-295`. Instead of sending every tool, OpenCode sends one `execute` tool plus a catalog in text; the model writes JS that calls tools.
- [shown] The catalog is a chronological "system update". `oc/packages/ai/src/protocols/shared.ts:196-198` `wrapSystemUpdate()` wraps it as `<system-update>` user text on routes without a system role (OpenAI chat, which our gateway uses).
- [shown] Text comes from `CodeModeInstructions.render/update` (`instructions.ts:18-130`). The inline catalog is capped by `INLINE_BUDGET = 2_000` tokens (`catalog.ts`, about 8k chars). That matches the 8,991-char message.
- [shown] A message is emitted whenever the catalog value changes. `update()` returns either a full replacement or a smaller delta ("New tools are available...", "no longer available...") whichever is shorter. Inventory is cached by the visible tool-name set (`tool.ts:264-269`).
- [suggested] Why it alternates 8,991 / 5,046: the visible tool set changes between turns (an MCP server such as openbot or the browser connecting or dropping, or a failed turn losing and regaining tools), giving full text then a different text. Not verified against 2.1.4. Check by logging `execute`'s catalog on two consecutive requests.
- [shown] Switches: Code Mode is on unless the permission ruleset wholly denies `execute` (`tool.ts:258` `whollyDisabled("execute", rules)`); then all tools become direct tool definitions (`tool.ts:260-262`). Per MCP server: `codemode: false` in the server's config (`oc/packages/core/src/v1/config/mcp.ts:20,53`) makes that server's tools direct.
- [shown] OpenBot only sets `permission` in the profile-generation layer (`src/backend/opencode-config.ts:81`) and builds `OPENCODE_CONFIG_CONTENT` (line 83). OpenCode also reads the user's own global/project config first (file header comment, lines 1-6).
- [suggested, untested] `"permission": {"execute": "deny"}` in `~/.config/opencode/opencode.json` or in OpenBot's overlay would turn Code Mode off. Trade-off: every tool then ships as a full JSON schema, so the 14k-char tools JSON would likely grow. Better: keep Code Mode on and make the tool set stable and small (fewer MCP servers). Not turning it off is probably right for a slow-prefill model.

## 3. Custom providers and a built-in "Premonition"

- [shown] File `openbot-custom-providers-v1.json` in Electron userData (`src/main/application-services.ts:362`, store created at 1260-1266). Format `{version:1, providers:[{id,name,baseUrl,models:[{id,name}],secret}]}` (`src/main/custom-provider-store.ts:44-52`). The key and headers are encrypted in `secret`; keyless endpoints work without a keychain (save(), "A keyless local endpoint still saves").
- [shown] At spawn, `configs()` goes through `openCodeConfigEnv` into `OPENCODE_CONFIG_CONTENT` as `provider.<id> = {npm:"@ai-sdk/openai-compatible", name, options:{baseURL}, models}` (`src/backend/opencode-config.ts:~100-170`). Model ids become `<providerId>/<modelId>` (`packages/contracts/src/ipc-custom-providers.ts:170`).
- [shown] `provider-detection-settings-store.ts` is only for scanning Ollama/LM Studio, not provider storage.
- [shown] Picker: `packages/ui/src/components/ProviderModelPicker.tsx` puts every opencode model whose id prefix is a saved endpoint id on the "Custom" tab (`isCustomProviderModelId`, lines 214-228). The Custom tab's icon is lucide `SlidersHorizontal` (ProviderMark, ~line 1139). A separate rail per endpoint does not exist; a true separate tab needs a new `AgentProviderId` (DB CHECK lists, i18n, descriptors), which is much bigger. [suggested] Not worth it.
- [shown] New-agent default: `src/backend/agent-store.ts:151-152,1625-1626` (`codex` / `gpt-6-luna`), plus `defaultModel` in the descriptor (`packages/contracts/src/agent-providers.ts`, opencode block ~line 243, currently `""`), used by `startingModel` (`src/backend/agent/model-choice.ts:~30-45`).
- Patches in /tmp/claude-0/-home-user-learner/e2cbeab6-ff63-5408-a99c-383b597f7517/scratchpad/openbot-patches/ (each passes `git apply --check`; none built or run):
  - 0001: seeds the `premonition` endpoint in `CustomProviderStore.load()` (new file or file lacking it) with the three models; sets the new-agent defaults to provider `opencode`, model `premonition/qwen36-auto`. [suggested] Risk: changing `DEFAULT_AGENT_PROVIDER` also feeds `developmentDefaultsApply` (model-choice.ts:106) and the endpoint-removal fallback; if the gateway is down, new agents have no listed model and fall back to the first listed one. A user who deletes Premonition gets it back on next launch.
  - 0002: replaces the Custom-tab sliders icon with an eye SVG (swap in a brand SVG). It applies to all custom endpoints, not only Premonition.
  - 0003: `updatesEnabled = false && ...` at `src/main/application-services.ts:2720`. The service still constructs but is disabled (`createDisabledUpdateAdapter`, line ~2728).
  - 0004: the lean ~1.5k-char instructions for `opencode` agents on `premonition/*` models (section 1).
- [suggested] Without patches, Ben can do the same by hand: Settings > add OpenAI-compatible endpoint, id `premonition`, no key, the three models; the picker lists them under Custom. Updates can be toggled in Settings (preference store `updatePreference.autoDownload`) but not fully off.

## 4. Building the macOS app

- [shown] Package manager Bun 1.4.2 (`package.json:77`), Electron + electron-vite. `bun install` (postinstall fetches Electron, line 83), `bun run dev` (line 111) runs from source.
- [shown] `bun run package` (`package.json:330`) = voice runtime, remote-desktop runtime, verify, cua-driver, `electron-vite build`, then `electron-builder --dir --mac --config.mac.identity=null --config.mac.notarize=false`. `--dir` yields an unpacked `.app` in `dist/` (default output dir; not checked). `dist:mac` (line 341) does the same but makes zip/dmg.
- [shown] Signing: release needs a Developer ID cert and notarization (`docs/RELEASING.md:10-46`, `electron-builder.yml:94` notarize, hardenedRuntime). Local script disables both. `electronFuses.resetAdHocDarwinSignature: true` (`electron-builder.yml:12`) shows the build expects to reset the ad-hoc signature itself.
- [suggested] An unsigned/ad-hoc `.app` runs locally on Apple silicon (right-click Open or `xattr -dr com.apple.quarantine`). Computer Use TCC grants and the macOS keychain-encrypted features may behave differently without Developer ID; auto-update cannot work. Prerequisites like Xcode tools, network access for voice/cua-driver/OpenCode downloads, and `native-runtime.lock.json` fetches: not tested (no macOS here).
- [suggested] Alternative with no build: set `OPENBOT_OPENCODE_PATH` (README "OpenCode" section) to your own OpenCode binary; this does not remove Code Mode or the 21k block.

## Most important levers (ranked)
1. Fix why turns fail so the block is not re-sent (`acp-client.ts:2128`), and ensure usage updates (`:1884`).
2. Patch 0004 (21.5k to ~1.5k chars).
3. Keep Code Mode, but stabilize the tool set (fewer MCP servers) so the 9k/5k catalog message stops changing; its catalog is budget-capped at ~8k chars.
4. System message 33.7k chars is OpenCode's own prompt, not OpenBot; a custom `agent` prompt in OpenCode config is [suggested] but untested.
