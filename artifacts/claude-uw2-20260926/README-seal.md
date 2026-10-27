# uw-2 test panel (corrpanel-uw2), sealed

Sealed 2026-09-26 21:23 UTC (`date -u`) by the wrong-as-fact thread, for uw-2 (PASSMARKS-uw2.md, 4d535f833; ADDENDUM-1,
ed39303d0).

TEST-ONLY. Never trained on, tuned on, read item by item or quoted by anyone building uw-2 or any other change.
Scripts that run on it print counts only. No system has ever run on it.

## What it is
- 24 fresh fictional lives in the 331 bank format, written blind on 2026-09-26 by a single writer agent.
- The writer's brief was artifacts/claude-sf401-20260926/PANEL-SPEC.md plus PANEL-SPEC-uw2-addendum.md (07b065d7d).
- Size: 552 turns, 215 asks, 72 corrections (12 per style), 32 decoys.
- 48 of the corrections are about a named person or pet referred to only by a pronoun or role word. That count is
  by code: scripts/claude_uw2_panelcheck.py.
- Both checkers pass: claude_sf401_panelcheck.py and claude_uw2_panelcheck.py.
- A second blind agent listed the corrections from the label-free turns and agreed on 71 of 72, with 0 extra
  listings (audit/AUDIT.md).

## Custody
- Copied unread from /mnt/project-files/escrow-uw2/bank.
- The .jsonl hashes match the ones the writer reported when it finished (SEAL-uw2-panel.sha256.txt).

## Files
panel/turns.jsonl, truth.jsonl, decoys.jsonl, corrections.jsonl, README.md (the writer's counts, no items).
