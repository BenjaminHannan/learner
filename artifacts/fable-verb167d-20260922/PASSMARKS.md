# Exp 167d PASSMARKS — widened verb table (sealed BEFORE any registered run)

Base agent: loop167b (scripts/fable_loop167b_agent.py,
artifacts/fable-verb167b-20260922/loop167b-config.json).

Director probe 08:57 on loop167b: "Tom works at Acme.", "Where does Tom
work?", "Rana speaks Hindi.", "What language does Rana speak?" all ->
"I didn't understand that. Could you say it another way?", 0 writes
(reproduced pre-seal, temp dirs). The possessive twins save and answer
today: "Tom's employer is Acme." -> teach (Tom, employer, Acme);
"Rana's language is Hindi." -> teach (Rana, language, Hindi); "Who is
Tom's employer?" / "What is Rana's language?" answer. Relation keys
are the possessive path's own, verified pre-seal.

THE ONE CHANGE, behaviour (scripts/fable_fix167d_verb.py,
Verb167dMixin, stacked INSIDE the untouched 167b value screen as
`Loop167dEars(ValueScreen167bMixin, Verb167dMixin, Plural162bMixin,
TheName162Mixin, OfficeholderGuardMixin, Loop150Ears)` in
scripts/fable_loop167d_agent.py; no 167/167b/139e/139c/162b file
edited): four added rows beside V167's closed table, rewritten to the
possessive twin and handed to super().hear() untouched:
1. "X works at Y" -> "X's employer is Y." (employer);
2. "X speaks Y" -> "X's language is Y." (language);
3. "Where does X work?" -> "Who is X's employer?";
4. "What language(s) does X speak?" -> "What is X's language?".
"Who does X work for?" stays exactly as 167 left it (V167 owns it;
167d never claims it -- disjoint shapes, verified pre-seal).
Guards identical to 167/167b: single capital-lead token subject with
the 150c whole-subject veto; no "?" in statements, no ";" or extra "."
in the value; Actually,/No, prefix preserved; negations (doesn't/does
not), hedges (maybe), tense changes (used to work), hypotheticals,
yes/no verb questions, reverse questions ("Who works at Acme?"), and
multi-word subjects all decline to the base clarify with 0 writes.
New-shape statements pass the same 167b value screen (loop139e tail
strip, then determiner/lowercase veto with loop167's own no-write
clarify), applied in the 167d mixin via S167B.screen_value because
S167B's twin regex only matches 167's three surfaces. New-shape
questions pass straight to the twin (no object to screen), as in 167b.
Base-owned carve-out (same precedent as 167's "the city of" veto):
"X speaks the language of Y" stays on the base path (bench73 template
scripts/fable_bench73_english_arm.py -> languages_spoken_written_or_
signed; the base teaches redteam136 C033 today) -- the mixin declines
it, verified byte-identical pre-seal.

## Sealed inputs

- T1 probe: artifacts/fable-verb167d-20260922/cases167d.json (32 rows,
  all fictional names: 7 works-teach W01-W07 incl. the director's "Tom
  works at Acme.", multi-word values Deutsche Bank / Cedar Clinic /
  Blue Finch / Halden Mill / Porto Labs, tail "Sanna works at Acme
  now." -> stripped, correction "Actually, Emir works at Porto Labs.";
  7 speaks-teach S01-S07 incl. the director's "Rana speaks Hindi.",
  multi-word "Brazilian Portuguese", tails "now"/"too", correction
  "No, Petra speaks Korean."; 8 asks-after-possessive Q01-Q08 --
  possessive teach then verb questions incl. singular+plural language
  forms and "Who does X work for?" staying; 10 traps X01-X10 -- the 6
  listed negations/hedges/descriptions/multi-word-verbs/reverse/yes-no
  plus doesn't-speak, speaks-a-dialect, maybe-speaks, does-not-work.
  Every teach row carries verb-Q + possessive-Q asks, the exact Saved
  reply, and a possessive-twin triple check vs base loop167b.
- T2: loop167b's own sealed probe (cases167b.json, 64 rows) re-driven
  through loop167d, per-case identical to the sealed registered output
  probe167b-loop167b.json (stored + teach reply + ask replies).
- Config: artifacts/fable-verb167d-20260922/loop167d-config.json.
- Code: scripts/fable_fix167d_verb.py,
  scripts/fable_loop167d_agent.py; drivers scripts/fable_fix167d_probe.py,
  scripts/fable_fix167d_bench.py, scripts/fable_fix167d_g3.py,
  scripts/fable_fix167d_marksdiff.py.
- G1 references: base loop167b's rows
  artifacts/fable-verb167b-20260922/fable_bench167b_loop167b_*_rows.jsonl
  AND loop162b's frozen rows
  artifacts/fable-plural162b-20260922/fable_bench162b_loop162b_*_rows.jsonl,
  read-only.
- G2 reference: base marks167b
  (artifacts/fable-verb167b-20260922/marks167b, all suites completed),
  read-only.
- G3 inputs: sealed cases136.json, fable_redteam143_cases.json,
  sessions152.json, read-only; plus loop167b's frozen G3 rows
  (redteam136-loop167b.json, redteam143-loop167b.json,
  sessions152-loop167b.json), read-only. The base side also runs live
  in scripts/fable_fix167d_g3.py (167b files never edited).

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop167d (scripts/fable_fix167d_probe.py): 32/32 OK
  -- 7/7 works-teach + 7/7 speaks-teach (verb teach stores expected
  triple = possessive-twin triple on loop167b; teach reply
  byte-identical to hand-checked expect_reply; every verb-Q and
  possessive-Q contains its want), 8/8 asks-after-possessive, 10/10
  traps (0 writes + reply byte-identical to the base clarify).
- T2 (same script, second phase): 64/64 IDENTICAL to the sealed
  loop167b probe rows (stored + reply + ask replies).
- G1 bench (scripts/fable_fix167d_bench.py, bench121 driver by import):
  per-item verdict AND reply identical to frozen loop167b rows AND
  frozen loop162b rows on all 600 items, 0 new wrong vs loop167b,
  every move listed (prediction: ZERO moves).
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case
  identical to the base marks167b folder except predicted cases
  (scripts/fable_fix167d_marksdiff.py): prediction -- NO moves on any
  suite; sleep SKIP identical, reason names loop167d; summary numbers
  identical to loop167b on every suite; seconds/statuses volatile;
  soak/rt110 flakes under load are the known mailbox race -> re-run
  that suite once in the open and report both.
- G3 sessions152 + redteam136/143 (scripts/fable_fix167d_g3.py): 0
  per-case verdict moves vs live loop167b AND vs loop167b's frozen
  rows, 0 new WRONG/WRONG-WRITE, 0 new writes, every move predicted
  (prediction: none).
- G4 each registered run (probe, bench, G3, marks123, diffs) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs)

- Director probes (temp dirs): all 4 clarify with 0 writes on loop167b;
  on loop167d all 4 save/answer; stored triples exactly the twin's.
- Exact-schema scan with the SEALED claim function
  (V167D.parse_verb167d_turn, no agent runs): 0 added-frame hits in
  4,375 bench teaches+questions, cases136 (145), rt143 (425 turns),
  sessions152 (180 turns), rt110 (174 sends), p2 (202 turns), rt81 (73
  turns), p4 (30 sentences). The only overlap ever seen --
  redteam136 C033 "Tom speaks the language of French." (bench73-owned
  "the language of" shape) -- is declined by the sealed veto,
  verified byte-identical (reply + stored triple) 167d vs 167b.
- p3/q1/soak/sleep inputs inspected: possessive-only turn templates
  ("{name}'s city is {value}.", "What is {name}'s city?", Q1's fixed
  city strings, SKIP sleep) -- no shape the claim function can match
  (p3 sources contain zero occurrences of works/lives/speak/born/
  married/language/employer).
- Sealed T1 expectations + T2 identity verified end-to-end in dev
  (temp dirs only, nothing written to the artifact folder): 32/32 OK,
  64/64 IDENTICAL.
- Daemon check (pre-seal): Loop167dDaemon stores idle_seconds as given
  (12.5 in, 12.5 out).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. No code/case/config/driver edits after the seal;
any edit is reported and the affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167d_probe.py --out artifacts/fable-verb167d-20260922/probe167d-loop167d.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167d_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167d_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167d_agent.py --config artifacts/fable-verb167d-20260922/loop167d-config.json --out artifacts/fable-verb167d-20260922/marks167d --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167d_marksdiff.py
