# rd-378L addendum C (2026-09-26 ~12:55 UTC, before 007g ran): an extra output, no mark changes

For Benchmarks' answer-level follow-up (agreed 12:50 UTC): the score step also writes ranked_turns.jsonl, per question and store, the
first 20 distinct turn positions in rank order (fused), numbered as claude_bm395_store_answer.build_store numbers them.
Positions only, no text. Marks L1-L3 are unchanged. SEAL-C.sha256.txt covers the script now in use.
Agreed follow-up (Benchmarks owns it, registered separately): only if L1 passes, the plain 1B answers from store B's
first 20 distinct turns vs store A's, with bm-398d's layout, prompt and blind check.
