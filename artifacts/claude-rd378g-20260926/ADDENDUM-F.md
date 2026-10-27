# rd-378g addendum F (2026-09-26 20:33:05 UTC): route losses in rd378g-writemore, fixed before its result exists

Written while rd378g-writemore runs (launched about 20:27 UTC) and before any of its output has been seen. A batch lost
only to empty answers (every try logged "call failed" by claude_rd378g_writemore_oc.py) is a route loss, not a failed
check. Route-lost batches may be written again, once the route works, under an addendum; batches that fail the code
checks stay skipped. The 120-dialog floor of addendum D counts only after that.
