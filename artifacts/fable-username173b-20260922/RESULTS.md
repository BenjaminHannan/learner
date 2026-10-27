# Exp 173b RESULTS (plain words for Ben) — SCORE: T1/T1b/T1c/T2/G1/G2/G3/G4 PASS (2 deviations disclosed)

The idea: last time, the assistant learned names like Sam but said "I
didn't understand that" to Maya, Rose, Grace, Rue, Sol, and Pip — because
those are also ordinary English words and the old rule rejected any name
that appears in the dictionary. This run keeps everything else identical
and only relaxes that one test: after "My name is" / "Call me" (the
sentence itself says it is a name), a word like Maya or Rose now counts as
a name. Safety nets stay: a sealed list of 37 non-names ("not important",
"a secret", "later", "back", "whatever"…) still clarifies, "Call me"
needs a capital letter (so "Call me later" works exactly as before), and
after "I'm" / "I am" the old careful rule stays, except real first names
from the proper-names list (Grace, Grant, Mark, Will, Rich) now work
there too.

## Marks table (integer counts)

| check | bar | got |
|---|---|---|
| T1 sealed 166 probe (52 rows) vs loop173 | 52/52 byte-identical | 52/52 PASS (1.1 s) |
| T1b 173's sealed probe (45 rows) vs loop173 | 44 identical + 1 listed | 44 OK + S13 LISTED-DIFF PASS (0.9 s) |
| T1c new 42-dialogue probe | 42/42 OK | 42/42 PASS (0.9 s) |
| T1c word-names W01-W16 (save + answer) | 16/16 | 16/16 PASS |
| T1c closed/look-alikes C01-C14 (0 writes + identical) | 14/14 | 14/14 PASS |
| T1c I'm-propernames I01-I06 (name set) | 6/6 | 6/6 PASS |
| T1c other O01-O06 (identical) | 6/6 | 6/6 PASS |
| T2 wrong writes (139 rows) / non-USER entities | 0 / 0 | 0 / 0 PASS |
| G1 bench 600/600 vs frozen loop173 rows | 0 moves, 0 new wrong | 0 moves PASS (15.0 s) |
| G2 marks123 per-case vs marks173 | predicted-only | PASS w/ race (165.6 s) |
| G3 redteam136 (145) + redteam143 (124) + sessions152 (180 turns) | 0 moves | 0 moves PASS (4.1 s) |
| G4 every run < 1500 s Mac CPU | < 1500 s | max 168.1 s PASS |

Suite detail: p2/p4/q1/bench/rt81/sleep/soak/p3/q4 per-case 0 moves;
p3-L2 0 moves; q1 F5+M5 FAILs, p3-L2 FAIL, p2/rt81/q4 FAILs all
byte-identical inherited base behaviour. rt110: registered run moved R1,
open re-run moved R1+T5 — always exactly the `log.statuses` field
(the daemon appends the log after the reply, so under load the read lands
early), verdicts/replies/writes equal everywhere. Summary WHOLE-DIFF is
only the predicted sleep-SKIP row naming the new agent file (truncation
shifts by the 1-char name-length difference; sleep-report.json identical).

## What it means

"My name is Maya." / "Call me Pip." / "My name is Grace." now save and
answer ("Your name is Maya."), "I'm Grace." / "I am Grant." name too —
while all 600 bench items, all marks123 suites, and all 449 G3 turns move
nowhere in verdicts, replies, or writes.

## What it does not mean

It does not mean anything goes: "My name is not important.", "Call me
later", "call me back", "I'm tired", "I am from Oslo", "Call me Whatever"
still clarify exactly as loop173 does; and "I'm Maya." (bare "I'm" +
dictionary word missing from propernames) still does not name — accepted
known miss, listed before the run.

## Deviations (two, both reported, sealed files untouched, seal 3/3 OK)

- D1 (pre-seal dev slip): one `--once` smoke turn ("My name is Maya.")
  ran with the default state dir and appended 3 events (USER name=Maya,
  n=28-30) plus the fix77 seal rewrite to the repo-root notebook/.
  No registered run touches the root notebook (all use temp/scratch
  dirs), so no mark is affected; never repeated (all later smokes used
  temp dirs).
- D2 (rt110 mailbox/log race, both runs reported): registered moved R1,
  open re-run moved R1+T5, always exactly `log.statuses`, verdicts equal,
  replies equal, writes equal, 0 new WRONG. Same mechanism as 173's D2;
  measurement noise, not behaviour; no further re-runs.

## Questions for Ben

None.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_probe.py --which t1 --out artifacts/fable-username173b-20260922/probe173b-t1.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_probe.py --which t1b --out artifacts/fable-username173b-20260922/probe173b-t1b.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_probe.py --which t1c --out artifacts/fable-username173b-20260922/probe173b-t1c.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_g3.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop173b_agent.py --config artifacts/fable-username173b-20260922/loop173b-config.json --out artifacts/fable-username173b-20260922/marks173b --workers 2
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix173b_marksdiff.py
