# Exp 189b PASSMARKS — widened repeat-request grammar on loop189, sealed before run

Agent: `scripts/fable_loop189b_agent.py` (Loop189bAgentLoop /
Loop189bDaemon, build_agent189b, DEFAULT_CONFIG189B, is_repeat189b +
BARE189B grammar + NO_PREV189B). Subclasses the frozen loop189 stack;
the one change is the widened outermost repeat-request stage in turn()
(new file only, no existing file edited).
Config: `artifacts/fable-sayagain189b-20260922/loop189b-config.json`.
Driver (new, sealed): `scripts/fable_fix189b_sayagain.py`
(`--only w1|w2|junk|rt143|sessions|bench|marks123|all`).
W1 cases (new, sealed): `artifacts/fable-sayagain189b-20260922/cases189b.json`
(44 turns: 2 noprev + 21 repeat + 12 Say/repeat traps + 9 teach/ask base).
Design: `design/v3/30-modes/189b-sayagain-muse.md`.
Ledger P189b.1–P189b.8 appended pre-run. Sealed files hashed to
SEAL.sha256.txt: this file, the agent file, the driver, the case file,
the config.
Base: `scripts/fable_loop189_agent.py`,
`artifacts/fable-sayagain189-20260922/` (W2 reference + 189 rows),
`artifacts/fable-agent138g-20260922/` (sealed rows compared against).

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1`, `uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B …`. Every seed/case reported, never
averaged. A registered FAIL stays FAIL with one diagnosis note. No rule
changes after the seal. Heavy suites run one at a time, each < 1500 s.
Daemon wrappers use idle_seconds=3600.0. Fictional names only.

## The one change (frozen)

Outermost repeat stage in `Loop189bAgentLoop.turn`, before the unchanged
loop189 path (hence before the 137d Say-pretend rule). Whole-turn,
case-insensitive match (lowercase, commas dropped, trailing .?! stripped;
one leading/trailing "please" stripped): (a) bare shapes again | what |
huh | sorry what | come again | pardon | pardon me | sorry |
what did you say | what did you just say | say again; (b) grammar:
optional (could you | can you | would you | will you), verb
(say | repeat), optional object (what you just said | what you said |
it | that), optional marker (again | one more time | once more), with at
least one of (politeness, object, marker, please) present — bare
"say"/"repeat" alone never match. The 8 loop189 shapes are a strict
subset. Match -> echo `_prev189` (verbatim reply of the latest NON-REPEAT
turn; repeats never overwrite it) or the one fixed line
"I haven't said anything yet." (same string as loop189). Never writes,
never re-runs. "Say X" with any other content stays pretend exactly as
loop189 (Ben's ruling).

## Marks

- W1 (`--only w1`, sealed 44-turn session, loop189 + loop189b in
  lockstep, fresh in-process loops): 44/44 OK predicted —
  B01–B02 noprev -> fixed line, 0 writes (2/2);
  21 repeat turns (19 distinct new phrasings incl. the four director
  probes "Could you say that again?", "What?", "Say that one more
  time.", "Say again please.") -> 189b's own previous non-repeat reply
  byte-identical, 0 writes (triples+facts+events.jsonl identical
  before/after) (21/21);
  12 traps (incl. all 7 brief-listed: "Say hello.",
  "Say Kim's boss is Lee.", "Say it in French.", "What is Kim's boss?",
  "What about Lee?", "Again, Kim's boss is Lee.", "Say something nice.")
  + 9 base turns byte-identical to loop189 replies AND stored triples
  AND facts AND events (21/21). Any other verdict/reply/store/events
  diff FAILs.
- W2 (`--only w2`, 189's sealed 38-turn cases189.json, loop189 vs
  loop189b in lockstep): 38/38 byte-identical (reply + triples + facts +
  events) predicted. Any diff FAILs.
- W3 junk (`--only junk`: redteam136 + cases150 + f1 + cases139b with
  loop189b vs SEALED loop138g rows AND loop189 rows): 0 moves, 0 new
  WRONG / WRONG-WRITE / junk writes predicted on all 8 comparisons.
- W3 rt143 (`--only rt143`) vs sealed redteam143-loop138g.json and vs
  redteam143-loop189.json: 0 moves. W3 sessions (`--only sessions`) vs
  sealed sessions152 rows (138g + 189): 0 verdict/reply moves, 0 new
  wrong, 0 new writes.
- W3 bench (`--only bench`, base driver's scorer over the 4 sealed
  splits vs sealed loop138g rows and loop189 rows): 0 verdict moves,
  0 new wrong on all 8 comparisons.
- W3 marks123 (stock `scripts/fable_marks123_all.py --agent
  scripts/fable_loop189b_agent.py --config
  artifacts/fable-sayagain189b-20260922/loop189b-config.json --out
  artifacts/fable-sayagain189b-20260922/marks189b`): every suite report
  per-case identical to sealed marks138g AND marks189 after scrubbing
  volatile metadata (agent/config paths, seconds, timings; daemon-log
  `statuses` compared separately as timing-volatile, never moves);
  suite-status vectors identical (incl. inherited p3-l5z1/p4/rt81 FAILs
  and overall FAIL, same as base); only predicted metadata diffs are the
  agent/config paths and the sleep SKIP agent filename. The stock runner
  exits nonzero on the inherited overall FAIL; the mark is identity, not
  rc==0. Pilot note (part of seal): one pilot run showed a single
  statuses-only diff (rt110 F3 msg_03 [] vs ['OK'], replies and verdicts
  byte-identical), 0/3 on targeted rerun — daemon log-flush race.
- G4: every registered invocation < 1500 s wall-clock (pilots: w1+w2
  ~10 s, junk ~10 s, rt143+sessions ~17 s, bench ~91 s, marks123
  ~395 s).

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any W1 non-OK, any W2 diff, or any W3 move/new-wrong/new-write
  beyond the enumerated empty sets (W1 repeat-vs-189 reply diffs are the
  intended change and are NOT counted as moves: W1 checks them
  explicitly).
- F2: any new WRONG / WRONG-WRITE / junk write vs loop189 or sealed
  loop138g rows on any suite.
- F3: "Say that one more time." and "Say again please." must echo
  (repeat wins over Say-pretend); "Repeat after me: ..." / "Again, ..."
  / "Say something nice." must stay base-identical.
