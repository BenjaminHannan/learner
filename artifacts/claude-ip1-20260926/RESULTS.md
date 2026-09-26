# ip-1 result: registered FAIL (I2, I3, I4). The safety marks held.

Run: `python -B scripts/claude_night_interrupt.py --run` on the Fix-sleep session's CPU (4 cores, 15 GB), plain
MiniCPM5-1B @87179e5c, started 15:07:09 UTC 2026-09-26 (date -u), once. Raw: ip1_results.json, log.txt.
A first, unkilled night took 91.5 s (stages train, save, record, switch, after, exit) and made v0001 active.

| Mark | Result | Counts |
|---|---|---|
| I0 each staged kill reached its stage | PASS | 5 of 5 (train, save, record, switch, after) |
| I1 ACTIVE old or complete new after every kill | PASS | 11 of 11; only the "after" kill (and the unkilled k07) moved ACTIVE, both to complete accepted versions |
| I2 active version loads in a fresh process, fingerprint matches | FAIL | 10 of 11; k08: v0004 did not match, though the same v0004 matched in k07, k09 and k10 |
| I3 live answers identical and within 15 s during and after every kill | FAIL | 6 of 11; the 5 failures (k05, k06, k08, k09, k10) all had a live answer slower than 15 s (19.8 to 40.1 s) while the night child loaded or trained on the same CPU; whether their text also differed was not recorded separately |
| I4 clean recovery night accepted and active, fingerprint matches | FAIL | accepted, v0005 active, rc 0, but its fingerprint check in a fresh process did not match |
| I5 stop_night stops a running night within 3 s | PASS | 0.06 s (SIGTERM was enough) |
| D1-D4 dormancy gate | PASS | 4 of 4 |

Random kills landed at: load/score, train, exit (the night finished before its 88.3 s kill), train, train, train.
Leftovers: a half-written v0002.pt.tmp and an ACTIVE.tmp stayed on disk; loaders never read them. One orphan v0002.pt
(no record) after the "record" kill was overwritten by the next night's v0002, as designed.

What it shows:
- Shown: a killed night never left ACTIVE pointing at a missing, half-written or unaccepted adapter, at any of the 5
  moments or 6 random times. Stopping a night takes well under a second. The idle gate behaves as specified.
- Shown: on this 4-core CPU, a night running next to the live model makes live answers 8 to 17 times slower
  (2.3 s reference, up to 40.1 s). Ben's rule already says sleep only while dormant; the live path must stop the
  night before answering, not answer alongside it.
- Suggested, not shown: the fingerprint check is flaky across processes on CPU. After the run, v0004 and v0005 were
  each reloaded twice in a quiet process and matched their records exactly (max difference 0.0). The two misses are
  most likely CPU arithmetic differences at the 3-decimal rounding, not damaged files, but the run cannot prove it.

A FAIL stays a FAIL. Next: ip-1b, sealed before it runs.
