# PASSMARKS — Exp 215: "X IS THE R OF Y" MEANS "Y'S R IS X" (Muse)

Agent: `scripts/fable_loop215_agent.py` (subclass of loop138i; 138i never
edited). Config: `artifacts/fable-ofteach215-20260922/loop215-config.json`.
Cases: `cases215-p1.json` (40 teach+ask sets), `cases215-p2.json` (25 traps).
Drivers: `scripts/fable_ofteach215_marks.py` (`--only
p1|p2|rt136|rt143|sessions|bench|reversal`, one suite at a time),
`scripts/fable_ofteach215_scan.py` (pure-function pre-seal predictor),
`scripts/fable_ofteach215_cmps.py` (marks123 per-case diff),
`scripts/fable_sleepsmoke206.py` (stock sleep smoke), stock
`scripts/fable_marks123_all.py`.
Base: loop138i live (plus its sealed rows for the frozen diffs).

## The one change (outermost ears rewrite, no _act change)

Teach `"X is the R of Y."` -> `"Y's R is X."` before the normal pipeline
(any R = 1-3 lowercase words, no clause/function words; Y name-like or a
known entity; last-`of` split; never first-person / no-article /
non-name Y / hearsay / wh-subject / glued turns). Question `"Who/What is
the R of Y?"` -> `"Who/What is Y's R?"` iff the notebook already holds R.

## M1 — P1 panel: 40/40 sets correct, 0 junk

Bar: every set —
teach replies `Saved:`, both asks (`Y's R?` and `the R of Y?`) answer X,
stored taught triple exactly `(Y, R, X)`, and 0 stored relations matching
`*_of` / `* of *`. Piloted pre-seal: 40/40, junk 0.

## M2 — P2 traps: 25/25 byte-identical to loop138i

Bar: every trap — reply AND stored FACT/RELATION/ENTITY events identical
between loop215 and loop138i (fresh notebooks). Piloted pre-seal: 25/25.

## M3 — frozen suites + marks123 + bench: 0 moves except the predicted set

Bar: per-case identical to loop138i (verdict + reply + stored/writes),
0 new WRONG / WRONG-WRITE / junk writes outside the predicted set below;
bench 0 new wrong outside the predicted set; marks123 per-case identical
to the sealed marks138i rows except the predicted bench rows and the
volatile set (`seconds` timings, l6 `replied_before_kill` counts, sleep
SKIP agent filename).

PREDICTED MOVES (pure-function scan `fable_ofteach215_scan.py` + pilots,
all of the shape "junk `R_of` echo becomes the true `(Y, R, X)` triple";
the old judges reward the junk echo, so their labels flip while the new
stored triples are the true readings; 0 junk writes in every case):

- rt136 (14): C013, C019, C020, C021, C022, C023, C024, C025, C026, C027,
  C028, C029, C030, C031. Piloted: exactly these 14 move; rest 0 moves.
- rt143 (gate-open of-question class J6/J8/K2/K9/O3; piloted actual moves
  J8, K9, O3): reply takes the possessive twin's shape; verdicts
  neutral-or-better (K9 WRONG-ANSWER -> OK), new_wrong 0, 0 new writes.
- bench-v3 edit200 (25): bench65-rev-f00-fwd … bench65-rev-f24-fwd (all 25
  `-fwd` rows; sealed golds echo the junk object for a subject-question,
  so true answers score wrong). All other bench splits 0 moves.
- marks123 (25): the same 25 bench65-rev-*-fwd rows in
  `bench-rows-fable_edit_200.jsonl`; p2/p3/p4/rt110/q1/q4/rt81/soak/sleep
  per-case identical (p3 same pass/fail pattern; seconds volatile).
- sessions152: 0 moves, 0 new writes (piloted).

## M4 — exp 210 harness on loop215

Bar: junk `"R of"` saves 26 -> 0; all 70 items reported with verdicts in
{right, wrong, abstain}; reversal table identical to loop138i otherwise.
Piloted pre-seal: junk 0/70, coverage 70/70, reversal 0/47/3, controls
5/14/1, teach rejects 9 -> 0, inverse stored 0.

## M5 — sleep smoke on loop215

Bar: `scripts/fable_sleepsmoke206.py` passes (installs, 5/5 probes, 0
wrong, taught intact, broken-chain abstains). Piloted pre-seal: 5/5, 0
wrong, taught 50/50 dupes 0, overwrites 0, 105.3 s.

## M6 — 0 new wrong writes anywhere

Bar: no new WRONG / WRONG-WRITE / junk writes vs loop138i outside the M3
predicted set (whose new triples are the true readings, verified with
the true subject in the reply).

## Common rules

Seal: `shasum -a 256 PASSMARKS.md cases215-p1.json cases215-p2.json
scripts/fable_loop215_agent.py scripts/fable_ofteach215_marks.py
scripts/fable_ofteach215_scan.py scripts/fable_ofteach215_cmps.py
loop215-config.json > SEAL.sha256.txt` BEFORE any registered run. Ledger
P215.n appended before the run. Fictional names only. Each run < 25 min
Mac CPU, OMP/MKL=1, idle_seconds=3600 for daemon wrappers. Verdict PASS
iff M1-M6.
