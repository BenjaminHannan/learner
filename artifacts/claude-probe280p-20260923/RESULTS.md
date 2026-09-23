# Held-out probe for 280p (sealed 280m join on base 260) — RESULTS (report-only, CPU only)

**Verdict: HOLD (report-only probe, no bar can be changed by it). Measured: 280m agrees with the
mechanical owner on 73/73 fresh probe turns and 91/91 chatweak dev turns, 0 overlaps, 0 writes on
question or small-talk turns, 0 store differences vs 260, 0 old-sheet hits.**

Agent: `scripts/claude_loop280m_agent.py` + `artifacts/claude-join280m-20260923/loop280m-config.json`
(sealed, unchanged; 280m seal 12/12 OK checked before the runs; no code change to any agent).
Scorer rule (sealed `scripts/claude_join280p_score.py`, mechanical owner for EVERY turn): the owner is
the single piece arm (280b, 281 or 282b) whose reply, writes or store differ from 260's, or 260 if
none differs; 2+ differing pieces on one turn = overlap = fail.
Probe panel: 60 NEW dialogs / 73 turns of my own (fictional names; everyday chat), run ONCE per arm on
all five arms (260, 280b, 281, 282b, 280m) with the sealed runner, scored with the sealed scorer.
Dev material: `artifacts/claude-chatweak-20260923/dialogs.json` (12 dialogs / 91 turns), run ONCE per
arm with the new driver-only runner (`scripts/claude_probe280p_run.py`, same sealed driver), scored
with the same mechanical rule (`scripts/claude_probe280p_score.py`).

## Marks table (integer counts)

| mark | probe (60 dialogs / 73 turns) | chatweak dev (12 dialogs / 91 turns) |
|---|---|---|
| turns run once per arm x5 | 73 | 91 |
| agreement (280m == mechanical owner, reply + writes + store) | **73/73** | **91/91** |
| overlaps (2+ piece arms differing from 260 on one turn) | **0** | **0** |
| miss ids | none | none |
| writes on question turns (280m) | **0** | **0** |
| writes on small-talk turns (280m) | **0** | **0** |
| writes on non-teach turns, probe = category != teach | 11, all control-statement turns (plain teaches 46-49, correction turns 56-59), every one byte-identical to its owner | n/a (no categories; all 15 writes are statement turns, 0 on "?" turns, 0 in small-talk dialog) |
| store differences 280m vs 260 | **0** | **0** |
| owner counts | 260: 55, 280b: 11, 282b: 5, 281: 2 (sums to 73) | 260: 87, 282b: 2, 280b: 1, 281: 1 (sums to 91) |
| old-sheet scan hits on 280m replies | **0** | n/a (director claim check; reply files below) |

## Every move / every case

- Probe by category (agree/denom): ability 10/10, teach 8/8, called 12/12, smalltalk 15/15,
  mixed 8/8, control 20/20. Miss ids: none. Overlap ids: none.
- Probe ability-text counts (report only, no bar): 280m CAN-line 9 turns + mixed 2 turns vs 260
  5 turns + mixed 2 turns; every such turn agrees with its mechanical owner, so the difference is
  inherited from the piece arms, not new behaviour.
- Probe control writes (11 ids, statements only, 0 questions among them): probe280p-46#0,
  probe280p-47#0, probe280p-48#0, probe280p-49#0, probe280p-56#0, probe280p-56#1, probe280p-57#0,
  probe280p-57#1, probe280p-58#0, probe280p-59#0, probe280p-59#1. All are teach/correction
  statements and agree with the owner on reply + writes + store.
- Chatweak: 91/91 agree; overlap ids: none; question-write ids: none; all-write ids (15, every one
  a statement turn): t01-teach-askback#1, t01-teach-askback#2, t01-teach-askback#5, t02-twohop#1,
  t02-twohop#2, t03-backwards#0, t03-backwards#1, t03-backwards#3, t03-backwards#5,
  t04-corrections#0, t04-corrections#1, t04-corrections#3, t05-forgetting#0, t12-restart#0,
  t12-restart#1 (ids only, no text). Store-diff ids vs 260: none.
- Combined: 164/164 turns agree with the mechanical owner; 0 overlaps in 164 turns.

## Deviations

- The brief's rules file path (`/private/tmp/claude-502/.../OPUS-RULES.txt`) does not exist in this
  environment; I followed the key points quoted in the task itself (additive only, fictional names,
  sealed python command, run-once, append-only ledger untouched, integer counts).
- I listed (but never read item-by-item) the sealed panel folder `artifacts/claude-joinpanel280p-20260923`
  while orienting; no panel item text was read, tuned on, or quoted, and all 60 probe dialogs are my own.
- Driver-only fixes to my own NEW (unsealed) scripts, reported here: `scripts/claude_probe280p_run.py`
  handles the chatweak restart marker row (fresh daemon on the same root, same as the sealed dev runner);
  `scripts/claude_probe280p_score.py` had an argv off-by-one fixed before its first successful run.
  No sealed file was touched; 280m seal still 12/12 (checked before the runs).
- No suites, no smalltalkpanel234, no claim grading: not asked for; this probe is report-only and no bar
  can be changed by it. No commit/push performed; files ready for the director to push:
  `artifacts/claude-probe280p-20260923`, `scripts/claude_probe280p_run.py`,
  `scripts/claude_probe280p_score.py`.

## Reply files for the director's claim check

- `artifacts/claude-probe280p-20260923/run/probe-280m.json` (all 280m probe replies + writes + stores)
- `artifacts/claude-probe280p-20260923/run/probe-score280p.json` (old-sheet hits: none; agreement table)
- `artifacts/claude-probe280p-20260923/run/probe-260.json`, `probe-280b.json`, `probe-281.json`,
  `probe-282b.json` (reference arms for the mechanical rule)
- `artifacts/claude-probe280p-20260923/run/chatweak-280m.json` + `chatweak-score280p.json` (dev set)

## What it means (plain high-school English)

- On 73 brand-new everyday-chat turns I wrote myself, the joined agent gave exactly the answer the
  responsible piece would have given every single time, and on the 91 dev turns it did the same.
  Zero turns where two pieces fought over the answer.
- The agent never wrote anything to memory on a question or a greeting, and its memory after every
  turn matched the base exactly except where a piece had already changed it.

## What it doesn't mean

- It does not change the 280p PASS: this probe is report-only by design.
- It does not mean the agent answers everything correctly: it only means the join faithfully replays
  its pieces. Wrong facts would be a piece's fault, and checking the truth of claims is the
  director's separate job (0 old-sheet hits here).
- 164 turns can't prove overlaps never happen: it proves 0 overlaps on these 164 turns.
