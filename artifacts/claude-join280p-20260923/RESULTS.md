# Exp 280p — RESULTS (registered re-test of the SEALED 280m join agent, no code change, CPU only)

**Verdict: PASS (M1–M4 all pass).** This is the join's last attempt per the director, and it passes.

Agent: `scripts/claude_loop280m_agent.py` + `artifacts/claude-join280m-20260923/loop280m-config.json`
(sealed, unchanged; 280m seal 12/12 OK before and after; no code change to any agent).
Panel: blind joinpanel280p, 73 dialogs / 90 turns, run ONCE on all five arms (260, 280b, 281, 282b, 280m)
with 280m's sealed runner; scored with the new sealed mechanical scorer
(`scripts/claude_join280p_score.py`: owner = the single piece arm whose reply, writes or store
differ from 260's, else 260; 2+ differing = overlap = fail).
Panel seal 2/2 OK. Own seal 3/3 OK after the runs. No sealed file changed. No re-seal. No silent re-runs.

## Marks table (integer counts)

| mark | bar | result |
|---|---|---|
| M1 agreement (280m == mechanical owner, reply + writes + store) | 90/90 | **90/90** |
| M1 overlaps | 0 | **0** |
| M1 writes on question turns (280m) | 0 | **0** |
| M1 writes on smalltalk turns (280m) | 0 | **0** |
| M1 wrong answers on called + control questions | 0 (director) | **0 misses vs owner; director claim check over reply files below** |
| M1 unsupported claims | 0 (director) | **old-sheet scan 0 hits; director checks** |
| M1 store diffs 280m vs 260 | report | **0** |
| M2 sessions152 | exactly the 3 reply-only moves | **3/3 exact ids, 0 write changes** |
| M2 bench (4x200) | 0 moves | **0** |
| M2 rt136 (145 units) | 0 field diffs, labels + gate identical to 260's | **0 diffs, labels identical, gate identical** |
| M2 rt143_nogate (124 rows) | 0 moves | **0** |
| M2 verifier vp / vs | exactly N06+E04 / 0 | **N06+E04 / 0** |
| M2 GATE | identical to 260's | **identical (suites gate clean on both; rt136 gate NOT-clean on both, same string)** |
| M3 smalltalkpanel234 wellbeing | 280m ≥ 260 | **17/20 vs 16/20** |
| M3 other items identical | 36/36 | **36/36** |
| M3 writes / setup / store diffs | 0 | **0 / 0 / 0** |
| M4 notebook-zero | 0 diffs | **0** |

## Every move / every case

- M1 by category (agree/denom): ability 25/25, called 12/12, teach 8/8, smalltalk 25/25, mixed 10/10,
  control 10/10. Miss ids: none. Overlap ids: none.
- Mechanical owners: 280b 24 turns, 281 4 turns, 282b 5 turns, 260 57 turns (sums to 90).
- Ability-text counts (report only, no bar): 280m CAN-line 24 turns (ability 22 + mixed 2) vs 260 20 turns
  (ability 19 + mixed 1); every such turn agrees with its mechanical owner, so the difference is inherited
  from the piece arms, not new behaviour.
- M2 moves: sessions152 exactly S2-casual-friends#1, S3-teachers-correction#0, S4-pets-identity#9
  (reply-only, UNHELPFUL->UNHELPFUL, stored identical, 0 write changes); everything else 0.
- M3: the 1 wellbeing move is the same row 282 moved (observed in 280m and 280n); miss ids on 280m:
  s234-015, s234-016, s234-020 (ids only, no text).
- 5x abstain follow-up: not triggered (no unpredicted flip toward an abstain; N06/E04 move away from
  abstains as predicted).

## Deviations

- None. Panel seal check passed first try; schema clean; suites ran once post-seal with the sealed
  runall/regscore (no driver fix needed); smalltalkpanel234 ran once per arm as registered.
- Deviation from "pilot everything" (inherited from 280m): smalltalkpanel234 was never run pre-seal,
  forced by the run-once rule; recorded in PASSMARKS before the seal.
- No push performed: standing rules forbid commits/pushes. Files ready for the director to push:
  `artifacts/claude-join280p-20260923`, `scripts/claude_join280p_score.py`, `scripts/claude_280p_panel.sh`,
  `artifacts/fable-predictions-ledger.md` (appended P280p.1–P280p.4).

## Reply files for the director's claim check

- `artifacts/claude-join280p-20260923/run/panel-280m.json` (all 280m panel replies + write counts + stores)
- `artifacts/claude-join280p-20260923/run/panel-score280p.json` (old-sheet hits: none; agreement table)
- `artifacts/claude-join280p-20260923/run/panel-260.json`, `panel-280b.json`, `panel-281.json`,
  `panel-282b.json` (the four reference arms' rows the mechanical rule was computed from)

## What it means (plain high-school English)

- The join works as advertised: on 90 brand-new turns, the joined agent gave exactly the answer the
  responsible piece would have given, every single time, with zero turns where two pieces fought.
- The rule that failed the last two tries (fixed owners per category) is replaced by a simple measured
  rule (whoever actually answered differently from the base owns the turn), and under that rule the
  score is a perfect 90 out of 90.
- Nothing else broke: the frozen school tests moved only where the pieces were already known to move,
  and small talk got slightly better, not worse.

## What it doesn't mean

- It does not mean the agent is perfect at answering questions — it means it faithfully replays its
  pieces. Any wrong fact would be a piece's wrong fact, and the director's claim check (0 hits here)
  is the separate guard for that.
- It does not mean the pieces are done: their inherited limits (shapes they can't read) are still there;
  the join adds no new understanding, only stacking.
- One panel of 90 turns can't prove overlaps never happen — it proves zero overlaps on these 90 turns
  (plus zero on the 180 before, so 0 in 270).
