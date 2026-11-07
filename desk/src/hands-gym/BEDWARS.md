# Real private Bedwars daytime gym

`hands_gym.bedwars_env.BedwarsEnv` adapts the existing 1.8.9 bridge to the
unchanged `GymPolicy` and shared native action dictionaries. This is not a
separate Bedwars brain: Glim supplies slow tactical text, HANDS supplies all
keys/mouse movement, and the existing PlayKit server plugin supplies rewards.
The first experiment starts fresh HANDS weights, not a pretrained VPT policy.

## Safety and ownership

- Private Paper 1.8.8 + BedWars1058, existing privately generated `duel` map.
  No public server, private footage, desktop inputs, Lunar Client, or sleep job.
- Server lives under `C:\Users\benja\bedwars-play\bedwars1\server`.
  Minecraft/RCON/bridge ports are loopback 25571/25581/7796.
- **Do not render clients on BensPC.** Its Windows iGPU preference was ignored
  in smoke setup. The BensPC `join` command deliberately refuses rendering.
  Server and HANDS inference/PPO are CPU-only (two PyTorch threads, explicit CPU
  tensors/optimizer). `CUDA_VISIBLE_DEVICES` is cleared as an extra precaution;
  Windows may still report CUDA available, so that flag is not isolation proof.
  They need no GPU lease. Any future CUDA trainer must use `gpu_gate.Lease`.
- Brikto's two own clients are under `C:\Users\Public\bedwars1`, run hidden
  where possible, below normal priority, 426x240, capped at 20 FPS. Ben permits
  this anytime. Only exact owned Java executable + bot-name matches are killed.
  Scheduled tasks refuse unknown/running replacements. No personal profile
  permissions or programs are changed.
- The server task has a six-hour execution limit; clients/controller have two
  hours. Quit owned clients after recorded play so the server remains idle.
  Check Windows reboot flags; trainer writes atomic weights and optimizer/RNG
  state every PPO update. It does not promise exact live-world crash recovery.

## Launch / join / quit through tools

All commands run from `desk/src/hands-gym` on the Mac. Existing offline Java,
Fabric 1.8.9 assets and `bwbridge189` are reused, not downloaded by these tools.
`bedwars-runtime.json` contains the cached launch arguments, no login tokens.
It rewrites paths into the dedicated Brikto root and derives per-name offline
UUIDs. Never substitute another user's game directory.

```sh
python3 bedwars-session.py launch --log /absolute/evidence/lifecycle.jsonl
```

Keep these two SSH tunnels running (the reversed client connections terminate
only on loopback; Minecraft's offline server must not be exposed publicly):

```sh
ssh -N -C -o IPQoS=none -o ExitOnForwardFailure=yes -o ServerAliveInterval=60 \
  -o ServerAliveCountMax=5 \
  -L 127.0.0.1:25572:127.0.0.1:25571 \
  -L 127.0.0.1:7797:127.0.0.1:7796 benspc
ssh -N -C -o IPQoS=none -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=60 -o ServerAliveCountMax=5 \
  -R 127.0.0.1:25571:127.0.0.1:25572 \
  -R 127.0.0.1:7796:127.0.0.1:7797 brikto
```

Use the Tailscale `benspc` and `brikto` SSH aliases, not the unavailable LAN
aliases. Compression reduces the raw bridge frames' transport load. Start the
controller before joining, through PowerShell EncodedCommand/Python stdin or
an interactive terminal on BensPC:

`python3 bedwars-pc.py --log /absolute/evidence/command.log` accepts Python
source on stdin and executes it in the existing BensPC gym environment. It
records the exact transport, source, stdout, stderr and exit status. It uses
the working Tailscale alias instead of changing the shared `pc.py` helper.

```powershell
Set-Location C:\Users\benja\hands-gym
.\venv\Scripts\python.exe -m hands_gym.bedwars_run --mode practice `
  --output C:\Users\benja\bedwars-play\bedwars1\new-unique-run `
  --seeds 11 22 33 --eval-games 4 --updates 24 --rollout 16 --practice-minutes 10
```

For a stationary paired comparison, add `--plan` with the path to the actual
retained Glim response JSON (`source: glim`). The controller copies and hashes
that response and uses it unchanged for both phases, without a network relay
freshness dependency. A frozen plan is not a measurement of live replanning.
Live mode omits `--plan`; the relay receives an authoritative server-state
snapshot every few seconds. That snapshot never enters HANDS' pixel tensors
or proprioception directly, and Glim never assigns rewards.

The helper `hands_gym.bedwars_tools.detached(arguments, cwd, 'controller')`
can run this as our own hidden interactive scheduled task, persisting after SSH
disconnect. It refuses an already running task rather than taking it over.

```sh
python3 bedwars-tactics.py --output /absolute/evidence/tactics --minutes 90
python3 bedwars-session.py join --log /absolute/evidence/lifecycle.jsonl
python3 bedwars-session.py status --log /absolute/evidence/lifecycle.jsonl
python3 bedwars-session.py quit --log /absolute/evidence/lifecycle.jsonl
```

`join` starts both own clients; use `--name BotHands1` or `BotIdle1` to target
one. The idle opponent receives zero input, never scripted server teleports.
Join/quit are tested native launch/termination steps, not screen automation.
`launch` refuses occupied ports; use `status` to reuse the running own server.

## Control and referee boundary

Bridge packets are length-prefixed, allowlisted by owned bot name, capped at
2 MiB and bound to loopback. `parse_pixels` discards client coordinates, yaw,
health, inventory and chat before constructing policy inputs. The policy sees
only resized pixels, tactical text and twelve zero proprioception values.
Truth supplies reward, terminal state and evaluation, plus a separate bounded
state snapshot for slow-brain planning. Raw truth never enters HANDS directly.

Shared action kinds are click/drag/key/scroll. W/A/S/D, space, C=sneak,
R=sprint, F=attack, G=use, and 1-9=hotbar are translated to the old bridge's
key mask. In-world click/drag controls relative camera plus attack; GUI clicks
use its 16x9 grid. Unsupported keys are explicit no-ops. One action cannot
express arbitrary simultaneous W-tap/strafe/jump combos; this introductory
adapter does not claim advanced combat or reliable shop/bridge skills.

The Mac relay calls the actual Nanbeige Glim endpoint only through
`realmodel-lock.sh BEDWARS`, at most once per 15 seconds. Busy/failed/stale
requests produce logged scripted instructions. It receives the separate game
snapshot but never grades a result. No changes are made to Glim, its gateway,
or Ben's chat.
Atomic tactical-state publication is best-effort: a Windows reader-sharing
conflict is recorded and retried at the next two-second publication, never
treated as a game failure or a reward. Stale tactics still fall back explicitly.
`--plan /absolute/saved-glim-response.json` retains an actual Glim plan for a
stationary paired PPO measurement. Its source is `glim_cached` and its hash is
recorded; this is not a claim of online replanning. Omit `--plan` for live
low-rate requests and explicitly logged busy/timeout fallback.

## Evaluation and evidence

Prerecorded contract: goals are reach own generator within 1.5 blocks, collect
four iron, and survive ten server seconds without a death. Stock server events
end introductory rounds naturally; upgrade starts are shortened to 5/10 seconds,
then beds/dragon/end countdowns are 15 seconds each. Draws usually take 1,281
ticks. Timeouts with `end:why=restarting` count as completed draws, not wins.
Plugin-disable and fixed-horizon episodes never count as completed games.

Each run records timestamped PNGs (up to 5 FPS/client), native policy actions,
bridge action/ACK sequences, instruction provenance, raw copied server truth,
episode rates, PPO curves and weight hashes. Correlate frame `wall_ms`, bridge
sequence, native generation and truth `ms` rather than equating the clocks.
Current map is fixed: held-out action RNG seeds are not held-out map seeds.
Replay is unavailable; worlds cannot be restored to an identical RNG snapshot.

For ten additional live, replanned/fallback games without fitting weights:

```powershell
.\venv\Scripts\python.exe -m hands_gym.bedwars_run --mode live `
  --output C:\Users\benja\bedwars-play\bedwars1\live-unique-run `
  --seeds 11 --eval-games 10 `
  --checkpoint C:\Users\benja\bedwars-play\bedwars1\primary-04\seed-11-final.pt
.\venv\Scripts\python.exe -m hands_gym.bedwars_audit `
  --run C:\Users\benja\bedwars-play\bedwars1\live-unique-run
```

Restart the Mac relay without `--plan` before live play. Its fallback can be
used when chat or another experiment owns the brain lock; never steal the lock.
The offline auditor independently recomputes every goal from raw truth, checks
natural completion, unique matches, applied/ACKed commands and PNG hashes, and
writes `audit.json` plus `goal-rates.csv`. It never changes game results.

```sh
.venv/bin/python ../../test/hands-gym-bedwars.test.py
```

These offline tests exercise actual loopback framing, pixel isolation, server
goal checks, partial truth lines, stale tactics and lifecycle refusal. Windows
execution validates this adapter only, not the Mac app. Report every seed and
any lack of improvement; rewards never come from a model's opinion.
