# Exp 165 PASSMARKS — missing-apostrophe possessives (sealed BEFORE any registered run)

Ben's ruling (2026-09-22): fix typos silently. THE ONE CHANGE, behaviour
(scripts/fable_fix165_typo.py, Typo165Mixin, stacked outermost as
`Loop165Ears(Typo165Mixin, Loop162bEars)` in scripts/fable_loop165_agent.py;
no 162b file edited): in teach turns `W R is V` and question turns
`Who/What/Where is|are W R`, a word W ending in s with no apostrophe,
directly followed by a person-relation word R, is read as the possessive of
W-minus-s when and only when (a) W-minus-s matches exactly one known
notebook entity (case-insensitive) and (b) W itself is not a known entity
and not a known plural name (final word of a known multi-word entity, e.g.
"Toms" while "The Toms" is taught). Claimed turns are rewritten to
`W-minus-s's R ...` (rest byte-preserved) and delegated to the loop162b
hear literally, so the save path and reply text are the base's own: no
extra reply text, the normal reply ("Saved: Tom's boss is Lee." /
"Tom's boss is Lee.") shows the reading. Base agent: loop162b
(scripts/fable_loop162b_agent.py,
artifacts/fable-plural162b-20260922/loop162b-config.json).

Step 1 (base parse site): scripts/fable_agent_loop.py:93
(`_APOS = r"[''s]\b\s*"`) via :102 (`_chain()` splits owner/relation on the
apostrophe-s). Today "toms boss" never splits: teach clarifies
("I didn't understand that. Could you say it another way?", 0 writes) and
questions clarify the same way (verified live on loop162b pre-seal).

## Sealed inputs

- T1/T2 probe: artifacts/fable-typo165-20260922/cases165.json (53 rows:
  29 NEW typo T01-T29 across 7 person relations boss/mother/father/sister/
  brother/friend/teacher, teaches and questions, lowercase and capitalised,
  incl. "Chriss" for "Chris" -> read as the possessive, exact write+answer;
  12 guard G01-G12 flagged identical_to_base (stripped unknown: Zorgs/Qaxs/
  Beatles/Blargs; W itself known: taught "Toms"/"Chris"; plural-name block:
  "The Toms"+Tom; shape-adjacent: 3-token left, office relation, hearsay);
  12 other C01-C12 flagged identical_to_base).
- Config: artifacts/fable-typo165-20260922/loop165-config.json (this folder).
- G1 reference: BASE agent's frozen rows
  artifacts/fable-plural162b-20260922/fable_bench162b_loop162b_*_rows.jsonl
  (edit200/old_s2fresh_4hop/new_121_4hop splits), read-only.
- G2 reference: base marks162b
  (artifacts/fable-plural162b-20260922/marks162b, completed every suite),
  read-only. Bench splits + scorer v2 + 123 suites sealed in their own
  exps, read-only.
- G3 inputs: sealed cases136.json, fable_redteam143_cases.json,
  sessions152.json, read-only; base side runs live (loop162b files never
  edited), same pattern as 162b.

## Marks (integer counts, every seed/case reported, never averaged)

- T1 probe through loop165 (scripts/fable_fix165_probe.py): 29 typo ->
  29/29 exact triples + typo Who-ask and proper What/Who-ask answering V;
  12 guard + 12 other -> 24/24 stored+reply byte-identical to loop162b.
- T2: 0 wrong writes over all 53 rows.
- G1 bench (scripts/fable_fix165_bench.py, reuse of the bench121 driver by
  import): per-item verdict AND reply identical to the frozen loop162b rows
  on all 600 items except predicted items (prediction: ZERO moves),
  0 new wrong, every move (none predicted) listed.
- G2 marks123 (scripts/fable_marks123_all.py --workers 2) per-case
  identical to marks162b except predicted cases (prediction: ZERO semantic
  moves on every suite; sleep SKIP verdict identical, reason text names the
  new agent file; soak/rt110 flakes under load are the known mailbox race
  -> re-run that suite once in the open and report both).
- G3 sessions152 + redteam136/143 (scripts/fable_fix165_g3.py, base-folder
  patterns): 0 per-case verdict moves vs loop162b, 0 new WRONG/WRONG-WRITE,
  0 new writes, every move predicted (none).
- G4 each registered run (probe, bench, G3, marks123, diffs) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function check of rewrite_teach/rewrite_ask on a stub notebook: 10/10
  shape cases rewrite as specified; unknown stripped, office relation,
  apostrophe-present, 3-token left, "The Beatles founder", W-known, and
  plural-name ("The Toms") cases all return None; "Chriss" rewrites to
  "Chris's", "Chris" returns None.
- Base loop162b dev runs: "Toms boss is Lee." clarifies with 0 writes;
  "Tom's boss is Lee." saves with reply "Saved: Tom's boss is Lee.";
  lowercase "tom's boss is Lee." saves; repeated-name setups reuse the
  entity (no duplicate); "The Toms' founder is Lennon." saves "The Toms".
- Shape scan (scripts/fable_fix165_scan.py, linear tokenizer, no backtrack):
  0 claim-shape hits in bench edit200/s2fresh/121-4hop inputs,
  cases136.json, fable_redteam143_cases.json, sessions152.json,
  fable_redteam110_cases.json, fable_redteam81_results.json.
- Config written by the agent's own --write-config (no loop ran).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

## Registered reproduce (run from worktree root, after sealing, one at a time)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix165_probe.py --out artifacts/fable-typo165-20260922/probe165-loop165.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix165_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix165_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop165_agent.py --config artifacts/fable-typo165-20260922/loop165-config.json --out artifacts/fable-typo165-20260922/marks165 --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix165_marksdiff.py
