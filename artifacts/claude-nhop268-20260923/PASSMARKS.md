# Exp 268: n-hop direction guard — pass marks (registered before the seal)

**Agent:** `scripts/claude_loop268_agent.py` with
`artifacts/claude-nhop268-20260923/loop268-config.json`.

**Base:** 138m (`scripts/claude_loop138m_agent.py`,
`artifacts/claude-merge138m-20260922/loop138m-config.json`, saved rows in
`artifacts/claude-merge138m-20260922/run/`).

**The one change:** `scripts/claude_fix268_nhopdir.py` — question-side
direction guard around `compose_n_hop`, installed process-locally by
rebinding the module global (the way 138m installs its own overrides; no
existing file edited). Full spec in
`design/v3/30-modes/268-nhop-direction-guard.md`.

**Driver:** `scripts/claude_268_runall.sh artifacts/claude-nhop268-20260923/run`
(one suite at a time; `uptime` checked before each step, waits while 1-min
load > 60). **Scorer:** `scripts/claude_268_score.py`.

**Dev material (never the blind panel):** the 36 nhopdiag dev dialogs
(`dev_dialogs.json` on builder-outbox, reproduced here) + 34 own dialogs
(fictional names) in `scripts/claude_268_devrepro.py` (definitions sealed
in `artifacts/claude-nhop268-20260923/dev/dialogs268.json`) + 7
supplemental founder dialogs in `scripts/claude_268_supp.py`.
The o11–o14/o25 teaches used "The founder of X is Y.", which the teach
side does not parse (empty notebook, honest "couldn't save"); the p01–p07
supplementals repeat them with parsable possessive phrasing. o11/o13/o25
are RECORD (broken teaches), kept as-is.

**Predicted moves:** `artifacts/claude-nhop268-20260923/predicted_moves268.json`
(every move by id with exact 268 stage+reply, built from pre-seal pilots).

**Blind:** the panel was never opened, printed, or tuned on. M1 numbers
below are predictions by shape from dev evidence, with 138m's number
beside every figure after the run.

## Marks

PASS only if all four marks pass.

### M1: blind panel nhoppanel268 (70 items; run once per arm with the sealed score_panel.py)

Predicted 268 behaviour by shape (dev evidence: all 21 reverse-shaped
chained dev questions stopped answering forward facts; 184/205 other
turns byte-identical, 0 teach/triple changes):

- Whose-spouse / who-has-as-spouse shapes → 190 gold "S's spouse is V."
  (dev 4/4: d01, d03, d29, o02).
- "Who is/was married to V?" → "Was that a question?" (no layer on the
  138m lineage parses married-to; dev d02, d04). Not wrong, not right.
- husband/wife/partner-whose → 190 honest decline naming V
  (stored key is "spouse"; dev d05, d06, o04). Not wrong, not right.
- what-written / what-found shapes → honest abstain
  (dev d11, d12, d16, o20, o29, p01, p04). Not wrong, not right.
- whose-author/founder/employer/child → 153-wording TRUE fact
  "V is the R of S.", naming the gold subject S
  (dev d33, d34, o09, o15, o18, p02). True, not a wrong value; whether it
  counts "right" depends on the sealed scorer's criterion.

Bars:

1. **reverse_chain >= 22/24 right (all gold subjects named).** Reachable
   iff the panel's reverse_chain items are dominated by 190-answerable
   shapes (spouse whose/has-as) and/or the scorer counts
   gold-subject-naming 153-wording replies as right. Composition risk is
   stated here, not hidden: on dev shapes, 4/12 dev WRONGs reach gold.
2. **reverse_nochain: no item right on 138m is not right on 268.**
   Guard cannot fire without a composer frame (no chain → no frame by the
   walk + coverage gate); dev no-chain/sink cases all identical.
3. **0 wrong over all 70.** No reply asserting a false value on either
   arm beyond 138m's own; dev shows 0 new wrong values on all 21 moves.
4. **0 question writes.** Dev 0 triple changes; M2/M3 0 write changes.
5. **uncued_reverse 8/8, forward_chain 12/12, forward_1hop 10/10,
   abstain 6/6 byte-identical to 138m.** Dev: every forward / uncued /
   2-subject / over-walk (d13, d17) control identical; M2 bench 0 moves.

Note on the design doc: its "12/12 WRONG flip to gold" was proposed (not
built) on 138n. Measured on the 138m base used here, fall-through gives
gold only for 190-answerable shapes; everything else becomes an honest
non-answer (decline / abstain / "Was that a question?") or a true
153-wording fact. The falsifier still holds absolutely: any reverse_chain
item answered with V's own forward fact, any forward n-hop reply change,
or any new wrong value proves the change wrong.

### M2: frozen suites vs 138m's saved rows (as 138m did)

- **sessions152, bench, marks123** (`fable_suitediff218 --base-dir
  .../run/sd`): moves exactly []. Pilot: 0 moves, GATE clean, all bench
  and marks123 row files byte-identical.
- **rt136** (`--base-dir artifacts/fable-agent138j-20260922 --only rt136`):
  label set exactly [C019–C031 (13 inherited 222 WRONG-WRITE) + C076, C079
  reply-only]; 0 new WRONG, 0 new WRONG-WRITE beyond the 13 inherited, 0
  junk, 0 lost OK. Direct row compare (reply/stored/verdict) vs 138m's
  saved `run/sd136/rt136-rows.json`: moved == []. Pilot: exactly so.
- The 63 inherited 222 exception rows identical to 138m's saved rows
  (seconds excluded on rt136).
- **rt143 no-gate** (`claude_138l_rt143nogate.py` vs 138m's saved
  `run/rt143nogate-m.json`): moves == [], 0 verdict flips. Pilot: 124/124
  ids, 0 moves.
- Any forward n-hop move fails M2. Pilot: none (every dev move is a
  reverse-shaped question; bench contains forward n-hop items, 0 moved).

### M3: restart + verifier probes (0 ghost answers, 0 write changes, every reply change predicted)

- 138m's M6 files (`138j/p3-dialogs, p3c-restart2, p3d-ghost`,
  `138k/v-dialogs, v-supp`) on 268 vs 138m's saved `run/probe/m-*` rows:
  rows equal (agent field excluded). Pilot: 5/5 equal.
- `138m/probes.json` (98) on 268 vs `rows-138m.json`: diff == [].
  `138m/probes-supp.json` (12) vs `supp-rows-138m.json`: diff == [].
  Pilot: both [].
- Ghost = a changed reply stating a notebook value where 138m
  abstained/declined: predicted none. Duplicate-index audits hold.
  Write changes (events/triples/stored): predicted none.

### M4: latency

- `claude_merge138k_latency` alternating processes m,n,m,n,m,n, 2 reps
  each, on 138j's p3-dialogs, p3c-restart2, p3d-ghost.
- Bar: median(268) − median(138m) <= +5 ms. Pilot (1 rep each, n=104):
  1.723 − 1.731 = −0.008 ms.

## Rules in force

- Unpredicted abstain flips count against their mark (then run that item
  alone 5 times and report). Known flake (~1/800 toward abstain) reported
  as-is if seen.
- After the seal, any change to a sealed file makes the verdict FAIL (no
  re-seal). A driver-only fix after the seal is reported with its diff.
- Report every case and every miss. Claims never exceed the numbers.
