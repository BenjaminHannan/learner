# rd-378k addendum H (2026-09-26 20:33:05 UTC): route losses in gate3oc, fixed before its result exists

Written while rd378k-gate3oc runs (launched about 20:27 UTC) and before any of its output has been seen. The Thread
manager (20:33 UTC) reports that lis-320's pilot 3 had 30 of 32 opencode calls fail (exit 1 or 300 s timeouts) with
long instruction prompts. PASSMARKS.md and addenda B-G stay as sealed; this file adds one rule to F.

A failed try whose raw answer is empty (the helper raised after its own 3 tries, or returned nothing) is a route loss,
not a grade: claude_rd378k_teacher3oc.py logs "call failed" and failures.jsonl records raw "". A dialog is a route loss
when every failed try on it has an empty raw answer.
- If every row passes, the PASS stands (route losses only made coverage harder).
- If a row fails and at least one unusable dialog is a route loss, gate3oc has no verdict (like gate3's 402s), the
  route is fixed first (Reading facts' diagnosis, lis320-ocdiag-mac), and the same 38 dialogs run again under a new
  addendum.
- If a row fails with no route loss, it is a registered FAIL and GLM grading stops, as F says.
