# y1g GPU results (Answering-from-memory thread, DEV diagnosis, 2026-09-26)

Run: scripts/claude_y1g_doubt.py --model BASE --out gpu (code never edited).
BASE = plain openbmb/MiniCPM5-1B snapshot, commit 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected).
GPU: NVIDIA GeForce RTX 5090. Instance 52778874 (label claude-memory-y1g), $0.4944/hr.
Model run wall time: about 2 minutes (started 16:43:00 UTC, 71 [y1g] lines + 2 JSON lines done by 16:44:30 UTC).
Spend: rental 3 ran ~16:33-16:45:23 UTC (~0.21 h x $0.4944 = ~$0.10); rentals 1 (52776862) and 2 (52777941) stuck
in loading past the 6-minute rule and were destroyed before running ($0). Task total ~$0.10 of the $0.30 budget.
Credit at gate: 9.54. Post-run: 0 claude-memory-y1g live; nothing else touched.
Setup: image torch 2.2.1 too old for transformers 5.17 (PyTorch disabled), so per the rent kit TORCH UPGRADE note
upgraded torch to 2.14.0+cu130, uninstalled torchvision/torchaudio, import check ok. First launch then crashed in
generate (torch 2.14 triton bmm_outer_product kernel, no C compiler in image); installed gcc (env-only, code
untouched) and relaunched unchanged; the failed launch's log was kept on the rental only, not copied back.
Checks: SEAL-y1g.sha256.txt 9/9 OK; --selftest printed "selftest ok".
Outputs: gpu/y1g_rows.jsonl (71 rows), gpu/y1g_summary.json, gpu/log.txt (75 lines: 71 [y1g] + weights + 2 JSON).
DEV only (71 asks: 56 answerable + 10 never-told + 5 others); no TEST-ONLY bank involved. Script's own verdict
lines (copied by script, never retyped):
{"pick": {"candidates": [{"config": "C3", "right": 16, "wrong": 5, "never_told_idk": 6, "eligible": false}, {"config": "C4", "right": 10, "wrong": 1, "never_told_idk": 9, "eligible": true}, {"config": "V", "right": 10, "wrong": 5, "never_told_idk": 9, "eligible": true}, {"config": "A1", "right": 26, "wrong": 24, "never_told_idk": 2, "eligible": false}], "winner": "C4", "go": false}}
{"answerable_right": {"A0": 26, "A1": 26, "C3": 16, "C4": 10, "V": 10}, "answerable_wrong": {"A0": 27, "A1": 24, "C3": 5, "C4": 1, "V": 5}, "never_told_idk": {"A0": 1, "A1": 2, "C3": 6, "C4": 9, "V": 9}, "signal": {"C3": {"right_share": 0.615, "signal": true, "wrong_share": 0.281}, "C4": {"right_share": 0.385, "signal": true, "wrong_share": 0.062}, "V": {"right_share": 0.385, "signal": true, "wrong_share": 0.188}, "any": true}}
