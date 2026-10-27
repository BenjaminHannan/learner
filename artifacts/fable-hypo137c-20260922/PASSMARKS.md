# PASSMARKS — Exp 137c: hypotheticals saved as facts (Muse, 2026-09-22)

Base: loop137b (`scripts/fable_loop137b_agent.py`,
`artifacts/fable-discourse137b-20260922/`). Step-1 fact: loop137b strips
"Suppose" at `scripts/fable_loop137b_agent.py:125`
(`rest = D137B.strip_first_token(...)` in `_upgrade137b`, lines 109–131;
"?" strip lines 163–178) and re-teaches the rest as fact.

THE ONE CHANGE (sealed): turn-initial closed-list hypothetical markers
(suppose, supposing, imagine, pretend, pretend that, let's say, lets
say, hypothetically, in theory, what if, say that), after optional
case-insensitive ok/so/and fillers + punctuation, never write and reply
exactly: `OK, I'll treat that as pretend, so I won't save it.`
(`scripts/fable_fix137c_hypo.py`, `scripts/fable_loop137c_agent.py`).
Everything else byte-identical to loop137b.

## T1 — new probe `scripts/fable_fix137c_probe.py` (58 cases, every case reported)

- H-pure 22: `[hypo teach, question]` across all 11 markers (plain +
  filler twins "Ok, so/And/So/Ok" + "SUPPOSE"), 6 relations
  (boss/mother/city/song/movie/friend). PASS = turn 1 replies the exact
  sentence, 0 writes after each turn, turn-2 reply holds no pretend
  value, notebook empty.
- H-conflict 8: `[real teach, hypo rival, question]` (suppose/imagine/
  what if/pretend that/in theory/say that/hypothetically/let's say;
  boss/mother/city/song/movie/friend). PASS = real saved, hypo exact
  reply, question answers the REAL value, triples hold only real fact.
- N 12: marker-word titles/names ("Kim's song is Imagine", "Kim's film
  is What If", "Kim's book is Suppose", "What If's boss is Kim.",
  value "Suppose"/"Pretend That"/"In Theory"/"Lets Say" ...).
  PASS = reply+triples identical to loop137b.
- O 16: plain teaches, "Btw./So/Hi." phone teaches 137b saves, "Say
  Kim's ...", bare-"If ..." decline, real names, "Okay/And Kim's ...".
  PASS = reply+triples identical to loop137b.
- Bar: 58/58 OK.

## T2 — 0 wrong writes

0 writes on every hypothetical turn (asserted per H case in the probe).

## G1 — bench121 (reuse `fable_bench121_run` by import; frozen 137b rows)

Pre-seal static scan of all 800 bench inputs (taught `sentence_en` +
`question` in all 4 splits): 0 hypothetical-led inputs. Prediction: 0
verdict moves, 0 reply moves, 0 new wrong on all 4 splits. Bar: 0 new
wrong, every move predicted (predicted: none).

## G2 — `scripts/fable_marks123_all.py` per-case vs `marks137b`

Pre-seal static scan of suite sources (p2 redteam98 768 texts, p3
literals, p4 30 innocents incl. setups, rt110 62, q1 fixed turns, bench
A/B taught+questions, rt81 74 turns, sleep/soak templates): 0
hypothetical-led inputs. Prediction: every suite per-case identical to
the base marks folder (incl. inherited p3 L5-Z1 58/60 and rt81 60/0/14
FAIL labels byte-identical). Soak/rt110 flakes under heavy load are a
known mailbox race: re-run that suite once in the open and report both.

## G3 — sessions152 + redteam136/143 (base-folder patterns)

Pre-seal scan: sessions152 180 turns 0 hits; rt143 124 cases 0 hits;
rt136 145 cases 3 hits: C089 "Suppose Tom's boss is Ann." (frozen
WRONG-WRITE storing `[Tom,boss,Ann]`), C090 "Imagine the capital of
Peru is Lima." (frozen OK, 0 writes), C091 "What if Tom's city is
Rome." (frozen OK, 0 writes). Predictions: sessions 0 verdict/reply
moves; rt143 0 moves; cases150/f1/139b 0 moves (scans clean); rt136
C089 WRONG-WRITE→OK with 0 writes and the exact pretend reply (the one
predicted wrong→correct move), C122 identical (stores, WRONG-WRITE),
C090/C091 verdict stays OK with 0 writes and the reply moving to the
exact pretend sentence (predicted reply-only moves; the rt136 compare
is verdict-only). Bar: 0 new WRONG/WRONG-WRITE, every move predicted.

## G4 — time + daemon

Each registered run < 1500 s (< 25 min) Mac CPU, OMP/MKL=1, offline;
daemon wrappers accept idle_seconds (Loop137cDaemon default 30.0).

## Sealed files (sha256 in SEAL.sha256.txt)

PASSMARKS.md (this file), scripts/fable_fix137c_hypo.py,
scripts/fable_loop137c_agent.py, scripts/fable_fix137c_probe.py,
scripts/fable_fix137c_bench.py, scripts/fable_fix137c_junk.py,
scripts/fable_fix137c_sessions.py, scripts/fable_fix137c_redteam143.py,
artifacts/fable-hypo137c-20260922/loop137c-config.json.
Ledger P137c.1–6 appended BEFORE any registered run. No rule changes
after the seal; any post-seal code edit is reported and the affected
marks re-run in the open. A FAIL is recorded as FAIL, never re-run
into a pass.
