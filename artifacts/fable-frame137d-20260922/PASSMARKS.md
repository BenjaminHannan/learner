# PASSMARKS — Exp 137d: non-assertive framings never write (Muse, 2026-09-22)

Base: loop137c (`scripts/fable_loop137c_agent.py`,
`artifacts/fable-hypo137c-20260922/loop137c-config.json`; design
`design/v3/30-modes/137c-hypo-muse.md`; RESULTS
`artifacts/fable-hypo137c-20260922/RESULTS.md`).

Step-1 facts: 137c's closed sentence-initial marker list lives at
`scripts/fable_fix137c_hypo.py:48-60` (`_MARKERS`, longest-first).
The path that produced the Supposedly junk: on loop137c "Supposedly
Kim's boss is Lee." is NOT hypothetical, so `Loop137cEars.hear` falls
through at `scripts/fable_loop137c_agent.py:84`
(`return super().hear(turn)`) into the unchanged loop137b/138b
pipeline, which parses "Supposedly Kim" as a possessive subject and
SAVES the junk triple `[Supposedly Kim,boss,Lee]` (live-verified on the
base pre-seal; reply "Saved: Supposedly Kim's boss is Lee."). "Say
Kim's boss is Lee." saves `[Kim,boss,Lee]` on loop137c (only "say that"
is a 137c marker, so bare "say" teaches). Ben's ruling (2026-09-22):
"Say X..." is pretend, never a fact; hearsay is never a fact.

THE ONE CHANGE (sealed): two new closed groups, fixed in
`scripts/fable_fix137d_frame.py` before any panel read, matched in the
SAME sentence-initial position with the SAME rules as 137c (after
optional case-insensitive ok/so/and fillers + punctuation, repeatable;
case-insensitive; trailing boundary end/whitespace/punctuation, never
an apostrophe so "Say's ..."/"They Say's ..." possessives stay names),
checked FIRST before the unchanged loop137c pipeline:
(a) Say-group: `say`, `say that` (longest-first). Reply: the sentence
echoed WITHOUT the marker + ` (I'm treating that as pretend, so I
won't save it.)`, e.g. "Say Kim's boss is Lee." -> "Kim's boss is Lee.
(I'm treating that as pretend, so I won't save it.)". NOTE: "say that"
moves from the 137c pretend reply to the say echo reply by design
(never writes either way).
(b) Hearsay-group: `supposedly`, `apparently`, `allegedly`,
`reportedly`, `rumor has it`, `rumour has it`, `i heard`,
`i heard that`, `they say`, `they say that`, `people say`
(longest-first). Reply exactly: `That sounds like hearsay, so I won't
save it as a fact. If it's true, just tell me plainly.`
Neither group ever writes. Later questions answer only from real saved
facts. Marker words later in a sentence or inside names/titles
("Kim's song is Say My Name", "Kim's book is Apparently") never match:
only turn-initial position counts -- identical to loop137c. All 137c
hypo markers keep the 137c path byte-identical.

## T1 — new probe `scripts/fable_fix137d_probe.py` (76 cases, every case reported)

- S-say 16: `[say frame, question]` (say x8 incl "SAY" twin + fillers
  "Ok, so/And/So,/Ok,/And,"; say that x8 incl "Say That" twin +
  fillers; 6 relations boss/mother/city/song/movie/friend). PASS =
  turn 1 replies the exact say echo + parenthetical, 0 writes after
  each turn, turn-2 reply holds no framed value, notebook empty.
- S-hear 24: `[hearsay frame, question]` (all 11 hearsay markers x
  plain + filler/case twin + "SUPPOSEDLY"/"They Say" twins; 6
  relations). PASS = turn 1 replies the exact hearsay sentence, 0
  writes after each turn, turn-2 reply holds no framed value, notebook
  empty.
- C 6: `[real teach, framed rival, question]` (say x2, say that x1,
  supposedly/apparently/they say x3; boss/city/song/mother/movie).
  PASS = real saved, framed exact reply, question answers the REAL
  value, triples hold only the real fact.
- N 12: marker-word titles/names ("Kim's song is Say My Name",
  "Kim's book is Apparently", "Say's boss is Kim.",
  "They Say's mother is Beth.", "What If's boss is Kim.", ...).
  PASS = reply+triples identical to loop137c.
- O 18: plain teaches, "Btw./So/Hi." phone teaches, hypo twins
  Suppose/Imagine/What-if, bare-"If ..." decline, real names,
  "Okay/And Kim's ...". PASS = reply+triples identical to loop137c.
- Bar: 76/76 OK.

## T2 — 0 wrong writes

0 writes on every framed turn (asserted per S/C case in the probe).

## G1 — bench121 (reuse `fable_bench121_run` by import; frozen 137c rows)

Pre-seal static scan of all 800 bench inputs (taught `sentence_en` +
`question` in all 4 splits): 0 frame-led inputs. Prediction: 0
verdict moves, 0 reply moves, 0 new wrong on all 4 splits. Bar: 0 new
wrong, every move predicted (predicted: none).

## G2 — `scripts/fable_marks123_all.py` per-case vs `marks137c`

Pre-seal static scan of suite sources (p2 64 texts, p4 40 texts, rt110
62 texts, rt81 74 steps, bench113 A/B 400 inputs, q1 fixed turns, soak
templates, q4 underscore scan): 0 frame-led inputs; neither sealed
reply holds an underscore. Prediction: every suite per-case identical
to the base marks folder (incl. inherited p3 L5-Z1 58/60 and rt81
60/0/14 FAIL labels byte-identical), except the sleep SKIP reason
naming the new agent file `fable_loop137d_agent.py`. Soak/rt110 flakes
under heavy load are a known mailbox race: re-run that suite once in
the open and report both.

## G3 — sessions152 + redteam136/143 (base-folder patterns)

Pre-seal scans: sessions152 180 turns 0 hits; rt143 124 cases 0 hits;
rt136 145 cases 2 frame hits: C101 "I heard Tom's city is Rome.", C102
"Apparently Tom is French." (both frozen OK, 0 writes, on loop137c);
cases150 6 frame hits (R02/R03/R04/R05/R08/A01 hearsay turns, all
frozen OK, 0 writes); f1 + cases139b 0 hits. Predictions: sessions 0
verdict/reply moves; rt143 0 moves; rt136 0 VERDICT moves (C101/C102
stay OK with 0 writes; their replies move to the exact hearsay
sentence -- the rt136 compare is verdict-only so no move is listed);
cases150 6 reply-only moves (R02/R03/R04/R05/R08/A01: verdict stays OK,
0 writes, reply moves to the hearsay sentence); f1 + cases139b 0
moves. Bar: 0 new WRONG/WRONG-WRITE, every move predicted.

## G4 — time + daemon

Each registered run < 1500 s (< 25 min) Mac CPU, OMP/MKL=1, offline;
daemon wrappers accept idle_seconds (Loop137dDaemon default 30.0).

## Sealed files (sha256 in SEAL.sha256.txt)

PASSMARKS.md (this file), scripts/fable_fix137d_frame.py,
scripts/fable_loop137d_agent.py, scripts/fable_fix137d_probe.py,
scripts/fable_fix137d_bench.py, scripts/fable_fix137d_junk.py,
scripts/fable_fix137d_sessions.py, scripts/fable_fix137d_redteam143.py,
artifacts/fable-frame137d-20260922/loop137d-config.json.
Ledger P137d.1-6 appended BEFORE any registered run. No rule changes
after the seal; any post-seal code edit is reported and the affected
marks re-run in the open. A FAIL is recorded as FAIL, never re-run
into a pass.
