# Exp 144 PASSMARKS (sealed BEFORE the registered run — do not edit after)

One change: loop129b + the exp-144 single-"of"-name mixin. A SPLIT clarify
becomes the structured teach/correct only when the turn parses as ONE teach
(bench73 first, else exp-92 extra patterns) whose value is a single
capitalised "of"-name span with no embedded complete teach frame; every
other screen and every other turn is byte-identical to loop129b.
Base loop: loop129b.

Step 1 diagnosis: the "split that" reply is scripts/fable_earsguard91.py:34
(SPLIT_MSG) via screen_value() at fable_earsguard91.py:53-60. The value
"The Protocols of the Elders of Zion" is 7 words > MAX_VALUE_WORDS = 6
(fable_earsguard91.py:45, check at :58); loop121's Title-Case exemption
(fable_loop121_agent.py:78-99, applied at :117-120) needs "and", so the
pure-"of" name refuses there and again at fable_earsguard91.py:58. No
"of"-counter exists anywhere; one-"of" probes pass only because they are
short (5 words).

## Sealed case files (sha256)

- f1-cases.json (46 NEW probe turns, written before any run: 26 must-write
  teaches with 2+ "of" phrases across 7 relation frames + 20 genuine
  two-fact messages):
  7a8ef0f756b1d9a55a6aeac3258aa21fdff1fce27adfa35c1d2d85685a635719
- loop144-config.json (loop129b config + 2 renamed plug strings):
  d70edbdb9d1a5d6f0525d7071666b485976d01db4d3c454ea675becc9d128534

## Marks

- F1 NEW probe (artifacts/fable-fix144-20260922/f1-cases.json): must-write
  >= 25/26 exact triples with 0 wrong writes; two-fact 20/20 with 0 writes
  of any wrong triple (refusing is fine).
- F2 bench: bench132-4hop-022 edit teach #6
  ("Charles M. Schulz is famous for The Protocols of the Elders of Zion")
  now saves (Charles M. Schulz, notable_work,
  The Protocols of the Elders of Zion) and the item moves wrong -> correct
  (Charleroi). edit200 + old_s2fresh_4hop per-item identical to the sealed
  loop129b rows; new_121_4hop per-item identical EXCEPT bench121-4hop-069
  (same edit teach shape; teach #6 now Saved, item moves wrong -> correct,
  Canberra). Predicted diffs (ledger P144.2/P144.3): exactly these two
  items; every other teach sentence in all four splits was scanned
  pre-seal (5863 turns) with zero other upgrade flags.
- F3 marks123 all suites per-case identical to the loop129b reference
  (artifacts/fable-fix140-20260922/marks123-129b): pre-seal scan of every
  suite input turn (redteam98/p4-30/redteam110/redteam81/bench splits;
  p3/soak/q1 use short synthetic tokens; sleep SKIP) found zero SPLIT
  replies on single-"of"-name teaches, so zero predicted moves (P144.4).
- F4 every registered run < 25 min wall-clock, Mac CPU,
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 (P144.5).

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix144_f1.py --out artifacts/fable-fix144-20260922
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix144_bench.py --run
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop144_agent.py --config artifacts/fable-fix144-20260922/loop144-config.json --out artifacts/fable-fix144-20260922/marks123 --workers 4
