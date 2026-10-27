# Exp 159 PASSMARKS — hop through known names (sealed BEFORE any registered run)

Registered single-change fix on loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-fix150-20260922/loop150-config.json; loop150 = loop129b +
139b value guard + 150 subject guard). The exp-152 red team (class N9, its
only WRONG) found: after "Biscuit's color is brown." and "Ana's pet is
Biscuit.", "Who is Ana's pet's color?" replies "Ana's pet is Biscuit,
which is not someone I can look up." 152's turn 26 ("Who is Biscuit's
owner's pet?", same reply) was judged OK by mistake.

THE ONE CHANGE (scripts/fable_fix159_hop.py, Hop159Reasoner77; thin
loop159 = loop150 + reasoner swap in scripts/fable_loop159_agent.py with
--daemon entry incl. idle_seconds; loop150/fix77 imported read-only, no
file edited): inside the reasoner's hop loop, a mid-chain LITERAL value
continues the walk from the matching entity iff it exactly equals -- after
the loop's own name normalisation (C._norm: lowercase, collapse
whitespace, fable_notebook_contract.py:116-117) -- the display name of
EXACTLY ONE entity heading at least one LIVE taught fact (source
"taught" and nb.active); otherwise the old BROKEN_CHAIN reply,
byte-identical. Zero matches, alias-only matches, and ambiguous matches
keep the old reply. Untouched by design: teaches/corrections/forgets,
qualifiers, learned-word stages, multi answers, conf threshold,
final-literal answers; execution is line-identical whenever the walk never
stands on a mid-chain literal. Case-only differences ("Rope" vs subject
"rope") DO continue -- the loop itself normalises case away, so they are
exact matches, not loose ones.

Sealed inputs:
- H1 probe: artifacts/fable-hop159-20260922/cases159.json (48 dialogues:
  26 chain C01-C26 + 11 nobody N01-N11 + 11 traps T01-T11; every dialogue =
  teaches then one 2/3-hop question; fresh loop per dialogue).
- loop159-config.json (loop150 config + 2 renamed reasoner/daemon strings).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl) +
  bench splits + scorer v2 sealed in their own exps, read-only.
- G2 reference: sealed loop150 marks run
  (artifacts/fable-fix150-20260922/marks150) via
  scripts/fable_marks123_all.py into this exp's marks159 dir.
- G3 reference: sealed exp-152 sessions
  (artifacts/fable-session152-20260922/sessions152.json +
  turns152-T-T-*.json; import scripts/fable_session152_run.py shapes, swap
  target to loop159).
- 123 suites, bench splits, session harness: sealed in their own exps,
  read-only.

## Marks (integer counts, every seed/case reported, never averaged)

- H1 NEW probe of 48 dialogues through loop159
  (scripts/fable_fix159_probe.py): 26/26 two/three-hop chains through
  non-person relations (pets C01-C06, objects C07-C11, places C12-C16,
  organisations C17-C21, works C22-C26) -> correct answer; 11/11
  mid-value-nobody dialogues (N01-N11) -> old BROKEN_CHAIN reply unchanged;
  11/11 loose-match traps (T01-T11: sub/super-strings, plurals, extra
  words) -> old reply, 0 wrong answers; every teach Saved, 0 question-turn
  writes over all 48.
- G1 bench121 new + old-fresh + Fable-Edit per-item verdicts AND replies
  identical to the sealed loop150 rows (scripts/fable_fix159_bench.py)
  with ZERO predicted moves, 0 new wrong.
- G2 marks123 suites (scripts/fable_marks123_all.py --agent
  scripts/fable_loop159_agent.py --config
  artifacts/fable-hop159-20260922/loop159-config.json --out <this-dir>/marks159)
  per-case verdict-identical to loop150's run (marks150) with ZERO
  predicted moves (sleep SKIP reason text names the agent file, verdict
  identical, as in 150).
- G3 exp-152 phone sessions through loop159
  (scripts/fable_fix159_session.py): every reply byte-identical to the T-T
  run except exactly 4 predicted S4-pets-identity turns (7+27 ->
  "Ana's pet's color is brown.", 20 -> "Ana's pet's owner is Ana.", 26 ->
  "Biscuit's owner's pet is Biscuit."); 0 new WRONG; 0 new writes except
  predicted (none: asks never write).
- G4 each registered run (probe, bench, marks123, sessions) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrapper
  takes idle_seconds (default 30.0).

## Pre-seal evidence (dev only, NOT registered runs; the new loop never ran)

- Base calibration (scripts/fable_fix159_calib150.py, BASE loop150 only,
  on the frozen probe): 48/48 well-formed -- every teach Saved, every
  question BROKEN_CHAIN on the base (the base is blind to all 48). Two
  case-authoring bugs found and fixed pre-seal: N03's employer-tail
  question truncates to 1-hop in the 113b composer when ungrounded
  (replaced with a gift/boss shape that full-parses via fallback); T09
  used "boss" (a PERSON_RELATIONS entity hop, fable_agent_loop.py:91 --
  replaced with "assistant"). All five 3-hop frames verified full
  ([pet,owner,pet], [dog,toy,color], [city,capital,river],
  [employer,boss,city], [book,author,city]) via ears.hear on the base.
- G1 item-by-item scan of the 600 sealed loop150 rows: 0 BROKEN_CHAIN
  replies (0/200 edit200, 0/200 old_s2fresh, 0/200 new_121) -- only that
  branch changed, so 0 moves predicted.
- G2 scan of all 4446 marks150 files: 0 BROKEN_CHAIN replies -- 0 moves
  predicted.
- G3 scan of all 180 sealed T-T turns (6 x 30): BROKEN_CHAIN replies only
  at S4 turns 7 (WRONG), 20 (OK), 26 (OK), 27 (WRONG) -- exactly the 4
  predicted moves (mid "Biscuit" heads live Biscuit facts at 7/20/27; mid
  "Ana" heads the live Ana fact at 26).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. Any code edit after this seal is reported and the
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix159_probe.py --out artifacts/fable-hop159-20260922/probe159-loop159.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix159_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop159_agent.py --config artifacts/fable-hop159-20260922/loop159-config.json --out artifacts/fable-hop159-20260922/marks159 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix159_session.py
