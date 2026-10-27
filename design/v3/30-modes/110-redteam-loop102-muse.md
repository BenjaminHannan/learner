# 110 — Red team round 2 of the loop102 agent (Muse, 2026-09-22)

Round 1 (exp 98) found 16 bugs in the loop90 agent; exp 102 fixed all 16 in
`scripts/fable_loop102_agent.py` with no edits elsewhere. This experiment
attacks NEW ground only: 62 fresh cases in 10 families (no sentence, name,
or shape re-used from the 64 sealed redteam98 cases), each with the exact
sealed expectation (store X / answer X / clarify / refuse / no write), every
case through a REAL loop102 daemon subprocess via its mailbox. New files
only: `scripts/fable_redteam110_cases.py`,
`scripts/fable_redteam110_runner.py`, `artifacts/fable-redteam110-20260921/`.

## Attack design (why these families)

Round 1 closed hearsay-suffix, raw forget, Actually-prefix, qualifier, and
byte-crash seams. Round 2 probes adjacent seams: pronouns (a stored "Her"
would corrupt identity), second-teacher phrasings without round-1 markers
("Ben says ...", "Tom said ..." prefix, "According to my friend",
"Apparently"), duplicate teaches (dup FACT rows), forget through every
loop102 shape (raw / possessive / that- / please-) followed by re-teach,
asks with no taught answer (invention test), packed multi-fact turns (the
guard's word-count vs "?" ordering), lookalike names (Zoë vs Zoe must stay
distinct people), relation-word noise (case, shouting, typos), self-question
+ teach packings, and daemon abuse (empty, 1 MB, binary, 200 files,
deleted-mid-read, 150 KB whitespace, emoji, NUL).

## Harness

Per case: fresh dir, boot `fable_loop102_agent.py --daemon` (uv, offline,
OMP/MKL=1), write inbox files, poll outbox/done (120 s/file, 900 s burst),
count FACT events in events.jsonl before/after each turn, statuses from
daemon.log.jsonl, STOP at the end. Delete-mid-read is deterministic
(stop/plant/delete/reboot), not a race. Daemon death mid-case = BUG/high;
live-timeout = HARNESS-ERROR (0 occurred). The judge is the exp-98 judge
plus vanish/all-done checks; hearsay/split/question clarifies are checked
by contains because the abstain-bit list does not cover those sentences.

## Findings

56 OK / 6 BUG / 0 HARNESS-ERROR. Two genuine bugs: (1) loop102 please-forget
drops a space (`"forget" + t[m.end(1):]` → "forgetMira city"), so that shape
never parses — forget unreachable, stale value stands (safe symptoms);
(2) FakeEars `_APOS` matches lowercase 's only, so shouted possessives
("WHO IS MIRA'S CITY?") never split and clarify. The other four are my own
expectation errors, all with safe agent behaviour: first-name asks decline
(R4), "Was that a question?" is not in my abstain bits (N6), the "?" screen
fires before the word-count screen (S3), and FakeEars clarifies dissolve
into the chain-miss message (S6). Nothing stored a wrong fact; nothing
answered wrongly with confidence; the daemon survived all 8 abuse cases
including the full 200-file burst.

## Limits and deviations

Single-turn mailbox only (no cross-case state, no restart/kill-9 — covered
in round 1); vanish via stop/reboot per sealed note; one pre-run smoke with
unsealed sentences; 4/6 BUGs are checker gaps, recorded as BUG per the
sealed rule and explained in RESULTS.md. Sleep/neural ears idle by
construction. Fixes belong to a follow-up experiment, not this file.

## What it means / does not mean

Means: the loop102 fixes generalise (new-ground hearsay/forget/qualifier
shapes 17/18, daemon 8/8) and round 2 leaves exactly two small, safe,
well-located bugs. Does not mean the agent understands the new phrasings:
most "attacks" were declined by template screens, and first-name resolution
exists only on the forget path, not on asks.
