# Exp 157b PASSMARKS — capitalised/stacked filler strip on loop157 (sealed BEFORE any registered run)

Registered single-change fix on loop157 (scripts/fable_loop157_agent.py,
artifacts/fable-filler157-20260922/loop157-config.json sealed; RESULTS.md
and docs 157/152 read first). Director probe 04:20 on loop157: "btw Tom's
sister is Jo." and "also, Jo's teacher is Max." save, but "Oh and Tom's
mother is Rita.", "So Tom's boss is Bob.", "Oh and Jo's teacher is Max."
and "Btw who is Tom's sister's teacher?" are refused. Cause: 157's title
rule (scripts/fable_fix157_filler.py:67-101; capitalised block lines
92-96) strips a leading filler only when typed all-lowercase or followed
by a comma. Phones auto-capitalise the first word, so the most common
phone form is exactly the one that fails.

THE ONE CHANGE (scripts/fable_fix157b_capfiller.py, CapFiller157bMixin;
thin loop157b = loop157 + mixin in scripts/fable_loop157b_agent.py with
--daemon entry incl. idle_seconds; loop157 imported read-only, no file
edited): at ears hear(), run the unchanged loop157 hear first; if it
parses, return it. Else strip up to TWO leading discourse fillers from
the SAME closed list as 157 (longest-match per step, any capitalisation,
each optionally followed by one comma; covers single capitalised fillers
"Btw"/"Also"/"So"/"Oh"/... and stacked pairs "Okay so", "Oh and btw",
"And also") and accept a remainder ONLY when the unchanged loop157 chain
parses it as a complete teach/correct or question (ask); otherwise the
original result returns byte-identical. No _act change. Titles/names
beginning with a filler word ("Hey Jude", "Also Sprach Zarathustra",
"So Far Away", "Well Played") keep word one exactly as on loop157: their
remainders never parse as complete frames, so the parse gate rejects them
by construction. Correction markers (actually, no, wait, sorry, I meant)
are NOT fillers and are never stripped (the base already parses them, so
step 1 returns first).

Sealed inputs:
- T1 probe: artifacts/fable-filler157b-20260922/cases157b.json (60 cases:
  34 capitalised/stacked filler teaches+questions with bare twins across
  14 fillers and 8 relations; 13 filler-word-initial titles incl. the 4
  brief cases in non-parsing forms; 13 garbage/correction/hedge
  same-as-157 cases).
- loop157b-config.json (loop157 config + 2 renamed plug strings; verified
  field-equal to DEFAULT_CONFIG157B of scripts/fable_loop157b_agent.py).
- G1 reference: sealed loop157 bench rows
  (artifacts/fable-filler157-20260922/fable_bench157_loop157_*_rows.jsonl).
- G2 reference: sealed loop157 marks run
  (artifacts/fable-filler157-20260922/marks157/) via
  scripts/fable_marks123_all.py (loop157's marks157 is itself sealed at
  zero per-case moves vs loop150's marks150).
- G3 reference: sealed loop157 session runs
  (artifacts/fable-filler157-20260922/turns157-loop157-*.json) via
  scripts/fable_fix157b_session152.py (imports
  scripts/fable_session152_run.py, target swapped to loop157b).
- 123 suites, bench splits + scorer v2, 152 sessions + judge: sealed in
  their own exps, read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- T1 new probe of 60 (scripts/fable_fix157b_probe.py): 34/34
  capitalised/stacked filler forms give exactly the triple (teach, stored
  non-empty and equal) / answer (question, reply byte-equal and want
  present) of the bare twin run on loop157; 13/13 titles identical to
  loop157 with 0 stripped-subject writes (all store [] on both loops);
  13/13 garbage/correction replies and stored triples identical to
  loop157. Any FAIL fails T1.
- T2 pass bar: >= 95 % of the 34 T1 must-cases exact (>= 33/34), 0 wrong
  writes over all 60 cases.
- G1 bench121 new/old + Fable-Edit per-item verdicts AND replies
  identical to the sealed loop157 rows
  (scripts/fable_fix157b_bench.py): ZERO predicted verdict moves, ZERO
  reply moves, 0 new wrong.
- G2 marks123 suites (scripts/fable_marks123_all.py --agent
  scripts/fable_loop157b_agent.py --config
  artifacts/fable-filler157b-20260922/loop157b-config.json --out
  <this-dir>/marks157b --workers 4): every suite per-case verdict
  identical to loop157's marks157 run; the ONLY allowed text diff is the
  sleep SKIP reason naming fable_loop157b_agent.py instead of
  fable_loop157_agent.py (verdict identical: skipped, pass).
- G3 phone sessions (scripts/fable_fix157b_session152.py): every reply
  identical to the sealed loop157 session runs; ZERO predicted moves, 0
  new WRONG, 0 new writes.
- G4 each registered run (probe, bench, marks123, sessions) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
  --no-project --python 3.12 --with torch --with numpy python -B ...);
  daemon wrapper takes idle_seconds.

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure-function scan of strip_candidates157b over all 600 bench items
  (teaches + questions, all fields): 0 fires.
- Pure-function scan of 3052 redteam strings (rt110 716, redteam98 764,
  rt143 819, rt136 753): 0 fires. p4 innocents (105 strings): 0 fires.
  loop96-marks literals (281): 0 fires. rt81 probe (273): 0 fires.
- Session152 runner texts: strip fires only on the same 8 turns 157
  handles (3 lowercase N4 teaches, 4x "ok cool", 1x "and his dad?"); every
  157b candidate remainder is identical to 157's remainder, so G3 is
  identical by construction. Soak/q1 flows by inspection: soak turns are
  "SoakPnnn's city..." ("so"+"ak..." has no word boundary), "Actually, ..."
  (correction, not a filler), "What is ...?"; q1 turns are formal Mira
  sentences + "WHO IS MIRA'S CITY?". 0 fires.
- cases150.json scan: 11 fires, all on exp-150 probe strings (not marks123
  inputs per 157's seal); every remainder ("Kip Dune ...", "maybe Kip
  Dune ...") clarifies on base loop157 (multi-word/one-part subjects), so
  the gate rejects them regardless.
- Base calibration (loop157 only, frozen cases157b.json): 34/34 bare
  twins write/answer with want; 13/13 titles clarify-nowrite with full
  subjects retained; 13/13 garbage clarify-nowrite except S03/S04
  correction writes ("Saved: Tom's boss is Sam." on both loops by
  construction -- base parses first-try, mixin never triggers).
- Remainder gate check (loop157 ears only): all 13 title + 6 garbage
  remainders clarify/answer (never teach/correct/ask); all sampled cap
  remainders parse complete (teach/ask).
- loop157b-config.json verified field-equal to DEFAULT_CONFIG157B.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. Any code edit after the seal is reported and the
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157b_probe.py --out artifacts/fable-filler157b-20260922/probe157b-loop157b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop157b_agent.py --config artifacts/fable-filler157b-20260922/loop157b-config.json --out artifacts/fable-filler157b-20260922/marks157b --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157b_session152.py
