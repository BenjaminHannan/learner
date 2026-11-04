# BensPC tools for Glim (contract v2, 2026-11-04)

Glim (on the Mac) plays Bedwars on BensPC with no human help (plan v4.1 §3b). This file is the contract between:
- the BensPC side (`benspc/`, PowerShell, plus the GlimTruthKit server plugin in `benspc/truthkit/`);
- the Mac-side client (`benspc.js`, used by the adapter and `session.js`).

v2 changes from v1: `ping` reports `locked` and `idle_s` (the hands rule); matches start with no typing (GlimTruthKit); the truth log `logs\truth.jsonl` exists, with ms times, hits, crits, void deaths, pickups, per-tick positions and edges; `log-read` gained `--types`, `source` and `more`; `client-launch` reports `nvidia`; `desk` input is refused while our client runs.

## Transport
- Mac → BensPC: `ssh -o HostName=10.0.0.188 benspc` (LAN) first, then plain `ssh benspc` (Tailscale) as fallback. The ConnectTimeout is 8 s. Slow verbs get longer waits on the Mac side (`benspc.js` SLOW: server-start 240 s, client-launch 150 s, match-start 120 s).
- The SSH key for Glim is restricted on BensPC to one forced command: `glimtool.ps1`. Only the verbs below are allowed; anything else returns `{"ok":false,"error":"not allowed"}`. (setup.ps1 prints the key line; it never installs it.)
- Every verb prints ONE JSON line on stdout: `{"ok":true,...}` or `{"ok":false,"error":"<plain text>","next":["<verb or hint>",...]}`. `next` comes from the runbook.

## The signed-in session (bridge)
SSH runs outside the interactive desktop. Reading the idle time and launching Minecraft so that it gets the NVIDIA GPU must run in benja's signed-in session. Auto sign-in is on, and Ben locks the screen on purpose: **a locked screen is normal**. Glim never unlocks it and never asks to.
- `glimtool` hands these to a **bridge**: the scheduled task `GlimBridge` (interactive token; it runs only while benja is signed in), started hidden through `wscript.exe bridge-launch.vbs`. It reads request files under `C:\Users\benja\glim-bedwars\bridge\`, runs the action, writes a result file, and stays up while requests keep coming (it exits after 25 s with none).
- If benja isn't signed in, the result is `{"ok":false,"error":"no signed-in session",...}`.

## Minecraft is driven from the inside
Never with desktop clicks or typing. Joining, starting, stopping and (for tests) nudging go through server-side commands of our own plugin **GlimTruthKit** (console / RCON on 127.0.0.1:25577, our server copy only). The bot's own moves go through the bedwars-189 bot-client control path (not wired into glimtool yet).

## Verbs (v2)
| verb | args | ok result | notes |
|---|---|---|---|
| `ping` | | `{ok, host, time, session_user, signed_in, locked, lock_src, idle_s, last_input_ms, free_gb}` (+ `idle_error` when idle is unknown) | `locked`: the session's WTS lock flag read in the session (`lock_src:"wts"`), else LogonUI present (`"logonui"`). `idle_s`: seconds since the last keyboard/mouse input in benja's session (GetLastInputInfo, through the bridge); `null` = unknown. `last_input_ms` = that input's time, epoch ms on BensPC's clock |
| `disk` | | `{ok, free_gb, floor_gb}` | floor 15 GB: verbs that write refuse below it |
| `gpu-status` | | `{ok, holder, free, last_line, util, mem_mb}` | reads `C:\Users\benja\qonly-staging\runs\autopilot\GPU_LOAN.txt` (last line) |
| `gpu-acquire` | `--who glim-bedwars --why TEXT` | `{ok, holder}` | only if the last line starts with "GPU free"; appends "GPU in use by glim-bedwars since <ET>" |
| `gpu-release` | | `{ok, released}` | appends "GPU free <ET>" only if glim-bedwars holds it |
| `server-start` | `[--map NAME]` | `{ok, pid, port, rcon, truthkit, autojoin}` | our copy in `C:\Users\benja\glim-bedwars\server` (Paper 1.8.8 + BedWars1058 + GlimTruthKit), port 25567; records the pid in `pids.json`. `--map` sets GlimTruthKit's auto-join arena. Waits for the port (≤120 s), then RCON and `tk status` (≤60 s). An already running server of ours is reused (`note:"already running"`) |
| `server-stop` | | `{ok, stopped}` | stops only pids in `pids.json` (command line checked first) |
| `server-status` | | `{ok, running, pid, port, players, names}` | |
| `map-list` | | `{ok, maps:[...], source}` | BedWars1058 arenas in our server copy |
| `match-start` | `--map NAME [--mode 1v1] [--opponent none] [--name GlimBot]` | `{ok, match_id, arena, state, joined_by, command}` | see "Starting a match"; only `--opponent none` exists yet (`opponent-unavailable` otherwise) |
| `match-status` | | `{ok, state, t, match_id, map, teams:[{team, bed, members}], beds:{team: bool}, players}` | `state`: `idle`, `starting`, `running`, `ended`, `no-server`, `unknown`. Our match is `ended` once its arena restarts or resets. `t` = seconds since match-start |
| `match-stop` | | `{ok, stopped, arena_stopped}` | `tk stop <map>` (a playing arena restarts; players waiting in it leave), then auto-join off |
| `log-read` | `--since ISO [--max N] [--types a,b,...]` | `{ok, source, count, more, next_since, events:[...]}` | see "Reading the truth log" |
| `client-launch` | `--name GlimBot [--server 127.0.0.1:PORT]` | `{ok, pid, window, nvidia}` | **our offline launcher** (no Microsoft login), through the bridge so it runs in the signed-in session (locked is fine). Needs the GPU signed up first. `nvidia`: the pid appears in `nvidia-smi --query-compute-apps` within 15 s (`null` = could not check) |
| `client-stop` | | `{ok, stopped}` | only our pids |
| `desk` | `look\|press\|click\|type\|key\|scroll\|open-app\|screenshot ARGS` | deskhelper.exe's JSON | through the bridge, never on a locked screen. Input sub-verbs are refused (`desk-refused`) while our client runs: Minecraft is never driven with desktop input. `screenshot` saves under `glim-bedwars\shots\` (newest 60 files, ≤300 MB) |
| `fetch` | `--path REL` | `{ok, path, bytes, b64}` | only under `glim-bedwars\`, ≤8 MB |

## Starting a match (no typing)
1. `server-start --map duel` writes the auto-join arena; GlimTruthKit sends every player whose name matches `^Glim[A-Za-z0-9_]*$` into it 1.5 s and 8 s after login, by running `bw join duel` **as that player** (`performCommand`; no chat).
2. `client-launch --name GlimBot` logs the bot in. `match-start --map duel` sets auto-join again (`tk autojoin duel`), waits ≤45 s for GlimBot to be in the arena (after ~4 s it also runs `tk join GlimBot duel`; `joined_by` says which worked).
3. Then `tk start duel`: GlimTruthKit runs BedWars1058's own **`/bw forceStart debug`** as GlimBot, with op for that one command only (`CmdStart` needs a player in the arena; `debug` + op allows a start with one player; the countdown is then 5 s). match-start waits ≤30 s for the arena to reach `playing`. `command` in the reply names the command used.

GlimTruthKit console / RCON commands (op players too): `tk status` (JSON), `tk autojoin <arena|off>`, `tk join <player> <arena>`, `tk start <arena>`, `tk stop <arena|all>`, `tk nudge <player> vx vy vz` (test only; each ≤1), `tk truth on|off`.

## Reading the truth log
`log-read` returns events after `--since` in time order (ms, then file order), at most `--max` (default 200, cap 2000), optionally only `--types`. A page never splits one millisecond across two pages. If `more` is true, call again with `--since <next_since>`.
- `source:"truth"`: `C:\Users\benja\glim-bedwars\logs\truth.jsonl`, written by GlimTruthKit; lines are passed through exactly as written (rotates at 64 MB to `truth.prev.jsonl`).
- `source:"server-log"`: only when truth.jsonl is missing or empty; whole-second times and fewer event types (no hits, no ticks).

### truth.jsonl (GlimTruthKit): one JSON object per line
Every line starts `{"ms": <epoch ms>, "t": "<ISO with ms and offset, the same instant>", "type": "<type>", ...}`. Human chat is never stored (the plugin has no chat listener, and its console filter hides chat lines).

| type (event table, not verbs) | fields | when |
|---|---|---|
| **join**, **leave** | `player` | a player logs in / out |
| **match_start** | `arena, match_id, group, teams:[{team, members, bed:[x,y,z]}]` | the arena reaches `playing` |
| **match_end** | `arena, match_id, winner_team, winners, why ("game end"\|"restarting"\|"server stop"), ticks` | |
| **hit** | `attacker, victim, damage (final), raw_damage, crit, via (melee\|arrow\|snowball\|fireball\|...\|tnt), victim_hp, arena` | a player damages another player (cancelled hits are not logged). `crit`: the 1.8 rule (melee, attacker falling, not on ground, not on a ladder/vine/in water, no blindness, not riding) |
| **death** | `victim, killer, cause, final, void, arena` | every death. `cause`: BedWars1058's cause (e.g. `PVP`, `VOID`, `VOID_FINAL_KILL`) or Bukkit's damage cause |
| **kill** | `killer, victim, cause, final, void, arena` | same death, when there is a killer (same `ms`) |
| **void_death** | `victim, killer, final, arena` | same death, when it was the void (same `ms`) |
| **bed_broken** | `by, by_team, team, arena` | `team` = whose bed |
| **purchase** | `player, item, item_id, cost?, currency?, arena` | `item` = the shop id's last part (`wool`, `clay`, `glass`, `stone` = end stone, `wood`, `obsidian`, `stone_sword`, ...) |
| **upgrade** | `player, upgrade, arena` | team upgrade bought |
| **pickup** | `player, item, count, arena` | `item`: `iron_ingot`, `gold_ingot`, `diamond`, `emerald`, ... |
| **block_place**, **block_break** | `player, block, x, y, z, arena` | |
| **tick** | `arena, tick, p:[{n, team, x, y, z, yaw, pitch, vx, vy, vz, og, alive, hp, sneak, sprint, held}]` | every server tick (20 Hz) while a match plays. `vx/vy/vz` in blocks/s (position change since the last tick), `og` on ground 0/1 |
| **edge** | `player, arena, x, y, z, ground_y, og, vx, vz, last_supported_ms` | the first tick the 0.6-wide feet footprint no longer has a solid block under it at the last ground level (walking or mid-jump). `last_supported_ms` = the tick before; the true crossing is between them. Teleports and respawns are ignored |

On the Mac, `truthlog.js` reads these lines (`normalize` uses `ms`), merges the death/kill/void_death lines of one death, and applies Ben's reward rules; `truthlog.track(events, name)` gives one player's per-tick rows; `timing.js` takes the ideal jump moment midway between `last_supported_ms` and `t`.

## The hands rule (session.js)
Before a session and every ~2 s during play, Glim calls `ping`:
- signed out or `locked: true` → go (nobody can be using it);
- unlocked and `idle_s` < 120 → someone is using BensPC: don't start;
- unlocked and idle ≥ 120 → ask Ben once per idle stretch through the `askUser` hook (yes → go, no → don't, no answer in 60 s → go);
- `idle_s` unknown → don't start.
During play, new input (last_input_ms moved by more than 1.5 s), an unlock, or 3 unreadable pings in a row freeze the session: play stops at once and the normal cleanup runs (match, client, server, GPU).

## Guardrails (all verbs)
- They write only under `C:\Users\benja\glim-bedwars\`. Existing `bedwars-189\` files are read-only sources, copied once by `setup.ps1`.
- They stop only processes they started (`pids.json`), and only after checking the command line. They never touch Ben's programs.
- They respect `GPU_LOAN.txt`, the STOP files, and the 15 GB disk floor.
- They never use Hypixel. They never type Ben's password. They never make purchases. They never unlock the screen.
