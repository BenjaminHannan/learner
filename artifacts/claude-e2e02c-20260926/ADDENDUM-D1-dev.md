# ADDENDUM to VERIFY-02c D1 (2026-09-26 ~14:30 UTC): the DEV gate used the wrong reader too

VERIFY-02c.md is unchanged; this adds one fact to deviation D1. The 0.2c verdict (registered FAIL) does not change.

Checked in origin/main:handoff/held/superseded/rent-02c.md step 3 and handoff/queue/006k-02c-benspc.md (lines 13-14, 18):
the DEV gate's arm X runs (bank dev-20260924 and the dev chat panel) passed `--model READER`, which is the lis-301 reader
(sha256 b4fd93a2...), not READER319 (lis-319, sha256 e688e1b2...). Sleep (step 4) and the chat/creative panel X runs used
READER319 as intended; bank D X used READER (D1).
Meaning: the DEV gate showed that the 0.2c code runs end to end, not that it runs with lis-319. No dev number from 0.2c
may be quoted as a lis-319 result. 0.2d-r (artifacts/claude-e2e02dr-20260926) and every later run launch through
scripts/claude_readersha_wrap.py, which refuses a reader whose sha256 is not the one named.
