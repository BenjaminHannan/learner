# y1t-H1: the BensPC job file changed; the run did not (note written 2026-09-27 11:51 UTC)

Answering from memory said at 11:51 UTC that handoff/held/benspc-y1t.md (named in ADDENDUM-3) is superseded by
BASH-ONLY passes handoff/held/180-y1t-benspc-bo-p1..p4, with kit handoff/kit/y1tpc and y1t ADDENDUM-6 to 8.

Checked in handoff/kit/y1tpc/remote/chain.cmd:
- Runner: scripts/claude_y1t_h1run.py (lines 38 and 43).
- Panel: artifacts/claude-spare401-20260926/panel (line 16). The pass checks the SEAL-spare401 panel line.
- Models: A = BASE, MiniCPM5-1B snapshot 87179e5c (line 14). B = y1t's merged model tr/merged.
- Machine: BensPC.
- Output: h1/rows_A.jsonl and h1/rows_B.jsonl, copied with the two logs to artifacts/claude-y1tH1-20260926/run/ on
  builder-outbox.

The runner, the panel, the models, the machine, the marks, the judges and the scoring are unchanged, so no addendum
is needed. One difference: if h1_A fails, h1_B does not run. A missing rows_B then means no verdict, and it is
reported as that.
