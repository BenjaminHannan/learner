# uw-2 test panel: blind audit (counts only)

Plan: AUDIT-PLAN.md (ff424f157), fixed before the audit ran.
- A fresh blind auditor read only the label-free turns (scripts/claude_uw2_audit.py nogold: 552 turns, 24 lives).
  It listed every message that changes something told earlier: 71 lines, 21 about the user and 50 about someone
  else. It reported 2 messages as hard to decide.
- `scripts/claude_uw2_audit.py compare` gave: corrections 72, agree 71, missed 1, owner or value differs 0, extra
  listings 0. Earlier-owner corrections: 48, agree 47.
- Bar: at least 95% of corrections (71 of 72 is 98.6%), at least 95% of earlier-owner corrections (47 of 48 is
  97.9%), and at most 5 extra listings (0). PASS as written, so no fix round.
- The auditor's answers and the disagreement id stay in /mnt/project-files/escrow-uw2/audit/. The builder has not
  read them.
