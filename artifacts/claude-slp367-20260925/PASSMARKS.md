# slp-367 pass marks (registered 2026-09-25, before any run)

Change (one): idle sleep (scripts/claude_slp367_idle.py). Sleep is due on an idle step when ≥ 10 new turns arrived
since the last sleep, or ≥ 1 new turn and 30 min passed since the last sleep; never inside a user turn.
Twin: FORCED = the 336 harness's forced end-of-day sleep. Both arms have slp-360. Card test, CPU, $0, seeds 1-2.
Simulated daemon: turns in bursts of 5, one idle step after each burst (fake clock +60 s), then up to 3 evening idle
steps. World: exp-104 (75 turns), then 5 new-people probes + 1 broken-chain probe.

| Mark | Bar (each seed) |
|---|---|
| P367.1 sleeps that start inside a user turn (IDLE) | 0 |
| P367.2 IDLE: the word installs and the new-people probes are right | installed; ≥ 4/5 |
| P367.3 replies to the 50 teaches and 5 fillers identical to FORCED | 55/55 |
| P367.4 quiet check: 3 new turns, 60 s idle → no sleep | not SLEEP |
| P367.5 quiet check: then 30 min idle → sleep | SLEEP |

Report only: how many grandmother questions were answered by a route learned earlier the same day (IDLE can learn
mid-day; FORCED cannot), number of idle sleeps.
Stated limit, not a mark: a message arriving during a running sleep waits for it to end (~1.5 min on CPU).
