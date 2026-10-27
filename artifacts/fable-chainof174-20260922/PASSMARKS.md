# Exp 174 PASSMARKS — "of"-phrased chain questions on loop138f, sealed before run

Agent: `scripts/fable_loop174_agent.py` (Loop174Ears / Loop174AgentLoop /
Loop174Daemon, build_agent174, DEFAULT_CONFIG174) = clean base loop138f
(`scripts/fable_loop138f_agent.py`, read-only) + ONE outermost ears stage:
ChainOf174Mixin (`scripts/fable_fix174_chainof.py`, read-only).
Config: `artifacts/fable-chainof174-20260922/loop174-config.json`.
Design: `design/v3/30-modes/174-chainof-muse.md`.
Seeded in this file before any registered run; hashed to SEAL.sha256.txt
together with the config, the two agent files, the three
`scripts/fable_fix174_*.py` drivers, and the T1 case file.
Ledger P174.1–P174.7 appended pre-run.

Environment: Mac CPU only, offline, `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1`,
`uv run --offline --no-project --python 3.12 --with torch --with numpy python -B …`.
Every seed/case reported, never averaged. A registered FAIL stays FAIL
with one diagnosis note. No rule changes after the seal. Heavy suites run
one at a time. Each run < 1500 s wall-clock. Daemon wrappers take
idle_seconds. Never write to the repo-root notebook/.

## The one change (ears only)

Question-frame rewrite before the unchanged base hears the turn:
"What/Who is the R of X's S?" -> "What/Who is X's S's R?" and
"What/Who is the R of X?" -> "What/Who is X's R?", only when R and S are
in REL174 (closed list read from the code, listed here) and X is a single
capitalised name, and only for questions (terminal "?", no interior marks).
The candidate is used only when the unchanged base parses it as an ask;
else the original passes through. Statements are NEVER rewritten.

REL174 (13 surfaces): boss brother father friend husband mother neighbour
neighbor partner sister teacher wife (12 × `scripts/fable_agent_loop.py`
PERSON_RELATIONS) + city (FakeEars generic-relation surface stored and
answered by the base: director probe "Lee's city is Oslo." + possessive
twin "What is Kim's boss's city?" -> "Kim's boss's city is Oslo.").

## Marks

- T1 (`scripts/fable_fix174_t1.py`, fresh in-process loops,
  `artifacts/fable-chainof174-20260922/cases174.json`, 40 turns: 6 teaches,
  12 of-asks each followed by its possessive twin, 10 traps):
  T1a every of-ask reply174 == its twin reply174 (same notebook), 12/12.
  T1b every of-ask reply174 == base reply138f(twin), 12/12.
  T1c taught of-asks answer exactly: n7 "Wren's city is Lumen.",
  n9 "Zara's boss is Wren.", n11 "Zara's boss's city is Lumen.",
  n13 "Pip's mother is Tilda.", n15 "Tilda's teacher is Miro.",
  n17 "Pip's mother's teacher is Miro.", n19 "Kess's friend is Jola.",
  n21 "Jola's sister is Nia." (8/8).
  T1d untaught of-asks == the base twin's honest no-record reply:
  n23 "I don't know Zara's city.", n25 "I don't know Wren's boss.",
  n27 "I don't know Pip's boss.", n29 "I don't know Zara's friend."
  (4/4, each an abstain, never a guess).
  T1e traps byte-identical to base (10/10): n31–n34, n36, n39 the long
  abstain ("I do not know that from what you taught me. I have no record
  of it, so I will not guess. I didn't understand that, I don't know —
  could you say it another way?"); n35 "I have no opinions. Oslo and
  Paris are only values you taught me."; n37 "I don't know anyone called
  the city of zara."; n38/n40 "I don't know anyone called the city of
  Zara.".
  T1f 0 writes from asks (events delta 0 on all 24 ask/twin turns) and 0
  writes from the statement traps n35/n36.
  T1g whole-script replies identical to base except exactly the 12
  predicted of-ask moves (no other per-turn difference).
  T1h rewrite_chainof fires on all 12 of-asks, on 0/10 traps.
- T2 (`scripts/fable_fix174_t2suites.py --only rt136|rt143|sessions|bench`,
  `scripts/fable_marks123_all.py --agent scripts/fable_loop174_agent.py
  --config artifacts/fable-chainof174-20260922/loop174-config.json --out
  artifacts/fable-chainof174-20260922/marks174 --workers 4`,
  `scripts/fable_fix174_markscmp.py`): every suite per-case identical to
  the sealed loop138f rows (verdict + reply + stored/writes) with 0 moves:
  redteam136 (145 cases), redteam143 (124), sessions152 (180 turns),
  bench121 4 splits (new_121_4hop, old_s2fresh_4hop, edit200,
  bench132_4hop; 0 new wrong), marks123 all suites (p2/p3/p4/q1/q4/rt110/
  rt81/bench/sleep/soak). 0 new WRONG / WRONG-WRITE / junk writes anywhere.
  Pre-seal static evidence (pure-function scan, no loop run):
  rewrite_chainof returns None on all 325 redteam136+redteam143+sessions152
  turns, all 605 bench questions (edit200 + bench121 new + bench103
  s2fresh), and all 168 redteam98/81/110 question literals.
- G4: every registered run < 1500 s wall-clock (pilots: T1 7.3 s).

## Predicted fault lines (part of the seal; FAILs stay FAIL)

- F1: any per-case move beyond the enumerated 12 T1 of-ask moves.
- F2: any new WRONG / WRONG-WRITE / junk write vs loop138f on any suite.
- F3: mailbox-race flakes (empty-read clarifies, lost teaches) under
  parallel-agent load: recorded, re-run once in the open, both reported.
