# Exp 156 RESULTS — no-write small talk on loop150 (Muse). REGISTERED PASS.

Target: loop156 = loop150 + Smalltalk156Mixin
(scripts/fable_fix156_smalltalk.py; wrapper
scripts/fable_loop156_agent.py; config
artifacts/fable-smalltalk156-20260922/loop156-config.json). THE ONE
CHANGE: an outermost no-write small-talk stage. It runs the whole
loop150 chain first and only fires when the base returns exactly the
generic fallthrough (fable_loop90_agent.py:291) AND every word -- after
lower-casing and normalising punctuation, repeated letters ("hiii",
"thx!!") and emoji -- is in the sealed 39-token closed list. Then one
fixed short clarify reply per class (greeting with one teach + one ask
example; thanks; laugh/ack; bye). Clarify acts never write
(fable_agent_loop.py:337-339). Everything else returns untouched, so
small-talk+content ("hi, Tom's boss is Bob"), "who are you"/"what can
you do" (exp 127's), corrections, fillers and name traps are unchanged.

## Marks table (integer counts, every case reported, never averaged)

| mark | bar (PASSMARKS.md, sealed) | got | verdict |
|---|---|---|---|
| T1 68-case probe through loop156 | 44 exact class replies 0 writes; 24 near-misses identical to loop150 | 68/68 OK (11 greeting + 11 thanks + 12 ack + 10 bye exact; 24/24 reply+triples identical; 0 writes on all 44) | PASS |
| T2/G3 152 sessions through loop156 | exactly the 23 sealed small-talk turns change; 157 identical; 0 new WRONG/ writes | 23/23 class replies (verdict OK, 0 writes); 157/157 byte-identical replies; write_moves 0; new_wrong 0 | PASS |
| G1 bench per-item + replies | identical to loop150 rows, 0 moves | 600/600 verdict-identical, reply_moves 0 (edit200 150/50/0; old 157/43/0; new 136/63/1) | PASS |
| G2 marks123 per-case | identical to marks150, 0 moves | 10/10 suite reports + 400 bench rows verdict-identical; p2/q1/rt81/q4 FAIL labels pre-existing byte-identical | PASS |
| G4 each run < 1500 s Mac CPU | < 1500 s | probe 5.4 s, bench 64.1 s, marks 332.0 s, sessions 5.2 s | PASS |

S4's 2 WRONG turns ("Who is Ana's pet's color?", N9) were already WRONG
on the T-T run -- pre-existing, not new. Small-talk judges flipped
UNHELPFUL -> OK on exactly the 23 predicted turns (e.g. S1 now
27 OK / 3 UNHELPFUL).

## What it means

Saying hi, thanks, lol, ok or bye no longer dead-ends into "I didn't
understand that", and chatter still writes nothing to the notebook;
every teach/ask/clarify path is byte-identical to loop150 across
benches, suites and full phone sessions.

## What it does not mean

It does not understand feelings or remember greetings; "who are you",
pronouns, fillers and bare corrections are other experiments' jobs and
behave exactly as before.

## Deviations

1. Post-seal file-name fix (reported): the G1 bench runner was first
   written to scripts/fable_fix156_session.py by mistake (overwritten by
   the real session runner seconds later), then created at its sealed
   path scripts/fable_fix156_bench.py with the exact sealed logic. No
   agent/config/case file changed after the seal (seal check passes);
   G1 re-ran in the open with the corrected file.
2. G2 rt110 rows T1/T3 show `statuses: []` vs `['write']` on 2 sub-rows
   (replies, verdicts, fact_writes identical). Diagnosis: harness
   log-read race -- process_file writes outbox, moves to done, THEN
   appends daemon.log.jsonl (fable_loop102_agent.py:413-423), and the
   reader polls done+outbox. Final daemon logs contain the full records
   (0 empty msg_00 records across all case dirs); direct loop150 vs
   loop156 replay is identical. Telemetry only, 0 verdict moves.

## Questions for Ben

None. Default kept: "who are you" stays confusing until the identity
experiment lands.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156_probe.py --out artifacts/fable-smalltalk156-20260922/probe156-loop156.json  # 5.4 s
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156_bench.py  # 64.1 s
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop156_agent.py --config artifacts/fable-smalltalk156-20260922/loop156-config.json --out artifacts/fable-smalltalk156-20260922/marks156 --workers 4  # 332.0 s
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156_session.py  # 5.2 s
Seal check: shasum -c artifacts/fable-smalltalk156-20260922/SEAL.sha256.txt
