# Owner review: artifacts/codex-retention-20260927 (c7c8221a0), by Sleep research, 2026-09-27 03:55:08 UTC

This review covers the marks and run note only. No R1 or C1 result exists on main yet. Nothing in that folder counts until the owner (Sleep research for R1, Fix sleep for C1) verifies it.

## Blocking, before any registered run counts
1. **The code is not on main.** The pilot ran `scripts/codex_retention_reasoner.py` (EXPLORATORY-INTERRUPTED.md), but that file and `implementation/retention.py` are on no branch I can see. Project rule: seal first. The code and a sha256 seal of it must be committed before the registered runs, next to PASSMARKS.md. A run whose code was not sealed first is exploratory, like the seed-27 pilot.
2. **The seed-27 pilot stays out.** Its note says so, and seeds 29-30 and panel seeds 92029-92030 are fresh. I checked the panel seeds against scripts/: no overlap. Any RESULTS.md must repeat that the pilot is excluded.

## R1 (task-labelled snapshots), checked against rsn-358e/e3/e4
- **Recipe matches the 358e dense arm.** 1,646,750 weights; 2,500 + 2,500 steps; batch 64; AdamW 1e-3, wd 0.1, betas 0.9/0.95; 100-step warm-up then cosine (claude_rsn358e_moe.py:51-53, :156-157). Shown.
- **The validity bar (190 of 200) can be reached.** The same dense recipe scored grids5 after grids 199/198 (358e), 199/198 (358e3) and 194/194 (358e4 s3/s4), and sums4 after sums 200/200 in every run, all on dev seed 48000. R1 uses fresh panels (92000+s), so this is suggested, not shown.
- **The overwrite control will almost surely forget.** The dense arm with no replay went from grids5 199/198 to 0/0 after sums in 358e (RESULTS.md). Expect the same; R1's "not reproduced" clause is unlikely to fire.
- **What a PASS can mean.** Serving a stored copy per skill, chosen by the caller's label, isolates by construction. A PASS is a software check (bit-identical weights and outputs, reload, routing refusals). It is not a retention finding about one net. The marks already say "not an equal-size or learned-routing comparison". Any result must say that too, and must also say:
  - the task label is hand-given, a disclosed stand-in;
  - storage grows by one full model per skill (2x here).
- **Useful fact for the reader: every 358 net already gets the task kind as input.** `Item.env` is embedded and added to every cell (claude_rsn358a_run.py:78, :96). So R1's "task identity" is information the nets already had. In 358e/e3/e4 the learned routers had that label at every token and still misrouted or starved. The routing failures there were failures to learn, not missing information (suggested).
- **Overlap with rsn-358e5: none that duplicates.** 358e5 uses the kind to force routing only in the first 10% of new-kind training batches, inside one equal-size net, never at test time. R1 uses it at test time to pick between two whole nets.

## C1 (live adapter bypass)
This belongs to Fix sleep (the 1B on/off switch), not to me. I have routed it there through the Thread manager. From the marks alone:
- dl-5 adapters are correctly limited to finding-only software fixtures (Claude-worded training rows).
- The MiniCPM5-1B revision 87179e5c... matches the one the project's kits expect (handoff/held/rent-0y1t.md:20).
- A PASS is software behaviour only, as the marks say.
- The marks' line "Luna-written data is permitted by Ben's subsequent clarification" needs checking by the Thread manager against Ben's words. It does not matter for these code-only tests.
