# Exp 167e PASSMARKS — every-template label render (sealed BEFORE any registered run)

Base agent: loop167c (scripts/fable_loop167c_agent.py,
artifacts/fable-label167c-20260922/loop167c-config.json).

Director probe 09:10 on loop167c: "Forget Ada's place of birth." ->
"Forgotten: Ada's place_of_birth."; then "Where was Ada born?" ->
"I don't know Ada's place_of_birth.". Root cause: loop167c
(scripts/fable_fix167c_label.py) renders ONLY the Saved confirmation
with the answer path's own surface rule (`key.replace("_", " ")`, the
exact expression FakeMouth.say uses on relation parts at
scripts/fable_agent_loop.py:166-167); every other template that
interpolates the RAW inventory key still leaks it. 167c is a
registered G2 FAIL only because its q4 leak-list improved 7 -> 4
without being predicted.

THE ONE CHANGE, behaviour (scripts/fable_fix167e_label.py,
Label167eMouth stacked onto loop167c's mouth in
scripts/fable_loop167e_agent.py; no 167c/167b/167/162b/agent-loop/
contract/listening file edited): the mouth -- result record ->
English -- applies the answer path's own surface rule to the relation
slot of EVERY reply template that prints a relation key, for every
relation key containing an underscore (optional "(I dropped my earlier
question.) " prefix tolerated). Stored facts, keys, matching, and
which reply is chosen stay byte-identical to loop167c (the notebook
write happens before the mouth runs; the wrapper only post-processes
the outgoing sentence).

## Template enumeration from the code (the seal list)

Prints a relation key -- MOVES (relation slot spaced iff it has "_"):
1. Saved fact confirmation -- scripts/fable_notebook_contract.py:77
   (TEMPLATES[SAVED]), text built at :349 -- already spaced by the
   inner loop167c mouth; the outer render is idempotent on it.
2. CONFLICT change-prompt -- contract.py:79 ("I have {subject}'s
   {relation} as {old}. Do you want me to change it to {new}?").
3. MISSING_FACT "I don't know" -- contract.py:82 ("I don't know
   {subject}'s {relation}.", via ask at :411-412 and the forget-no-rows
   path at scripts/fable_listening_m1.py:143-144).
4. BROKEN_CHAIN -- contract.py:83 ("{subject}'s {relation} is {value},
   which is not someone I can look up.", via ask at :405-407).
5. Forgotten -- listening_m1.py:147 ("Forgotten: {entity}'s
   {relation}.").
No relation key -- byte-identical, enumerated so the seal is complete:
6. Answer path -- agent_loop.py:166-167 already spaces every relation
   part (correction re-teaches through Saved; multi-value listings and
   the verb-question twin render here).
7. Clarifies -- agent_loop.py:115,126-127,139,142,144,148,350,367 and
   listening_m1.py:78,157,163,166 are fixed strings with no relation
   slot.
8. AMBIGUOUS (:80), UNKNOWN_ENTITY (:81), DUPLICATE_OK (:78),
   NOT_ALLOWED (:86), BAD_REQUEST (:87) -- no relation slot.
9. Internal Saved texts never reaching the mouth: declare_relation
   "Saved: relation {relation}." (:266, return ignored at
   listening_m1.py:60-63), retract "forgot {fact_id}" (:362, superseded
   by the Forgotten text), entity/alias/rule/merge texts
   (:277,:286,:294,:387, no relation slots).

## Sealed inputs

- T1 probe: artifacts/fable-label167e-20260922/cases167e.json (34
  turns, all fictional names: Saved/MISSING/CONFLICT/BROKEN/Forgotten
  each with place_of_birth + birth_year + country_of_citizenship (verb
  "was born in", possessive, correction, post-forget asks), spaced
  answers, no-key clarify/other controls).
- T3 reference: loop167c's sealed cases167c.json + frozen
  probe167c-loop167c.json (read-only).
- Config: artifacts/fable-label167e-20260922/loop167e-config.json.
- Code: scripts/fable_fix167e_label.py,
  scripts/fable_loop167e_agent.py; drivers scripts/fable_fix167e_probe.py,
  scripts/fable_fix167e_t3.py, scripts/fable_fix167e_bench.py,
  scripts/fable_fix167e_g3.py, scripts/fable_fix167e_marksdiff.py.
- G1 references: loop167c's frozen rows
  artifacts/fable-label167c-20260922/fable_bench167c_loop167c_*_rows.jsonl.
- G2 reference: base marks167c
  (artifacts/fable-label167c-20260922/marks167c, all suites completed).
- G3 references: loop167c's frozen rows redteam136-loop167c.json,
  redteam143-loop167c.json, sessions152-loop167c.json; plus sealed
  cases136.json, fable_redteam143_cases.json, sessions152.json.

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop167e (scripts/fable_fix167e_probe.py): 34/34
  turns OK -- every reply matches its want_template shape, ZERO
  replies contain an underscore relation-key token, stored triples
  identical to a fresh loop167c run, notebook events identical after
  dropping volatile event_id/prev hash fields (uuid hex per run by
  Listening._eid construction), no-key synthetic templates
  byte-identical through the renderer.
- T3 (scripts/fable_fix167e_t3.py): all 25 cases167c rows OK; stored,
  teach reply, and ask replies byte-identical to frozen
  probe167c-loop167c.json; predicted move set EMPTY.
- G1 bench (scripts/fable_fix167e_bench.py): verdict 0 moves on all
  600 items; teach_replies 0 moves; reply moves EXACTLY on the 37
  edit200 MISSING_FACT replies with never_taught_rel_N keys
  (bench65-abs-absent-01/03/05/07/09/11/13/15/17/19/21/23 +
  bench65-abs-broken-00..24), each by exactly the shared render; 0
  reply moves in old_s2fresh_4hop/new_121_4hop; 0 new wrong vs
  loop167c.
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case vs
  marks167c (scripts/fable_fix167e_marksdiff.py): identical except (a)
  exactly 3 label-render reply moves in rt110 -- F6 log Forgotten
  country_of_citizenship, L6 log MISSING city_and_who_is_mira, S2 log
  MISSING city?_also_mira (the only frozen marks167c replies with an
  underscore relation key); p2/p3/p4/q1/bench/rt81/sleep/soak ZERO
  reply moves; (b) loop167c->loop167e / marks167c->marks167e /
  label167c->label167e path renames; (c) volatile seconds/statuses;
  (d) q4 flips FAIL -> PASS with number exactly "leaks=[]"; sleep
  verdict identical with reason naming loop167e; all other summary
  numbers identical; 0 new WRONG / WRONG-WRITE / junk writes; soak/rt110
  flakes under load are the known mailbox race -> re-run that suite
  once in the open and report both.
- G3 sessions152 + redteam136/143 (scripts/fable_fix167e_g3.py) vs
  loop167c frozen rows: 0 verdict moves, stored/fact_writes identical,
  0 new WRONG/WRONG-WRITE, 0 reply moves on all three suites (pre-seal
  scan: no frozen 167c reply on any suite has an underscore
  relation-key token in any template).
- G4 each registered run (probe, T3, bench, G3, marks123, diffs) < 25
  min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs)

- Render unit matrix 21/21 (dev): spaced Saved/MISSING/CONFLICT/
  BROKEN/Forgotten incl. multi-word subject, dropped-question prefix,
  and punctuated keys (city?_also_mira); 13 no-key templates
  byte-identical (incl. "Saved: relation birth_year." internal text).
- All 34 sealed turns verified end-to-end in dev (temp dirs): every
  loop167c reply matched its template; loop167e dev replies spaced
  with triples and scrubbed events identical to 167c.
- Director probe verbatim in dev: 167e "Forgotten: Ada's place of
  birth." then "I don't know Ada's place of birth.", same triples.
- Exact scans (no agent runs): frozen bench167c rows 37
  underscore-MISSING replies (all edit200, listed above) / 0 in the
  4hop splits; marks167c reply fields underscore-keyed only in rt110
  F6/L6/S2; G3 frozen 167c rows zero underscore replies.
- Daemon check (pre-seal): Loop167eDaemon stores idle_seconds as given
  (12.5 in, 12.5 out); mouth chain Label167eMouth(Label167cMouth(...)).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. No code/case/config/driver edits after the seal;
any edit is reported and the affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_probe.py --out artifacts/fable-label167e-20260922/probe167e-loop167e.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_t3.py --out artifacts/fable-label167e-20260922/t3167e-vs167c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167e_agent.py --config artifacts/fable-label167e-20260922/loop167e-config.json --out artifacts/fable-label167e-20260922/marks167e --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167e_marksdiff.py
