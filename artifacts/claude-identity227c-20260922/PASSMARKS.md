# Exp 227c pass marks — WIDER IDENTITY MATCHING (sealed before the registered runs)

Base: loop227b (scripts/claude_loop227b_agent.py, config
artifacts/claude-name227b-20260922/loop227b-config.json), wrapped read-only.
Verifier-found misses on 227/138i (used ONLY as pilots, not in the
registered sets): "What's your name?" and, after "My name is Corvina.",
"Is your name Corvina?" get the user-name denial; missing "?", "anyway"/
"exactly" tails and casual words (bot, real person, learn stuff) get the
long refusal; "Your name is Pip." gets the refusal.

One change (scripts/claude_identity227c.py + scripts/claude_loop227c_agent.py):
inside the notebook-miss branch, after the untouched 227 exact gate (with
227b's Premonition text), a widened whole-sentence matcher: normalise
(lowercase, curly quotes, drop commas and ending punctuation, strip leading
so/hey/ok/okay/well/oh/um/and/hi/hello and trailing anyway/anyways/exactly/
then/though/actually/again/please/really/by the way, expand what's who's
where's where're what're you're i'll i'm i'd how's when's whats whos), then
an explicit sentence list per sheet intent, plus NAMECHECK ("Is your name
X?", "Are you called/named X?", "Is X your name?" -> "No, my name is
Premonition." / "Yes, my name is Premonition." if X = Premonition) and
RENAME ("Your name is X.", "I'll call you X.", "Can I call you X?" ... ->
"My name is Premonition."). X must be one capitalised word. A second-person
word is still required. Reply-only, 0 writes. Notebook answers still win.

Mac CPU, offline, OMP/MKL=1, fresh temp notebook per session, fictional
names only, one suite at a time, `uptime` before each registered run, each
run < 25 min. Every case reported. Any change to a sealed file after the
seal = FAIL. Honest limit: the dev cases were written by the same author
who wrote the sentence list (after it), so they show the matcher covers
these forms, not that it generalises to unseen phrasing.

- M1 fresh identity turns (m1-cases.json, 75: NAME 13, MAKER 10, WHAT 13,
  LEARN 8, AGE 7, HOME 7, NAMECHECK 8, RENAME 9; 7 with a user name taught
  first; 6 with follow-ups "What is my name?" (must give the user's name)
  / "What is your name?" (must give Premonition)). `--m1`. PASS iff 75/75
  reply = sheet answer, 0 writes on identity and follow-up turns, teach
  turns identical to 227b, "Premonition" never stored.
- M2 user-name near-misses (m2-cases.json, 36 texts x untaught / after
  "My name is Hedda." = 72 runs; incl. "What's my name?", "Is my name
  Hedda?", "Do you know my name?", "Call me Hedda.", "Your friend is
  Hedda."). `--m2`. PASS iff 72/72 replies and notebooks byte-identical to
  227b.
- M3 227b's own cases (227 m1 36 + m2 32 + 227b Juno sessions 7 = 75
  sessions). `--m3`. PASS iff 75/75 byte-identical to 227b.
- M4 frozen suites (fable_suitediff218): sessions152, bench, marks123 vs
  --base-dir artifacts/claude-name227b-20260922; rt136, rt143 vs --base
  138i (227b == 138i there, 0 moves). PASS iff 0 moves, GATE clean.
  Predicted moves: none. Known flake rule applies.
- M5 sleep smoke (fable_sleepsmoke206, seed 1, idle 30): sleeps=1
  installed=1 probes=5/5 wrong=0 taught=50/50 ow=0 broken=abstain (as 227).

Verdict PASS iff M1-M5 all pass. Pilots (pre-seal, final code): M1 75/75,
M2 72/72, M3 75/75, suitediff all five 0 moves GATE clean, smoke
sleeps=1 installed=1 probes=5/5 wrong=0 taught=50/50 ow=0 broken=abstain;
all 9 verifier sentences pass as pilots.
