# Exp 93 RESULTS — daemon soak (registered FAIL at turn 17,716 of 20,000)

Seed 93, single deterministic plan: 11,288 teaches + 2,715 corrections +
5,997 asks (1–3 hops) over 2,000 people × 6 relations. Restart schedule sealed
with the plan: kills at 3797, 5281, 17710, 18711, 18898; graceful at 6214,
8556, 12968. Driving pipeline: up to 3 turns in flight; latency =
submit→reply under load. Reproduce: the command in PASSMARKS.md (stops itself
at the failing point; REPRODUCER.md has the exact turn).

## Marks

| mark | bar | outcome |
|---|---|---|
| K1 0 wrong over 20,000 turns | 0 wrong | FAIL: 1 wrong at seq 17716 (teach, reply `I already have that. I already have that.` — sentence duplicated, fact stored once) |
| K2 0 lost/duplicated over 8 restarts | clean audits ×8 | FAIL (incomplete): audits clean at restarts 1–5 (lost/dupes/wrongval/dupe_entities all 0); restart 6 not assessable in-sync (see below) |
| K3 final boot+verify < 10 s | < 10 s | PASS: boot 0.153 s + verify 0.064 s = 0.217 s |
| K4 p99 last-1000 < 10× p99 first-1000 | ratio < 10 | PASS (partial): 214.1 ms / 69.4 ms = 3.1× at turn 17,716, not 20,000 |
| K5 whole soak < 25 min, 20,000 done | < 1500 s + complete | FAIL: stopped at 17,716 turns, 665.5 s |

## Growth curve (per-1,000-turn checkpoints; latency excludes restart-straddlers)

| turns | wall s | wall rate/s | RSS MB | notebook MB | p50 ms | p99 ms |
|---|---|---|---|---|---|---|
| 1k | 22.7 | 44.1 | 29.2 | 0.56 | 68.3 | 77.4 |
| 5k | 133.9 | 32.4 | 33.6 | 2.01 | 91.1 | 118.1 |
| 9k | 274.9 | 26.2 | 44.5 | 3.14 | 112.6 | 141.4 |
| 13k | 444.1 | 23.0 | 70.3 | 4.22 | 129.9 | 159.2 |
| 17k | 628.9 | 20.4 | 73.7 | 5.30 | 145.4 | 170.9 |

Throughput halves (~44→20/s) and latency doubles (p50 68→145 ms) over 17k
turns — smooth, no cliff. Restart costs stay flat: boot 0.09–0.20 s, chain
verify 0.03–0.06 s. Pace projected ~800 s for 20k, inside budget.

## The failing point (the finding this soak was for)

Kill -9 #6 fired at turn 17,710 with 27 turns in flight. The daemon was
mid-turn (large notebook → ~70 ms ticks → the 250 ms pre-kill sleep ends
mid-tick). That turn's text was already saved in `state.json`'s loop inbox by
`AgentLoop.submit()` but its end-of-step save never ran — so the reboot
resurrected the in-flight text and re-executed it as a **ghost tick** inside
the next `turn()` call. The ghost text was the same file being reprocessed, so
the reply came out doubled (`I already have that.` twice) while the fact was
stored exactly once. Early kills passed because the daemon drained the small
burst and was idle at kill time — the ghost needs kill-during-turn, which only
long-tick (large-notebook) soaks hit. Exp 74 D2 could never see this.

Post-hoc verification (analysis only, not mark re-runs): every one of the
17,736 logged replies checked against plan ground truth — exactly 1 bad (seq
17716). Full notebook audit over all replied facts: 10,138 taught pairs, 0
lost, 0 duplicated, 0 wrong current values, 0 duplicate entities. The ghost
corrupted one reply; it never corrupted the fact store. A deterministic demo
(`scripts/fable_soak93_ghostdemo.py`, sealed classes only) reproduces the
resurrection without timing luck: GHOST93 PASS.

## Deviations

Pre-seal dev (all in the sealed driver sha): fresh daemon dir per run (dir
reuse aliased stale replies in smoke); pipeline depth 3 (sequential driving
projected ~24 min, no margin); daemon-death detection; K4 small-N guard. One
unexplained silent daemon death in one probe never reproduced. Post-run: the
offline reply/audit sweeps and ghost demo above.

## Questions for Ben

None — the FAIL stands as registered; the ghost-tick fix belongs to whoever
owns the loop/daemon persistence (resurrect nothing: drain or drop
loop.inbox on boot), not to this soak.

## What it means

The daemon is fact-durable under kill -9 at 17k-turn scale (0 lost/duplicated
of 10,138 pairs), boots in ~0.15 s on a 5 MB log, and degrades smoothly — but
a kill landing mid-turn duplicates one reply sentence via a resurrected
in-flight turn, so the reply stream is not exactly-once.

## What it does not mean

It does not mean facts are at risk (they were not: the store stayed exact),
and it does not mean the daemon fails at scale (pace, memory, and boot cost
all projected inside their bars at 20k).
