# Exp 150d PASSMARKS — hedge words are case-sensitive, sealed before run

Agent: `scripts/fable_loop150d_agent.py` (Loop150dEars / Loop150dAgentLoop /
Loop150dMouth / Loop150dDaemon, build_agent150d, DEFAULT_CONFIG150D).
Guard: `scripts/fable_fix150d_subjectguard.py` (screen_subject_150d).
Config: `artifacts/fable-hedgecase150d-20260922/loop150d-config.json`.
Probe: `artifacts/fable-hedgecase150d-20260922/cases150d.json` (44 cases).
Seeded in this file before any registered run; hashed to SEAL.sha256.txt
together with the config, cases, agent, guard, and all five drivers.
Ledger P150d.1–P150d.6 appended pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL.
No code edit after the seal except as reported in RESULTS.md (affected
marks re-run in the open). No rule changes after the seal.

## Step 1: file:line of the hedge match (exp 150, the bug)

`scripts/fable_fix150_subjectguard.py:144-145` (`_is_hedged`, via the
case-insensitive `_starts_with_phrase` at `:121-124`): any subject starting
with a hedge opener (ci) refuses, so "I Believe I Can Fly" refuses as
"i believe" and bench132-4hop-152 answers short (WRONG).

## The one change (sealed rule)

A hedge phrase counts only when its content word is lowercase as typed, or
the whole span is all-caps (scripts/fable_fix150d_subjectguard.py,
`_hedge_counts`): "i think/guess/believe/suppose" need a lowercase content
word ("I believe Kip" hedges; "I Believe I Can Fly" stores); single-word
hedges need a lowercase hedge word ("maybe Kip" hedges), a comma
("Maybe, Kip" hedges), a 2+-token remainder ("Maybe Kip Dune", "Maybe the
capital of Peru" hedge), or all-caps ("MAYBE KIP", "I BELIEVE TOM" hedge);
only a lone Title-Case token remainder ("Maybe Tomorrow", "Perhaps Love")
stores. Reporting openers, filler stripping, rule (c), and both replies are
byte-identical to 150. Possessive owners keep the 150 case-insensitive veto
in the 137-upgrade path (scripts/fable_loop150d_agent.py `_upgrade137`):
"Maybe Tom's boss" (sealed C081, nowrite) is indistinguishable from "Maybe
Tomorrow's author" there, so both refuse exactly as on loop138b (documented
limitation, not a regression; bench132-152's teach is copula-shaped).

## Marks (commands + bars + predictions)

- T1/T2: `python -B scripts/fable_fix150d_probe.py` (44 cases, fresh
  in-process loops per case per arm + registered bench132-152 item).
  Bar: title 16/16 (12 singles save exact triples incl. 2 value-side
  same-saves; 4 chains answer gold; subject-side titles refuse on loop138b),
  hedge 16/16 reply- and store-identical to loop138b with 0 writes either
  arm, other 12/12 identical (incl. 3 neutral twins answering gold and the
  title-possessive O11 refused on both), T2 bench132-152 correct+exact.
  0 wrong writes anywhere.
- G1: `python -B scripts/fable_loop150d_bench.py` (138b bench module by
  import, 150d repointed). Bar: per-item verdicts equal loop138b frozen rows
  on all 4 splits EXCEPT exactly bench132-4hop-152 wrong->correct; 0 new wrong.
- G2: `python -B scripts/fable_marks123_all.py --agent
  scripts/fable_loop150d_agent.py --config
  artifacts/fable-hedgecase150d-20260922/loop150d-config.json --out
  artifacts/fable-hedgecase150d-20260922/marks150d --workers 4`, then
  `python -B scripts/fable_fix150d_markscompare.py`. Bar: per-case identical
  to marks138b on every suite (p2/p3/p4/rt110/q1/bench/rt81/sleep/q4/soak).
  Static pre-seal scan: zero hedge-led inputs in any G2 suite (bench DATA_A/B
  = edit200/s2fresh already scanned clean; rt81 SEQS, rt98 CASES, rt110
  cases, p4 innocents, q1/p3/soak fixed turns all clean).
- G3: `python -B scripts/fable_loop150d_junk.py` (redteam136/cases150/f1/
  cases139b vs loop138b frozen rows), `python -B
  scripts/fable_loop150d_redteam143.py` (143 vs frozen rows), `python -B
  scripts/fable_loop150d_sessions.py` (sessions152 vs frozen rows). Bar: 0
  moves everywhere, 0 new WRONG/WRONG-WRITE. Static pre-seal scan: every
  hedge-led sealed input (rt136 C064/C081/C083/C085, cases150 H/A, sessions
  S2 "I think Kip Dune's city is Reno") stays refused under the sealed rule
  (verified live pre-seal: C081 nowrite, S2 identical).
- G4: every registered run above < 25 min wall-clock Mac CPU
  (OMP/MKL=1); daemon wrappers take idle_seconds (Loop150dDaemon default
  30.0; drivers pass 3600.0; soak/rt110 race: one open re-run allowed,
  both reported).

## Frozen references (read-only, never rewritten)

- Sealed loop138b rows: artifacts/fable-agent138b-20260922/
  (fable_bench121_loop138b_*_rows.jsonl, marks138b/, redteam136-loop138b.json,
  probe150-loop138b.json, f1-loop138b.json, probe139b-loop138b.json,
  redteam143-loop138b.json, sessions152-loop138b.json).
- Junk cases + seals: artifacts/fable-redteam136-20260922/,
  fable-fix150-20260922/, fable-fix139b-20260922/, fable-fix144-20260922/.
- 143 cases: artifacts/fable-redteam143-20260922/;
  sessions: artifacts/fable-session152-20260922/sessions152.json.
