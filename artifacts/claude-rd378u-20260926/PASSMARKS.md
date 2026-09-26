# rd-378u: does the notes gain hold on unseen chats, through the store the build would use? (registered 2026-09-26 16:35 UTC)

Thread "Trustworthy notes". Written after rd-378L's PASS (VERIFY 274fae558) and before any note is written over
LoCoMo conversations 5-9. Development measurement on LoCoMo PRACTICE ("after using LoCoMo for development"); nothing is
trained on LoCoMo or any benchmark; no question, answer, turn or note text is printed or pushed.

## Why
rd-378L measured notes on conversations 0-4 with its own scorer and store v1 (v3 numbers were report only). Before the
note pointer goes into the build, check the same gain on the five conversations no notes decision has used, through
the code path the build would call: store v4's recall() with its defaults (scripts/claude_ep382_store_v4.py).

## The one change
A = store v3 (0.2c's store), heard rows only, recall() defaults. B = store v4: the same heard rows plus the rd-378
writer's notes (unchanged writer, merged sha256 dbcc8db5...; same write command as rd-378L), recall() defaults, which
rank notes with heard rows and return only the raw lines they point to. Rows are built exactly as rd-378L's scorer
builds them. Both return raw lines only, one per turn, so the number of lines shown is the same.
Script: scripts/claude_rd378u_confirm.py score --convs 5-9. Questions: categories 1-4 with evidence.

## Marks (any@10: an evidence line among the first 10 lines returned)
| Mark | Bar |
|---|---|
| U1 | B any@10 >= A any@10 + 5 points overall |
| U2 | no category (1, 2, 3, 4) more than 3 points below A |
PASS = U1 and U2. Proved wrong: B any@10 <= A + 1 point.
Report only: @5 and @20, all@k, lines shown @10, lines reached through a note @10, notes per turn, unparsed turns,
median and p90 write ms.

## What happens next (fixed now)
PASS: store v4 is offered to Month-end for the joined build (switch EP382_STORE=claude_ep382_store_v4; the note writer
writes a note per turn in the turn loop), with rd-378u's numbers. Answers still read only raw lines.
FAIL: notes stay out of the build's recall; the rd-378L gain is recorded as not confirmed on unseen chats, and the
cut-only writer (371c step 4b) is judged on truth only, not proposed for search.
Either way, 4b (making the notes truer) goes on: rd-378 judged 31% of its notes unsupported, and an untrue note can
still pull a wrong line into view.

## Seal
SEAL.sha256.txt covers this file, the confirm script, store v2/v3/v4, rd-378L's scorer and the writer code. The rental
runs the exact commit that added SEAL.sha256.txt.
