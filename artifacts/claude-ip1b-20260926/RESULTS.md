# ip-1b result: registered PASS (J0-J5); blind recount agrees (VERIFY below)

Run: `python -B scripts/claude_ip1b.py --run`, Fix-sleep session CPU (4 cores), plain MiniCPM5-1B @87179e5c, started
15:36:42 UTC 2026-09-26 (date -u), once. Raw: ip1b_results.json, negative_control.json, log.txt.

| Mark | Result | Counts |
|---|---|---|
| J0 staged nights reached their stage | PASS | 5 of 5 |
| J1 ACTIVE old or complete new after every stop | PASS | 11 of 11 (only the "after" stop moved it, v1 -> v3) |
| J2 fresh-process load, fingerprint close | PASS | 11 of 11 (all 11 also exact) |
| J3 mid-night messages answered identically within 15 s | PASS | 33 of 33 answers identical; slowest 3.63 s incl. stop; 11 of 11 messages found a night running |
| J4 recovery night accepted, active, close | PASS | rc 0, v4 active, close (and exact) |
| J5 dormancy gate D1-D4 | PASS | 4 of 4 |

Stops took at most 0.12 s. Random stops landed in train (4) and load/score (2).
Addendum 1 negative control: 0 of 6 pairs of different versions came out close; no pair shared top-5 ids; smallest
largest-log-prob gap between different versions 0.132 (v2 vs v3, two children of v1), 6.6x the 0.02 tolerance; the
gap between reloads of the same version was 0 in all 12 checks (all exact). So the tolerant check still tells
versions apart.

What it shows: with the live path stopping the night first, a message mid-night is answered as fast as with no night
(2.4-3.6 s vs 2.3 s) and identically, at every stage including mid-save and mid-switch, and ACTIVE is never left bad.
Limits: CPU, tiny nights, the bare 1B as the live model (not the joined agent); ip-1's fingerprint misses did not recur
here (12 of 12 exact), so the tolerance was not needed in this run; SIGTERM path (ip-1 covered SIGKILL).

## VERIFY (blind recount)
A blind agent read only PASSMARKS.md, ip1b_results.json and negative_control.json and recomputed J0-J5 from raw
fields: all PASS with the counts above, no disagreement with the precomputed flags. It noted that the same-version gap
figure asked for in Addendum 1 was only implied by "exact" (so 0); it is stated above.
