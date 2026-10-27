# Exp 148b PASSMARKS (sealed BEFORE the registered run — do not edit after)

Registered single-change follow-up to the exp-148 FAIL
(artifacts/fable-screen148-20260922/RESULTS.md,
design/v3/30-modes/148-question-screen-muse.md).

THE ONE CHANGE (record plumbing only): the screen's refusal is recorded
through the reasoner record path with an explicit abstain-type status
(`scripts/fable_loop148b_agent.py`, subclass/wrap; 148 imported read-only).
Detection is 148-identical (same "?" gate, same taught entity/value
exemption, same sealed word list in `scripts/fable_screen148_mixin.py`,
neg-wins precedence). On a hit the turn is parsed with the unchanged base
ears and the ask is tagged screen148b=neg/time; the wrapped reasoner
(`ScreenStatusReasoner148b` over `QualifierAwareReasoner77`) runs the real
lookup first (read-only, never writes): a non-OK verdict is returned as-is
plus a marker (MISSING_FACT then literally true BY CONSTRUCTION — the store
itself said so); an OK verdict (the qualifier-blind answer 148 screens) is
replaced with an UNSUPPORTED_QUESTION refusal. The mouth renders marked
records as 148's exact clarify texts (imported, byte-identical). Word list,
matching, and every other behaviour identical to 148.

Status vocabulary: all contract statuses pre-existing; one new status
UNSUPPORTED_QUESTION (well-formed question whose negation/time qualifier the
notebook cannot represent; refused before answering; never a confident
answer, never a write). MISSING_FACT is used ONLY where the lookup itself
abstains (literally true by construction). Per-judge treatment, shown in the
registered run: p3 L5-Z2 (`status in B65.ABSTAIN`) never receives the new
status — all its screen hits are genuinely never-taught relations; p3 L5-Z1
(exact match) sees it only on turns 42/43 (predicted below); reply-text
judges (P2/R98 is_abstain, RT110, 143-runner, benches, Q1/Q2) see 148's
byte-identical clarify text.

Pre-seal evidence (dev-context repros in scratch, plus 148's sealed runs):
- loop134 base on L5-Z1 turns 42/43 observes OK (148's sealed
  marks123-134/p3/l5z1-report.json: obs OK both turns) via taught
  year-named relations (dev repro: relations city_in_2019/job_in_2019, trail
  F00024, reply "Mira's city in 2019 is Port Azure."). The sealed expectation
  OK encodes that qualifier-blind answer.
- 148b on the same turns: screen fires (stage loop148b-screen-time), lookup
  would answer OK, refusal carries UNSUPPORTED_QUESTION + 148's exact time
  text (dev repro).
- 148b on a never-taught relation question: MISSING_FACT (reasoner's own
  fields + marker) + 148's exact neg text; status in B65.ABSTAIN (dev repro).
- 148b on "Mira's city in 2019" with only current city taught: MISSING_FACT
  (relation city_in_2019 genuinely unknown there) + exact time text.

## Sealed case files (sha256)

- fable_screen148_cases.json (148's 40 NEW probes, read-only reuse):
  0c998442f5cf9b5a28438c5c64bbf41b7b74ca073f61699b273d7dae2bdaee5c
- fable_redteam143_cases.json (sealed 143 set, read-only, never overwritten):
  3e39464ad7c0ffa50a603b4f02e36d0c4facedc500af318dc869d384b6deaadb
- loop148b-config.json (DEFAULT_CONFIG148B + thinker module string):
  a4c2e59fa9103b8723b7425c11989ff1c80e3b83cb0c9dbdadd92bb9fc4f8b39
- loop148b-on132-config.json (DEFAULT_CONFIG148B_ON132 + thinker module):
  2c1fd1d1b087f140004d0f303a8ac7b4be6dd117834075a3bae4afcb3228fc97

## Marks

- R1: 148's Q1 and Q2 re-run (scripts/fable_loop148b_q1.py,
  scripts/fable_loop148b_q2.py) -> per-item verdicts AND full reply texts
  identical to 148's sealed reports
  (fable_q1_143_on132plus148_results.json, fable_q2_report.json); Q1 targets
  8/8 no confident answer, 0/116 worse; Q2 20/20 clarify + 20/20 innocent
  byte-identical to base.
- R2: bench121 new/old, bench132, Fable-Edit-200 (scripts/
  fable_loop148b_bench.py --run, scorer v2): per-item verdicts (and replies)
  identical to 148's loop148 rows on all 800 items.
- R3: marks123 (scripts/fable_marks123_all.py) 148b arm vs fresh loop134 arm,
  both in this folder: identical EXCEPT p2 P2-D8 (sealed BUG -> OK, as in
  148: the screen clarifies without `Warsaw`, reply-text judge) and p3 L5-Z1
  turns 42/43 (observed UNSUPPORTED_QUESTION vs base OK; the sealed
  expectation encodes the old qualifier-blind answer — predicted in writing
  now); p3 L1/L2/L3/L4/L6 identical; p3 L5-Z2 per-item verdicts identical to
  loop134 (exactly 37 reply-diffs, the never-items, each MISSING_FACT ->
  abstain_ok in both arms, 0 MISS); p4/rt110/q1/bench-per-item/rt81/sleep/
  soak/q4 identical.
- R4: each registered run < 25 min (< 1500 s) wall-clock, Mac CPU,
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1. All drivers use in-process daemons
  (mailbox files, same code as subprocess daemons); daemon classes accept
  idle_seconds (default 30.0).

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop148b_q1.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop148b_q2.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop148b_bench.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop148b_agent.py --config artifacts/fable-screen148b-20260922/loop148b-config.json --out artifacts/fable-screen148b-20260922/marks123-148b --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop134_agent.py --config artifacts/fable-loop134-20260922/loop134-config.json --out artifacts/fable-screen148b-20260922/marks123-134base --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_loop148b_verify.py
