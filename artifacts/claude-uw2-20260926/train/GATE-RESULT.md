# uw-2 full data gate: GATE-PASS, 60 of 60 (checked 2026-09-27 19:43 UTC)

- Cut (ADDENDUM-3): scripts/claude_uw2_cut.py pick gave K = 8. Chunks 1 to 8 were all stop=ok, with worded_ok 1584.
  - make: the seeds sha matched chunk 1; rawcheck2 rc 0; check_we3 rc 0.
  - resume_clean: 1584 rows in, 1584 out.
  - 10851 kept rows. Every sha256 is in CUT.json.
- Cards: claude_uw2_data.py build, sealed code, unchanged. build.json has the counts:
  - 10809 cards; 6395 in the mix.
  - 1279 corrections, 481 of them correct_ref; 5116 NONE.
  - Skipped: 273 turns not kept, 42 corrections whose old fact is not a note, 0 value-not-span drops.
  - Minimum: 300 corrections and 80 correct_ref. Met.
- dev.jsonl: 569 uw-1 DEV rows, 47 of them changes. This is the trainer's report-only dev set.
- Gate: gateprep, seed 4053, drew 60 cards: 30 corrections (15 correct_ref) and 30 look-alike NONE.
  - Two new fresh blind judges each got JUDGE-gate-uw2.md verbatim and only their own copy of packets.jsonl.
  - gatecmp: 0 splits, so no third judge. 60 of 60 agree with the code label: 30 of 30 corrections and 30 of 30 NONE.
  - Blind recount by a separate script, not gatecmp: judge 1 agrees on 60 of 60, and judge 2 on 60 of 60.
- Verdict: GATE-PASS (bar 54 of 60). The judges only decide whether the data is used. Nothing trained on was written or
  judged by Claude: Luna wrote the wording, and code wrote the labels and targets.
