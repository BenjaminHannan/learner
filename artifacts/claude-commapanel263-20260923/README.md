# commapanel263 — blind panel (base260 behaviour)

60 items, ids c263-001 … c263-060. Base arm: scripts/claude_loop260_agent.py
with artifacts/claude-openers260-20260922/loop260-config.json, driven like
openpanel260 drives 138m: one fresh agent per item, setup then turn then
followup in order, stored triples read after each turn; plain_turn asked
in a second fresh agent with the same setup. 10 panel fields and 10
base-row fields, same names as openpanel260. Category level only: no item
text is quoted here.

## Families (exact counts)

- unlisted_opener_teach (20): teach opening with an everyday opener or
  interjection most lists miss, then a comma, then a plain possessive or
  verb teach. expect_store = the plain teach's triple; the stored subject
  must be the name alone.
- appositive_subject (10): appositive-subject teaches of the two spec
  templates. Gold stores nothing whose subject contains a comma;
  expect_store is [] (the base's plain reading of these stores nothing).
- comma_value_ok (8): facts whose VALUE correctly holds a comma. The value
  may keep its comma; only subjects are guarded. expect_store = the plain
  teach's triple.
- question (8): questions with an unlisted opener + comma after a plain
  setup teach. 0 writes; gold = the value.
- control (14): plain teaches (+ followup) and plain questions (after
  plain setups) with no comma in any subject; byte-identical to base260.

## Judgement rules (for the scorer)

Normalise strings by lowercasing and stripping edge punctuation/spaces.
- junk: any triple stored after the turn or the followup that is in
  neither stored_after_setup nor expect_store.
- base_junk (row flag): any stored subject after the turn or followup
  contains a comma.
- store_ok: expect_store is a subset of stored_after_turn and nothing
  else was added at the turn.
- question_write: a question turn, or a followup, changes the store.
- reply_ok: gold is "" or a substring (normalised) of the scored reply
  (followup reply for teaches, turn reply for questions).
- right by family:
  - unlisted_opener_teach, comma_value_ok: store_ok, reply_ok, no junk,
    no question_write.
  - appositive_subject: no comma-subject stored, store_ok, reply_ok,
    no junk, no question_write.
  - question: reply_ok, no junk, no question_write.
  - control: right as its shape (teach/question above).
- Schema mismatch (file/field/family/label counts) must print
  SCHEMA-MISMATCH and exit 3: VOID, not FAIL.

## Base260 results (category level)

| family | n | base right | base junk (comma subject) |
|---|---|---|---|
| unlisted_opener_teach | 20 | 1 | 16 |
| appositive_subject | 10 | 0 | 0 |
| comma_value_ok | 8 | 8 | 0 |
| question | 8 | 4 | 0 |
| control | 14 | 14 | 0 |
| TOTAL | 60 | 27 | 16 |

Junk count (rows storing a comma subject): 16, all in
unlisted_opener_teach. Question/followup writes: 0 rows. Control 14/14
right. Each item's note carries its base marker (RIGHT / WRONG /
WRONG+JUNK). Two full base runs give byte-identical base260.jsonl
(second run artefacts compared then discarded; sealed file is run one).

## Files

- make_panel.py: deterministic panel generator (no RNG).
- run_base.py: base runner + judge; appends base markers to panel notes.
- panel.jsonl (60), base260.jsonl (60 rows).
- SEAL.sha256.txt: sha256 of the four files above, repo-root paths.

CPU only, one process at a time. All names fictional.
