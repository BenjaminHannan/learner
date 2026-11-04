# Bedwars adapter (Glim team, Bedwars side)

This folder holds Glim's Bedwars adapter, harness and play session (plan v4.1: `bedwars/GLIM-MERGE-PLAN.md` in the research repo).
It's Mac-side JavaScript: pure logic, no network in tests. The BensPC scripts live in `benspc/` (with our server plugin GlimTruthKit in `benspc/truthkit/`) and their contract in `TOOLS.md` (v2).

## Files
| file | what it is |
|---|---|
| `core-iface.js` | The only door to I3's two-speed core (`src/games/core/`): re-exports the real intent channel, plan memory, action schedule, reflex + sleep, `runEpisode` and the brain prompt/parser (no stand-ins). Adds `LiveLoop` / `runLive`, a game-agnostic tick driver for a real-time game whose slow brain is slow and often wrong (see Core below). |
| `tactics.js` | The slow brain's vocabulary: 9 calls in I3's format (`GET res= n=`, `BUY item=`, `BRIDGE n=`, `BREAK_BED`, `FIGHT`, `RETREAT`, `DEFEND`, `HOME`, `HOLD`), one line each, OWN vs ENEMY spelled out. The plan rules: `repair()` (done steps dropped, iron and wool derived, shears added for a covered bed, home before the shop, the goal kept) and `urgent()` (enemy within 5 → FIGHT now; bed attacked → HOME + DEFEND). Old short codes (`jc 3`, `br 2`, `buy wool`) still parse for truth-log cards. |
| `timing.js` | Timed actions ("baseball"): tau estimators for jump-at-edge, block-at-hit and crit-on-fall (1.8 jump physics: crit window 350–550 ms after the jump), the fire-on-nearest-tick rule, and the timing error in ms against the truth-log ideal moment. |
| `truthlog.js` | Turns `log-read` events (GlimTruthKit's truth.jsonl, field list in TOOLS.md) into (a) Ben's rewards, exactly; (b) hindsight labels (time-to-hit, time-to-edge, crit windows); (c) the long-horizon goal scorer (steps in order, replans counted); (d) "worked / failed" text cards for sleep; and `track()`, one player's per-tick rows. Truth log only, no grader. |
| `adapter.js` | The adapter for I3's core, same shape as `src/games/adapters/sparksquest.js` / `orchard.js`: `observe`, `judge` (done / going / blocked per step), the hand rule `fallback` (hits whoever is in reach whatever the call, else does the call), `rawFrame` / `features` / `nightLabel` (truth-log hindsight), `timedTargets` (jump-crit 450 ms ahead, jump at the bridge end), plus `repair` / `urgent` / `interrupted` for `LiveLoop`. Allowed inputs only (`validateObs`: no minimap, reach, coords, freelook; FOV ≤ 110). A coarse 1-D side-rush **practice model** (`init` / `observe` / `step`) so tests can run the core on it: ours, not Bedwars physics. Sleep data from the truth log only (`nightPlay: false`). |
| `benspc.js` | The Mac client for TOOLS.md: ssh over LAN first, then Tailscale, with timeouts. Parses the one JSON line and refuses unsafe argument text. A state-changing verb that times out is not re-sent on the other route. The runner can be swapped for tests. |
| `session.js` | The self-sufficient play session as a step machine: hands check → gpu-acquire → server → map-list → hands re-check → client → match → play (hands watch every ~2 s) → stop all → gpu-release. The hands rule (Ben, 11-04): locked → go; unlocked and input < 2 min ago → don't; unlocked and idle ≥ 2 min → ask once through `askUser` (silence for 1 min = go); idle unknown → don't; any input or an unlock during play → freeze (play aborted, clean stop). It retries with backoff and runs the runbook's `next` alternatives (read-only ones, or the matching stop inside its own start step). `askBen` is used only when signed out, a login is missing, a purchase is needed, or a UAC prompt appears. It always cleans up and never stops what it didn't start. `wantToPlay()` returns the activity. |
| `harness.js` | Measurements from logs: p95 frame→key, timing error per skill, the long-horizon score, and the self-sufficient-play acceptance (≥ 9/10, failures per step). |

Tests: `desk/test/bedwars-{tactics,timing,truthlog,benspc-client,session,adapter,core-wiring}.test.js`.

## Hooking it up
**Motivation (not edited here).** `wantToPlay(opts)` returns a Mote-pool job `{kind: 'game:bedwars', topic, realtime, needs, run(ctl)}`. The pool already drives jobs with their own `run(ctl)` (see `src/motepool.js`), so the job obeys the same gate, Ben-first stop and memory budget. Suggested one-line hookup in `main.js` `aoUrgeTick()`, right after `const sci = ...`, behind a setting that defaults OFF:
```js
if (store.getSettings().bedwarsPlay === true) { const b = require('./src/games/bedwars/session').wantToPlay({ benspc: new (require('./src/games/bedwars/benspc').BensPC)(), askBen: (why, detail) => aoWorthTelling('I need you for Bedwars: ' + why + ' (' + detail + ')', 0.9), askUser: null /* hands question: wire to a yes/no prompt that resolves 'yes' | 'no' | null; without it, idle >= 2 min just goes */ }); if (b) sci.push(b); }
```
- A busy GPU gives `outcome: 'deferred'` (Glim does something else).
- Ben chatting closes the pool gate, so the session yields and cleans up.

**Core (wired).** The real slow brain gives ~0.3–0.4 calls/s (2.7 s per call, 3.5–11 s per plan) and is often wrong (right next call 6/12, whole plan 1/12, done list ignored, follow-ups 0/6). So it only picks the aim. `LiveLoop` (in `core-iface.js`) does the rest every 50 ms tick:
- **Rules first:** play starts at once on the rules' plan; the brain's first plan replaces it when it lands. Brain hung → the rules still win (test).
- **Plan rules:** every plan (brain or ours) goes through `repair`; death and urgent threats are fixed at once by rule, not by asking.
- **Plan memory:** `judge` marks steps done, the next step's call goes out by itself.
- **Reflex:** the hand rule (later the slept net) acts on the current call every tick.
- **Schedule:** timed jumps are re-estimated every tick and fire on their own.
- The brain is asked at most once per 2.86 s, and only for a first plan or a surprise the rules can't fix.

Fake brain as bad as the measured one, 12 practice games (`test/bedwars-core-wiring.test.js`): wired 12/12 beds (6/6 covered), 1.0 brain call per game, ~8 plan advances per game; same brain without the rules 6/12 (0/6 covered), 7.7 calls per game. On the real game the loop needs the reflex's key path on BensPC (not built, see below).

## Stubbed or missing (said plainly)
- **No real play loop yet.** `session.play()` only watches `match-status` and reads the truth log. The reflex that presses keys next to the game on BensPC isn't built here (the core and sleep own it). Pass `play` to plug it in.
- **Truth log: written, not yet proven live.** GlimTruthKit (`benspc/truthkit/`, built on BensPC with its JDK, installed only into our server copy) writes `logs/truth.jsonl` with ms times: hits with crit and damage, kills, deaths, void deaths, bed breaks, purchases, upgrades, pickups, block place/break, match start/end, per-tick position/velocity/on-ground, and `edge`. It compiles; see the latest smoke-test report for what was seen live.
  - If truth.jsonl is missing, `log-read` falls back to the plain server log (whole seconds, no hits); `rewards()` then reports `hitsLogged: 0` so nobody trusts a total built without hits.
  - The edge detector is ours (0.6-wide footprint vs the last ground level). Its exact match with "the feet leave the block" in the client is not measured yet.
- **No opponent yet.** `match-start` supports `--opponent none` only (one player, started with `/bw forceStart debug`). A scripted opponent (`scripted:L2`) is not built.
- **Bot control path.** The bot's moves should go through the bedwars-189 bot-client control path; glimtool doesn't call it yet. `tk nudge` (server-side velocity) is a test aid only.
- **Our own choices** (not Ben's rules):
  - the 5 s respawn used for "both alive";
  - LOW_HP = 6;
  - step timeouts;
  - the 2-tick late-cancel;
  - retry counts and backoff;
  - the 1 s window for merging kill and death lines;
  - the 3–45 s card windows;
  - in tactics/adapter/core-iface: the 9-call vocabulary, FIGHT within 5 blocks, a fight over beyond 8, wool 16 per buy and prices, the 2.86 s minimum between brain asks, jump-crit only for approaches starting ≥ 2 blocks outside reach, a new approach id after 8 still ticks or 0.5 blocks apart, and every number in the practice model.
- **Also ours:** in the hands rule, the 2 s watch, 1.5 s input slack, 3 unreadable pings → freeze. In GlimTruthKit: auto-join regex `^Glim...`, 1.5 s / 8 s auto-join delays, 64 MB log rotation.
- **Not measured yet:** `timing.js` and `truthlog.js` were checked only on hand-made logs shaped like GlimTruthKit's lines.
