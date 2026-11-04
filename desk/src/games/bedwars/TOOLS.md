# BensPC tools for Glim (contract v1, 2026-11-04)

Glim (on the Mac) plays Bedwars on BensPC with no human help (plan v4.1 §3b). This file is the contract between:
- the BensPC side (`benspc/`, PowerShell);
- the Mac-side client (`benspc.js`, used by the adapter).

## Transport
- Mac → BensPC: `ssh -o HostName=10.0.0.188 benspc` (LAN) first, then plain `ssh benspc` (Tailscale) as fallback. The ConnectTimeout is 8 s.
- The SSH key for Glim is restricted on BensPC to one forced command: `glimtool.ps1`. Only the verbs below are allowed; anything else returns `{"ok":false,"error":"not allowed"}`.
- Every verb prints ONE JSON line on stdout: `{"ok":true,...}` or `{"ok":false,"error":"<plain text>","next":["<verb or hint>",...]}`. `next` comes from the runbook.

## Desktop steps need the signed-in session
SSH runs outside the interactive desktop. Clicking, typing and screenshots, and launching Minecraft so that it gets the NVIDIA GPU, must run in benja's signed-in session. Auto sign-in is on, and the screen gets locked after sign-in.
- `glimtool` hands these to a **bridge**: a scheduled task with an interactive token (runs only when benja is signed in). It reads a request file under `C:\Users\benja\glim-bedwars\bridge\`, runs the action, writes a result file, and `glimtool` waits for that result (with a timeout).
- If benja isn't signed in, the result is `{"ok":false,"error":"no signed-in session","next":["ask-ben: sign in to BensPC"]}`.

## Verbs (v1)
| verb | args | ok result | notes |
|---|---|---|---|
| `ping` | | `{ok, host, time, session_user, signed_in}` | |
| `disk` | | `{ok, free_gb}` | floor 15 GB: verbs that write refuse below it |
| `gpu-status` | | `{ok, holder, free, last_line, util, mem_mb}` | reads `C:\Users\benja\qonly-staging\runs\autopilot\GPU_LOAN.txt` (last line) |
| `gpu-acquire` | `--who glim-bedwars --why TEXT` | `{ok, holder}` | only if the last line starts with "GPU free"; appends a line "GPU in use by glim-bedwars since <ET>" |
| `gpu-release` | | `{ok}` | appends "GPU free <ET>" only if glim-bedwars holds it |
| `server-start` | `[--map NAME]` | `{ok, pid, port}` | our copy in `C:\Users\benja\glim-bedwars\server` (Paper 1.8.8 + bedwars plugin); records the pid in `pids.json` |
| `server-stop` | | `{ok}` | stops only pids in `pids.json` (command line checked first) |
| `server-status` | | `{ok, running, pid, port, players}` | |
| `map-list` | | `{ok, maps:[...]}` | |
| `match-start` | `--map NAME --mode 1v1 [--opponent scripted:L2\|none]` | `{ok, match_id}` | via the plugin's commands (console/RCON) |
| `match-status` | | `{ok, state, t, teams, beds}` | |
| `match-stop` | | `{ok}` | |
| `log-read` | `--since ISO [--max N]` | `{ok, events:[{t, type, ...}], next_since}` | parsed server or plugin log + our truth log; event types: hit, kill, death, void_death, bed_broken, purchase, pickup, block_place, block_break, join, leave, match_start, match_end |
| `client-launch` | `--name GlimBot [--server 127.0.0.1:PORT]` | `{ok, pid, window}` | **our offline launcher** (no Microsoft login), through the bridge so it runs in the signed-in session on the NVIDIA GPU |
| `client-stop` | | `{ok}` | only our pid |
| `desk` | `look\|press\|click\|type\|key\|scroll\|open-app\|screenshot ARGS` | deskhelper.exe's JSON | through the bridge; `screenshot` saves under `glim-bedwars\shots\` (short window, size cap) |
| `fetch` | `--path REL` | file bytes (base64) | only under `glim-bedwars\` (e.g. screenshots) |

## Guardrails (all verbs)
- They write only under `C:\Users\benja\glim-bedwars\`. Existing `bedwars-189\` files are read-only sources, copied once by `setup.ps1`.
- They stop only processes they started (`pids.json`), and only after checking the command line. They never touch Ben's programs.
- They respect `GPU_LOAN.txt`, the STOP files, and the 15 GB disk floor.
- They never use Hypixel. They never type Ben's password. They never make purchases.
