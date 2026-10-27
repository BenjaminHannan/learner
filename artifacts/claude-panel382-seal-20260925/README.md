# Seal: chatpanel382 and creativepanel382 (month-end thread, 2026-09-25 ~20:45 UTC)

TEST-ONLY. Written blind (spec design/v3/30-modes/382-panels-spec.md), audited blind, held in
/mnt/project-files/escrow-382/{chat,creative}/. The registered version is items_v2.jsonl in each folder (the
audit's corrections); items.jsonl is the writer's first version and is never run. Nobody who builds 0.x reads them.
- chatpanel382: 60 conversations, 318 turns (think 29, 23 with a number; teach 15; ask_known 6; ask_unknown 4).
  Audit: 4 turns reworded (3 depended on an assistant reply, 1 wording), 0 gold changes, 19/19 checks.
- creativepanel382: 60 items (40 idea, 10 uses_facts, 10 puzzle). Audit: 3 facts lists trimmed, 0 puzzle changes,
  all puzzle checks passed (exact-fraction gold, each number once, brute-force solvable).
A run copies each items_v2.jsonl, unread, to a new folder as items.jsonl and checks SEAL.sha256.txt against it
(the path prefix names the panel) before anything runs.
