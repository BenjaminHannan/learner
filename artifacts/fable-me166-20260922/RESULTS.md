# Exp 166 RESULTS (plain words for Ben) — SCORE: T1/T2/G1/G2/G4 PASS, G3 FAIL (diagnosed)

The idea: the assistant had no idea who "me" is -- "My mom is Rita" got "I
didn't understand that." This run adds one reserved notebook page for the
user, so "my ... " teaches and questions land there: "My mom is Rita."
saves, "Who is my mom?" answers "Your mother is Rita.", and "Where is my
mom's city?" chains through normally. Questions about the assistant itself
("What is your name?") and everything else work exactly as before.

## Marks table (integer counts)

| check | bar | got |
|---|---|---|
| T1 probe (52: 25 first-person, 27 identical-to-base) | 52/52 OK | 52/52 PASS (2.0 s) |
| T1 first-person (8 relations, synonyms, 3 two-hop, 3 corrections) | 25/25 exact | 25/25 PASS |
| T1 identical to loop162b (10 agent-itself + 17 other) | 27/27 | 27/27 PASS |
| T1 raw USER key in any reply (except literal-USER control O13) | 0 | 0 PASS |
| T2 wrong writes (52 rows) | 0 | 0 PASS |
| G1 bench 600/600 vs frozen loop162b rows | 0 moves, 0 new wrong | 0 moves PASS (51.8 s) |
| G2 marks123 per-case vs marks162b/marks150 | only predicted moves | predicted-only PASS (187.5 s) |
| G3 redteam136 (145) + redteam143 (124) + sessions152 (180 turns) | predicted-only, 0 new WRONG | 3 unpredicted reply-case moves -> FAIL (19.3 s) |
| G4 every run < 1500 s Mac CPU | < 1500 s | max 187.5 s PASS |

Suite detail: rt81 74 cases: exactly the 2 predicted O_user moves
(O_user-02 UNCLEAR->UNCLEAR `I don't know your mother yet.`, O_user-03
UNCLEAR->BUG `Saved: your city is Lisbon.`, +entity USER), other 72/74
identical; p3 L2 pass True->False with changed=+O_user-02/+O_user-03 and
wrong=[O_user-03] exactly as predicted, L1/L3/L4/L5/L6 identical; p2 64/64
and q1 F5+M5 FAILs byte-identical to base (seconds only differ); bench
tables identical (seconds only); soak 2000 turns 0 lost/0 wrong/0 doubled
clean, no open re-run needed; sleep SKIP, reason names the new agent file
only; q4 leaks identical to marks150; rt110 first run 1 log-only move (R5
msg_02 empty-read race, verdicts 62/62 equal), open re-run 0 moves --
both reported, no further re-runs.

## The G3 FAIL (one diagnosis note, recorded as FAIL, no re-run)

Predicted the S4-pets-identity/1 write (`my dog is biscuit` UNHELPFUL->OK,
`Saved: your dog is biscuit.`) but not its cosmetic cascade: the value is
stored with the display case as typed (`biscuit`), so turns 2, 3 and 26 of
the same session render `biscuit's ...` where the base renders `Biscuit's
...`. Verdicts on all three stay OK, fact-writes equal, 0 new WRONG
anywhere in G3. Cause: entity display-case carryover from the new correct
write, invisible to the pre-seal pure-function scan (which sees turns, not
stored displays). Fix for a follow-up, not this run: none -- sealed code
was left untouched and the FAIL stands.

## What it means

First-person teaches/asks/corrections/two-hop questions work across 8
relations with exact stored triples and natural `your/Your` replies, while
600 bench items, all marks123 suites, and 449 G3 turns move only where
predicted in writing (plus 3 cosmetic reply-case words in one session).

## What it does not mean

It does not mean every "my ..." sentence is understood -- office heads
(`My manager ...`), chained teaches (`My mom's city is X`), and multi-word
relations stay on the old path on purpose; and a literal input of `USER's
...` still shows the raw key exactly as the base does.

## Deviations (two, both reported)

- Pre-seal dev trial of the sealed probe to scratch (/tmp/me166_trial.json,
  52/52 OK) -- NOT a registered run; the registered probe ran after the
  seal. No sealed file changed after `shasum -c` (12/12 OK at report time).
- rt110 open re-run (suite only, separate out dir) for the known mailbox
  race: first run 1 log-only move, re-run 0 moves; both reported per the
  brief. Soak was clean first try, so no open re-run there.

## Questions for Ben

None.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166_probe.py --out artifacts/fable-me166-20260922/probe166-loop166.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop166_agent.py --config artifacts/fable-me166-20260922/loop166-config.json --out artifacts/fable-me166-20260922/marks166 --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix166_marksdiff.py
