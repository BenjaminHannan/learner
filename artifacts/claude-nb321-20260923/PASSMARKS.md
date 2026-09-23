# nb-321 PASSMARKS (for the later nb-321-run)

Copy these VERBATIM into artifacts/claude-nb321-20260923/PASSMARKS.md before sealing. The run uses the sealed nb-320 runner scripts/claude_nb320_scale.py, unchanged, with --factory scripts/claude_nb321_store.py:open_compact, on the same workload seeds. The baseline numbers come from the verified nb-320 results.
- M1 size: file bytes per FACT write at 1,000,000 facts are at most 1/5 of the baseline's. Prediction P321.1: at most 1/8.
- M2 lossless: export_events equals the baseline events.jsonl byte for byte at 20,000 and 100,000 facts, and at 1,000,000 if the baseline finished.
- M3 same answers: every probe gives the same result as the baseline, and 0 wrong against the ground truth at every size. T1 is 30/30. T2 has 0 differences.
- M4 usable at scale: cold open at 1,000,000 facts takes 1.0 s or less. Peak memory of the open-and-probe process is at most 1/4 of the baseline's.
- M5 recall not slower: one-hop p99 is at most max(1 ms, baseline p99) at every size.
- M6 crash: 0 acknowledged-lost, 0 duplicates, 0 failed opens in the nb-320 crash test (30 kills).
- M7 tamper: 20/20 history edits caught by open or verify_all; 2/2 UPDATE/DELETE blocked.
