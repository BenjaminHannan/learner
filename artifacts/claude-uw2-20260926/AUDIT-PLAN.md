# uw-2 test panel: blind audit plan (fixed before the audit runs)

Wrong-as-fact thread, 2026-09-26. The plan was written while the blind writer was still working. No audit answer
existed yet. The builder (this thread) sees counts and ids only.

## Steps
1. The builder runs `python3 scripts/claude_uw2_audit.py nogold /mnt/project-files/escrow-uw2/bank
   /mnt/project-files/escrow-uw2/audit_in`. This writes only life_id, turn_index and user_text.
2. A fresh blind auditor (Claude, never the writer) reads audit_in/turns_nogold.jsonl life by life.
   - For every user turn that changes something the user said earlier to a new value, it writes one line:
     {life_id, turn_index, whose, new_value}. That covers the user's own mistakes and real changes.
   - "whose" is the name used earlier in that life, or "me" for the user.
   - Plans, what-ifs, visits, second values, someone else's claims and past-as-past are not changes.
   - The auditor sees no labels, no truth, no spec and no counts. It writes only to
     /mnt/project-files/escrow-uw2/audit/answers.jsonl.
3. The builder runs `python3 scripts/claude_uw2_audit.py compare /mnt/project-files/escrow-uw2/bank
   /mnt/project-files/escrow-uw2/audit/answers.jsonl` (counts; ids in escrow-uw2/audit/disagree_ids.json).

## Bar and fixes
- Pass as written:
  - agree on at least 95% of the corrections;
  - agree on at least 95% of the earlier-owner corrections;
  - at most 5 extra listings in all.
- Otherwise:
  - The writer gets the disagreement ids only and makes each of those turns unambiguous, or confirms it. A confirm
    must come with a one-line reason that names no content.
  - Both checkers are re-run.
  - A second fresh auditor re-audits the lives that contain those ids.
  - The bar is then checked again on all corrections.
  - At most two rounds. If the bank still misses the bar, it is not used, and a new bank is written.
- Then the bank is copied unread into artifacts/claude-uw2-20260926/panel/. Its hashes must match the writer's
  reported sha256 (or the post-fix hashes), and it is sealed in SEAL-uw2-panel.sha256.txt with a README-seal.md.
