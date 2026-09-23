# Exp 146 PASSMARKS — refused-correction doubt (sealed BEFORE any registered run)

THE ONE CHANGE (scripts/fable_doubt146_store.py, new file; thin wrappers
scripts/fable_loop146_agent.py = loop129b + doubt, scripts/fable_loop146b_agent.py
= loop139 + doubt; no existing file edited): when a teach message is refused
or answered with a clarify reply AND names a notebook-known subject (resolve
OK/AMBIGUOUS) AND a relation cue is identified by the existing parsers only
(B73.hear_teach_template, B92.hear_teach92, FakeEars teach/correct; chit-chat
/ opinions / small talk never parse, never doubt), record a DOUBT on
(subject, relation). While it stands, a question whose answer walk uses that
(subject, relation) abstains: "You told me something new about S's R that I
could not store. I can take one fact at a time — could you say it again as
one fact?" (contains the scorer abstain phrase, no underscore). A walk that
stops at a doubted subject also abstains when the doubted relation is
question-mentioned (existing cue lists) or the question mentions relations
beyond the walked frame (truncation IS the refusal gap; covers paraphrases
like "calls home"). A later successful teach of the same (subject, relation)
(Saved: new value, or "I already have that." repeat) clears it. Stored
notebook-side (doubts146.json, atomic write, reloaded per build, survives
restarts), never weights, never edits/deletes old facts.

Sealed inputs:
- D3 probe: artifacts/fable-doubt146-20260922/doubt146-cases.json (32
  dialogues: A01-A08 refused->abstain; B01-B08 no-doubt small talk; C01-C04
  re-teach/unrelated; D01-D03 repeat-old; E01-E04 restart; F01-F03
  relation-specificity; G01-G02 loop146b negation),
  sha256 d55ab5e05c518d1f809ce668e53e4e9881c0e5dbbea562bf09aeb85da6926ba7
- loop146 config artifacts/fable-doubt146-20260922/loop146-config.json,
  sha256 4009cb46636db55571b4bc41c838df5ddd39adc22d9e9f900ba051b5eb977d32
- loop146b config artifacts/fable-doubt146-20260922/loop146b-config.json,
  sha256 363fa57ea2b326513356f032d063f166f76ebfb2095d54ea87a5b692e16d3e9c
- Comparators (read-only): sealed loop139 rows (artifacts/fable-fix139-20260922),
  sealed loop129b rows (artifacts/fable-fix129-20260922), sealed loop121
  bench132 rows (artifacts/fable-bench132-20260922), marks123-129b reference
  (artifacts/fable-fix140-20260922/marks123-129b).

## Marks (integer counts, every seed/case reported, never averaged)

- D1: loop146b over edit200 + old_s2fresh + new_121 (600 items): the 11
  items 139 flipped correct->wrong (new_121 019 047 136 139 142 195 196;
  old_s2fresh 056 103 124 196) are no longer wrong (abstain or correct),
  and 0 other per-item verdicts are worse vs sealed loop139 rows.
- D2: loop146 over edit200 + old_s2fresh + new_121 + bench132 split
  (800 items): 0 new wrong and 0 correct lost vs sealed loop129b rows
  (bench132 vs sealed loop121 rows, verdict-identical to loop129b per
  pre-seal evidence) except items predicted in writing before the run
  (P146.2: new_121 069 wrong->abstain; bench132 022 wrong->abstain); case
  022 no longer wrong.
- D3: probe (scripts/fable_doubt146_probe.py --run, 32 sealed dialogues):
  refused corrections of known facts -> abstain (never the old value);
  chit-chat/opinions/small talk mentioning a known person -> no doubt,
  questions answered; doubt + clean re-teach -> new value; doubt + repeat
  old -> old value; restart mid-dialogue -> doubt persists. 0 stale
  confident answers, 0 lost answers on no-doubt dialogues; 32/32 pass.
- D4: marks123 (scripts/fable_marks123_all.py --agent
  scripts/fable_loop146_agent.py --config
  artifacts/fable-doubt146-20260922/loop146-config.json --out
  <this-dir>/marks146) per-case identical to the loop129b reference on
  every suite (p2, p3, p4, rt110, q1, bench, rt81, sleep, soak, q4).
- D5: each registered run < 25 min (< 1500 s) wall-clock Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrapper
  takes --idle-seconds (Loop146Daemon/Loop146bDaemon set idle_seconds).

## Pre-seal evidence (dev only, NOT registered runs; the new loops never ran)

- Pure-function checks: 022 + GB&I teaches parse (B73/B92) with (subject,
  relation); 022 value refused by screen_value_121, GB&I value refused by
  the 139 screen; all 8 chit-chat shapes parse to None; all 5 refusal
  shapes refused by the 121 screen.
- Offline walk analysis over sealed 139 rows + sealed items: 10/11 D1 items
  fire via traversal-or-mentioned-sink, 142/11 via wants-more (paraphrase
  "calls home"); 025/073/149/069 cannot get worse (wrong/abstain only).
- Pre-seal base loop129b evidence run on bench132 (scripts/scratchpad/
  doubt146-evidence/, same harness): 139 correct / 59 abstain / 2 wrong;
  rejects only on 022 (SPLIT, known subject, on-path), 105 (CONFLICT, no
  doubt), 162 (CONFLICT on founded_by: no doubt; SPLIT on (Elizabeth II,
  spouse): doubt recorded but the asked walk never visits Elizabeth II); per-item
  verdicts identical to sealed loop121 rows. Sealed 129b rows: only reject
  item on new/old/edit200 is 069 (wrong; on-path like 022).
- Static suite scan (pure parsers + pure screens, no loop runs): 0
  refused-known-teach-followed-by-question dialogues in p2 (64), rt110
  (62), rt81 (17 seqs), p4 (30); 0 refusal-shape literals in p3 runners;
  q1/soak flows contain no refusals by construction; sealed 129b bench
  splits contain 0 teach rejects; doubt reply has no underscore (q4).

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence.

Reproduce (each AFTER seal; ledger P146.x appended BEFORE these ran):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_doubt146_probe.py --run   # D3
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_doubt146_bench.py --agent loop146b   # D1
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_doubt146_bench.py --agent loop146    # D2
  uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop146_agent.py --config artifacts/fable-doubt146-20260922/loop146-config.json --out artifacts/fable-doubt146-20260922/marks146   # D4
