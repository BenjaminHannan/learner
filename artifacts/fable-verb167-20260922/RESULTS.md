# Exp 167 RESULTS (plain words for Ben) — SCORE: PASS

The idea: sentences like "Kwame lives in Accra." got "I didn't understand
that," while "Kwame's city is Accra." saved fine. Now the verb forms save
the exact same fact as the possessive forms: lives in → city, works for →
employer, was born in → place of birth. "Is married to" already saved, so
it was left alone. No's, tense changes ("used to live", "will move"),
hedges ("I think…"), and what-ifs still save nothing.

## Marks table (integer counts)

| check | bar | got |
|---|---|---|
| T1 probe (61: 20 mapped + 18 nowrite + 20 other + 3 chains) | 61/61 OK | 61/61 PASS (2.3 s, open re-run; first registered run 60/61 FAIL, see deviations) |
| T1 mapped: verb teach = possessive-twin triple, verb-Q + possessive-Q answer | 20/20 | 20/20 PASS |
| T1 nowrite (6 negations, 6 tense, 6 hedges) | 18/18, 0 writes | 18/18 PASS |
| T1 other byte-identical to loop162b | 20/20 | 20/20 PASS |
| T2 wrong writes (61 rows) | 0 | 0 PASS |
| G1 bench 600/600 vs frozen loop162b rows | 0 moves, 0 new wrong | 0 moves PASS (46.1 s) |
| G2 marks123 per-case vs marks162b | identical except predicted | predicted-only PASS (190.5 s) |
| G3 redteam136 (145) + redteam143 (124) + sessions152 (180 turns) | 0 moves, 0 new wrong | 0 moves PASS (17.2 s) |
| G4 every run < 1500 s Mac CPU | < 1500 s | max 190.5 s PASS |

G2 detail: p2 64/64, p4 30/30, p3 L1-L6 PASS, q1/bench/rt81/soak/q4
byte-identical (suite-level FAILs on p2/q1/rt81/q4 match base exactly, as
in 162b); sleep SKIP identical, reason names loop167; rt110 P1+P3 move
exactly as predicted (verb fact now saves + answers; ruling overrides
their stale "store nothing" checks), other 60 rows identical; summary
deltas only rt110 0→2 OK->BUG + sleep naming + timings.

## What it means

Verb facts now teach, answer both question forms, and chain through hops
(C2/C3 end at verb-taught facts), with movement confined to the two
predicted rt110 cases: 600/600 bench, 449 G3 turns, and every other marks
suite move-free.

## What it does not mean

It does not mean every phrasing works -- "Who is X married to?",
multi-word names, "moved to", and yes/no verb questions still clarify
(future work below); employer/city values can't be hopped through
(non-person mids), so chains only cross person-valued middles.

## Deviations (all reported; sealed files otherwise shasum-clean)

- Registered probe run 1: 60/61 FAIL -- diagnosis: MY case bug, O03 set
  expect-nowrite on "The president of Zorvia is Mel Ash." which the base
  office path writes (identical_to_base half passed). Post-seal case fix
  (O03 expects the officeholder triple; old/new hashes below), probe
  re-ran in the open: 61/61.
- Post-seal driver amendment (scripts/fable_fix167_marksdiff.py): first
  G2 FAIL had 3 unpredicted rt110 row diffs -- diagnosis: harness metadata
  only (log `statuses` [] vs ["OK"]/["write"], replies+verdicts+writes
  equal; L2 was the known mailbox race, cleared on re-run). Sanctioned
  open rt110 re-run (both reports kept: rt110-report.first-run.json +
  rerun dir) shows statuses differ on different rows run-to-run with equal
  replies/verdicts/writes, so the driver now normalises `statuses` and
  asserts the summary deltas; diff re-ran in the open: G2 PASS.
- Seal deltas: cases167.json 532c175a…→4598688e…; marksdiff
  b1a8d0cf…→77d25c4a… (full hashes in SEAL.sha256.txt + this note).
- Dev pollution (mine): early base probes appended Kwame facts F00007-09
  to the shared root notebook/events.jsonl (append-only, chain-valid).
  All registered runs use isolated temp state dirs. Left in place +
  disclosed (truncating would break the hash chain).

## Questions for Ben

1. rt110 P1/P3 now "fail" their old checks (verb facts save by design).
   Keep the ruling (update those two cases) or keep the old checks?
2. "Who is X married to?" needs wife~=spouse synonymy to answer -- want
   that next, or leave clarifying?

## Future work (verbs with no existing relation / out of scope)

"The Guardian lives in…", "moved to", "likes", "works at", "was married",
"will marry", yes/no verb questions, pronoun subjects (kept clarifying by
the 150c veto: rt110 P4 proves it).

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167_probe.py --out artifacts/fable-verb167-20260922/probe167-loop167.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop167_agent.py --config artifacts/fable-verb167-20260922/loop167-config.json --out artifacts/fable-verb167-20260922/marks167 --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix167_marksdiff.py
