# Exp 156b RESULTS — small-talk classes on loop150 (Muse). REGISTERED: T1/T2/G1/G3/G4 PASS, G2 FAIL (mailbox race, see diagnosis).

Target: loop156b = loop150 + Smalltalk156bMixin
(scripts/fable_fix156b_smalltalk.py; wrapper
scripts/fable_loop156b_agent.py; config
artifacts/fable-smalltalk156b-20260922/loop156b-config.json). THE ONE
CHANGE: 156's exact-word list is replaced by a closed rule-based
classifier -- six lexicons from general English chat (greeting with
time-of-day forms; thanks with spelling variants + "so much"/"a lot"
tails; laugh/reaction incl. emoji-only; ack incl. "got it"; bye incl.
goodnight/gn/see-you/later/ttyl; apology/hesitation), normalisation
(repeated letters, phrase glue, punctuation/emoji split). It fires only
when the notebook path returns exactly the generic fallthrough AND the
whole message is small talk; any content word leaves the reply
untouched. Laughter gets "Haha, nice!", apologies get "No worries!".
The mixin wraps loop150 directly (156's stage would shadow the new
classes). Clarify acts never write (fable_agent_loop.py:337-339).

## Marks table (integer counts, every case reported, never averaged)

| mark | bar (PASSMARKS.md, sealed) | got | verdict |
|---|---|---|---|
| T1 116-case probe through loop156b | 84 exact class replies 0 writes; 32 near-misses identical to loop150 | 116/116 OK (14x6 classes exact, 0 writes; 32/32 reply+triples identical) | PASS |
| T2 156's 68 cases through loop156b | 59 identical; only 9 listed changes | 68/68 OK (8 laugh rows -> "Haha, nice!", N20 "thanks a lot" -> thanks; rest identical, 0 writes) | PASS |
| G1 bench per-item + replies | identical to loop150 rows, 0 moves | 600/600 verdict-identical, reply_moves 0 (edit200 150/50/0; old 157/43/0; new 136/63/1) | PASS |
| G2 marks123 per-case | identical to marks156, 0 moves | all suites identical EXCEPT rt110 R6/D8 OK->BUG (mailbox race, see below); p2/q1/rt81/q4 FAIL labels pre-existing byte-identical | FAIL |
| G3 152 sessions through loop156b | exactly the 23 sealed small-talk turns change; 157 identical; 0 new WRONG/writes | 23/23 class replies (laugh -> "Haha, nice!"); 157/157 byte-identical; write_moves 0; new_wrong 0 | PASS |
| G4 each run < 1500 s Mac CPU | < 1500 s | T1 4.9 s, T2 4.5 s, bench 128.8 s, marks 326.8 s, sessions 2.4 s | PASS |

S4's 2 WRONG turns are pre-existing on the T-T run (new_wrong empty).

## Diagnosis note (the one G2 failure)

R6/D8 flipped only because the daemon read an EMPTY inbox file:
daemon.log.jsonl records `turn_text: ''` with reply "I didn't catch
anything." on both msg_00s (a mid-write read race under parallel load;
suite rt110 spawns real daemon subprocesses while 3 other suites ran
concurrently). The classifier returns None on empty input by
construction, so it left the base reply untouched. Direct replay of the
exact R6/D8 sequences gives byte-identical loop156b == loop150 output
("Saved: ...", answers contain "Lisbon") -- the sealed-OK behaviour.
Agent behaviour is proven identical; the measurement was transport
noise. FAIL stays FAIL; no re-run. (Precedent: exp 158's soak race.)

## What it means

"Good morning", "thanx", "thanks a lot", "goodnight", "see you",
"wow", emoji-only texts, "got it" and "sorry" now get short sensible
replies instead of "I didn't understand that", laughter no longer gets
"Got it!", and chatter still writes nothing; every teach/ask path is
otherwise byte-identical across benches, suites and phone sessions.

## What it does not mean

It does not understand feelings or remember greetings; "who are you",
pronouns, fillers and bare corrections are other experiments' jobs and
behave exactly as before.

## Deviations

None after the seal (seal check passes; ledger P156b.1-6 appended
before any registered run). Pre-seal: K14 "yes" -> "yep" (the base
answers "yes" on the answer path, so it can never be a fallthrough
fire); the 156b stage wraps loop150, not loop156 (documented stacking
note -- 156's replies would shadow the new classes).

## Questions for Ben

None. Default kept: "who are you" stays confusing until the identity
experiment lands.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156b_probe.py --out artifacts/fable-smalltalk156b-20260922/probe156b-loop156b.json  # 4.9 s
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156b_probe156.py --out artifacts/fable-smalltalk156b-20260922/probe156b-cases156.json  # 4.5 s
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156b_bench.py  # 128.8 s
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop156b_agent.py --config artifacts/fable-smalltalk156b-20260922/loop156b-config.json --out artifacts/fable-smalltalk156b-20260922/marks156b --workers 4  # 326.8 s
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix156b_session.py  # 2.4 s
Seal check: shasum -c artifacts/fable-smalltalk156b-20260922/SEAL.sha256.txt
