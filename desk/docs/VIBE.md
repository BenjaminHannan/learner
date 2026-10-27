# What we borrowed (and from where, at the feature level)

Ben asked us to study similar apps (Manus, Muse, ChatGPT agent, Linear, Dynamic Island style status pills, Clippy lessons) and keep what feels good. Everything is written fresh.

- **Calm, quiet base.** Near-neutral warm surfaces, one amber accent used sparingly, hairline borders as 10-16% overlays instead of solid greys. Dark base is a warm near-black, not murky brown-grey. Body text >= 4.5:1; even the "faint" labels are >= 4.5:1 here. High-contrast toggle in Settings.
- **Reading column.** Chat capped at 760 px, 16.5 px / 1.5, system font. Ben's messages are soft filled bubbles, Glim's answers are plain text.
- **One collapsible activity block per task.** Reasoning, plan and tool calls fold into one block: live "doing X" line while running, collapses to "Did 6 things . 14 s" when done; every step stays inside (audit trail, nothing hidden).
- **Live browser card with take-over.** The card shows the agent's page live; click to take over in a popup; "Hand back to Glim" returns control. Logins, 2-step and passkeys are a named hand-off moment with a banner. Final purchases and sends always get their own `ask_user` confirm card (prompt rule), never a quiet click.
- **Page text is data, not instructions** (prompt-injection rule in the system prompt).
- **Top pill.** Compact (Glim + one line), expands on hover after a ~150 ms intent delay (280 ms with a little spring), collapses in ~190 ms. One state source with fixed priority (error > waiting for Ben > working > done) feeds the pill, the top-bar Glim and the dock badge.
- **Alive but not annoying.** Idle blink and an occasional glance on random timers, sleepy after 5 minutes idle; Glim only interrupts for errors, waiting-for-Ben and finished helper results.
- **New chat screen.** Glim, a greeting and four suggestion chips that fill the composer.
