# rd-371b = REGISTERED FAIL (C2; proved-wrong clause tripped) — PROVISIONAL record from the builder's report (2026-09-26 ~05:25 UTC)

Source: origin/builder-outbox:runs/006i-rd-371b-train/006i-rd-371b-train.go1.reply.md (rc=0). The 7 result files are on
the Mac but were not pushed: my PUSH line used bare file names (my error). The Director queued handoff/queue/000-push-rd371b.md;
it is held while the Mac has < 5 GB free. This file is updated with a recount when dev_pred/score arrive.

| Mark | Bar | Got (builder) | Verdict |
|---|---|---|---|
| C1 unsupported share of accepted | <= 5% | 0 of 1 accepted | PASS (on 1 note) |
| C2 key-ok notes kept | >= 80% | 1 of 132 | FAIL |
| C3 chat vs overheard C2 gap | <= 10 points | 1/68 vs 0/64 | PASS (both near 0) |
Proved wrong (< 50% of key-ok kept at the dev bar): TRUE.
Report only: accept-all baseline 145 of 277 key notes unsupported (52%); excluded 37; median 24 ms per note.

Run: seals all OK (1/1, 6/6, 7/7, key 6/6, panel 2/2); train 284 steps, 3.25 min, dev loss 0.198; merged sha f54dbe63...
(BensPC C:/Users/benja/rd371b/run/merged). Dev bar by the sealed rule: T = 0.98, where the checker accepted 6 of 277 dev
notes (0 unsupported, 6 of 167 ok). So the rule's 4% target was reached only by accepting almost nothing.

## What it shows / suggests
- Shown: this checker cannot keep most true notes while holding untrue ones near 4%; on the sealed test it kept 1 of 132.
- Suggested (to check on dev_pred when pushed): its yes/no scores barely separate true from untrue notes; training was
  60% "no" (1,510 no vs 965 yes), and the note writer's own notes are ~half untrue on fresh dialogs (52% on the key),
  so a filter must reject about half of everything and still keep 80% of the good half.
- The rule stands: notes stay search aids that point back to the original chat (Benchmarks + Month-end agreed).
