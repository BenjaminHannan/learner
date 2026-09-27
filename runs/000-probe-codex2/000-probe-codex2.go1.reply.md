Read-only probe — running tiny Codex model checks, no writes.
First candidate `gpt-6-luna` answered ok — checking the remaining IDs to complete the probe.
First `M` that answered `ok`: `gpt-6-luna`

Working form:
```
"/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" exec -m "gpt-6-luna" -C "$D" --sandbox read-only --skip-git-repo-check "Reply with exactly: ok" < /dev/null 2>&1 | tail -15
```

No flags rejected. All of `-m`, `-C`, `--sandbox`, `--skip-git-repo-check` accepted.

READ-ONLY note: skipped `rm -rf "$D"`, skipped write to `handoff/replies/000-probe-codex2.md`, skipped PUSH per COMMON RULES. `D=/var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.Gt7ifR8l5Z` left in place. Proposed file content below — Director please write/push.

---
Proposed `handoff/replies/000-probe-codex2.md`:
```
gpt-6-luna
"/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" exec -m "gpt-6-luna" -C "$D" --sandbox read-only --skip-git-repo-check "Reply with exactly: ok" < /dev/null 2>&1 | tail -15
[... full probe log below ...]
```

Probe log:

1. `exec --help | head -80`:
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
```
tail confirms `--skip-git-repo-check`, `-C`, `-s` all valid.

2. `M=gpt-6-luna` — OK:
```
approval: never
sandbox: read-only
reasoning effort: ultra
reasoning summaries: none
session id: 01a0e0ee-d153-7491-8ae9-4d6a94a299ee
--------
user
Reply with exactly: ok
warning: Under-development features enabled: context_management. Under-development features are incomplete and may behave unpredictably. To suppress this warning, set `suppress_unstable_features_warning = true` in /Users/ben-hannan/.codex/config.toml.
2026-09-27T03:35:43.823842Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 426 Upgrade Required, url: ws://127.0.0.1:17841/v1/responses
codex
ok
tokens used
5,681
ok
```

3. `M=gpt-6.0-luna` — FAIL:
```
model: gpt-6.0-luna
provider: openai
approval: never
sandbox: read-only
reasoning effort: ultra
reasoning summaries: none
session id: 01a0e0ef-0c78-7d40-956c-0e97711fd315
--------
user
Reply with exactly: ok
warning: Under-development features enabled: context_management...
warning: Model metadata for `gpt-6.0-luna` not found. Defaulting to fallback metadata; this can degrade performance and cause issues.
2026-09-27T03:35:58.598642Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 426 Upgrade Required, url: ws://127.0.0.1:17841/v1/responses
ERROR: {"detail":"The 'gpt-6.0-luna' model is not supported when using Codex with a ChatGPT account."}
ERROR: {"detail":"The 'gpt-6.0-luna' model is not supported when using Codex with a ChatGPT account."}
```

4. `M=luna` — FAIL:
```
model: luna
provider: openai
...
warning: Model metadata for `luna` not found. Defaulting to fallback metadata...
2026-09-27T03:35:58.620620Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 426 Upgrade Required, url: ws://127.0.0.1:17841/v1/responses
ERROR: {"detail":"The 'luna' model is not supported when using Codex with a ChatGPT account."}
ERROR: {"detail":"The 'luna' model is not supported when using Codex with a ChatGPT account."}
```

5. `M=gpt-6-luna-codex` — FAIL:
```
workdir: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.Gt7ifR8l5Z
model: gpt-6-luna-codex
provider: openai
...
2026-09-27T03:35:58.654281Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 426 Upgrade Required, url: ws://127.0.0.1:17841/v1/responses
ERROR: {"detail":"The 'gpt-6-luna-codex' model is not supported when using Codex with a ChatGPT account."}
ERROR: {"detail":"The 'gpt-6-luna-codex' model is not supported when using Codex with a ChatGPT account."}
```

6. No `-m` (default) — OK, model `gpt-6-astra`:
```
OpenAI Codex v0.158.0-alpha.2
--------
workdir: /var/folders/6q/27cy8k2s7w7cyb5spxrkj2mm0000gp/T/tmp.Gt7ifR8l5Z
model: gpt-6-astra
provider: openai
approval: never
sandbox: read-only
reasoning effort: ultra
reasoning summaries: none
session id: 01a0e0ef-2b8a-7592-b483-9a4fb0537983
--------
user
Reply with exactly: ok
warning: Under-development features enabled: context_management...
2026-09-27T03:36:06.670136Z ERROR codex_api::endpoint::responses_websocket: failed to connect to websocket: HTTP error: 426 Upgrade Required, url: ws://127.0.0.1:17841/v1/responses
codex
ok
tokens used
14,245
ok
```
