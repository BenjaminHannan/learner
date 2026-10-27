# Exp 157 PASSMARKS — ONE leading-filler strip for teaches/questions (sealed BEFORE any registered run)

Registered single-change fix on loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; RESULTS.md and docs
150/152 read first). Exp-152 red team class N4: "btw marta's brother is
kai", "also wren's city is miami", "oh and june's teacher is patel" are
refused and the next asks go stuck MISSING (3 refused teaches -> 8 stuck
turns in session S2); exp 150 refuses "Oh and ..." too.

THE ONE CHANGE (scripts/fable_fix157_filler.py, Filler157Mixin; thin
loop157 = loop150 + mixin in scripts/fable_loop157_agent.py with
--daemon entry incl. idle_seconds; loop150 imported read-only, no file
edited): at ears hear(), run the unchanged loop150 hear first; if it
parses, return it. Else strip exactly ONE leading discourse filler from
the closed list below (longest-match) and accept the remainder ONLY when
the unchanged loop150 chain parses it as a complete teach/correct or
question (ask); otherwise the original result returns byte-identical. No
_act change (actions carry no raw text; both hear calls run the full
loop150 chain: 129 strip + 139b value screen + 150 subject screen).

TITLE RULE (design a rule, stated here): strip only when the filler as
typed is all-lowercase ("btw marta..." strips) or is followed by a comma
("Hey, Marta..." strips). A capitalised filler without a comma is NEVER
stripped, so "Hey Jude's writer is Paul McCartney", "Also Sprach
Zarathustra's composer is Richard Strauss", "So Far Away's singer is
Carole King" keep word one (their remainders would parse as
multi-word-subject teaches on the bench73 path, so the re-parse gate
alone would not protect them). Correction markers (actually, no, wait,
sorry, I meant) are NOT fillers and are never stripped.

## Sealed filler list (exact; longest-match; one-line reason each)

- "by the way": multi-word textspeak filler, never a name lead.
- "okay so": multi-word discourse opener, never a name lead.
- "oh and": multi-word discourse opener, never a name lead (152 N4 case).
- "ok so": multi-word discourse opener, never a name lead.
- "anyway": discourse filler, never a name lead.
- "also": additive filler (152 N4 case), never a name lead.
- "hey": greeting filler, never a name lead.
- "fyi": preface marker, never a name lead.
- "well": discourse filler, never a name lead.
- "and": connective lead, never a name lead.
- "btw": textspeak filler (152 N4 case), never a name lead.
- "oh": discourse filler (152 N4 case), never a name lead.
- "so": discourse filler, never a name lead.
- "ok": discourse filler, never a name lead.
- "okay": spelling variant of ok, distinct token.

Sealed inputs:
- B1 probe: artifacts/fable-filler157-20260922/cases157.json (60 cases:
  32 filler+teach/question with bare twins across 13 fillers; 12
  filler-initial titles incl. the 3 brief cases; 16 filler+garbage and
  correction-marker same-as-150 cases).
- loop157-config.json (loop150 config + 2 renamed plug strings; verified
  byte-equal to DEFAULT_CONFIG157 of scripts/fable_loop157_agent.py).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl).
- G2 reference: sealed loop150 marks run
  (artifacts/fable-fix150-20260922/marks150) via
  scripts/fable_marks123_all.py.
- G3/B2 reference: sealed 152 T-T session replies
  (artifacts/fable-session152-20260922/turns152-T-T-*.json) via
  scripts/fable_fix157_session152.py (imports
  scripts/fable_session152_run.py, target swapped to loop157).
- 123 suites, bench splits + scorer v2, 152 sessions + judge: sealed in
  their own exps, read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- B1 new probe of 60 (scripts/fable_fix157_probe.py): 32/32 filler forms
  give exactly the triple (teach, stored non-empty and equal) / answer
  (question, reply byte-equal and want present) of the bare twin run on
  loop150; 12/12 titles identical to loop150 with 0 stripped-subject
  writes (all store [] on both loops); 16/16 garbage/correction replies
  and stored triples identical to loop150. Any FAIL fails B1.
- B2 on the 152 sessions (measured in the G3 run): S2 turns 4, 6, 12
  (N4 teaches) become OK with writes, turns 7, 13, 15, 28, 29 (the stuck
  asks after them) become OK answers; every other reply byte-identical.
- G1 bench121 new/old + Fable-Edit per-item verdicts identical to the
  sealed loop150 rows (scripts/fable_fix157_bench.py): ZERO predicted
  verdict moves, ZERO reply moves, 0 new wrong.
- G2 marks123 suites (scripts/fable_marks123_all.py --agent
  scripts/fable_loop157_agent.py --config
  artifacts/fable-filler157-20260922/loop157-config.json --out
  <this-dir>/marks157 --workers 4): every suite per-case verdict
  identical to loop150's marks150 run; the ONLY allowed text diff is the
  sleep SKIP reason naming fable_loop157_agent.py instead of
  fable_loop150_agent.py (verdict identical: skipped, pass).
- G3 phone sessions (scripts/fable_fix157_session152.py): every reply
  identical to the sealed T-T run EXCEPT the 8 predicted S2 turns
  {4, 6, 7, 12, 13, 15, 28, 29}; 0 new WRONG; new writes exactly turns
  {4, 6, 12}.
- G4 each registered run (probe, bench, marks123, sessions) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
  --no-project --python 3.12 --with torch --with numpy python -B ...);
  daemon wrapper takes idle_seconds.

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function scan of strip_one_filler157 over all 600 bench items
  (teaches + questions): 0 fires.
- Pure-function scan of 2548 suite/redteam strings (p2 64 cases, p4
  innocents, rt110 715, redteam98 766, rt81 613, loop96-marks literals):
  0 turn-text fires (2 loop96 hits are Python source fragments "and
  all(s[", not turns). cases150 scan: 1 fire ("So, Kip Dune..." — not a
  marks123 input; no marks impact).
- Soak/q1 flows by inspection: soak turns are "SoakPnnn's city..."
  ("so"+"ak..." has no word boundary), "Actually, ..." (correction, not
  a filler), "What is ...?"; q1 turns are formal Mira sentences. 0 fires.
- Session152 scan: strip fires only on the 3 N4 teaches (remainders
  parse as teach on base loop150: verified teach triples), on 4x "ok
  cool" (remainder "cool" clarifies on base) and 1x "and his dad?"
  (remainder "his dad?" clarifies on base) — both gate-rejected, so
  identical by construction.
- Base calibration (loop150 only, frozen cases157.json): 20/20 bare
  teaches write, 12/12 bare questions answer with want, 12/12 titles
  clarify-nowrite with full subjects retained.
- loop157-config.json verified field-equal to DEFAULT_CONFIG157.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. Any code edit after the seal is reported and the
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157_probe.py --out artifacts/fable-filler157-20260922/probe157-loop157.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop157_agent.py --config artifacts/fable-filler157-20260922/loop157-config.json --out artifacts/fable-filler157-20260922/marks157 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157_session152.py
