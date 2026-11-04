# The two-speed core (I3, 2026-11-04)

Ben: "I just want it to be able to have that long horizon thinking and quick reflexes."
Plan: GLIM-MERGE-PLAN.md v4.1, section 1 (the two-speed loop) and section 2 step 4 (reflex distillation). This is the lead's
part: the game-agnostic core. Bedwars is one adapter, built by the Glim team in `src/games/bedwars/` (not touched here).

## Files (`src/games/core/`, no game names inside)
| file | what it does |
|---|---|
| `intent.js` | the **intent channel**. The adapter declares a fixed tactical vocabulary (`{CODE: {args: {name: spec}}}`). The slow brain sends calls (`STRAFE dir=left wtap=1`), as text or objects. Unknown codes / bad args are rejected. The reflex reads `current(t)`; after 2 s with no call it keeps the last one (`stale: true`). `stats()` measures the real call rate. |
| `plan.js` | **plan memory**: goal → steps, lasting minutes, saved to a file if given. Each tick the adapter's `judge(step, obs)` says done / going / blocked (+ progress). Blocked, stalled (no progress for 6 s) or `interrupt()` → `needsReplan`; the brain returns new remaining steps; done steps are kept (that is the memory the screen does not show). |
| `schedule.js` | **timed actions** ("catching a baseball"). Each action has a time-to-go, re-estimated every tick from the measured gap (least-squares fit of the last 8 gaps with acceleration; Lee's tau = gap / closing speed is the first-order part). It fires on the tick nearest time-to-go 0, counting the action's wind-up lag; it moves earlier/later every tick, or is cancelled when the thing stops coming. `plan(id, action, inMs)` = "in 120 ms I will jump", `move()`, `cancel()`. `contact(id, t)` from the game's truth log → error in ms. |
| `reflex.js` | the **reflex** (action head + timing head) and its **sleep hook** `ReflexSleep`: logs the day's frames; at night replays only the day files (last 7 days), labels actions with the adapter's offline night labeller and times by hindsight (true seconds to contact), distils, and keeps each head only if it passes the held-out-day seatbelt (newest day's last 20 % and older days' held-out; agreement may not drop > 2 points, timing error may not grow > 1 ms, and it must improve). `model.prev.json` + `rollback()`. Any error skips the step. No games are played at night. |
| `loop.js` | `runEpisode(adapter, o)`: joins them. Slow brain asked every ~1 s (answers 0.5–2 s late, about an old picture); plan memory pushes the next step's call at once; the reflex acts every tick. Adapter interface documented at the top. |
| `brain.js` | prompt builder + reply parser for the real model (vocabulary, scene in words, goal, done steps, surprise). Not wired to the live loop yet. |

Adapters (`src/games/adapters/`): `sparksquest.js` (T6's Sparks from `realtime.js`, used as is, plus a 6-checkpoint goal, a
lock+key surprise, and shockwaves to jump), `orchard.js` (new: catch falling fruit with a timed net, deliver 3 in order, a tree
withers). Each is ~150 lines; core/ was not changed for the second one.

## Setting
`twoSpeedPlay` ("Two-speed play", Autonomy group), **default OFF**. When on: while Ben is away (idle ≥ 2 min, Mote budget), one
practice game at most every 10 minutes (Sparks quest / Orchard in turn) with the **stand-in** brain in simulated time; frames go to
`<userData>/twospeed/<game>/frames-YYYY-MM-DD.jsonl` (≤ 20 000 lines/day, a few hundred KB); a nightly job distils each game's
reflex. Logs: `twospeed/<game>/nightly.jsonl`, activity log entries `game`.

## Evidence
Toy: `~/learner-ops/premonition-sleeplab-i3` (MARKS-twospeed-v1/v2.md, results/). v2 PASS on fresh seeds 4-6, both games:
long horizon 0.90-1.00 (no-replan / no-memory controls 0), timing median 13-24 ms (once / react controls fail), sleep: time-to-go
error 0.25-0.56 x plain tau, poisoned nights rejected 6/6, no harm in play.
Real (kept apart, `real/REAL-RESULTS.md`): Nanbeige 8-bit on the M1 writes valid calls 24/24, but picks the right one only 6/12
(whole plans 1/12; never fetched the key after a lock), at ~2.7 s per call. So the core is ready, the slow brain is the weak part.

## Not done / next
- The live loop with the real model as the slow brain (async, real time) is not wired; `brain.js` is ready for it.
- Night 1 has no older held-out day, so a poisoned first night is not caught (known gap).
- Nightly distillation runs on the main process (~10–15 s for Sparks quest at the daily cap); move to a worker if it shows.
