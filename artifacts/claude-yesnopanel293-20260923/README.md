# yesnopanel293 (blind yes/no panel for exp 293)

Base: 138nb = scripts/claude_loop138nb_agent.py with artifacts/claude-merge138nb-20260923/loop138nb-config.json (fresh temp state_dir per item, sleep_threshold 100000, one process, CPU only).

Files: panel.jsonl (85 items), base138nb.jsonl (85 rows), make_panel.py, run_base.py, score_panel.py. SEAL.sha256.txt covers those five files.

Item fields: id (y293-001..y293-085), family, setup (1-4 teaches), question, expect (yes/no/unknown/control), gold, note. Row fields: id, setup_replies, question_reply, question_stage (loop.ears.last_stage), stored_after_setup_actual, stored_after_question_actual, question_wrote.

Families: have_true 10, have_unknown 8, live 10 (5 yes / 5 no), work 8 (4 yes / 4 no), born 6 (3 yes / 3 no), is_multiword 8 (4 yes / 4 no), is_of_form 6 (3 yes / 3 no), taken_back 6 (3 denials expect unknown, 3 corrections expect yes/no by new value), is_single_control 8, wh_control 8, statement_control 7. At least 20 items use a two-word person name (25 in this panel).

Scoring (score_panel.py): yes = starts Yes + all gold; no = starts No + all gold; unknown = contains don't know / not that I know and not starting Yes/No; control = identical to base row; wrong = yes expects No-start, no expects Yes-start, unknown expects Yes/No-start; question_wrote from rows. Schema mismatch exits 3 with SCHEMA-MISMATCH.

Base 138nb results (category level only, no item text):
- have_true (10): right 0, wrong 0, writes 0; stages none 10
- have_unknown (8): right 0, wrong 0, writes 0; stages none 8
- live (10): right 0, wrong 0, writes 0; stages none 10
- work (8): right 0, wrong 0, writes 0; stages none 8
- born (6): right 0, wrong 0, writes 0; stages none 6
- is_multiword (8): right 1, wrong 0, writes 0; stages none 7, loop138-nhop 1
- is_of_form (6): right 0, wrong 0, writes 0; stages none 6
- taken_back (6): right 2, wrong 0, writes 0; stages none 4, loop154d-yesno+none 2
- is_single_control (8): right 8, wrong 0, writes 0; stages loop154d-yesno+none 7, loop138-nhop 1
- wh_control (8): right 8, wrong 0, writes 0; stages fake 6, loop138-nhop 1, loop221-table-rekey 1
- statement_control (7): right 7, wrong 0, writes 0; stages none 7
- total (85): right 26, wrong 0, writes 0; stages none 66, loop154d-yesno+none 9, fake 6, loop138-nhop 3, loop221-table-rekey 1

Setup check: every non-taken_back setup stores exactly its teaches; taken_back denials store empty; corrections store the new value. No question turn wrote. All names fictional.
