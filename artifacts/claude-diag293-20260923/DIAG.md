# DIAG 293 — where yes/no questions fall through the ears on 138nb

Verdict: CAUSE FOUND. Every yes/no shape falls through the same cascade,
and the fall-through point is exact. The base parser only ever makes `ask`
out of who/what/where questions (`scripts/fable_agent_loop.py:96`), so no
yes/no turn ever parses as a question anywhere in the ears. The only live
yes/no reader is the 154d loop-level peek, and it answers just one narrow
slice: `Is`-questions with single-token names whose frame is grounded in
the notebook (`scripts/fable_fix154d_yesno.py:105-161`). Everything else —
all 30 `Does`/`Has` turns, `Is` with two-word names, `Is`-of-forms, and any
`Is` whose subject or relation is not currently stored — drops to the chain
miss (`scripts/fable_loop90_agent.py:291-292`, stage `none`), and the 224
wrapper re-labels that miss as Q2 "I didn't understand that question"
(`scripts/fable_loop224_agent.py:113-137`). 11 of 51 yes/no turns answer
(all correctly); 40 of 51 say "didn't understand", including 16 turns whose
fact IS stored. 0 of 61 question turns wrote. Diagnosis only: no model
changes, no panels, CPU only.

## Marks table (integer counts, all computed from rows.jsonl by script)

| # | Check | Count |
|---|-------|-------|
| M1 | Dev dialogs written (own wording, fictional names; one- and two-word names; corrections + taken-back + does/is statement controls) | 61 dialogs, 61 runs on 138nb |
| M2 | Yes/no-shaped turns (`does-have`, `does-noart`, `is-poss`, `is-of`, `is-inv`, `does-live`, `does-work`, `does-from`, `has`) | 51 turns |
| M3 | Yes/no turns answered (Yes / No / Not-that-I-know), all matching the stored fact | 11 / 51 |
| M4 | Yes/no turns replying "didn't understand" (Q2) | 40 / 51 |
| M5 | Q2 turns whose fact IS stored (taught-true: yes-able, got Q2) | 16 / 40 |
| M6 | Q2 turns with nothing stored (unknown / taken-back: IDK-able, got Q2) | 24 / 40 |
| M7 | Question turns that wrote to the notebook | 0 / 61 |
| M8 | Final turns engaging 224c (q1c log entries) | 0 |
| M9 | Final turns with d224 kind Q2 (all 40 yes/no Q2 + 1 inverted-wh boundary) | 41 |
| M10 | Statement controls (`stmt`) with 0 writes and no-save clarify | 4 / 4 |
| M11 | Wh controls parsing (`ask`, stage `fake`): answered / targeted-decline | 2 answered + 3 declined / 6 (1 inverted boundary Q2) |

## Shape x outcome table (reply kind per shape; n = turns)

Kind key: `yes` = "Yes, ..."; `no` = "No, ..."; `not-that-i-know` =
"Not that I know of. ..."; `didnt-understand` = 224 Q2; `decline-targeted` =
parsed lookup miss ("I don't know ..."); `nosave-clarify` = "I couldn't
save that as a fact ..."; `answer-or-other` = plain wh answer.

| Shape | Example | n | yes | no | not-that-i-know | didnt-understand | other |
|-------|---------|---|-----|----|-----------------|------------------|-------|
| does-have ("Does A have an R?") | Does Bex have a dog? | 9 | 0 | 0 | 0 | 9 | — |
| does-noart ("Does A have R?") | Does Lena have mother? | 1 | 0 | 0 | 0 | 1 | — |
| is-poss ("Is A's R B?") | Is Bex's mother Talia? | 12 | 3 | 3 | 1 | 5 | — |
| is-of ("Is B the R of A?") | Is Talia the mother of Bex? | 1 | 0 | 0 | 0 | 1 | — |
| is-inv ("Is B A's R?") | Is Talia Bex's mother? | 8 | 2 | 2 | 0 | 4 | — |
| does-live ("Does A live in V?") | Does Rin live in Bergen? | 7 | 0 | 0 | 0 | 7 | — |
| does-work ("Does A work at V?") | Does Rin work at Halden? | 5 | 0 | 0 | 0 | 5 | — |
| does-from ("Does A come from V?") | Does Rin come from Bergen? | 5 | 0 | 0 | 0 | 5 | — |
| has ("Has A a R?") | Has Bex a dog? | 3 | 0 | 0 | 0 | 3 | — |
| stmt (controls, no "?") | Bex does judo on Tuesdays. | 4 | 0 | 0 | 0 | 0 | 4 nosave-clarify |
| wh (controls) | What is Bex's mother? | 6 | 0 | 0 | 0 | 1 | 2 answer + 3 decline-targeted |

Arm split of the 40 Q2 yes/no turns: taught-true 16 (dh 5: true1,
true2, true-2word, corrected, noart; is-poss 2word 1; is-of 1; is-inv
2word 1; does-live 3: true, 2word-true, correct-new; does-work 2:
sameval, 2word; does-from 2: sameval, 2word; has-true 1), taught-false
3 (dl-false, dw-diffval, df-diffval), unknown 12, taken-back 9.
The 11 answered turns: is-poss taught-true 3 (Yes), taught-false 3
(No) + 1 multi (Not-that-I-know), is-inv taught-true 2 (Yes),
taught-false 2 (No). 0 answered wrong.

## Exact file:line where each shape falls through

All shapes share one cascade; the per-shape exit point is listed. Ears
order on 138nb: 221c QNorm > 236 first-name > 221b stored-rel > 237/221
table > 229 table-teach > 138m/138l/138j/138i chain (180b, 193, 164b,
190b, 190, 154f, 154g, 209, 223, 222/215, 232c, 174 ... 171) >
ChainEars miss; then the loop-level 154d peek; then DECLINE + 224.

Shared root — never an `ask` at the base:

- `scripts/fable_agent_loop.py:96` (`_QUESTION`): matches only
  `who|what|where + is|are`. `Does`/`Has`/`Is` turns never produce
  `ask` here; they drop to the statement path (`:134-147`, no match
  for questions) and out at the FakeEars clarify (`:148`).
- Terminal miss: `scripts/fable_loop90_agent.py:291-292` (ChainEars:
  nothing above tau → single clarify "I didn't understand that. Could
  you say it another way?", `last_stage = "none"`). Observed
  outer/inner stage `none` on all 40 Q2 turns (rows.jsonl).
- Q2 re-label: `scripts/fable_loop224_agent.py:113-137`, kind decision
  `:121-127` (no `ask` act + text ends with "?" → Q2); sentence from
  `scripts/fable_fix221_tableask.py`-independent
  `scripts/fable_decline224.py` (`Q2_SENTENCE`). d224 kind Q2 on 41/41
  such turns (M9); qbranch False throughout (never parsed).

Per-shape exits:

- does-have / does-noart / does-live / does-work / does-from / has
  (30 turns, 30 Q2): 221c normalise passes through
  (`scripts/claude_loop221c_agent.py:205-232`: rewrite adopted only if
  `unique_reading221(new)` hits — never does, see below); 221b needs
  an `ask` or abstaining ask (`scripts/claude_loop221b_agent.py:287-310`)
  — none exists; 237/221 table: turn matches no compiled pattern, so
  `unique_reading237`/`unique_reading221` is None and hear returns the
  base miss unchanged (`scripts/fable_fix221_tableask.py:494-497`;
  237 override `scripts/claude_loop237_agent.py:188-191`); 229 skips
  `?` turns (`scripts/claude_loop229_agent.py:392`); 190
  `parse_reverse190` None (`scripts/fable_fix190_reverse.py:103-146`,
  hear `:219-225`); 153 `parse_reverse` None
  (`scripts/fable_fix153_reverse.py:64-92`, hear `:148-164`); 154d
  `parse_yesno154d` None — `_ISQ_154D` requires leading `Is`
  (`scripts/fable_fix154d_yesno.py:67,105-109`); chain miss → Q2.
- is-poss / is-inv, single-token, grounded (11 turns, all answered):
  parsed (`:105-136`) AND grounded (`ground_yesno154d`, `:139-161`:
  `nb.resolve` OK + current rows) → `YesNo154dMixin._listening_tick`
  diverts (`:184-201`), reply built at `:156-161`, stage tag
  `loop154d-yesno+none` (`:213-214`). Recorded acts still show the
  base miss clarify (the peek re-hears before answering).
- is-poss / is-inv, single-token, ungrounded (9 turns, 9 Q2:
  ip-unknown-rel, ip-unknown-subj, ip-taken-forget, ip-taken-isnot,
  ii-unknown-subj, ii-unknown-rel, ii-taken + ip-false-arm? no —
  false arms grounded and answered): parsed but `ground_yesno154d`
  returns None (`:142-153`: unknown subject or no current rows for a
  taken-back/never-taught relation) → falls to `super()._listening_tick()`
  (`:201`) → DECLINE → Q2. So "Is Zane's mother Talia?" and the
  taken-back "Is Bex's dog Biscuit?" (nothing stored either way) both
  get "didn't understand" instead of "I don't know".
- is-poss / is-inv, two-word names (2 turns, 2 Q2: ip-true-2word,
  ii-2word): `_NAME_154D` (`:69`, single capitalised token) rejects
  "Mary Ann" at `:128-129` → parse None → miss → Q2, although the
  fact is stored and the wh-control answers it.
- is-of (1 turn, 1 Q2: ip-ofform): no `'s` split
  (`_POSS_154D.split`, `:113-114` yields 1 part) → parse None → Q2.
- stmt controls (4 turns, 4 nosave-clarify, 0 writes): not questions;
  ears miss clarify, loop `_act` no-save path (text at
  `scripts/fable_decline224.py:101` family / `scripts/claude_fix255_text.py:104`);
  ev unchanged 0→0. Distinct from the Q2 question path — good.
- wh controls (6 turns): `ask` acts, stage `fake` (FakeEars question
  path); taught answer (2), targeted decline on unknown/taken-back
  (3: "I don't know anyone called Zane.", "I don't know Marko's
  boss.", "I don't know Bex's place of birth."), Q2 on the inverted
  boundary "Where lives Bex?" (1, stage `none` — same fall-through as
  diag290's finding).

## Do any existing readers already parse yes/no forms?

- bench73 (`scripts/fable_bench73_english_arm.py:246-300`,
  `compose_question`): No. Handles `What`-never-taught, `Who`-of,
  `Who`-verb and MQuAKE two-hop wh-forms only; no Does/Is/Has branch.
  Bench-scoring composition code in any case, not a live ears stage.
- 221/237 table: the TABLE knows yes/no — the JSON
  (`artifacts/claude-relationtable-20260922/relation_table_v1.json`)
  ships `yesno` templates in the possessive, my, of_form and inverted
  families (e.g. "Is {X}'s {R} {Y}?", "Is {Y} {X}'s {R}?", "Is {Y}
  the {R} of {X}?", "Is my {R} {Y}?"). But the READER never compiles
  them: `scripts/fable_fix221_tableask.py:187-189` compiles only
  kinds `("ask", "inverse")`, and hear (`:485-508`, 237 override
  `scripts/claude_loop237_agent.py:178-203`) only emits ask/inverse.
  So no yes/no turn ever gets a table reading today.
- 190 (`scripts/fable_fix190_reverse.py:69-146`): No. Only reverse
  shapes (Whose/Who-has/Who-lives-in/Who-born-in). Does/Is return None.
- 153 (`scripts/fable_fix153_reverse.py:64-92`): No. Only the four
  reverse frames (whose / is-the-R-of). Does/Is return None.
- The only live yes/no reader is 154d
  (`scripts/fable_fix154d_yesno.py:105-161`): `Is V X's R?` /
  `Is X's R V?` with single-token names, grounded-only. The old 154
  (which answered `Is` via a wh-run, incl. of-forms and two-hop) is
  OFF since 138f (`scripts/fable_loop138f_agent.py:50,127`).

## Smallest single change proposed (not implemented — diagnosis only)

One new additive loop-level wrapper (new file only, no frozen file
touched), in the 154d slot: on the didn't-understand miss clarify,
before deferring to the base tick — (a) parse `Does X have a/an R?`,
`Does X have R?`, `Has X a R?`, `Does X live in V?`, and the `Is`
family widened to multi-word names (via `nb.resolve` instead of the
single-token regex) plus `Is V the R of X?`; (b) ground with the same
read-only calls 154d uses (`nb.resolve` + `nb.current`): have/has on
key(R) itself, live-in on `city`; (c) answer Yes (value match), No
(mismatch on a single-valued key), "Not that I know of" (mismatch on
a multi-valued key), or the targeted "I don't know X's R." when
subject unknown / relation not stored / taken-back; unparsed shapes
pass through byte-identical. Fires only on the miss clarify, emits
clarify records only → provably 0 writes, same as 154d.

Dev turns it would move (40/40 current Q2 yes/no turns; the 11
answered and all 10 controls unchanged):

- → Yes (12): dh-true1, dh-true2, dh-true-2word, dh-corrected,
  dh-noart, ip-true-2word, ip-ofform, ii-2word, dl-true,
  dl-2word-true, dl-correct-new, h-true.
- → No (1): dl-false (stored Bergen vs asked Oslo, `city`
  single-valued).
- → targeted "I don't know" (27): dh-never1, dh-never2,
  dh-never-2word, dh-taken-forget, dh-taken-isnot, ip-unknown-rel,
  ip-unknown-subj, ip-taken-forget, ip-taken-isnot, ii-unknown-subj,
  ii-unknown-rel, ii-taken, dl-unknown, dl-taken-forget,
  dl-taken-isnot, dw-unknown, dw-taken, df-unknown, df-taken,
  h-never, h-taken (21) + dw-sameval, dw-diffval, dw-2word,
  df-sameval, df-diffval, df-2word (6, value stored under `city`
  but asked as work/from — Yes/No needs a director key ruling, so
  they move Q2 → honest decline only).
- Open ruling needed: which stored key (if any) `work at` and `come
  from` verify against (`city`? `place_of_birth`? a new key?). The
  10 does-work/does-from turns move to Yes/No only after that ruling;
  without it they still improve (Q2 → IDK) under this change.

## Every move, miss, deviation

- Moves: none possible in diagnosis (no model change). Observed
  answer-vs-Q2 split on 138nb: 11 answered (all ideal), 40 Q2, 0
  wrong answers, 0 writes.
- Misses (agent wrong today): the 16 taught-true Q2 turns (fact
  stored, agent claims non-comprehension) and the 24 unknown /
  taken-back Q2 turns (nothing stored, agent claims
  non-comprehension instead of the honest "I don't know"). The 3
  taught-false Does turns (dl-false, dw-diffval, df-diffval) are Q2
  where No (live) or a ruling (work/from) is due.
- Correct: all 11 grounded single-token `Is` turns (Yes/No/
  Not-that-I-know exactly per SINGLE_VALUED_154); all 4 statement
  controls (no-save clarify, 0 writes); 5/6 wh controls (2 answers,
  3 targeted declines).
- Deviation: run script wrote 61 rows, not 63 — the dialog list as
  sealed in `scripts/claude_diag293_run.py` holds 61 entries
  (10 + 13 + 8 + 7 + 5 + 5 + 3 + 4 + 6); the "63" in planning notes
  was a miscount, the code assert is `>= 60` and the task bar (60+)
  is met at 61. No re-runs, no pilots mixed in (pilots ran in
  throwaway temp state dirs, never the repo notebook, rows kept
  separate).
- Env: load 53-58 (bar 60), disk 11 GB free (bar 3 GB), 1 process,
  CPU only, no panels opened, no panel rows read, no model changes.
  138nb agent + label + config verified byte-identical to
  origin/builder-outbox before running (diff clean, no copy needed).

## What it means / what it doesn't mean

- Means: on 138nb, "Does Ana have a dentist?", "Does Ana live in
  Oslo?", "Is Ana's boss Tovi?", "Has Ana got a sister?" all fall
  through the ears without ever becoming a question inside the
  machine — except the narrow `Is A`s R B?` / `Is B A`s R?`
  single-token grounded slice, which answers Yes/No correctly. A
  stored fact ("Bex's dog is Biscuit") cannot buy a Yes to "Does Bex
  have a dog?", and an empty notebook cannot buy an "I don't know":
  both get "I didn't understand that question".
- Doesn't mean: the notebook is broken or anything was written by
  asking — 0 of 61 question turns wrote, taken-back facts stayed
  taken-back (taken-back `Is` correctly fails grounding), and every
  one of the 11 answers matched the stored value. The damage is one
  missing question shape in the ears, exactly 40 turns wide, one
  wrapper deep — plus a relation-table that already lists yes/no
  templates its reader never compiles.

## Repro

- `scripts/claude_diag293_run.py` — 61 dialogs x 138nb → rows.jsonl
- `scripts/claude_diag293_summary.py` — every count in the marks table
- `scripts/claude_diag293_pilot.py`, `scripts/claude_diag293_pilot2.py`
  — pilots (throwaway state dirs; interpreter + shape checks)
- Raw data: `artifacts/claude-diag293-20260923/rows.jsonl` (61 rows)
- Runner: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run
  --offline --no-project --python 3.12 --with torch --with numpy
  python -B <script>`
