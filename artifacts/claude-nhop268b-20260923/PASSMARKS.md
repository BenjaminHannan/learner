# Exp 268b: n-hop direction guard on 138nb — pass marks (registered before the seal)

**Agent:** `scripts/claude_loop268b_agent.py` with
`artifacts/claude-nhop268b-20260923/loop268b-config.json`.

**Base:** 138nb (`scripts/claude_loop138nb_agent.py`,
`artifacts/claude-merge138nb-20260923/loop138nb-config.json`, saved rows
in `artifacts/claude-merge138nb-20260923/run/`).

**The one change:** `scripts/claude_fix268_nhopdir.py`, used UNCHANGED
(byte-identical to builder-outbox; hash in the seal): question-side
direction guard around `compose_n_hop`, installed process-locally by
rebinding the module global (the way 138nb installs its own overrides;
no existing file edited). Full spec in
`design/v3/30-modes/268-nhop-direction-guard.md`; why 268 failed and why
the base is 138nb in
`design/v3/30-modes/268b-nhop-guard-on-138nb.md`.

**Loop:** `Loop268bAgentLoop(SrcGuardMixin228, Loop138nbAgentLoop)` —
SrcGuardMixin228 first, the 138nb stack (including the 190
"(worked out backwards)" label) unchanged below it.

**Driver:** `scripts/claude_268b_runall.sh artifacts/claude-nhop268b-20260923/run`
(one suite at a time; `uptime` + `df` checked before each step, waits
while 1-min load > 60). **Scorer:** `scripts/claude_268b_score.py`.

**Dev material (never any blind panel):** 268's 70 dev dialogs
(dev36+own34) + 7 supplemental founder dialogs (definitions imported
read-only from `scripts/claude_268_devrepro.py` /
`scripts/claude_268_supp.py`), re-run here on 138nb and 268b, + 46 own
new dialogs for 138nb's table reader shapes
(`scripts/claude_268b_newdev.py`, definitions sealed in
`artifacts/claude-nhop268b-20260923/dev/dialogs268b.json`). Fictional
names throughout. `nhoppanel268` was never dev material (regression
only, never read). `nhoppanel268b` was never opened, printed, or tuned
on. M1 numbers below are predictions by shape from dev evidence, with
138nb's number beside every figure after the run.

**Predicted moves:** `artifacts/claude-nhop268b-20260923/predicted_moves268b.json`
(every move by id with exact 268b stage+reply, built from pre-seal
pilots: 123 dialogs × 2 arms in separate processes).

**Pilots (pre-seal, this dir `pilot/`):** DEV 46/46 exact moves, 0 teach
changes; suites sessions152/bench/marks123 0 moves GATE clean; rt136
exactly the 16 inherited labels, 0 new WRONG, direct rows []; rt143 0
moves; 7/7 probe files rows equal; latency pilot (1 rep each, n=104)
+0.068 ms.

## Marks

PASS only if all four marks pass.

### M1: blind panel nhoppanel268b (run once per arm with the panel's sealed score_panel.py, after its SEAL appears)

Predicted 268b behaviour by shape (dev evidence: all 46 reverse-shaped
chained dev questions stopped answering forward facts; 315/361 other
turns byte-identical, 0 teach/triple changes):

- Whose-spouse / who-has-as-spouse shapes → 190 gold "S's spouse is V."
  + " (worked out backwards)" (dev 8/8).
- "Who is/was married to V?" → bench73 "Was that a question?" (dev 3/3:
  no layer parses married-to). Not wrong, not right.
- husband/wife/partner/son-whose → honest decline naming V (dev 4/4:
  stored key differs). Not wrong, not right.
- what-written / had-written / whose-was shapes the table/190 layers do
  not parse → honest abstain (dev 13/13). Not wrong, not right.
- founder/author what-found + who-has-as shapes → table-inverse gold
  "S's R is V." + " (worked out backwards)" (dev 8/8).
- whose-author/founder/employer/child → table-label153 true fact
  "V is the R of S.", naming the gold subject S (dev 10/10). True, not
  a wrong value; whether it counts "right" depends on the sealed
  scorer's criterion (same composition note as 268 carried over).

Bars (exactly those in the design note):

1. **bug family: 138nb wrong on every item (by construction); 268b 0
   wrong, and ≥ 14/16 right with the "(worked out backwards)" label**
   (the rest honest abstains).
2. **every other family byte-identical to 138nb.**
3. **0 question writes.**
4. Falsifiers: a forward-walk answer surviving on a bug item; any change
   to a forward two-step answer; a backwards answer naming someone not
   in gold.

### M2: invpanel138nb (regression only, once per arm, sealed score_panel.py)

- **moves 268b vs 138nb rows == []** (predicted: no invpanel setup forms
  a chain with an outgoing cued fact from the asked value, so the guard
  has no frame to suppress). Pilot: none (TEST-ONLY, run once).
- **0 new wrong** (no item wrong on 268b that is not wrong on 138nb).
- **every item right on 138nb stays right on 268b** (lost_right == []).
- **0 question writes** on 268b.
- Only score JSON with ids, families, stages and counts is pushed, never
  item text or replies.

### M3: frozen suites vs 138nb's saved rows

- **sessions152, bench, marks123** (`fable_suitediff218 --base-dir
  .../run/sd`): moves exactly []. Pilot: 0/0/0, GATE clean.
- **rt136** (`--base-dir artifacts/fable-agent138j-20260922`): label set
  exactly [C019–C031 (13 inherited 222 WRONG-WRITE) + C076, C079, C115
  (3 reply-only)] (16, the same set 138nb registered); 0 new WRONG, 0
  new WRONG-WRITE beyond the 13 inherited, 0 junk. Direct row compare
  (reply/stored/verdict) vs 138nb's saved `run/sd136/rt136-rows.json`
  (145 rows): moved == []. Pilot: exactly so.
- **rt143 no-gate** (`claude_138l_rt143nogate.py` vs 138nb's saved
  `run/rt143nogate-nb.json`): moves == [], 0 verdict flips. Pilot:
  124/124 ids, 0 moves.
- **restart + verifier probes** (7 files: 138j p3-dialogs, p3c-restart2,
  p3d-ghost; 138k v-dialogs, v-supp; 138n v138m-probes-dialogs,
  v138m-probes-supp-dialogs) on 268b vs 138nb's saved `run/probe/nb-*`
  rows: rows equal (agent field excluded). Pilot: 7/7 equal
  (15+2+1+15+3+98+12 dialogs).
- Ghost = a changed reply stating a notebook value where 138nb
  abstained/declined: predicted none. Duplicate-index audits hold.
  Write changes (events/triples/stored): predicted none.
- Any forward n-hop move fails M3. Pilot: none (every dev move is a
  reverse-shaped question; bench contains forward n-hop items, 0 moved).

### M4: latency

- `claude_merge138k_latency` alternating processes b,n,b,n,b,n, 2 reps
  each, on 138j's p3-dialogs, p3c-restart2, p3d-ghost.
- Bar: median(268b) − median(138nb) <= +5 ms. Pilot (1 rep each, n=104):
  2.197 − 2.128 = +0.068 ms.

## Ledger predictions

- P268b.1 DEV (123 dialogs: 70 rerun + 7 supp + 46 new): moves exactly
  the 46 predicted ids with exact stage+reply; 0 teach/triple changes;
  0 new wrong values.
- P268b.2 M1 blind nhoppanel268b (never read): bug 0 wrong, ≥ 14/16
  right with label; other families byte-identical; 0 question writes.
- P268b.3 M2 invpanel138nb: moves [], 0 new wrong, keep all
  138nb-right, 0 question writes.
- P268b.4 M3 frozen suites vs 138nb rows: suites 0 moves GATE clean;
  rt136 exactly the 16 labels, direct []; rt143 0 moves; probes 7/7
  equal; 0 ghosts, 0 write changes.
- P268b.5 M4 latency alternating processes: median(268b)−median(138nb)
  <= +5 ms/turn (pilot +0.068 ms, n=104).
- P268b.6 falsifiers: any surviving forward-walk answer on a bug item,
  any forward two-step change, or any backwards answer naming someone
  not in gold proves the change wrong.
