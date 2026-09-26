# lis-319k addendum: if the panel read is lost

Written 2026-09-26 15:19 UTC, before any result of lis319k-panel-mac is seen here (no reads file, count or reply from it exists on either branch at this time).

The running job's step 4 (claude_lis319k_score.py bar) imports claude_lis300_compiler, which needs design/v3/60-listener, and that is not in the
job's TREE. So the job may stop after its one panel read at step 3.

Rule, fixed now:
1. If reads_panel.jsonl survives (pushed or reported kept), the bar rewrite (a pure confidence rewrite, no model) runs here from it. No re-read.
2. If it is lost before anyone sees any of its content or counts, the lis-319 reader reads the panel once more, as a disclosed deviation, in a
   requeued job with design/v3/60-listener in the TREE. Why this doesn't burn the panel: a lost read gives nobody information. The reader, prompt
   and panel are unchanged, and nothing is chosen or tuned between the two reads. The VERIFY file will state that the panel was read twice by
   lis-319 and that the first read was lost unseen.
3. If any count or content of a lost read was seen by this thread, the panel counts as burned for lis-319k. A fresh panel is then sealed the same
   way (writer, labeller, adjudication) before any re-test.
