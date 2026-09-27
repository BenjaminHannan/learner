Summary:
1. codex path/version: `command -v codex` empty (not in PATH); bundled binary `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex` = `codex-cli 0.158.0-alpha.2`.
2. Non-interactive form: `codex exec -m <MODEL> -C <DIR> --sandbox workspace-write -a never [--json] "<PROMPT>"`; full-auto: `--dangerously-bypass-approvals-and-sandbox` (or `--approve-for-me`).
3. Luna model id: not found (no model-listing command in help).

# Probe Codex CLI (2026-09-27 03:30 UTC, read-only, help only)

## 1. `command -v codex; codex --version`
```
zsh:1: command not found: codex
```

## 2. `codex --help`
```
zsh:1: command not found: codex
```

## 3. `codex exec --help`
```
zsh:1: command not found: codex
```

## 4. Model listing
Help lists no `codex models` / `codex exec --list-models` command, and `--model <MODEL>` shows no listed values. Per instructions, no listing run. Luna model id: not found.

## 5. `ps -axo pid,etime,comm | grep -i codex | grep -v grep`
```
43119 01-01:58:56 /Applications/Codex Web GPT.app/Contents/MacOS/Codex Web GPT
43194 01-01:58:47 /Applications/Codex Web GPT.app/Contents/Frameworks/Codex Web GPT Helper.app/Contents/MacOS/Codex Web GPT Helper
43195 01-01:58:47 /Applications/Codex Web GPT.app/Contents/Frameworks/Codex Web GPT Helper.app/Contents/MacOS/Codex Web GPT Helper
43205 01-01:58:47 /Applications/Codex Web GPT.app/Contents/Frameworks/Codex Web GPT Helper (Renderer).app/Contents/MacOS/Codex Web GPT Helper (Renderer)
44030 01-01:56:12 /Applications/Codex Web GPT.app/Contents/Frameworks/Codex Web GPT Helper.app/Contents/MacOS/Codex Web GPT Helper
44570 01-01:55:09 /Users/ben-hannan/.codex-chatgpt-web/bin/tunnel-client
44571 01-01:55:09 /Users/ben-hannan/.codex-chatgpt-web/versions/6.1.0-darwin-arm64/runtime/bun
44581 01-01:55:09 /Users/ben-hannan/.codex-chatgpt-web/versions/6.1.0-darwin-arm64/runtime/bun
44655 01-01:55:09 /Applications/Codex Web GPT.app/Contents/Frameworks/Codex Web GPT Helper (Renderer).app/Contents/MacOS/Codex Web GPT Helper (Renderer)
46313 01-01:54:59 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/browser_crashpad_handler
46316 01-01:54:59 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/browser_crashpad_handler
46375 01-01:54:59 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/Codex (Service).app/Contents/MacOS/Codex (Service)
46377 01-01:54:59 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/Codex (Service).app/Contents/MacOS/Codex (Service)
46383 01-01:54:59 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/Codex (Service).app/Contents/MacOS/Codex (Service)
46555 01-01:54:58 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/Codex (Renderer).app/Contents/MacOS/Codex (Renderer)
46556 01-01:54:58 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/Codex (Renderer).app/Contents/MacOS/Codex (Renderer)
46561 01-01:54:58 /Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex
47223 01-01:54:54 /Users/ben-hannan/.codex/computer-use/Codex Computer Use.app/Contents/MacOS/SkyComputerUseService
47329 01-01:54:53 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/Codex (Renderer).app/Contents/MacOS/Codex (Renderer)
47922 01-01:54:47 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/Codex (Renderer).app/Contents/MacOS/Codex (Renderer)
47928 01-01:54:47 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/Codex (Renderer).app/Contents/MacOS/Codex (Renderer)
47929 01-01:54:47 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/Codex (Renderer).app/Contents/MacOS/Codex (Renderer)
49092 01-01:52:37 /Applications/Codex Web GPT.app/Contents/MacOS/Codex Web GPT
49185 01-01:51:59 /Applications/ChatGPT.app/Contents/Frameworks/Codex Framework.framework/Versions/154.0.8037.57/Helpers/Codex (Service).app/Contents/MacOS/Codex (Service)
79964       00:22 /Users/ben-hannan/.codex/plugins/cache/openai-bundled/chrome/latest/extension-host/macos/arm64/ChatGPT for Chrome
83652    02:02:56 /Users/ben-hannan/Library/Caches/com.openai.codex/org.sparkle-project.Sparkle/Launcher/FiDImuDeb/Updater.app/Contents/MacOS/Updater
86478    16:03:22 /Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex-code-mode-host
```

---
# Supplemental (read-only, help-only): bundled binary found via ps, not in PATH
# `codex` not in PATH, but `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/` contains `codex` + `codex-code-mode-host`.

## A. `"/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" --version`
```
codex-cli 0.158.0-alpha.2
```

## B. `"/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" --help`
```
Codex CLI

If no subcommand is specified, options will be forwarded to the interactive CLI.

Usage: codex [OPTIONS] [PROMPT]
       codex [OPTIONS] <COMMAND> [ARGS]

Commands:
  agents            Browse all agent sessions on the shared local app-server daemon
  exec              Run Codex non-interactively [aliases: e]
  review            Run a code review non-interactively
  login             Manage login
  logout            Remove stored authentication credentials
  mcp               Manage external MCP servers for Codex
  plugin            Manage Codex plugins
  app-server        [experimental] Run the app server or related tooling
  remote-control    [experimental] Manage the app-server daemon with remote control enabled
  app               Launch the Desktop app (opens the app installer if missing)
  completion        Generate shell completion scripts
  update            Update Codex to the latest version
  doctor            Diagnose local Codex installation, config, auth, and runtime health
  sandbox           Run commands within a Codex-provided sandbox
  debug             Debugging tools
  apply             Apply the latest diff produced by Codex agent as a `git apply` to your local
                    working tree [aliases: a]
  resume            Resume a previous interactive session (picker by default; use --last to continue
                    the most recent)
  queue             Queue a message for an existing session
  archive           Archive a saved session by id or session name
  delete            Permanently delete a saved session by id or session name
  migrate-rollouts  Inspect or migrate legacy local sessions to paginated thread history
  unarchive         Unarchive a saved session by id or session name
  fork              Fork a previous interactive session (picker by default; use --last to fork the
                    most recent)
  cloud             [EXPERIMENTAL] Browse tasks from Codex Cloud and apply changes locally
  exec-server       [EXPERIMENTAL] Run the standalone exec-server service
  features          Inspect feature flags
  help              Print this message or the help of the given subcommand(s)

Arguments:
  [PROMPT]
          Optional user prompt to start the session

Options:
  -c, --config <key=value>
          Override a configuration value that would otherwise be loaded from `~/.codex/config.toml`.
          Use a dotted path (`foo.bar.baz`) to override nested values. The `value` portion is parsed
          as TOML. If it fails to parse as TOML, the raw string is used as a literal.
          
          Examples: - `-c model="o3"` - `-c 'sandbox_permissions=["disk-full-read-access"]'` - `-c
          shell_environment_policy.inherit=all`

      --enable <FEATURE>
          Enable a feature (repeatable). Equivalent to `-c features.<name>=true`

      --disable <FEATURE>
          Disable a feature (repeatable). Equivalent to `-c features.<name>=false`

      --remote <ADDR>
          Connect the TUI to a remote app server endpoint.
          
          Accepted forms: `ws://host:port`, `wss://host:port`, `unix://`, or `unix://PATH`.

      --remote-auth-token-env <ENV_VAR>
          Name of the environment variable containing the bearer token to send to a remote app
          server websocket

      --strict-config
          Error out when config.toml contains fields that are not recognized by this version of
          Codex

  -i, --image <FILE>...
          Optional image(s) to attach to the initial prompt

  -m, --model <MODEL>
          Model the agent should use

      --oss
          Use open-source provider

      --local-provider <OSS_PROVIDER>
          Specify which local provider to use (lmstudio or ollama). If not specified with --oss,
          will use config default or show selection

  -p, --profile <CONFIG_PROFILE_V2>
          Layer $CODEX_HOME/<name>.config.toml on top of the base user config

  -s, --sandbox <SANDBOX_MODE>
          Select the sandbox policy to use when executing model-generated shell commands
          
          [possible values: read-only, workspace-write, danger-full-access]

      --approve-for-me
          Route approval requests through automatic review using the workspace-write sandbox

      --dangerously-bypass-approvals-and-sandbox
          Skip all confirmation prompts and execute commands without sandboxing. EXTREMELY
          DANGEROUS. Intended solely for running in environments that are externally sandboxed

      --dangerously-bypass-hook-trust
          Run enabled hooks without requiring persisted hook trust for this invocation. DANGEROUS.
          Intended only for automation that already vets hook sources

  -C, --cd <DIR>
          Tell the agent to use the specified directory as its working root

      --worktree
          Run the session in a new managed Git worktree

      --add-dir <DIR>
          Additional directories that should be writable alongside the primary workspace

  -a, --ask-for-approval <APPROVAL_POLICY>
          Configure when the model requires human approval before executing a command

          Possible values:
          - on-request: The model decides when to ask the user for approval
          - never:      Never ask for user approval Execution failures are immediately returned to
            the model

      --search
          Enable live web search. When enabled, the native Responses `web_search` tool is available
          to the model (no per‑call approval)

      --no-alt-screen
          Disable alternate screen mode
          
          Runs the TUI in inline mode, preserving terminal scrollback history.

      --no-daemon
          Run without the shared background server, even if it is already running

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```

## C. `"/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" exec --help`
```
Run Codex non-interactively

Usage: codex exec [OPTIONS] [PROMPT]
       codex exec [OPTIONS] <COMMAND> [ARGS]

Commands:
  resume  Resume a previous session by id or pick the most recent with --last
  fork    Fork a previous session by id into a new session
  review  Run a code review against the current repository
  help    Print this message or the help of the given subcommand(s)

Arguments:
  [PROMPT]
          Initial instructions for the agent. If not provided as an argument (or if `-` is used),
          instructions are read from stdin. If stdin is piped and a prompt is also provided, stdin
          is appended as a `<stdin>` block

Options:
  -c, --config <key=value>
          Override a configuration value that would otherwise be loaded from `~/.codex/config.toml`.
          Use a dotted path (`foo.bar.baz`) to override nested values. The `value` portion is parsed
          as TOML. If it fails to parse as TOML, the raw string is used as a literal.
          
          Examples: - `-c model="o3"` - `-c 'sandbox_permissions=["disk-full-read-access"]'` - `-c
          shell_environment_policy.inherit=all`

      --enable <FEATURE>
          Enable a feature (repeatable). Equivalent to `-c features.<name>=true`

      --disable <FEATURE>
          Disable a feature (repeatable). Equivalent to `-c features.<name>=false`

      --strict-config
          Error out when config.toml contains fields that are not recognized by this version of
          Codex

  -i, --image <FILE>...
          Optional image(s) to attach to the initial prompt

  -m, --model <MODEL>
          Model the agent should use

      --oss
          Use open-source provider

      --local-provider <OSS_PROVIDER>
          Specify which local provider to use (lmstudio or ollama). If not specified with --oss,
          will use config default or show selection

  -p, --profile <CONFIG_PROFILE_V2>
          Layer $CODEX_HOME/<name>.config.toml on top of the base user config

  -s, --sandbox <SANDBOX_MODE>
          Select the sandbox policy to use when executing model-generated shell commands
          
          [possible values: read-only, workspace-write, danger-full-access]

      --approve-for-me
          Route approval requests through automatic review using the workspace-write sandbox

      --dangerously-bypass-approvals-and-sandbox
          Skip all confirmation prompts and execute commands without sandboxing. EXTREMELY
          DANGEROUS. Intended solely for running in environments that are externally sandboxed

      --dangerously-bypass-hook-trust
          Run enabled hooks without requiring persisted hook trust for this invocation. DANGEROUS.
          Intended only for automation that already vets hook sources

  -C, --cd <DIR>
          Tell the agent to use the specified directory as its working root

      --worktree
          Run the session in a new managed Git worktree

      --add-dir <DIR>
          Additional directories that should be writable alongside the primary workspace

      --thread-source <SOURCE>
          Source classification for newly created or forked threads

      --skip-git-repo-check
          Allow running Codex outside a Git repository

      --ephemeral
          Run without persisting session files to disk

      --ignore-user-config
          Do not load `$CODEX_HOME/config.toml`; auth still uses `CODEX_HOME`

      --ignore-rules
          Do not load user or project execpolicy `.rules` files

      --output-schema <FILE>
          Path to a JSON Schema file describing the model's final response shape

      --color <COLOR>
          Specifies color settings for use in the output
          
          [default: auto]
          [possible values: always, never, auto]

      --json
          Print events to stdout as JSONL

  -o, --output-last-message <FILE>
          Specifies file where the last message from the agent should be written

  -h, --help
          Print help (see a summary with '-h')

  -V, --version
          Print version
```
