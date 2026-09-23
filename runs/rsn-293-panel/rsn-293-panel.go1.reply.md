Writing your blind panel for exp 293 — fetching specs and checking resources.
Spec confirmed and base agent located — now studying how it stores facts to draft the 85 items.
I've mapped the required families and scoring rules — now probing the base to verify teach formats before building.
Early probes show basic teaches work and denials need specific phrasing — now testing question variants.
Probing complete — I know which phrasings store reliably. Now assembling the 85-item panel.
Panel drafted with all 85 items — now running the base agent to verify each setup.
Base verification passed — all setups store correctly. Now sealing the panel and writing the summary.
Panel sealed and verified — doing a final compliance check.
VERDICT: DONE — blind panel yesnopanel293 written, base 138nb run once, sealed. No item text quoted below.

Marks table (base 138nb, integer counts, 85 items, 0 writes everywhere):
- have_true (10): right 0, wrong 0, writes 0; stages: none 10
- have_unknown (8): right 0, wrong 0, writes 0; stages: none 8
- live (10: 5 yes / 5 no): right 0, wrong 0, writes 0; stages: none 10
- work (8: 4 yes / 4 no): right 0, wrong 0, writes 0; stages: none 8
- born (6: 3 yes / 3 no): right 0, wrong 0, writes 0; stages: none 6
- is_multiword (8: 4 yes / 4 no): right 1, wrong 0, writes 0; stages: none 7, loop138-nhop 1
- is_of_form (6: 3 yes / 3 no): right 0, wrong 0, writes 0; stages: none 6
- taken_back (6: 3 denials expect unknown, 3 corrections expect yes/no): right 2, wrong 0, writes 0; stages: none 4, loop154d-yesno+none 2
- is_single_control (8): right 8, wrong 0, writes 0; stages: loop154d-yesno+none 7, loop138-nhop 1
- wh_control (8): right 8, wrong 0, writes 0; stages: fake 6, loop138-nhop 1, loop221-table-rekey 1
- statement_control (7): right 7, wrong 0, writes 0; stages: none 7
- TOTAL (85): right 26, wrong 0, writes 0; stages: none 66, loop154d-yesno+none 9, fake 6, loop138-nhop 3, loop221-table-rekey 1

Every move / every miss:
- Right (26): all 8 is_single_control, all 8 wh_control, all 7 statement_control, 2 of 6 taken_back (the two correction items asked as Is-questions), 1 of 8 is_multiword.
- Not-right and not-wrong (59, all base replies in the didn't-understand family, stage none): all 10 have_true, all 8 have_unknown, all 10 live, all 8 work, all 6 born, 7 of 8 is_multiword, all 6 is_of_form, 4 of 6 taken_back (3 denials + 1 Does-work correction).
- Wrong (opposite Yes/No): 0 in every family. The base never gave the opposite answer; it either answered Is-questions correctly or said it didn't understand.
- Writes: 0 everywhere. No question turn changed stored triples. All setups stored exactly their teaches; denials stored empty; corrections stored the new value. Statement questions stored nothing new.
- Two-word person names: 25 items (requirement was at least 20).

Deviations:
1. Taken-back denial wording: the spec examples were leading-No / doesn't-have shapes. On the base those shapes do not remove the fact, which would violate the hard rule that a taken-back fact must no longer be stored. I used bare-negation denials and No/Actually corrections that do remove/replace on the base, and noted denial vs correction in each note. No other wording change.
2. None other. Counts exact (10/8/10/8/6/8/6/6/8/8/7 = 85). IDs y293-001..y293-085. No edits to any existing file; new folder only. CPU only, one process at a time. Disk was 12 GB free (above 3 GB bar). Load under 60. Fictional names only. Never opened forbidden 293 design/scripts, relation tables, or another panel's items.

What it means (plain high-school English): the base already handles plain Is-questions with short names, plain who/where questions, and leaves alone sentences it can't store. It does not yet handle Does-have, Does-live, Does-work, Does-come-from/Was-born, Is-the-R-of, or Is-questions with long names — on those it says it doesn't understand, so it scores 0 right but also 0 wrong. The two taken-back corrections asked as Is-questions already work; the rest of the new yes/no shapes are open for the builder.

What it doesn't mean: it doesn't mean the base is broken on old skills (controls are 23/23 right). It doesn't mean the new shapes are impossible (setups all store fine; only the question-answering is missing). It doesn't prove anything about the builder's future fix — that gets decided only when the sealed scorer runs on the builder's arm.

PUSH: artifacts/claude-yesnopanel293-20260923 (panel.jsonl 85, base138nb.jsonl 85, make_panel.py, run_base.py, score_panel.py, README.md, SEAL.sha256.txt; shasum -c OK on all five sealed files).
