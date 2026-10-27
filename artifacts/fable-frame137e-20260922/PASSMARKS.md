# PASSMARKS — Exp 137e: one hearsay reply (Muse, 2026-09-22)

Base: loop137d (`scripts/fable_loop137d_agent.py`,
`artifacts/fable-frame137d-20260922/loop137d-config.json`; design
`design/v3/30-modes/137d-frame-muse.md`; RESULTS
`artifacts/fable-frame137d-20260922/RESULTS.md`, registered FAIL on
G2/G3 for 7 frozen reply-text checks).

Step-1 facts: the existing hearsay reply HEARSAY_MSG lives at
`scripts/fable_loop102_agent.py:70-71`: "Do you know that yourself, or
did you hear it somewhere? I only save facts you tell me directly."
Loop137d replies sentence-initial hearsay framings
(`scripts/fable_fix137d_frame.py:86-98`) with a new sentence, while
trailing/base hearsay ("Nia's boss is Obi, I heard.") still gets
HEARSAY_MSG -- two hearsay replies (director probe 07:52; 6 cases150
OK->WRONG-REPLY + rt110-T6 OK->BUG, all storing nothing).

THE ONE CHANGE (sealed): `Loop137eEars` subclasses loop137d's ears;
turns whose 137d frame kind is "hearsay" return one clarify carrying
the EXISTING HEARSAY_MSG byte-for-byte (imported read-only from
`fable_loop102_agent`, never retyped). Say-group echo + pretend
parenthetical and every other turn run the unchanged loop137d path
byte-identical (`super().hear()`). Neither group ever writes; later
questions answer only from real saved facts.

## T1 — 137d's sealed probe reused UNCHANGED (by import)

`scripts/fable_fix137e_probe.py` imports SAY_TEACHES/HEAR_TEACHES/
CONFLICTS/NAMES_N/OTHERS_O from `scripts/fable_fix137d_probe.py`.
PASS = S-say 16/16 replies+triples byte-identical to loop137d (say
echo + parenthetical, 0 writes); S-hear 24/24 turn-1 == HEARSAY_MSG
exactly, 0 writes, turn-2 holds no framed value, notebook empty; C 6/6
(real saved, framed exact, question answers REAL value, only real
triple); N 12/12 + O 18/18 identical to loop137d. Bar: 76/76 OK.

## T1b — NEW probe sealed in `scripts/fable_fix137e_probe.py` (31 dialogues)

H 19 hearsay framings [frame, question], fictional names only: 15
leading (Supposedly, supposedly lower-case, Apparently, Ok-so
allegedly, Reportedly, Rumor has it, rumor has it lower-case, Rumour
has it, I heard, i heard lower-case, I heard that, They say, they say
that, People say that, people say) + 4 trailing/base (", I heard.",
"According to ...", ", Beth said.", "I read that ..."). PASS = turn-1
is HEARSAY_MSG exactly, 0 writes after each turn, turn-2 holds no
framed value, notebook empty. E 12 identical-to-loop137d [lead,
question]: 5 Say-group (Say, Say that, So+say, SAY, Ok-so+say that) +
7 plain (teach, Btw. teach, Suppose hypo, my-friend-says x2 declines,
teach, What-if). PASS = replies+triples identical to loop137d. Bar:
31/31 OK. Note: "my friend says ..." declines (never hearsay-shaped)
identically on both agents, so it sits in E, not H, by sealed design.

## T2 — 0 wrong writes

0 writes on every framed turn (asserted per T1 S/C + T1b H case).

## G1 — bench121 (reuse `fable_bench121_run` by import; frozen 137c rows)

Pre-seal real-agent scan (`scripts/fable_fix137e_scan.py`, every input
executed live on loop137e + loop137c): 0 frame-kind fires in all 800
inputs. Prediction: 0 verdict moves, 0 reply moves, 0 new wrong, all 4
splits. Bar: 0 new wrong, every move predicted (predicted: none).

## G2 — `scripts/fable_marks123_all.py` per-case vs `marks137c`

Pre-seal real-agent scan of every suite input (p2 202 texts, p4 40,
rt110 175 incl steps[].text, q1 5, bench113 400, rt81 73, soak 440
templates, p3 469 quoted template strings, sessions/rt143/rt136/
cases150/f1/139b texts): fires only at p2-A4-turn1 ("Rumor has it that
...", single-fire), rt110-T6 ("Apparently ..."), rt136 C101/C102,
cases150 R02/R03/R04/R05/R08/A01 -- on ALL of which loop137c's own
live reply is HEARSAY_MSG with 0 writes (scan compared reply+writes
live, mismatch 0 except p2-A4 turn-1 text). p2-A4: 137c turn-1 is a
decline, 137e turn-1 is HEARSAY_MSG, but the p2 row records
sealed/agent verdict + agent_final (turn-2 "Poland's capital is
Warsaw."), all unchanged -- per-case identical. Prediction: every
suite per-case identical to the base marks folder, except the sleep
SKIP reason naming the new agent file `fable_loop137e_agent.py`
(verdict identical). Soak/rt110 flakes under heavy load are a known
mailbox race: re-run that suite once in the open and report both.

## G3 — sessions152 + redteam136/143 + cases150/f1/139b (base patterns)

Pre-seal real-agent scan: sessions 180 turns 0 fires; rt143 124 inputs
0 fires; rt136 145 cases 2 fires (C101/C102, replies equal live);
cases150 57 texts 6 fires (replies equal live); f1 46 + cases139b 202
texts 0 fires. Predictions: sessions 0 verdict/reply moves; rt143 0
moves; rt136/cases150/f1/139b 0 moves, 0 new WRONG/WRONG-REPLY. Bar: 0
new WRONG/WRONG-REPLY, every move predicted.

## G4 — time + daemon

Each registered run < 1500 s (< 25 min) Mac CPU, OMP/MKL=1, offline;
daemon wrappers accept idle_seconds (Loop137eDaemon default 30.0).

## Sealed files (sha256 in SEAL.sha256.txt)

PASSMARKS.md (this file), scripts/fable_loop137e_agent.py,
scripts/fable_fix137e_probe.py, scripts/fable_fix137e_bench.py,
scripts/fable_fix137e_junk.py, scripts/fable_fix137e_sessions.py,
scripts/fable_fix137e_redteam143.py, scripts/fable_fix137e_scan.py,
artifacts/fable-frame137e-20260922/loop137e-config.json,
artifacts/fable-frame137e-20260922/scan137e-prescan.json.
Ledger P137e.1-6 appended BEFORE any registered run. No rule changes
after the seal; any post-seal code edit is reported and the affected
marks re-run in the open. A FAIL is recorded as FAIL, never re-run
into a pass.
