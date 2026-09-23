# lis-310 RESULTS: PASS (registered run 2026-09-23, builder)

Registered verdict: PASS. 11/11 sealed unit tests passed, exit 0; 0
base-chain writes across the 5 blocked-write turns. Seal 4/4 OK after the
run; no post-seal change. No TEST-ONLY panel was opened, tuned on, or quoted
(none is used by this task). All names fictional.

## Marks table (integer counts)

| Mark | Bar | Got |
|---|---|---|
| P310.1 all sealed unit tests pass | 11/11, exit 0 | 11/11, exit 0 |
| P310.2 base-chain writes in T7 (5 turns) | 0 | 0 |

## Every move (registered run, StubReader, threshold 0.99)

- T1 two-facts-save-2: PASS. Saved 2 triples (USER,sister,Mira),
  (USER,sister,Tal); reply the base mouth's confirmation.
- T2 whose-ask: PASS. Exact "Whose dog is Pip, yours or someone else's?";
  0 triples.
- T3a askback-yes: PASS. Exact "Just to check: is Mira's dog Pip?", 0
  triples; "yes" saved exactly 1 triple with a Saved reply.
- T3b askback-no: PASS. 0 triples, "Okay, I won't save that."
- T3c askback-dropped: PASS. A non-yes/no turn dropped the pending fact and
  saved normally (1 triple; the dog fact never saved).
- T4 negation: PASS. 0 triples; base reply used (no write attempted).
- T5 CHECK: PASS. Base answered "I already have that."; triples stayed 1,
  0 new notebook events.
- T6 question: PASS. Answered from the notebook
  ("Mira's dog is Pip. (worked out backwards)"); 0 new events.
- T7 blocked five: PASS. All 5 turns grew notebook events on the raw 291
  base (validity check in-run) and grew 0 events / 0 triples under 310.
  Base-chain writes: 0.
- T8 unparsed: PASS. Exact sorry-reply; 0 triples.
- T9 chatdemo-load: PASS. load_agent finds Loop310Daemon + build_agent310 +
  DEFAULT_CONFIG310; the demo's server-style mailbox build ran a turn and
  saved 2 triples. The server file itself was not edited.

Misses: 0. Deviations: 0 (every prediction in PASSMARKS.md matched exactly).

## Hook point + me-storage (for the record)

- Hook: turn310 installed as the outermost instance wrapper, outside
  turn291: turn310(turn291(turn260(turn224c(turn224(class turn))))). No frozen
  file edited; 291 chain untouched.
- "me" facts are stored as subject USER: probed raw 291 turn "My sister is
  Mira." -> triple ('USER','sister','Mira'), reply "Saved: your sister is
  Mira." The 310 doorway calls loop._act with name "USER" plus the base's own
  Me166 reply render, giving byte-identical confirmations ("Saved: your ...").
- Screens applied to every listener save: 209 screen_action209 and 252b
  value_ok252b; any rejection blocks the whole turn (0 hits in tests, all
  values clean). 228 source guard untouched on the daemon path.
- Writes blocked in the base pass by wrapping loop._act: teach/correct
  actions that would mutate the notebook are swallowed (silent note);
  no-op re-teaches run so the base's "I already have that." survives.
- Every turn logged to <state_dir>/lis310_log.jsonl (frame, confs, decision,
  blocked count, ms).
- Real-model 20-turn chat: SKIPPED. ~/premonition-models/lis300-merged/ does
  not exist (~/premonition-models/ itself is absent), so no weights, no GPU
  run, no ms numbers. Nothing real-model is claimed.

## What it means (plain high-school English)

- The chat agent can now take facts from the listener instead of its own
  hand-written rules, and in these tests it saved exactly what it should and
  nothing it shouldn't. Questions still get answered from the notebook, and
  the old rule chain cannot sneak in a save anymore.
- "My sister is Mira" is stored under the name USER and reads back as
  "your sister", exactly like before, so old and new saves mix cleanly.

## What it doesn't mean

- This used a fake reader with hand-picked frames, not the real fine-tuned
  model, so it says nothing about how well the real listener hears. Speed
  (median/p90 ms) is unmeasured for the same reason.
- It does not prove safety on tricky turns (typos, quotes, "we", corrections
  of corrections); those belong to lis-300's blind panel, not this build.
