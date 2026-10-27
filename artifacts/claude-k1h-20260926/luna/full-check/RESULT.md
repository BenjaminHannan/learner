# k1h Luna full data RESULT: all three data gates PASS; 895 rows for training (Creative answers in chat thread, written 2026-09-27 14:28 UTC)

Label for every k1f and k1h result: K, F and H run on 0.2c's build, whose talker carries the puzzle-trained 0.2c sleep
adapter. H minus F is still one change, because both share that talker.

## Answers (the r-chain, data of record per run/RUN-NOTE-luna-full-r.md)
- 971 chats: 240 k1e (kt-), 593 GLM k1h (kh-), 138 Luna (kl-). Every answer is Luna's; the prefix names who wrote the chat.
- All 971 answered in 4 of ADDENDUM-5's 6 chunks: the pilot's 40, then chunk 1 (old job) 286, r1 195, r2 275, r3 175.
  0 failed calls. Every try was kind=ok (answer-log-1, -r1, -r2, -r3 in ../full-chain/).
- errlike tries, an upper bound on false route losses: 0.
- Route filter: 1 answer emptied (R1_marker), so 970 non-empty (answers_filtered.jsonl).
- GLM's 240 answers (../../glm/answers.jsonl) exist and were not trained on. They are not an input to anything here.

## Check (claude_k1h_train.py check; check.txt, run with Python 3.12, the same kept, packet and key as the 3.11 run)
- 942 kept of 971. Dropped: trim 16, G1 7, G2 1, no answer 1, near-copy of a DEV chat 4.
- kept by kind: idea 674, uses_facts 268.

## Gate 1: PASS (ADDENDUM-6's gate 1b decides)
- Gate 1b (scripts/claude_k1h_gate1b.py, sha256 180b7303...; selftest 1/1 ok): top sentence in 16 of 942 (0.017,
  bar 0.02); top opening share 0.013 (bar 0.25). PASS. By chat writer (report only): k1e 4 of 235, GLM k1h 10 of 577, Luna 2 of
  130; each passes (gate1b_by_writer.txt).
- The sealed gate 1, reported beside it: top sentence in 222 of 942 (0.236). FAIL. Its top piece has no letter in
  it, since the count falls to 16 once such pieces are skipped. On the pilot those pieces were list numbers.
- ADDENDUM-6 was found on the Luna pilot, before any full-data gate 1 was run.

## Gate 2: PASS
- 60 kept answers (seed 4611), JUDGE-k1f's words, blind judges; pass or fail only, no answer kept or dropped by it.
- Judge 1: 60 useful, 0 made-up. Judge 2: 60 useful, 1 made-up. They split on 1 line; judge 3 decided it (useful,
  not made-up).
- Result: useful 60 of 60 (bar 48), made-up 0 (bar 3 or fewer). gate2_result.json.
- By chat writer (report only): k1e 13 of 13 useful, GLM k1h 39 of 39, Luna 8 of 8; made-up 0 in each.

## Gate 3: PASS
- Size: 942 kept, above the 600 floor.
- Near-copy rows removed by a blind Claude agent (hygiene only; 47 rows): it read the 942 practice chats and the
  sealed k1fpanel, and returned only ids and a count (gate3_agent_drop.json). By chat writer: k1e 11, GLM k1h 31, Luna 5.
- Beside it, report only: the code-only near-copy count against the panel (DEV rule: same request, or 80% or more of
  the request's words shared) is 4 of the 942 kept (5 of 971) (gate3_code_hits.json). None of those 4 is among the
  agent's 47. Under the sealed rule the agent's list decides, so those 4 stay in the training rows. The Thread
  manager may rule that they come out too before training (a drop that can only make the test cleaner).
- Training rows: kept_train.jsonl, 942 minus 47 = 895 (k1e 224, GLM k1h 546, Luna 125). Gate 1b on these 895 still
  passes (16 of 895, 0.018; gate1b_by_writer_train.txt).

## Files here
check.txt, kept.jsonl (942), kept_train.jsonl (895), gate1b*.txt, split_kept*.txt (the sealed gates by writer from
claude_k1h_luna.py split), gate2_packet.jsonl, gate2_key.json, gate2_judge1-3.jsonl, gate2_splits.json,
gate2_result.json, gate3_agent_drop.json, gate3_code_hits.json. No test item is in any of them.

## Next
The BensPC (or vast) k1h training job, sent to the Thread manager before it is queued. It trains on kept_train.jsonl
with the sealed recipe, then runs the H arm on k1fpanel.
