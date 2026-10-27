# Exp 138g PASSMARKS — merge layer A (loop138f + 4 verified mixins), sealed before run

Agent: `scripts/fable_loop138g_agent.py` (Loop138gEars / Loop138gAgentLoop /
Loop138gDaemon, build_agent138g, DEFAULT_CONFIG138G). Subclasses the frozen
loop138f stack; every rule body imported read-only, no existing file edited.
Config: `artifacts/fable-agent138g-20260922/loop138g-config.json`.
Design: `design/v3/30-modes/138g-merge-layer-a-muse.md` (Step-1 file:line +
composition + the two left-out pieces with reasons).
Drivers (new, sealed): `scripts/fable_fix138g_m1.py` (M1+M2),
`scripts/fable_fix138g_suites.py` (M4+G1+G3, `--only`),
`scripts/fable_fix138g_compareg2.py` (G2 enumeration, read-only).
G2 runner: stock `scripts/fable_marks123_all.py` (new args only).
Ledger P138g.1–P138g.8 appended pre-run. Sealed files hashed to
SEAL.sha256.txt: this file, the agent file, the config, the 3 drivers.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL with
one diagnosis note. No rule changes after the seal. Soak/rt110 flakes under
heavy parallel-agent load are a known mailbox race: that suite may be re-run
ONCE in the open and both reported. Open pilots (same drivers, same paths)
enumerated the predicted moves below; the registered runs re-run everything
after the seal. Heavy suites run one at a time.

## In / out of this build

IN (4, ported read-only): 139e relation-gated tail guard (incl. the 139c
closed-list strip it applies first); 137c hypo + 137d say/hearsay frames +
137e hearsay unification (HEARSAY_MSG; 137b discourse upgrade NOT ported);
158c wh-city rewriter (e1–e5 shapes + 158b entity gate, ask-only, never
writes; second-pass target adapted: verbatim "Where does X live?" first,
then "What is X's city?" city-path fallback, because 138f lacks the 158b
(d) table — final replies byte-identical on the sealed probe); 168
grounded self replies (turn shape).
OUT (2, clean port impossible, reasons in design doc): 157c title guard
(needs 157b's capitalised-filler strip, absent from 138f; guard alone is a
no-op); 160c two-hop (needs 160b's bare-correction machinery, absent from
138f; interceptor alone is a no-op).

## Marks

- M1 (`scripts/fable_fix138g_m1.py --only pieces`, fresh in-process loops):
  each ADDED piece's own sealed probe vs its sealed rows — 139e 65/65 OK
  (27/27 tail-exact, 0 wrong writes, 0 diffs); 137e 101/107 identical, 6
  exempt interactions (below); 158c 38/46 identical, 8 exempt interactions
  (below); 168 61/61 identical (A25 0 crash/0 naming/0 writes, B/C/D
  identical). Exempt = listed here with expected reply; any other diff FAILs.
  - 137e interactions (all 138f-lineage discourse leads, 138f-identical
    reply+write): T1-O-01 "Btw. Kim's boss is Lee." saves "Btw. Kim";
    T1-O-02 "So Kim's boss is Lee." saves "So Kim"; T1-O-03 "Hi. Kim's
    boss is Lee." saves "Hi. Kim"; T1-O-16 "Okay Kim's boss is Lee."
    saves "Okay Kim"; T1-O-17 "And Kim's boss is Lee." saves "And Kim";
    T1b-E06 "Btw. Nia's city is Rome." saves "Btw. Nia", follow-up "I
    don't know anyone called Nia." (137 lineage strips the lead via the
    unported 137b upgrade).
  - 158c interactions: O01 "Where does Sue live?", O03 "What city is
    Sue?", O04 "How old is Ann?", O05 "When is Ann's birthday?", O07
    "What job is Bob?", O08 "Where does Kim's mother live?" — all
    138f-identical clarifies (158b (d)/(a) base shapes absent from 138f);
    O06 "What color is Rex?" → "I do not have favourites." (168
    grounding; 158b answered via its base); O10 "Where is Mira from?" →
    "You did, in turn 6." (168 grounding; 158b gave the ungrounded
    correction clause).
- M2 (`--only f`): 138f's M1 (the 8 138d pieces) unchanged on loop138g,
  EXCEPT one exempt reply-only interaction: 156b-N11 → "I have no
  opinions." (168 grounding strips the ungrounded Oslo/Paris clause; 0
  writes, verdict class unchanged). All other pieces at bar (142 500/500;
  146d 21/21 with H13 ok + H17/H18 fail-as-on-146c; 153 50/50 0 writes;
  156b 116/116 + T2 68/68; 157 60/60; 158 59/59; 159 48/48 0 writes;
  150b 49/49).
- M4 (suites driver): the 7 cases byte-identical (verdict+reply+stored) to
  loop138b (C124/C127/C129/C142/C10/C21/M3); per-case vs loop138f rows
  identical EXCEPT one predicted improvement: redteam136 C089
  WRONG-WRITE→OK ("Suppose Tom's boss is Ann." now hypo-refused, 0
  writes). cases150 57/57, f1 46/46, cases139b 101/101, rt143 0 moves
  (M3 identical to 138f), sessions152 0 moves (165 OK/15 UNHELPFUL, 0 new
  writes). 0 new WRONG / WRONG-WRITE / junk writes anywhere vs 138b.
- G1 (suites driver `--only bench`): bench121 4 splits per-item vs sealed
  138f rows: 0 verdict moves, 0 new wrong (194/2/4, 198/2/0, 150/50/0,
  196/3/1).
- G2 (`scripts/fable_marks123_all.py --agent scripts/fable_loop138g_agent.py
  --config artifacts/fable-agent138g-20260922/loop138g-config.json --out
  artifacts/fable-agent138g-20260922/marks138g --workers 4`): every suite
  per-case vs sealed marks138f EXCEPT 5 predicted moves, all enumerated
  in pilots: p4 P4-09 → nonpass with reply "Saved: Mira's teacher is
  Ana." + stored ["Ana"] (139c comma-tail strip; the stored triple is
  correct, not a wrong write); rt81 I_edges-03 + O_user-03 reply-only
  tightenings ("I cannot predict." / "I have no opinions.", verdicts
  UNCLEAR kept); p3-l2 I_edges-03 + O_user-03 same two reply-only moves.
  Sleep SKIP reason names the new agent file (verdict identical). l6
  pass/correct/wrong predicted (replied_before_kill timing-volatile,
  reported not predicted). p3 l5z1 FAIL + rt81 FAIL labels inherited
  per-case. 0 new WRONG anywhere vs 138b rows.
- G3 (suites driver `--only g3`, 7 fresh loops): G3-1 "Saved: Pax's
  sister is Ivy." + [[Pax,sister,Ivy]]; G3-2 "Saved: Quin's city is
  Leeds." + [[Quin,city,Leeds]]; G3-3 HEARSAY_MSG + []; G3-4
  "OK, I'll treat that as pretend, so I won't save it." + []; G3-5
  "Saved: Hey Jude's singer is Paul." + [[Hey Jude,singer,Paul]]
  (138f-identical; 157c left out); G3-6 "I do not have favourites." +
  []; G3-7 "You never told me your name, so I do not know it." + []
  (168-intended text, already so on 138f for this turn).
- G4: every registered run < 1500 s wall-clock (pilot: m1 21 s + 26 s,
  junk 6 s, rt143 7 s, sessions 5 s, bench 43 s, g3 2 s, marks wave 261 s).

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any move beyond the enumerated sets (M1 6+8+1, M4 1, G2 5).
- F2: any new WRONG / WRONG-WRITE / junk write vs loop138b on any suite
  (P4-09's clean ["Ana"] store is correct by construction, not a wrong).
- F3: mailbox-race flakes (empty-read clarifies, lost teaches, l6
  kill-counters) under parallel-agent load: recorded, re-run once in the
  open, both reported.
