# Glim BensPC runbook

Generated from `runbook.json` (that file is the source of truth; `glimtool.ps1` reads it to fill `next`).

Rules: try the fixes in order. Ask Ben ONLY for: no signed-in session, a login we do not have, a purchase, a Windows UAC prompt. The locked screen is normal (Ben locks BensPC on purpose): never unlock it, never ask to, and never drive Minecraft with desktop clicks or typing. Everything else, retry or do something else.

Happy path: `ping` (hands rule) -> `disk` -> `gpu-acquire` -> `server-start --map M` -> `map-list` -> `client-launch` (GlimTruthKit auto-joins GlimBot) -> `match-start` -> play (`ping` every ~2 s, `match-status`, `log-read`) -> `match-stop` -> `client-stop` -> `server-stop` -> `gpu-release`.

## connect

### `ssh-down`
Error text: ssh: connect to host 10.0.0.188 port 22: Connection timed out / refused

1. retry over Tailscale: ssh benspc (the LAN address 10.0.0.188 may be wrong)
2. wait 60 s and retry both routes, up to 3 times
3. BensPC may be off or restarting: do something else now and try again later (do not ask Ben)

Ask Ben: no

### `no-session`
Error text: no signed-in session

1. check signed_in again in a minute (auto sign-in can still be finishing after a restart) (`ping`)
2. wait up to 3 minutes, then ping again

Ask Ben: **yes** - sign in to BensPC (Minecraft needs a signed-in Windows session to use the NVIDIA GPU)

### `screen-locked`
Error text: the screen is locked, so desk clicks and screenshots cannot work

1. normal: Ben locks BensPC on purpose; Glim never unlocks it and never asks to
2. Minecraft is driven from the inside: server-start, client-launch, match-start and match-stop all work while locked; do not use desk input
3. a locked screen means nobody is using BensPC, so the hands rule allows play (`ping`)

Ask Ben: no

### `not-set-up`
Error text: C:\Users\benja\glim-bedwars does not exist yet (setup.ps1 has not run)

1. run setup.ps1 on BensPC (one-time; it is idempotent and has -DryRun)

Ask Ben: no

### `bad-arg`
Error text: bad argument

1. re-read the verb table in TOOLS.md and call again with valid arguments

Ask Ben: no

## disk

### `low-disk`
Error text: only N GB free on C: (floor is 15 GB)

1. check free_gb again (`disk`)
2. fetch then remove old screenshots in glim-bedwars\shots (the tool keeps only the newest 60 anyway)
3. stop writing: do not start a match until free space is back above 15 GB; try again later

Ask Ben: no

## gpu

### `gpu-held`
Error text: GPU is held by <who>

1. read the holder and last_line (`gpu-status`)
2. wait 10 minutes and gpu-acquire again; meanwhile do something else (never take the GPU from another job)
3. a match without the GPU is not possible: skip playing for now

Ask Ben: no

### `gpu-not-held`
Error text: sign up for the GPU first

1. gpu-acquire --who glim-bedwars --why TEXT, then client-launch again (`gpu-acquire`)

Ask Ben: no

### `gpu-sheet-missing`
Error text: GPU_LOAN.txt not found

1. do not play without the sheet; tell the coordinator thread (the sheet moved)

Ask Ben: no

## server

### `server-wont-start`
Error text: the server exited while starting / did not open its port within 120 s / no Java 21 found

1. check whether it is actually running (`server-status`)
2. read the tail in the error text (it comes from logs\server.out); a Java error means check C:\Program Files\Eclipse Adoptium
3. stop, wait 10 s, then server-start once more (`server-stop`)
4. if it still fails twice, stop and report it to the coordinator thread

Ask Ben: no

### `port-in-use`
Error text: port 25567 is already used by a process that is not ours

1. check it is not our own server (running:true) (`server-status`)
2. never kill the other process; wait 2 minutes and try again; report to the coordinator thread if it stays

Ask Ben: no

### `server-down`
Error text: our server is not running / nothing is listening

1. start it (`server-start`)

Ask Ben: no

## map

### `map-missing`
Error text: map 'X' is not in map-list

1. list the maps and pick one from the list (known: duel, squad) (`map-list`)
2. if the list is empty, setup.ps1 has not copied the server: report to the coordinator thread

Ask Ben: no

### `opponent-unavailable`
Error text: opponent 'scripted:L2' is not built yet (only 'none')

1. call match-start again with --opponent none

Ask Ben: no

### `truthkit-missing`
Error text: the GlimTruthKit plugin did not answer on RCON (tk status)

1. check that our server is up (`server-status`)
2. run setup.ps1 (it builds GlimTruthKit and puts it in server\plugins), then server-stop and server-start
3. if it is still missing, report it to the coordinator thread

Ask Ben: no

### `arena-join-failed`
Error text: GlimBot is on the server but not in arena X

1. look at the arena state and players (`match-status`)
2. call match-start again: it sends GlimBot with /bw join run as the player (no typing)
3. if the arena is restarting, wait 30 s and try again

Ask Ben: no

### `match-wont-start`
Error text: tk start did not start the arena / the arena did not reach playing within 30 s

1. read the arena state (`match-status`)
2. reset the arena (`match-stop`)
3. match-start once more; if it fails twice, report it to the coordinator thread

Ask Ben: no

## client

### `client-crash`
Error text: the client did not start / the game process did not appear within 90 s

1. clear any half-started client (`client-stop`)
2. check free space (`disk`)
3. launch once more; read logs\client.err via fetch --path logs\client.err (`client-launch`)
4. if it crashes twice, stop and report it to the coordinator thread

Ask Ben: no

### `client-not-joined`
Error text: GlimBot is not on the server yet

1. look at names; wait 20 s for the join (`server-status`)
2. launch the client if it is not running (GlimTruthKit sends it into the arena on login) (`client-launch`)

Ask Ben: no

### `bridge-missing`
Error text: the GlimBridge scheduled task is not registered

1. run setup.ps1 on BensPC (it registers the task)

Ask Ben: no

### `bridge-timeout`
Error text: the bridge did not answer within N s

1. check signed_in (`ping`)
2. try the same verb once more; a first start of the bridge can take 10 s
3. if signed_in is false, follow no-session

Ask Ben: no

### `desk-failed`
Error text: deskhelper reported an error

1. look at the screen again (`desk look`)
2. try another way (key instead of click, or open-app Minecraft first)

Ask Ben: no

### `login-required`
Error text: a login screen or Microsoft sign-in is on the screen

1. our own client never needs a login; if one appears, close the window with client-stop and relaunch with client-launch

Ask Ben: **yes** - a login is needed that Glim does not have (Glim never types Ben's password)

### `purchase`
Error text: a screen asks to buy something

1. do not click anything; close with client-stop

Ask Ben: **yes** - something asks for a purchase (Glim never buys anything)

### `uac`
Error text: a Windows UAC (administrator permission) prompt appeared

1. do not touch it; wait 30 s in case it was a one-off

Ask Ben: **yes** - a Windows UAC prompt needs a person

### `desk-refused`
Error text: Minecraft is driven from the inside (server commands, client control path), never with desktop clicks or typing

1. use match-start / match-stop (server-side commands) instead; while our client runs, desk is for look and screenshot only

Ask Ben: no

## files

### `no-such-file`
Error text: no file at <path>

1. take the screenshot again (desk screenshot), then fetch the new path

Ask Ben: no

### `too-big`
Error text: file is N bytes (cap is 8 MB)

1. take a smaller screenshot: desk screenshot name.png --max 1280

Ask Ben: no
