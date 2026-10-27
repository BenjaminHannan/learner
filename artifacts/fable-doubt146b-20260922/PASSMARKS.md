# Exp 146b PASSMARKS — doubt with hearsay exemption (sealed BEFORE any registered run)

THE ONE CHANGE vs exp 146 (scripts/fable_doubt146b_store.py, new file;
thin wrappers scripts/fable_loop146c_agent.py = loop129b + 146b doubt,
scripts/fable_loop146d_agent.py = loop139b + 146b doubt; 146 imported
read-only, no existing file edited): a turn is hearsay-exempt when the
loop's own F1 classifier fires (L102.is_hearsay), the parsed teach
subject is hearsay-shaped (L102.subject_is_hearsay_shaped), or the turn
carries reported-speech / quoted-content markers (leading "Ann said
...", "X says ...", "someone told me ...", "I heard ...", "apparently
...", "according to ...", quotation marks). An exempt turn NEVER records
a doubt (ears hear + loop _act); only first-person refused
teaches/corrections do. Everything else identical to 146: same parsers,
same doubt reply ("could not store ... one fact"), same walk screening
(questions after an exempt turn still screen against older first-person
doubts), same clearing rule (a later successful teach of the same
(subject, relation) clears; hearsay neither records nor clears), same
notebook-side doubts146.json store (atomic, reloaded per build).

Sealed inputs:
- H1 probe: artifacts/fable-doubt146-20260922/doubt146-cases.json (32
  dialogues, read-only reuse),
  sha256 d55ab5e05c518d1f809ce668e53e4e9881c0e5dbbea562bf09aeb85da6926ba7
- H2 probe: artifacts/fable-doubt146b-20260922/doubt146b-cases.json (24
  dialogues: H01-H10 hearsay/quoted contradictions incl. trailing said,
  according-to, read-online, told-me, heard, brother-says, apparently,
  leading Ann-said, quoted; H11-H14 first-person refusals; H15-H16 mixed
  orders; H17-H18 re-teach clears; H19-H20 restarts; H21-H22 plain/opinion
  controls; H23 double hearsay; H24 unrelated-subject hearsay),
  sha256 SEALED-BELOW
- loop146c config artifacts/fable-doubt146b-20260922/loop146c-config.json,
  sha256 SEALED-BELOW
- loop146d config artifacts/fable-doubt146b-20260922/loop146d-config.json,
  sha256 SEALED-BELOW
- Comparators (read-only): sealed 146 rows
  (artifacts/fable-doubt146-20260922/fable_bench146_loop146_*_rows.jsonl),
  sealed loop139b rows (artifacts/fable-fix139b-20260922/), sealed
  loop129b marks123 reference
  (artifacts/fable-fix140-20260922/marks123-129b).

## Marks (integer counts, every seed/case reported, never averaged)

- H1: 146 D3 probe re-run on 146c
  (scripts/fable_doubt146b_probe.py --run-h1): every dialogue as in 146
  except B07 (predicted: B07 step 0 keeps the known expectation error --
  an opinion correctly clarifies instead of Saving; steps 1-2 pass).
  Predicted: 31/32 pass, the single failure is B07 step 0 only; 0 stale
  confident answers, 0 lost answers on no-doubt dialogues.
- H2: new probe (scripts/fable_doubt146b_probe.py --run-h2, 24 sealed
  dialogues on 146c): 24/24 pass. Hearsay/quoted contradictions get a
  clarify reply, the standing taught answer is still given, 0 doubts
  recorded (expect_doubts 0); first-person refused corrections doubt +
  abstain (expect_doubts 1); mixed orders (H15 refusal wins after
  hearsay; H16 doubt stands through later hearsay); re-teach/repeat
  clears (expect_doubts 0); restarts preserve. 0 stale, 0 lost.
- H3: marks123 (scripts/fable_marks123_all.py --agent
  scripts/fable_loop146c_agent.py --config
  artifacts/fable-doubt146b-20260922/loop146c-config.json --out
  <this-dir>/marks146c) per-case verdicts identical to the loop129b
  reference on every suite (p2, p3, p4, rt110, q1, bench, rt81, sleep,
  soak, q4). In particular p2 A2/A6/A8 and rt110 T4 match loop129b (the
  146 hearsay-veto moves are gone).
- H4a: bench121 new/old, Fable-Edit-200, bench132 per-item on 146c
  (scripts/fable_doubt146b_bench.py --agent loop146c) identical to 146's
  sealed rows: 0 verdict moves on all four splits.
- H4b: bench121 new/old + Fable-Edit-200 on 146d
  (scripts/fable_doubt146b_bench.py --agent loop146d) vs sealed loop139b
  rows: 0 new wrong, 0 correct lost, exactly one predicted move (new_121
  069 wrong->abstain).
- H5: each registered run < 25 min (< 1500 s) wall-clock Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
  --no-project --python 3.12 --with torch --with numpy python -B ...);
  daemon wrappers take --idle-seconds (Loop146cDaemon/Loop146dDaemon set
  idle_seconds).

## Pre-seal evidence (dev only, NOT registered runs; the new loops never ran)

- Pure-function checks: all 22 first-person refuse turns of the sealed
  146 probe parse (detect_teach146) and are NOT exempt (0/22 fire
  is_hearsay_exempt146b); all 4 D4 hearsay turns (p2 A2/A6/A8 trailing
  ", Tom said." / "according to the web." / "I read online.") fire
  L102.is_hearsay (exempt under 146b).
- Pre-seal BASE loop129b evidence runs
  (scripts/scratchpad/doubt146b-evidence/, base loop only): every H2
  hearsay/quoted candidate gets a clarify (hearsay-path "did you hear it
  somewhere" for trailing/leading-quote/is_hearsay shapes, generic
  "another way" for told-me/brother-says/leading-Ann-said) with 0 wrong
  writes; the standing answer is given afterwards; refusal-then-hearsay
  keeps the split-clarify then hearsay-clarify order.
- Static suite scan (inherited from 146, mechanism unchanged apart from
  strictly fewer recordings): exemption can only remove doubt
  recordings, never add replies; bench teaches contain no
  reported-speech markers.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

Reproduce (each AFTER seal; ledger P146b.x appended BEFORE these ran):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_doubt146b_probe.py --run-h1   # H1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_doubt146b_probe.py --run-h2   # H2
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_doubt146b_bench.py --agent loop146c   # H4a
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_doubt146b_bench.py --agent loop146d   # H4b
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop146c_agent.py --config artifacts/fable-doubt146b-20260922/loop146c-config.json --out artifacts/fable-doubt146b-20260922/marks146c   # H3
