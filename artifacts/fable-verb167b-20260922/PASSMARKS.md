# Exp 167b PASSMARKS — verb-object value screen (sealed BEFORE any registered run)

Base agent: loop167 (scripts/fable_loop167_agent.py,
artifacts/fable-verb167-20260922/loop167-config.json). Exp 167 is a
registered FAIL for process reasons (first probe 60/61 on a case-file bug;
post-seal edits to cases167.json and scripts/fable_fix167_marksdiff.py);
its behaviour is intact and evidenced in its artifact folder.

Director held-out probe on loop167: "Nia lives in Accra." -> Saved city
(good); "Nia works for Obi." -> employer (good); negations/used to/might/
maybe -> no write (good); BUT "Ivy lives in a flat." -> "Saved: Ivy's
city is a flat." and "Uma lives in Accra now." -> "Saved: Uma's city is
Accra now." (2 wrong writes), and "Raj was born in Pune." -> "Saved:
Raj's place_of_birth is Pune." (raw underscore label; the answer path
already renders "place of birth").

THE ONE CHANGE, behaviour (scripts/fable_fix167b_valuescreen.py,
ValueScreen167bMixin, stacked outermost as
`Loop167bEars(ValueScreen167bMixin, Loop167Ears)` in
scripts/fable_loop167b_agent.py; no 167/139e/139c/162b file edited): a
claimed 167 verb STATEMENT's object must be name-shaped before its
possessive twin is handed to super().hear():
1. strip trailing tail words with loop139e's sealed tail machinery
   (scripts/fable_fix139e_tail.py imported read-only; the strip is
   loop139e's sealed loop139c strip_chat_tail --
   scripts/fable_fix139c_tail.py:46 -- same closed list: too, also,
   actually, though, tho, lol, lmao, haha, btw, again, now, anyway,
   then, instead, rn, right, ok, okay + pairs "as well"/"i guess",
   lowercase-only, repeats for stacked tails, one value word must remain);
2. if the stripped object is empty, starts (case-insensitive) with an
   article/determiner in the closed DETERMINERS set (a, an, the, my,
   your, his, her, its, our, their, this, that, these, those, some, any,
   no, every, each, either, neither -- fixed in
   design/v3/30-modes/167b-verb-value-screen-muse.md before any panel
   read), or starts lowercase (home, town, abroad), write nothing and
   reply exactly loop167's own no-write clarify ("I didn't understand
   that. Could you say it another way?",
   scripts/fable_agent_loop.py:148);
3. otherwise hand on the twin rebuilt with the STRIPPED object, so the
   write/answer is the possessive path's own as in 167.
Verb questions take 167's path literally (no object to screen); anything
167 declines still declines identically (the mixin only acts when
V167.parse_verb_turn claims the turn).

Saved-label ruling: the verb path keeps "place_of_birth" raw. The answer
path renders spaces via FakeMouth.say's inline `part.replace("_", " ")`
(scripts/fable_agent_loop.py:166-167) while Saved text comes from the
notebook contract's TEMPLATES (scripts/fable_notebook_contract.py:77) --
NOT the same one-line render function -- so per the brief the label is
left as is and listed as future work (not a second change).

## Sealed inputs

- T1/T2 probe: artifacts/fable-verb167b-20260922/cases167b.json (64 rows,
  all fictional names, none reused from cases167.json: 22 mapped M01-M22
  -- 8 lives incl. 2 multi-word cities (New York, San Francisco) + 7
  works + 7 born, each with verb-Q + possessive-Q asks, exact Saved
  reply, and a possessive-twin triple check vs base loop167; 16 tail
  T01-T16 -- now/btw/too/actually/lol/stacked/rn/as well/anyway/also/
  though/again/i guess/instead/comma-too, each saved WITHOUT the tail
  word with exact Saved reply + asks + twin check; 16 descr D01-D16 --
  a flat/the city/my house/home/town/abroad/a company/the firm/a town/
  the village/capital-A flat/an apartment/capital-The city/his uncle/
  her hometown/some town, each no write + exact clarify; 10 neg N01-N10
  -- does-not/used-to/might/will/did-not/does-not/was-not/may/probably/
  would, each no write + exact clarify).
- Config: artifacts/fable-verb167b-20260922/loop167b-config.json.
- Code: scripts/fable_fix167b_valuescreen.py,
  scripts/fable_loop167b_agent.py; drivers scripts/fable_fix167b_probe.py,
  scripts/fable_fix167b_bench.py, scripts/fable_fix167b_g3.py,
  scripts/fable_fix167b_marksdiff.py.
- G1 references: loop167's rows
  artifacts/fable-verb167-20260922/fable_bench167_loop167_*_rows.jsonl AND
  loop162b's frozen rows
  artifacts/fable-plural162b-20260922/fable_bench162b_loop162b_*_rows.jsonl,
  read-only.
- G2 reference: base marks167
  (artifacts/fable-verb167-20260922/marks167, all suites completed),
  read-only.
- G3 inputs: sealed cases136.json, fable_redteam143_cases.json,
  sessions152.json, read-only; plus loop167's frozen G3 rows
  (redteam136-loop167.json, redteam143-loop167.json,
  sessions152-loop167.json), read-only. Loop162b's folder holds no frozen
  sessions/redteam rows, so the base side runs live in
  scripts/fable_fix167b_g3.py (162b files never edited).

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop167b (scripts/fable_fix167b_probe.py): 64/64 OK --
  22/22 mapped (verb teach stores expected triple = possessive-twin
  triple on loop167; teach reply byte-identical to hand-checked
  expect_reply; every verb-Q and possessive-Q contains V), 16/16 tail
  (stored WITHOUT the tail word; reply byte-identical; asks answer the
  clean value; twin-triple identical), 16/16 descr + 10/10 neg (0 writes
  + reply byte-identical to loop167's clarify).
- T2: 0 wrong writes over all 64 rows (no TWIN-DIFF, no WRONG-WRITE).
- G1 bench (scripts/fable_fix167b_bench.py, bench121 driver by import):
  per-item verdict AND reply identical to frozen loop167 rows AND frozen
  loop162b rows on all 600 items, 0 new wrong, every move listed
  (prediction: ZERO moves).
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case
  identical to the base marks167 folder except predicted cases
  (scripts/fable_fix167b_marksdiff.py): prediction -- NO moves on any
  suite (rt110 P1/P3 keep their sealed 167 replies: log[0] contains
  "Saved: Mira's city is Oslo.", log[2] contains "Mira's city is
  Oslo."); sleep SKIP identical, reason names loop167b; summary numbers
  identical to loop167 on every suite; seconds/statuses volatile;
  soak/rt110 flakes under load are the known mailbox race -> re-run that
  suite once in the open and report both.
- G3 sessions152 + redteam136/143 (scripts/fable_fix167b_g3.py): 0
  per-case verdict moves vs loop162b AND vs loop167's frozen rows, 0 new
  WRONG/WRONG-WRITE, 0 new writes, every move predicted (prediction:
  none).
- G4 each registered run (probe, bench, G3, marks123, diffs) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs)

- Screen unit matrix 26/26 (dev): clean/multi-word pass with identical
  twin; now/too-lol/as-well/comma-too/i-guess pass stripped; a-flat/
  A-flat/the-city/my-house/home/town/abroad/a-company/a-town/
  her-hometown/tail-only ("now") refuse; negations/used-to/might/married
  statements/questions decline to the 167 path untouched.
- End-to-end director probes (temp dirs): Nia city/employer saves
  byte-identical to 167; "Ivy lives in a flat." -> clarify, 0 writes
  (167 wrote (Ivy, city, a flat)); "Uma lives in Accra now." -> "Saved:
  Uma's city is Accra." (167 stored "Accra now"); born Saved keeps
  place_of_birth, answers render "place of birth" (different render
  functions, label left as is); negations byte-identical clarifies.
- All 64 sealed teaches + asks + twin-triples verified end-to-end in
  dev (temp dirs only, nothing written to the artifact folder): every
  stored triple, every exact reply, every ask want, every twin-triple
  matched the sealed expectation.
- Exact-schema scan (no agent runs): 0 verb-frame hits in 4,824 bench
  teaches+questions, cases136 (145), rt143 cases, sessions152 turns.
  rt110: only P1/P2/P3 "Mira lives in Oslo[. ...]" hit; P2 (two
  sentences) and P4 ("She lives...") vetoed as in 167; P1/P3 clean
  "Oslo" passes the screen -- verified byte-identical replies+triples
  167 vs 167b end-to-end. Subset argument: 167b claims a strict subset
  of 167's statements, and 167's registered G2 moved vs 162b ONLY on
  P1/P3, so no other marks123 input can move under 167b.
- Daemon check (pre-seal): Loop167bDaemon stores idle_seconds as given
  (12.5 in, 12.5 out).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. No code/case/config/driver edits after the seal;
any edit is reported and the affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167b_probe.py --out artifacts/fable-verb167b-20260922/probe167b-loop167b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167b_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167b_agent.py --config artifacts/fable-verb167b-20260922/loop167b-config.json --out artifacts/fable-verb167b-20260922/marks167b --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167b_marksdiff.py
