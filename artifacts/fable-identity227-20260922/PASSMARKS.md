# Exp 227 pass marks — QUESTIONS ABOUT THE ASSISTANT GET AN ANSWER ABOUT THE ASSISTANT (sealed before the run)

One change on loop138i: a fixed identity sheet (scripts/fable_identity227.py,
plain software like the capability sheet) served by scripts/fable_loop227_agent.py
(subclass; 138i and all earlier pieces unwrapped-read-only, never edited).
A "?" turn is served the sheet answer only when it contains a second-person
word (you, your, yours, yourself) AND exactly matches a normalised template
in scripts/fable_identity227_templates.json (38 templates, exact match, not
keywords). The gate sits inside the notebook-miss branch, so notebook answers
always win; it never writes (reply-only). User-about first-person questions
("What is my name?", "Do you remember my name?", "Do you know my name?") are
not templates, so they keep today's route exactly (exp 219's piece, not this).

Sheet (each literally true of this program): NAME "I don't have a name yet."
MAKER "Ben built me." WHAT "I'm a small program that keeps what you teach me
in a notebook and answers from it. When I don't know something, I say so
instead of guessing." LEARN "I learn when you tell me facts in plain
sentences, like "Kim lives in Oslo." I save each one and answer from my
notes." AGE "I don't have an age. I'm a program, so I don't measure my life
in years." HOME "I don't live anywhere. I'm a program that runs on a computer
and keeps a notebook file." AGE/HOME included because the Step-0 census (45
questions on 138i fresh notebook, census138i-rows.json) shows wrong/unrelated
replies for them: "What is your name?"/"Who made you?" get the D8 user-name
denial; WHAT/LEARN/HOME/AGE-how-old get unrelated DECLINE; "What is your
age?"/"birthday" get D9 (Mira's age).

Every seed/case reported, never averaged. Fictional names only. Isolated
scratch notebook dirs (never repo-root notebook/). Mac CPU, offline,
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B`.
Each run < 25 min, one suite at a time. A registered FAIL is recorded as FAIL,
never re-run into a pass. Any change to agent code, config, or case files
after the seal makes the verdict FAIL.

- M1: 36 identity cases (m1-cases.json, 6 per intent NAME/MAKER/WHAT/LEARN/
  AGE/HOME; 12 with "My name is <fictional>." taught first). PASS iff every
  reply equals the sheet answer for its intent and the question turn writes
  0 facts. Driver: `python -B scripts/fable_identity227_marks.py --m1`.
- M2: 32 user-name and other self questions (m2-cases.json: 16 texts x
  untaught/taught-first, incl. "What is my name?", "Do you remember my
  name?", "Do you know my name?"). PASS iff every reply + stored facts
  byte-identical to base loop138i. Driver: `--m2`.
- M3: `python -B scripts/fable_suitediff.py --agent scripts/fable_loop227_agent.py
  --config artifacts/fable-identity227-20260922/loop227-config.json --base 138i
  --out <dir> --only rt136,rt143,sessions152,bench` gives 0 moves
  (every moved case's detail line read, not only the summary).
- M4: `python -B scripts/fable_sleepsmoke206.py` on loop227 passes as on
  138i (sleeps>=1, installed, 5/5 probes right, 0 wrong, taught intact,
  0 overwrites, broken-chain abstains).
- M5: 0 new wrong writes anywhere (frozen suites redteam136, redteam143,
  sessions152, scripts/fable_marks123_all.py vs base; bench 0 new wrong).

Verdict PASS iff M1-M5 all pass; any miss is FAIL with one diagnosis note.
Pilots (pre-seal, final code): M1 36/36, M2 32/32 identical, suitediff
rt136/rt143/sessions152/bench/marks123 all 0 moves 0 new wrong/write,
sleep smoke 227 == 138i (sleeps=1 installed=1 probes=5/5 wrong=0
taught=50/50 ow=0 broken=abstain).
