# capability256 unfamiliar-question evaluation: marks not met

Shown: Ben approved the unchanged sealed final evaluation. Job `cap256-final-20260930T223706Z` ran through the Mac's existing `benspc` SSH route, using launcher/guard commit `3340ca252ec8f59b3ee26b5642e4a437caa46c25` and unchanged r4 / SEAL-v9 / RELEASE-v4. The actual runner argv is saved in RUNNER-ARGV.json: `--phase final`, all four checkpoint pins frozen before fresh model calls, no training phase. The phase claimed exactly once and completed with exit0 and FINAL-CLOSED.closed=true. All 640 main question predictions and 640 declared native zero-loop controls were saved. No test item was displayed to the agent; raw data were handled only by the sealed runner, no-model verifier and binary archive tools.

Before outcomes, the falsifier was fixed: any required recurrent seed/slice below TRAIN244/256,seen52/64,structural52/64,range26/32 fails the capability gate. Both recurrent seeds must pass; plain receives identical scoring. Thresholds, checkpoint selection, TRAIN exposure (20visits), and fixed4 architecture were unchanged.

| Arm | TRAIN | Seen-family | Structural | Range | Gate |
| --- | --- | --- | --- | --- | --- |
| loop seed 0 | 194/256 | 1/64 | 2/64 | 0/32 | fails |
| plain seed 0 | 214/256 | 0/64 | 1/64 | 1/32 | fails |
| loop seed 1 | 98/256 | 2/64 | 2/64 | 1/32 | fails |
| plain seed 1 | 185/256 | 0/64 | 3/64 | 0/32 | fails |

Independent saved-token recount PASS. Every count matches the per-arm and matrix FINAL-CLOSED receipts. It checks raw native token IDs against the exact target+actually emitted terminal EOS, validates stopping/parity/call metadata, exactly160 distinct sealed evaluation memberships per arm, and the final 256 TRAIN diagnostic records. Every main evaluation prediction emitted EOS. TRAIN-modal was independently fixed from TRAIN-only final diagnostic labels (same lexical tie rule) and scored 0/64,0/64,0/32; native zero-loop scored the same 0/64,0/64,0/32 in every arm. The verifier made 0 model calls and0 optimizer calls. The declared final runner/comparator reporting has the three sealed buckets; no additional per-family outcome field was declared or invented.

Paired unfamiliar-question counts across160 questions per seed:

| Seed | Both correct | Loop only | Plain only | Neither | Loop minus plain |
| --- | --- | --- | --- | --- | --- |
| 0 | 1 | 2 | 1 | 156 | 1 |
| 1 | 0 | 5 | 3 | 152 | 2 |

The loop models answered 8/320 unfamiliar questions correctly; plain answered 5/320. This small descriptive difference does not establish recurrent advantage. Plain also has higher TRAIN scores in both seeds (214vs194 and185vs98). Both recurrent seeds miss every required threshold, including TRAIN, so the sealed capability gate is marks-not-met. Suggested interpretation: the system is underfit at this size and has poor unfamiliar-question performance. Untested: the cause of the failures, larger/different models, real user/blind panels, and any retraining or revised evaluation. No further model calls are authorized by these results.

Measured timing: runner started `2026-09-30T22:37:09.673389+00:00`, exit observed `2026-09-30T22:43:30.351380+00:00`. Wrapper observed wall time 380.678s (6.345min), including startup and <=10s final exit polling. The sealed final phase reports 371.157s and 1280 native generation calls, or 3.449native calls/s including 640 zero-loop controls. End-to-end main-question throughput is 1.681questions/s; this is measured, not an ETA.

Operational recovery: first attempt `cap256-final-20260930T223350Z` exited during freeze validation after 10.021 s, before model import, before any model or optimizer call, and without FINAL-CLAIM or raw predictions. I initially serialized Windows checkpoint paths with forward slashes. The zero-call failure receipt proves the bounded correction was safe. The unclaimed freeze was moved beside that attempt's receipts with a SHA256 preservation manifest. The corrected wrapper copies the exact nested checkpoint pins from CLOSED.json; the sealed runner validated all four pins before claiming the final phase. No failed evaluation prediction was rerun, and no scientific input or threshold changed.

Preservation: raw generated IDs, native EOS positions, stop metadata, controls and target joins remain on PC in each arm's FINAL-RAW.jsonl. A local binary archive, PRESERVED-RAW-AND-RECEIPTS.tar, contains all final raw and operational receipts; its SHA256 is 63bd50f592b0230ca941e53fd0219e1dc5f0a701655fbcaf86c2bfdab5b35d49. It is preserved locally and is not committed to expose test-item data in the PR. PRESERVED-FILE-HASHES.json and INDEPENDENT-RECOUNT.json include the raw hashes. All final raw archive hashes match PC. All four checkpoint and TRAIN-RAW hashes are unchanged after evaluation; no capability worker or active lock remains. Unrelated apps were left running. No rental, spend, deletion, security change or merge.

Validation: 23 focused tests pass (17 launcher + 6 synthetic strict-token/EOS recount tests); wrapper/recount syntax and focused whitespace checks pass. The deployed evaluation wrapper source SHA256 is cbdc685d99ceb392e9dc2014b64b551d8d8d02e7efb771e77084ab3a0a2e3b23. The zero-call failed wrapper is also preserved in the raw receipt archive. The sealed runner source remained unchanged.
