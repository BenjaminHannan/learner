Starting the sealed Luna full run — duplicate guard and seals first.
No duplicate directory found — now checking for conflicting runs.
Tree ready — verifying seals and inputs.
Seals and selftests passed — launching chat generation.
Chats complete — starting answer batches.
Two answer batches done, 284 remaining — continuing.
All answers complete and route filter clean — running final counts.
Counts verified — copying results and writing the final report.
Report written — verifying copies and cleaning up.
RAN

Counts:
- chats calls 7, chats lines 138, chats try ok 7
- items total 971 (240 kt- + 593 kh- + 138 kl-)
- pilot reused 40, new answers 931 (286+361+284)
- answers.jsonl 971 lines, 971 nonempty, 0 empty
- answers_filtered.jsonl 971 lines, 971 nonempty, 0 empty
- distinct item_ids 971, nonempty prefixes 240/593/138
- answer try ok 931, median secs 9.1, max 92.4
- route_loss_rows 0, failed final 0, not_started final 0
- seals 25+2+4+5+3+5 OK, selftests 8/8,3/3,2/2 OK
- CRLF 0 in all 3 jsonl
- copies 7 files sha256-verified, staged with `git add -f`

Deviations:
1. origin/main moved 6a62dcae… → 756fdd302b301a58c6cec6f55d4c36db91c6dea6 between fetches; archived latter.
2. Wall clock exceeded 7h30 cap (deadline ~13:20Z Sep27): chunk1 done 08:05Z Sep27, 16h pause, chunks 2-3 ran Sep28 00:00-01:44Z. Compute ~186m, no data loss, stop condition met.
3. No other errors. No chat/answer quoted. Temp dir removed, confirmed gone.

PUSH ready: artifacts/claude-k1h-20260926/luna/full (watcher pushes; no checkout/push done here).
