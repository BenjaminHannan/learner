# rt-02g blind panel

- Written by: a blind agent that saw no route or reader code (it read only scripts/claude_rt02g_make_panel.py, and wrote the templates and negatives from its own head).
- Date: 2026-09-26
- Counts: 10 templates, 100 chat puzzles (34 with four numbers, 66 with three), 100 negatives (85 of them contain four or five whole numbers).

TEST-ONLY: never opened, printed or quoted by any builder; only the rt-02g runner and scorer read it

How the puzzles were filled: scripts/claude_rt02g_make_panel.py fills each of the 10 templates with 10 fresh puzzles from claude_blurt2.puzzles(4799, ...), excluding every puzzle from seeds 4700-4703, 4790, 4795, 4797, 4880 and 4881 (first 400 of each), and seals chat_puzzles.jsonl, negatives.jsonl and wordings.json in SEAL-panel.sha256.txt.
