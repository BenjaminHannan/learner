# Exp 227c RESULTS — wider identity matching (built on 227b)

**Verdict: PASS** (M1-M5 all pass; seal 7/7 OK after the runs; 227b seal 5/5 still OK; no post-seal edits).

One change on loop227b: when the 227 exact-template gate misses, a widened
whole-sentence matcher (scripts/claude_identity227c.py) handles contractions,
a missing "?", filler words at the start/end, casual synonyms, and two new
intents: NAMECHECK ("Is your name X?" -> "No, my name is Premonition." /
"Yes, ..." when X is Premonition) and RENAME ("Your name is X.", "I'll call
you X." -> "My name is Premonition."). Reply-only; the gate sits inside the
notebook-miss branch, so notebook answers still win. Agent:
scripts/claude_loop227c_agent.py.

## Marks table

| mark | result |
|---|---|
| M1 fresh identity turns (75) | 75/75 — NAME 13/13, MAKER 10/10, WHAT 13/13, LEARN 8/8, AGE 7/7, HOME 7/7, NAMECHECK 8/8, RENAME 9/9; 0 writes on every identity and follow-up turn; the 6 follow-up sessions keep user name vs Premonition apart; Premonition never stored — PASS |
| M2 user-name near-misses (36 texts x untaught/taught = 72) | 72/72 byte-identical to 227b (replies + notebook) — PASS |
| M3 227b's own sessions (36 + 32 + 7 = 75) | 75/75 byte-identical to 227b — PASS |
| M4 frozen suites (fable_suitediff218) | rt136 0, rt143 0 (vs 138i); sessions152 0, bench 0 (4 x 200), marks123 0 (vs 227b rows); GATE clean — PASS |
| M5 sleep smoke (seed 1) | sleeps=1 installed=1 episodes=20 probes=5/5 wrong=0 broken=abstain taught=50/50 ow=0 — PASS |

Verifier's sentences (pilots only, not in the registered set), on 227c:
"What's your name?" -> "My name is Premonition."; after "My name is
Corvina.", "Is your name Corvina?" -> "No, my name is Premonition.";
"what should I call you" -> Premonition; "Who made you, anyway?" -> "Ben
built me."; "Are you a real person?" / "Are you a bot?" / "What are you
exactly?" -> the WHAT sheet line; "How do you learn stuff?" -> the LEARN
line; "Your name is Pip." -> "My name is Premonition.", 0 writes.

Moves: only the targeted identity turns. No frozen-suite moves.
Slowest run: sleep smoke 94 s.

## Deviations
- rt136/rt143 compared against 138i rows (the 218 lookup finds no
  redteam136/143 rows file in 227b's folder; 227b == 138i there). Declared
  before the run.
- The dev cases were written by me after writing the sentence list, so the
  75/75 shows these forms are covered, not that unseen phrasings will be.

## Still wrong (left alone on purpose, reported for the director)
- "Got a name?" has no "you"/"your", so it is not treated as an identity
  question and still gets the user-name denial.
- After "My name is Corvina.", "Is my name Corvina?" still says "You never
  told me your name, so I do not know it." — a false denial about the USER.
  The brief said user-name questions must stay exactly as today, and 227b
  descends from 138i, not 219, so 219's fix is not in this line.

## What it means
The assistant now recognises many more everyday ways of asking about itself
("What's your name?", "who made you, anyway", "are you a bot?"). If someone
tries to give it a different name, it politely keeps its own name and saves
nothing. Questions about the user's own name behave exactly as before.

## What it doesn't mean
It does not understand questions in general. It matches a fixed list of
sentences after some tidying up, so a phrasing that isn't on the list (like
"Got a name?") still slips through. Its name is a fixed line, not something
it learned.

## Reproduce
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; R="uv run --offline --no-project --python 3.12 --with torch --with numpy python -B"
$R scripts/claude_identity227c_marks.py --m1 ; --m2 ; --m3
$R scripts/fable_suitediff218.py --agent scripts/claude_loop227c_agent.py --config artifacts/claude-identity227c-20260922/loop227c-config.json --base 138i --out <dir> --only rt136,rt143
$R scripts/fable_suitediff218.py --agent scripts/claude_loop227c_agent.py --config artifacts/claude-identity227c-20260922/loop227c-config.json --base-dir artifacts/claude-name227b-20260922 --out <dir> --only sessions152,bench,marks123
$R scripts/fable_sleepsmoke206.py --agent scripts/claude_loop227c_agent.py --config artifacts/claude-identity227c-20260922/loop227c-config.json --root <dir> --report <f> --label s1-227c --seed 1 --idle-seconds 30.0
