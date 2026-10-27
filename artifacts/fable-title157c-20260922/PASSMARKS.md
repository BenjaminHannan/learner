# Exp 157c PASSMARKS — filler+Capitalised title guard on loop157b (sealed BEFORE any registered run)

Base agent: loop157b (scripts/fable_loop157b_agent.py,
artifacts/fable-filler157b-20260922/loop157b-config.json; RESULTS.md and
design/v3/30-modes/157b-capfiller-muse.md read first). Director probe
05:30 on loop157b: "Hey Jude's singer is Paul." saves under "Jude"
(WRONG-WRITE); "Oh Brother's director is Joel." saves under "Brother".

Step 1 (file:line of the strip): scripts/fable_fix157b_capfiller.py:59
(strip_one_anycase157b; driven by CapFiller157bMixin.hear at :137). It
strips a capitalised filler whatever follows, so "Hey"/"Oh" are eaten
and the possessive frame re-parses on the shortened name.

THE ONE CHANGE (scripts/fable_fix157c_titleguard.py, TitleGuard157cMixin;
thin loop157c = loop157b + mixin in scripts/fable_loop157c_agent.py with
--daemon entry incl. idle_seconds; loop157b imported read-only, no file
edited): pure gate blocked157c — a turn-initial filler (same closed
list, any capitalisation) that as typed is NOT all-lowercase and is
followed directly (no comma/punctuation) by a Capitalised word BLOCKS
157b's strip; blocked turns return the deep loop157 parse of the
original turn (whole capitalised run, filler included, treated as the
name — exactly how loop157b handles any other multi-word name: refuse,
no write). All other turns delegate to super().hear() (loop157b,
byte-identical by construction). Lowercase fillers, comma fillers,
punctuation/lowercase follows, stacked pairs, corrections, values and
clarifications are untouched.

Sealed inputs:
- T1 probe: artifacts/fable-title157c-20260922/cases157c.json (56 cases:
  22 filler+Capitalised-possessive titles incl. the 2 brief cases across
  11 relations; 22 real fillers with punctuation/lowercase follow incl.
  the 3 brief examples; 12 other turns).
- loop157c-config.json (loop157b config + 2 renamed plug strings;
  verified field-equal to DEFAULT_CONFIG157C).
- G1 reference: sealed loop157b bench rows
  (artifacts/fable-filler157b-20260922/fable_bench157b_loop157b_*_rows.jsonl).
- G2 reference: sealed loop157b marks run
  (artifacts/fable-filler157b-20260922/marks157b/) via
  scripts/fable_marks123_all.py.
- G3 reference: sealed loop157b session runs
  (artifacts/fable-filler157b-20260922/turns157b-loop157b-*.json);
  redteam136/143 run two-arm (157c vs 157b fresh) in
  scripts/fable_fix157c_redteam.py.
- 123 suites, bench121 splits + scorer v2, 152 sessions + judge, rt136
  cases + rule, rt143 cases + judge: sealed in their own exps, read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- T1 new probe of 56 (scripts/fable_fix157c_probe.py): 22/22 titles never
  saved under the shortened name (stored empty = safe refuse, or every
  stored subject starts with the lead word); 22/22 fillers byte-identical
  to loop157b (teaches: stored+reply equal; questions: reply equal with
  want present); 12/12 others byte-identical to loop157b. Any FAIL fails T1.
- T2 pass bar: 0 wrong writes over all 56 cases (wrong = a title-case
  stored triple whose subject drops the lead word).
- G1 bench121 new/old + Fable-Edit per-item verdicts AND replies
  identical to the sealed loop157b rows
  (scripts/fable_fix157c_bench.py): ZERO predicted verdict moves, ZERO
  reply moves, 0 new wrong.
- G2 marks123 suites (scripts/fable_marks123_all.py --agent
  scripts/fable_loop157c_agent.py --config
  artifacts/fable-title157c-20260922/loop157c-config.json --out
  <this-dir>/marks157c --workers 4): every suite per-case verdict
  identical to loop157b's marks157b run; the ONLY allowed text diff is
  the sleep SKIP reason naming fable_loop157c_agent.py instead of
  fable_loop157b_agent.py (verdict identical: skipped, pass).
- G3 (a) phone sessions (scripts/fable_fix157c_session152.py): every
  reply identical to the sealed loop157b session runs; ZERO predicted
  moves, 0 new WRONG, 0 new writes. (b) redteam136+143 two-arm
  (scripts/fable_fix157c_redteam.py): ZERO predicted moves, 0 new
  WRONG-WRITE / WRONG-ANSWER, 0 new writes.
- G4 each registered run (probe, bench, sessions, redteam, marks123)
  < 25 min wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
  --no-project --python 3.12 --with torch --with numpy python -B ...);
  daemon wrapper takes idle_seconds.

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Pure gate scan over 9591 registered-input strings: 157b-strip fires on
  exactly 4 bench teaches + 8 session turns (+ 0 everywhere else:
  rt136 145, rt143 425 walked strings, rt110 717, rt81 616, redteam98
  1488, soak 403, bench113 A/B = bench121 files, bench121-edit 775;
  p4 innocents + loop96 literals 0 fires per 157b's sealed scan).
  Gate blocks 4 bench teaches ('Hey Jude was performed by The
  Beatles' x2 items, 'And I Love Her was performed by The Beatles',
  'Hey Jude was performed by Madonna') -- base calibration
  (loop157b vs loop157, dev only): byte-identical outputs on all three
  (both save under the FULL name via the bench73 path; base parses
  first-try so the strip never triggers) -> G1 0 moves by evidence.
  The 8 session fires are all lowercase-typed ("also wren's...",
  "and his dad?", "btw marta's...", "oh and june's...", "ok cool")
  -> gate allows -> identical by construction. All other suites: 0
  fires -> identical by construction. Soak/q1 static strings: no filler
  word boundary ("SoakPnnn", "Mira...") -> 0 fires.
- Base calibration (loop157b vs loop157, frozen cases157c.json shapes):
  all 20 strong title cases wrong-write shortened on loop157b and
  clarify-nowrite on loop157 (blocked path returns exactly the loop157
  result); the 2 controls ("Hello Dolly", "Yo Gabba", non-filler leads)
  clarify-nowrite on both. Allowed-path turns delegate to the same
  loop157b code -> identical by construction.
- loop157c-config.json verified field-equal to DEFAULT_CONFIG157C.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. Any code edit after the seal is reported and the
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157c_probe.py --out artifacts/fable-title157c-20260922/probe157c-loop157c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157c_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop157c_agent.py --config artifacts/fable-title157c-20260922/loop157c-config.json --out artifacts/fable-title157c-20260922/marks157c --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157c_session152.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix157c_redteam.py
