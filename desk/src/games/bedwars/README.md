# Bedwars adapter (Glim team, Bedwars side)

This folder holds Glim's Bedwars adapter, harness and play session (plan v4.1: `bedwars/GLIM-MERGE-PLAN.md` in the research repo).
It's Mac-side JavaScript: pure logic, no network in tests. The BensPC scripts live in `benspc/` and their contract in `TOOLS.md`; both belong to the other brief.

## Files
| file | what it is |
|---|---|
| `core-iface.js` | The only door to Glim's two-speed core. Small stand-ins for the intent channel, plan memory, action schedule and sleep hook, plus the exact map for wiring to I3's `src/games/core/` (one-file change). |
| `tactics.js` | The fixed tactical vocabulary from PVP-HABITS.md (`st l w`, `jc 3`, `bh`, `br 2; jg`, `buy wool`, `get iron 16`, `bb`, ...): typed params, short text, parser and validator. Also plan-level steps (get_resources → buy_blocks → bridge → break_bed) and replan triggers (knocked off, low HP, bed under attack, step timeout). `coreVocab()` gives the same vocabulary in I3's format. |
| `timing.js` | Timed actions ("baseball"): tau estimators for jump-at-edge, block-at-hit and crit-on-fall (1.8 jump physics: crit window 350–550 ms after the jump), the fire-on-nearest-tick rule, and the timing error in ms against the truth-log ideal moment. |
| `truthlog.js` | Turns `log-read` events into (a) Ben's rewards, exactly; (b) hindsight labels (time-to-hit, time-to-edge, crit windows); (c) the long-horizon goal scorer (steps in order, replans counted); (d) "worked / failed" text cards for sleep. Truth log only, no grader. |
| `adapter.js` | The game adapter. Allowed inputs (screen frame ref, whitelisted HUD, sound; no minimap, reach, distance, coords or freelook; FOV ≤ 110), keys and mouse plus timed actions, call → reflex conditioning vector. Flags: `realtime: true`, ≤ 30 ms frame→key, 50 ms tick, 2 s hold. Sleep hooks give day data only (`nightPlay: false`). |
| `benspc.js` | The Mac client for TOOLS.md: ssh over LAN first, then Tailscale, with timeouts. Parses the one JSON line and refuses unsafe argument text. A state-changing verb that times out is not re-sent on the other route. The runner can be swapped for tests. |
| `session.js` | The self-sufficient play session as a step machine: gpu-acquire → server → map/match → client → play → stop all → gpu-release. It retries with backoff and runs the runbook's `next` alternatives (read-only ones, or the matching stop inside its own start step). `askBen` is used only when signed out, a login is missing, a purchase is needed, or a UAC prompt appears. It always cleans up and never stops what it didn't start. `wantToPlay()` returns the activity. |
| `harness.js` | Measurements from logs: p95 frame→key, timing error per skill, the long-horizon score, and the self-sufficient-play acceptance (≥ 9/10, failures per step). |

Tests: `desk/test/bedwars-{tactics,timing,truthlog,benspc-client,session,adapter}.test.js`.

## Hooking it up
**Motivation (not edited here).** `wantToPlay(opts)` returns a Mote-pool job `{kind: 'game:bedwars', topic, realtime, needs, run(ctl)}`. The pool already drives jobs with their own `run(ctl)` (see `src/motepool.js`), so the job obeys the same gate, Ben-first stop and memory budget. Suggested one-line hookup in `main.js` `aoUrgeTick()`, right after `const sci = ...`, behind a setting that defaults OFF:
```js
if (store.getSettings().bedwarsPlay === true) { const b = require('./src/games/bedwars/session').wantToPlay({ benspc: new (require('./src/games/bedwars/benspc').BensPC)(), askBen: (why, detail) => aoWorthTelling('I need you for Bedwars: ' + why + ' (' + detail + ')', 0.9) }); if (b) sci.push(b); }
```
- A busy GPU gives `outcome: 'deferred'` (Glim does something else).
- Ben chatting closes the pool gate, so the session yields and cleans up.

**Core.** See the header of `core-iface.js` for the mapping to I3's `intent.js`, `plan.js`, `schedule.js` and `reflex.js`. This isn't wired yet because I3 was still changing those files.

## Stubbed or missing (said plainly)
- **No real play loop yet.** `session.play()` only watches `match-status` and reads the truth log. The reflex that presses keys next to the game on BensPC isn't built here (the core and sleep own it). Pass `play` to plug it in.
- **Hit, edge and position lines.** The plain server log (glimtool `log-read` v1) gives kills, deaths, void deaths, bed breaks, joins and match start/end.
  - Hits, crits, pickups, purchases and block places only come from our `logs/truth.jsonl` once a plugin writes it.
  - Until then, hits, the idle charge and void-kill credit can't be measured. `rewards()` reports `hitsLogged: 0` so nobody trusts a total built without hits.
  - Jump-at-edge timing needs `edge` events (`{t, type: 'edge', player}`: the moment the feet leave the last block). They aren't in TOOLS.md v1.
  - Server-log times are whole seconds, which is too coarse for timing metrics. Those need truth.jsonl times in ms.
- **Field names assumed** (aliases accepted): hit `{attacker, victim, crit?, damage?}`, kill `{killer, victim}`, death `{victim, cause?, final?}`, void_death `{victim}`, bed_broken `{by?, team?}` or `{text: "... destroyed by NAME"}`, pickup `{player, item, count}`, purchase `{player, item, cost?}`, block_place `{player}`.
- **Our own choices** (not Ben's rules):
  - the 5 s respawn used for "both alive";
  - LOW_HP = 6;
  - step timeouts;
  - the 2-tick late-cancel;
  - retry counts and backoff;
  - the 1 s window for merging kill and death lines;
  - the 3–45 s card windows.
- **Not measured yet:** `timing.js` and `truthlog.js` were checked only on hand-made logs. Nothing here has run against BensPC.
