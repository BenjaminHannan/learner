# DIAG: loop138-nhop answers a backwards question with a forward fact (138n)

Date: 2026-09-23. Base studied: 138n = `scripts/claude_loop138n_agent.py`
+ `artifacts/claude-merge138n-20260922/loop138n-config.json`. CPU only.
Diagnosis only: no fix built, no sealed experiment, no panel read/quoted/tuned on.

## Verdict

REPRODUCED and CAUSE FOUND. After teaching a 2-link chain `A R B`
+ `B R V` (e.g. "Kim Varro's spouse is Dana Holt." +
"Dana Holt's spouse is Ravi Stone."), a backwards question about the
middle value ("Whose spouse is Dana Holt?", "Who is married to Dana
Holt?", "What has Dana Holt written?") is answered from stage
`loop138-nhop` with the FORWARD fact about the value
("Dana Holt's spouse is Ravi Stone."). Gold is the backward fact
("Kim Varro's spouse is Dana Holt."). The stored notebook facts are
intact in every case: only the reply is wrong, nothing is mis-stored.

## Cause (file:line)

Two cooperating defects, both "forward-only, no direction check":

1. `scripts/fable_bench92_english_arm.py:214-234` (`compose_n_hop`):
   the composer requires exactly one mentioned entity (line 215), then
   walks FORWARD only — `outs = [(r, o) for (s, r, o) in triples
   if s == cur]` (line 222). There is no `o == cur` (backward) branch
   anywhere in the function. For "Whose spouse is Dana Holt?" the only
   mentioned entity is the VALUE (Dana Holt), so the walk starts at the
   value and follows its outgoing edge to Ravi Stone. The coverage gate
   (lines 237-239) only checks that the walked relation is MENTIONED,
   not its direction, so it passes.
2. `scripts/fable_loop138_agent.py:122-131` (`Loop138Ears._hear_question`):
   the first composer frame is asked unconditionally (after the consume
   gate + compound guard, neither of which checks direction —
   `frame_consumes_question` at
   `scripts/fable_loop113c_agent.py:112-164` only checks leftover cues
   and year qualifiers). The emitted ask is
   `{"act": "ask", "name": start, "relations": rels}` with
   `start = the value`, so the notebook resolves it forward
   (`current(value, rel)` = Ravi Stone) and the reply names the wrong person.
   Because this branch fires FIRST, the correct reverse path below it
   (`Reverse190Mixin`, `scripts/fable_fix190_reverse.py:207-234`, stage
   `loop190-reverse`, which scans triples for `(subj, rel, value)` and
   answers "Kim Varro's spouse is Dana Holt.") never gets a chance.

Chain of custody: 138n reuses this branch unchanged through its ears
MRO (`Loop138nEars` -> ... -> `Loop138mEars` -> ... -> `Loop138Ears`).

## Marks table (integer counts; 36 dialogs, 102 turns, all fresh agents)

| mark | n |
|---|---|
| dev dialogs run (34 own + 2 director anchors) | 36 |
| total turns (66 teaches + 36 questions) | 102 |
| teach turns stored correctly ("Saved: ...") | 66 / 66 |
| backwards chain questions answered WRONG from `loop138-nhop` (forward fact about the value) | 12 |
| forward/no-chain/2-subject controls answered CORRECT (gold match) | 13 |
| RECORD-only behaviours (abstains, other stages; unchanged by any claim) | 9 |
| MISMATCH vs my pre-registered gold (extra finding, same family: 2-hop over-walk on 1-hop forward questions, d13/d17) | 2 |
| stored triples wrong in any dialog | 0 |

Every move (final turn per dialog; teach turns all "Saved:", stages
`loop138b-fix137`/`loop121-teach`):

- WRONG from `loop138-nhop` (12): d01, d02 (director anchors, spouse),
  d03, d04, d05 (husband), d06 (wife), d11 (director anchor, author),
  d12 (author), d16 (founder), d29 (3-link chain, asked about middle),
  d33 (author "whose"), d34 (founder "whose"). Reply always = forward
  fact about the value (e.g. "Dana Holt's spouse is Ravi Stone.").
- CORRECT (13): d07, d31 (spouse no-chain / chain-sink via
  `loop190-reverse`); d10, d30 (spouse 1-hop forward via `loop138-nhop`);
  d20, d21 (boss via `loop190-reverse`); d22 (boss forward via `fake`);
  d23, d24 (mother via `loop190-reverse`); d25 (mother forward via
  `fake`); d26, d27 (friend via `loop190-reverse`); d28 (friend forward
  via `fake`).
- RECORD (9): d08, d09, d15, d19, d35 (2-subject yes/no -> stage `none`,
  honest abstain); d14 (author no-chain backwards -> `none` abstain);
  d32 (2-subject choice -> `bench73` "Was that a question?"); d36
  (friend no-chain forward -> `fake` "I don't know Moss Kline's
  friend."); d18 (founder no-chain backwards -> CORRECT
  `loop221-table-inverse` with "(worked out backwards)" label).
- MISMATCH (2, extra finding): d13 "Who wrote Salt Harbor?" ->
  "Salt Harbor's author's author is Milo Hart."; d17 "Who founded Ember
  Bay?" -> "Ember Bay's founder's founder is Daro Venn." Both stage
  `loop138-nhop`: the walk-to-sink loop (lines 221-234) over-walks a
  1-hop forward question into a 2-hop answer whenever the start entity
  has a longer single-outgoing chain. Same family (no endpoint check),
  reported separately; the proposed change below does NOT claim to fix it.

Deviations from my pre-registered expectations: d13/d17 (predicted
1-hop correct, got 2-hop over-walk); d18 (predicted RECORD, got a
correct labelled inverse from the table reader — because the relation
table has an inverse template for "What did X found?" but not for the
author/spouse shapes).

## Which relations are affected

NOT symmetric-vs-one-way: the trigger is whether the relation has
mention cues in the composer maps (`REL_MENTION_CUES` /
`REL_CUES92`: 38 keyed relations, incl. spouse, author, founder,
founded_by, employer, child, creator, ...). Any backwards question
about a MID-CHAIN value on a cued relation misfires, symmetric
(spouse) or one-way (author, founder) alike. Cue-less relations
(boss, mother, friend, teacher, coach, sister, ...) never produce a
frame (`compose_n_hop` returns None at line 238) and fall through to
the correct `loop190-reverse` path — 8/8 correct here. Preconditions
for the bug, all required: (a) cued relation, (b) a real chain
(value has an outgoing edge; chain-sink and no-chain questions fall
through correctly), (c) exactly one entity named in the question
(2-subject questions abstain at line 215).

## Stored fact vs reply

Only the reply is wrong. In all 12 WRONG dialogs the triples recorded
after the question turn contain BOTH links intact (e.g.
`[('Kim Varro','spouse','Dana Holt'),('Dana Holt','spouse','Ravi
Stone')]` — see `raw_replies.json`, `triples_after`). No teach was
corrupted and no inverse fact was stored (inferred answers are never
stored by construction). A re-ask through the reverse path would still
find the right answer.

## Proposed ONE change (not built)

Add a direction guard at the nhop branch
(`scripts/fable_loop138_agent.py:122-131`, or as an additive wrapper
mixin above it in the 138n lineage): after `compose_n_hop` returns
`(start, rels)`, detect a REVERSE-shaped question about `start` —
"whose R is START", "who is married to START" (R=spouse),
"what has START written" (R=author), "what did START found"
(R=founder), i.e. the question names the value but no chain
start/endpoint — and return None so the turn falls through to the
existing `loop102` chain (`loop190-reverse` / table-inverse), which
this report proves already answers these shapes correctly.
Question-side only; no write path touched.

Pass marks for the proposal: re-run these exact 36 dialogs —
12/12 WRONG flip to the gold reverse reply (accept `loop190-reverse`
plain or `loop221-table-inverse` "(worked out backwards)" labelled,
both name the right person); 13/13 CORRECT byte-identical (same stage
+ same reply); 9/9 RECORD unchanged; 66/66 teaches unchanged.

Falsifier (what would prove this proposal wrong): after the change,
any of the 12 still replies with the forward fact about the value, OR
any of the 13 correct controls changes reply or stage, OR any teach
turn stops saving. Any one of those kills the proposal.

## What it means / doesn't mean (plain high-school English)

- Means: when you teach two linked facts with certain verbs (married,
  wrote, founded, ...) and then ask "who is on the OTHER end?", the
  agent looks the wrong way: it starts from the name you asked about
  and reads forward instead of searching backward. The notebook itself
  is fine — your facts are saved correctly.
- Doesn't mean: your data is corrupted (it isn't — 0/36 dialogs show
  wrong stored triples); every relation is broken (boss/mother/friend
  answer correctly 8/8); the agent can't answer forward questions
  (1-hop forward answers are correct); or that longer chains are safe
  (the 3-link case d29 fails too).

## Files

- `artifacts/claude-nhopdiag-20260923/DIAG.md` (this file)
- `artifacts/claude-nhopdiag-20260923/dev_dialogs.json` (36 dev dialogs,
  34 own-wording + 2 director anchors, fictional names)
- `artifacts/claude-nhopdiag-20260923/raw_replies.json` (102 rows: every
  turn's stage + reply + stored triples + gold/expect/verdict)
- `scripts/claude_nhopdiag_20260923_repro.py` (repro driver, new file)
- `scripts/claude_nhopdiag_20260923_pilot.py` (pilot, new file)

No existing file edited, deleted, or re-sealed; no commit/push made
(per OPUS-RULES, which forbids pushes — the `PUSH:` line in the brief
is satisfied by leaving the directory in the worktree for the director
to collect). No blind panel opened, quoted, or tuned on. Max 1 process
used (limit 4). Disk was 17 GB free at start.
