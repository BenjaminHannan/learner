# Exp 160c PASSMARKS — bare correction after a >= 2-fact chain asks which fact is meant (sealed BEFORE any registered run)

Registered single-change fix on loop160b (scripts/fable_loop160c_agent.py,
artifacts/fable-twohop160c-20260922/loop160c-config.json; loop160b =
loop150 + 160b last-stated mixin, read-only, no file edited). Exp 160b's
sealed rule guesses the LAST hop after a multi-hop answer: teach Kim's boss
is Lee; Lee's city is Rome; ask "Where is Kim's boss's city?" (-> "Kim's
boss's city is Rome."); then "No, Milan." saves Lee's city = Milan, guessing
the last hop. Ben's ruling (2026-09-22): after a multi-hop answer, ask which
fact is meant.

Responsible code (Step 1): scripts/fable_fix160b_laststated.py:141-151
(LastStated160bMixin._act: on {"act":"bare_correct"} it reads
self._last_stated160b -- the triple the previous reply saved, or the
FINAL-hop fact of the answer it just gave (final_hop_triple, lines 73-110)
-- and synthesizes {"act":"correct", same name/relation/is_person, V}
through super()._act). That resolve is the guess this experiment removes
for chains of >= 2 facts.

THE ONE CHANGE (scripts/fable_fix160c_twohp.py, TwoHop160cMixin; thin
loop160c in scripts/fable_loop160c_agent.py with --daemon entry incl.
idle_seconds): when the agent's IMMEDIATELY previous reply stated a chain of
>= 2 facts (one OK answer record whose trail covers every hop exactly once
with >= 2 hops), a bare correction matching a sealed 160 shape with a valid
V writes NOTHING and replies with the chain's facts as options, e.g.
"Which one is wrong: Kim's boss is Lee, or Lee's city is Rome? Say e.g.
"Actually, Lee's city is Milan."" (the example names the LAST chain fact
with the bare value V; the turn performs 0 FACT writes and counts one
clarification, like 160's sealed clarify). An explicit follow-up correction
("Actually, Lee's city is Milan.") then works exactly as in loop160b through
the loop's EXISTING correction machinery (same guards, same "Saved: ..."
reply, same audit trail and supersede rules). Otherwise (single-fact
previous reply, no-fact previous reply, several records, or no previous
reply) the turn is delegated to loop160b byte-identically. Every turn's
records REPLACE the chain memory (a non-chain reply clears it to None);
nothing older than the previous reply is ever addressed. Chain persists in
state.json ("chain160c"). Non-matching turns never re-tag: byte-identical
to loop160b.

## Sealed bare-correction shapes (identical to 160/160b, reused by import)

- "no wait, [it's|its|it is] V" (e.g. "no wait, it's Denver")
- "wait, [it's|its|it is] V" (e.g. "wait, it's Denver")
- "sorry, [it's|its|it is] V" (e.g. "sorry, it's Denver")
- "I meant[,] V" (e.g. "I meant Denver"; no it's-form)
- "no, [it's|its|it is] V" (e.g. "no, Denver")
V valid iff ALL hold: non-empty; no "?" or "!" in the turn; no "'s"/"'s"
and no " is "/" are " in V; no ","/";"/":" in V; <= 8 words; not a bare
question word (what/who/where/when/why/how/which/whom/whose); does not
start with "to ". Else the base path runs untouched.

Sealed inputs:
- T1 probe: artifacts/fable-twohop160c-20260922/cases160c.json (20 H
  dialogues: 10 two-hop + 10 three-hop, one per bare shape per length,
  follow-ups naming first/middle/last hops, incl. the director's Kim/Lee/
  Rome/Milan probe verbatim as H01) plus the sealed 160b cases
  (artifacts/fable-correct160b-20260922/cases160b.json, read-only) for the
  identity arms (S: A 16 + B01-B08 8 one-hop; O: C 14 + D 10).
- loop160c-config.json (loop160b config + 2 renamed plug strings).
- G1 reference: sealed loop160b bench rows
  (artifacts/fable-correct160b-20260922/fable_bench160b_loop160b_*_rows.jsonl)
  via scripts/fable_loop129b_bench.py run_item by import.
- G2 reference: sealed loop160b marks
  (artifacts/fable-correct160b-20260922/marks160b) via
  scripts/fable_marks123_all.py.
- G3/C2 reference: base agent's own frozen session run
  (artifacts/fable-correct160b-20260922/turns160b-T-160b-*.json) via
  scripts/fable_session152_run.py run_session/judge by import; redteam136
  sealed cases + redteam143 sealed cases/judge by import, both arms live.

## Marks (integer counts, every seed/case reported, never averaged)

- T1 NEW probe of 68 dialogues (scripts/fable_fix160c_probe.py): H 20/20
  bare-after-chain -> exactly the which-one-is-wrong clarify built from the
  sealed chain + V with 0 FACT writes on the bare turn, and the explicit
  follow-up replies "Saved: ..." with the triple set changed ONLY in the
  named fact; S 24/24 single-fact dialogues -> triples AND replies identical
  to loop160b; O 24/24 other turns -> replies AND FACT counts identical to
  loop160b. 68/68 OK.
- T2 0 wrong writes: every H bare turn 0 FACT writes; every H explicit
  follow-up writes exactly the named triple (triple-set delta is one fact).
- C2/G3 sessions152 re-run through loop160c
  (scripts/fable_fix160c_session152.py): exactly ONE predicted move vs the
  loop160b frozen run, S3-teachers-correction turn 6 "no wait, it's denver"
  OK->UNHELPFUL with writes 1->0 and reply "Which one is wrong: Nadia's
  teacher is Rao, or Rao's city is seattle? Say e.g. "Actually, Rao's city
  is denver.""; the other 179 turns identical (reply, statuses, writes);
  0 new WRONG, 0 other new writes.
- G3 redteam136 (145 cases) + redteam143 (124 cases)
  (scripts/fable_fix160c_redteam.py, both arms live): ZERO predicted moves,
  0 new WRONG/WRONG-WRITE vs loop160b.
- G1 bench121 new + old fresh split + Fable-Edit per-item verdicts AND
  replies identical to the sealed loop160b rows
  (scripts/fable_fix160c_bench.py): ZERO predicted moves, 0 new wrong.
- G2 scripts/fable_marks123_all.py suites per-case verdicts identical to
  loop160b's marks160b run (same --workers 4 invocation, --out into this
  exp's marks160c dir): ZERO predicted moves except the sleep SKIP reason
  naming the new agent file (verdict identical, same precedent as
  139b->150 and 150->160->160b).
- G4 each registered run (probe, bench, marks123, sessions, redteam) < 25
  min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds.

## Pre-seal evidence (dev only, NOT registered runs)

- parse_bare_correction (the imported 160 function) over the 180 session152
  turns: exactly 1 hit (S3n6 "no wait, it's denver", previous reply the
  2-hop answer) — the single predicted C2 move.
- Same scan over 145 cases136 strings + 124 redteam143 case strings:
  0 hits -> redteam branch unreachable, 0 moves.
- 160b's sealed scans (cited, PASSMARKS.md): 0 hits over 26647 bench
  strings and 1068 suite/case strings; every bench/marks item runs on a
  fresh daemon (no previous reply), so the 160c branch is unreachable
  there too -> 0 moves.
- Dev smoke (fresh in-process loop160c, temp dirs, no artifact writes):
  director probe -> clarify verbatim as specified, 0 writes, triples
  unchanged; explicit "Actually, Lee's city is Milan." -> Saved + re-ask
  answers Milan; first-hop explicit after clarify saves exactly the first
  hop; 3-hop lists all three facts; single-fact save/answer dialogues
  byte-identical replies+writes to loop160b; 160b cases C+D 24/24 identical,
  A+B01-B08 24/24 identical, B09-B16 8/8 clarify (the intended change).
- Dev S3-only session run through loop160c: turn 6 UNHELPFUL, 0 writes,
  clarify text exactly as predicted above; turn 7 explicit still OK.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. No code edit after sealing except as reported with
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing, ONE AT A TIME)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160c_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160c_session152.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160c_redteam.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop160c_agent.py --config artifacts/fable-twohop160c-20260922/loop160c-config.json --out artifacts/fable-twohop160c-20260922/marks160c --workers 4
