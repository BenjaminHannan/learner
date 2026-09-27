# Exp 167c PASSMARKS — Saved-label render (sealed BEFORE any registered run)

Base agent: loop167b (scripts/fable_loop167b_agent.py,
artifacts/fable-verb167b-20260922/loop167b-config.json).

Director probe 08:57 on loop167b: "Ada was born in Paris." ->
"Saved: Ada's place_of_birth is Paris." while the answer already says
"Ada's place of birth is Paris.". Root cause: the Saved text comes from
the notebook contract's TEMPLATES (scripts/fable_notebook_contract.py:77,
text built at :349 with the RAW inventory key) while the answer path
renders spaces via FakeMouth.say's inline `part.replace("_", " ")`
(scripts/fable_agent_loop.py:166-167) -- NOT the same render function.

THE ONE CHANGE, behaviour (scripts/fable_fix167c_label.py,
Label167cMouth stacked onto loop167b's mouth in
scripts/fable_loop167c_agent.py; no 167b/167/162b/agent-loop/contract file
edited): the mouth -- result record -> English -- applies the answer
path's own surface rule (`key.replace("_", " ")`, the exact expression
FakeMouth.say uses) to the relation slot of `Saved: X's REL is V.` fact
confirmations, for every relation key containing an underscore. Stored
facts, keys, and matching are byte-identical to loop167b (the notebook
write happens before the mouth runs; the wrapper only post-processes the
outgoing sentence). Scope is deliberately narrow: ONLY Saved fact
confirmations move; CONFLICT / MISSING_FACT / Forgotten / clarify /
answer texts are byte-identical (answers already render spaces; the rest
are not confirmations); non-underscore relations pass through untouched.

Underscore relations the teach path can write (found in the code):
- ALLOWED_KEYS (scripts/fable_fix162_thename.py:73-79) underscore members
  (16): country_of_citizenship, country_of_origin, creator_country,
  educated_at, founded_by, headquarters_location,
  language_of_work_or_name, languages_spoken_written_or_signed,
  location_of_formation, notable_work, official_language, place_of_birth,
  place_of_death, position_played_on_team_speciality,
  religion_or_worldview, work_location.
- Verb path (scripts/fable_fix167_verb.py): place_of_birth (via
  "was born in"; city/employer/spouse have no underscore).
- FakeEars general possessive (scripts/fable_agent_loop.py:150-152,
  `_relation`: ANY multi-word surface -> underscore key), evidenced live
  in frozen redteam136-loop167b.json: apprentice_of, author_of,
  chief_executive_officer, composed_by, country_of_origin, discovered_by,
  founded_by, head_of_government, head_of_state, headquarters_location,
  invented_by, location_of_formation, mentor_of, official_language,
  place_of_birth, place_of_death, work_location, written_by (+ C008/C013
  multi-word-subject variants).

## Sealed inputs

- T1 probe: artifacts/fable-label167c-20260922/cases167c.json (25 rows,
  all fictional names: C01-C16 one possessive teach per ALLOWED_KEYS
  underscore relation; C17 the director verb probe "Ada was born in
  Paris." with verb-Q + possessive-Q asks; C18-C25 general FakeEars
  underscore relations apprentice_of, author_of, head_of_state,
  chief_executive_officer, composed_by, discovered_by, invented_by,
  mentor_of; every expect_reply the hand-checked spaced Saved line).
- T2 reference: loop167b's sealed cases167b.json + frozen
  probe167b-loop167b.json (read-only).
- Config: artifacts/fable-label167c-20260922/loop167c-config.json.
- Code: scripts/fable_fix167c_label.py, scripts/fable_loop167c_agent.py;
  drivers scripts/fable_fix167c_probe.py, scripts/fable_fix167c_t2.py,
  scripts/fable_fix167c_bench.py, scripts/fable_fix167c_g3.py,
  scripts/fable_fix167c_marksdiff.py.
- G1 references: loop167b's frozen rows
  artifacts/fable-verb167b-20260922/fable_bench167b_loop167b_*_rows.jsonl,
  read-only.
- G2 reference: base marks167b
  (artifacts/fable-verb167b-20260922/marks167b, all suites completed),
  read-only.
- G3 references: loop167b's frozen rows redteam136-loop167b.json,
  redteam143-loop167b.json, sessions152-loop167b.json, read-only; plus
  sealed cases136.json, fable_redteam143_cases.json, sessions152.json.

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop167c (scripts/fable_fix167c_probe.py): 25/25 OK --
  stored triples == expect, teach reply byte-identical to expect_reply,
  every ask contains its want, NO reply contains an underscore
  relation-key token, notebook events identical to a fresh loop167b run
  of the same turns after dropping volatile event_id/prev hash fields
  (uuid hex per run by Listening._eid construction).
- T2 (scripts/fable_fix167c_t2.py): all 64 cases167b rows OK; stored and
  ask replies identical to frozen probe167b-loop167b.json; teach replies
  identical EXCEPT the 11 predicted born rows (M16-M22, T03, T07, T11,
  T15) whose reply is exactly frozen-with-place_of_birth-spaced.
- G1 bench (scripts/fable_fix167c_bench.py, bench129 driver by import):
  verdict 0 moves on all 600 items; reply 0 moves; teach_replies move
  EXACTLY on Saved-confirmation entries with underscore keys (pre-seal
  scan of frozen base rows: 415 + 640 + 668 = 1723 entries), each by
  exactly the shared render; 0 new wrong vs loop167b.
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case vs
  marks167b (scripts/fable_fix167c_marksdiff.py): identical except (a)
  Saved-render reply moves ONLY in rt110 rows R4 (1 log reply), F6 (4),
  N5 (2) -- the only frozen marks167b replies containing an underscore
  relation key; (b) loop167b->loop167c / marks167b->marks167c /
  verb167b->label167c path renames; (c) volatile seconds/statuses;
  sleep verdict identical; summary numbers identical; 0 new WRONG /
  WRONG-WRITE / junk writes; soak/rt110 flakes under load are the known
  mailbox race -> re-run that suite once in the open and report both.
- G3 sessions152 + redteam136/143 (scripts/fable_fix167c_g3.py) vs
  loop167b frozen rows: 0 verdict moves, stored/fact_writes identical, 0
  new WRONG/WRONG-WRITE; reply moves ONLY by the shared render --
  predicted: 38 redteam136 Saved replies (C004, C006-C009, C011-C014,
  C016, C019-C029, C030-C035, C037, C039-C042, C044, C045, C049, C061,
  C112, C126), ZERO in redteam143/sessions152.
- G4 each registered run (probe, T2, bench, G3, marks123, diffs) < 25
  min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs)

- Render unit matrix 9/9 (dev): spaced Saved for place_of_birth and a
  4-word key; city/entity/MISSING/CONFLICT/Forgotten/clarify untouched.
- All 25 sealed teaches + 26 asks verified end-to-end in dev (temp dirs):
  every stored triple, every 167b reply, every ask want matched; loop167c
  dev replies spaced with triples and scrubbed events identical to 167b.
- Director probe verbatim in dev: 167b "Saved: Ada's place_of_birth is
  Paris.", 167c "Saved: Ada's place of birth is Paris.", same triple,
  same answers.
- Exact scans (no agent runs): frozen bench teach_replies 1723
  underscore-Saved entries / 0 Saved-shaped bench replies;
  marks167b Saved replies only in rt110 R4/F6/N5; G3 frozen replies only
  the 37 redteam136 Saved lines.
- Daemon check (pre-seal): Loop167cDaemon stores idle_seconds as given
  (12.5 in, 12.5 out); mouth wrapped exactly once.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. No code/case/config/driver edits after the seal;
any edit is reported and the affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_probe.py --out artifacts/fable-label167c-20260922/probe167c-loop167c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_t2.py --out artifacts/fable-label167c-20260922/t2167c-vs167b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167c_agent.py --config artifacts/fable-label167c-20260922/loop167c-config.json --out artifacts/fable-label167c-20260922/marks167c --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167c_marksdiff.py
