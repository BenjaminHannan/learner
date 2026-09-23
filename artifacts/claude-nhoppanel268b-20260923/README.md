# nhoppanel268b (backwards questions about a value with facts of its own)

Blind panel for exp 268b, run on base 138nb. 60 items, one fresh session
each. Category level only; no item text is quoted anywhere in this file.

Families (n):
- bug 16 (12 single-subject, 4 two-subject): a backwards question about a
  taught value V that also has its own taught fact. Relations covered:
  spouse / wife / husband, author, founder, employer, child. Every item
  was kept only because the base answered it from stage loop138-nhop
  naming the chained value instead of the gold subject(s).
- reverse_nochain 10: the same backwards shapes, but V has no facts of
  its own (setups pair the target teach with an unrelated distractor).
- forward_chain 12: two-step forward questions over the same relations
  with both links taught.
- forward_1hop 10: one-link forward questions plus a distractor teach.
- uncued_reverse 6: backwards questions over boss / mother / friend, half
  with and half without a chained fact on the value.
- abstain 6: backwards questions about a value that was never taught.

Shape: 56 two-teach items, 4 three-teach items (the two-subject bug
items). Items using a two-word name: 26.

Method: base 138nb (agent script plus config, unchanged copies matching
origin/builder-outbox), fresh temp state dir per item outside the repo,
sleep_threshold 100000, one process at a time, after waiting for the
1-minute load to drop below 60. Every setup stored exactly its teaches
(56 rows hold 2 triples, 4 rows hold 3). The question turn never wrote
(60 rows with question_wrote false). The question-stage tag
(loop.ears.last_stage) was recorded per row.

Scoring (sealed score_panel.py, schema-checked, VOID with SCHEMA-MISMATCH
exit 3 on any mismatch): bug / reverse_nochain / uncued_reverse need
every gold string (case-insensitive) plus the "(worked out backwards)"
label; right_names needs only the gold strings. Forward families need
the gold value. Abstain needs an honest abstain naming no taught person.
Wrong names a taught value or person outside gold while missing gold and
not abstaining.

Base 138nb counts per family (right / right_names / wrong /
question_wrote / stages):
- bug (16): 0 / 0 / 16 / 0; stages: loop138-nhop 16
- reverse_nochain (10): 10 / 10 / 0 / 0; stages: loop190-reverse 4,
  loop221-table-label153 3, loop221-table-inverse 3
- forward_chain (12): 12 / n-a / 0 / 0; stages: loop138-nhop 6, fake 6
- forward_1hop (10): 10 / n-a / 0 / 0; stages: loop138-nhop 4, fake 5,
  loop221-table-ask 1
- uncued_reverse (6): 6 / 6 / 0 / 0; stages: loop190-reverse 6
- abstain (6): 6 / n-a / 0 / 0; stages: loop221-table-inverse 4,
  loop190b-reverse-nomatch 2

Totals: n 60, right 44, wrong 16, question_wrote 0.

Panel construction: 100 pilot candidates were tried across 9 exploratory
sweeps during development (counts only); none was copied verbatim into
the final panel, whose 60 items were all written fresh. Zero final-panel
items were replaced after the verification run (60 kept, 0 dropped).

Files: panel.jsonl, base138nb.jsonl, make_panel.py, run_base.py,
score_panel.py. SEAL.sha256.txt holds sha256 of those five.
