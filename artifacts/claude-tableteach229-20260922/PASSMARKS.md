# Exp 229 PASSMARKS: relation-table TEACHES on 138i (sealed before registered runs)

Agent: scripts/claude_loop229_agent.py (138i + TableTeach229Mixin, the one change).
Config: artifacts/claude-tableteach229-20260922/loop229-config.json.
Table: artifacts/claude-relationtable-20260922/relation_table_v1.json (read-only, sealed here by hash).
Scorer / runner: scripts/claude_teach229_run.py (`run` = fresh daemon per item, optional setup turns;
`score` = the rule below). Dev cases: artifacts/claude-tableteach229-20260922/dev229.jsonl (77 items).
Design note: design/v3/30-modes/229-tableteach-opus.md.

## Scoring rule (from the brief)
A new triple is RIGHT when it has the gold subject and gold value (case-insensitive, trailing "." and one
leading "the " stripped, USER aliases user/me/i/my/myself) and its relation is in relation_any or is a
table alias of one of them (same table relation group). WRONG-SAVE = any new triple that is not right, or
any save on a nosave item. Item counts are used (an item with any wrong triple = 1 wrong-save item).
"New wrong save" = a wrong triple 229 stores that 138i did not store on the same item.

## Marks (all must hold for PASS)
- M1 fresh blind panel (artifacts/claude-teachpanel229-20260922/panel.jsonl, opened only after this seal;
  its own SEAL is checked with shasum -c first). Both 138i and 229 are run with the same runner.
  - M1a: wrong-save items(229) <= wrong-save items(138i).
  - M1b: 0 nosave items where 229 stores anything that 138i did not store (`new_wrong_on_nosave` = 0).
  - M1c: right saves on save items: 229 >= 138i + 15.
- M2 dev cases (dev229.jsonl), scored subset = all families except `of_form_cut` (73 items, 47 save):
  229 right >= 90% of save items (>= 43 of 47) AND 0 new wrong saves (`new_wrong_items_229` = 0).
  Wrong saves inherited unchanged from 138i (pilot: d229-031 composer_of, d229-048 officeholder in the cut
  family) are reported, not counted; see Deviations.
- M3 frozen suites: `scripts/fable_suitediff218.py --agent scripts/claude_loop229_agent.py --config <229 config>
  --base 138i --only rt136,rt143,sessions152,bench`. Bar: 0 new WRONG, 0 new WRONG-WRITE, 0 new junk write,
  0 lost OK, and every move is a predicted move (list below). Any unpredicted move counts against the mark
  (known-flake rule: reported as is, then that item run alone 5 times and reported).
- M4 same triples when 138i already saves: (a) suites: 0 moves of class "write change" and every M3 move
  "stored identical"; (b) panel and dev: every item where 138i stores new triples, 229 stores exactly the
  same set (`m4_mismatch_ids` empty on both).
- M5 sleep smoke: `scripts/fable_sleepsmoke206.py` on 229 gives sleeps>=1, installed=1, probes 5/5, wrong=0,
  broken=abstain, taught 50/50, ow=0 (as the pilot). 138i is run once too, for comparison (informational).
- M6 latency: median per-item added time (229 minus 138i, same statement) <= 10 ms on the panel, and on dev.
- Hygiene: every run < 25 min; uptime checked before each registered run (wait while 1-min load > 60);
  seal verifies after the runs; no post-seal edits.

## Predicted moves (from the pilots)
- rt136: exactly 1 move, C115 "the capital of peru is lima." reply-only (MISSED -> MISSED, stored identical);
  the new reply says it was not saved because "peru" does not look like a name.
- rt143: 0 moves. sessions152: 0 moves. bench (4 splits, 800 items): 0 moves.
- Flake caveat (not a prediction exemption): the 138i stale-id bug diagnosed by Exp 228
  (fable_fix170_compose `_SRC[id(list)]` outliving its list) can flip a bench item to a non-answer. In
  pilot I ran 229 with a passive stale-id detector on 4 full bench runs + 1 bench132 run: 1 move in 3,400
  items, and it was exactly the item with the detector hit (bench121-4hop-142). Earlier non-detector pilots
  showed moves on bench121-4hop-067/-166, bench132-4hop-061/-055/-173 (all correct -> non-answer, stored
  identical, different items each run).

## Pilot numbers (scratch, not registered)
- Dev: 229 right 46/47 in the scored subset (138i 1/47); 0 new wrong saves; 0 nosave saves; M4 3/3 same;
  median added time -1.5 ms. of_form_cut 0/4 both arms.
- Suites after the last fix: rt136 1 move (C115), rt143 0, sessions152 0, GATE clean.
- Sleep smoke 229: sleeps=1 installed=1 probes=5/5 wrong=0 broken=abstain taught=50/50 ow=0.

## Cut families and known misses
- Cut: of_form "The R of X is Y." as a generic family (turned rt136 nowrite traps C124/C127/C129/C142 into
  WRONG-WRITEs in pilot). The table's own teach rows that start with "The ... of {X} is {Y}" (capital,
  author, director, ...) stay, as table rows. Shouted all-caps turns are refused (rt136 C142 is nowrite).
- Out of scope (refused, counted as known misses on save items): pronouns, appositives, two facts in one
  sentence, negations, tense / "used to".
- USER + multi-word relation ("My best friend is ...", place_of_birth): the base one-word "My R is Y" path
  cannot store it; the reply says it was not saved.

## Deviations (declared before the seal)
- EXT229 adds teach shapes not in the table's teach rows: occupation "X is a/an J" (closed job lexicon) and
  "X works as a J", "Y is a/an R of X" and "X has a/an R called Y" (multi-valued relations only), "Y is my R",
  first-person forms, and a few verb forms. The 217 design left "X is a J" out; here it is lexicon-gated.
- M2 counts only NEW wrong saves (the brief says "0 wrong saves"). A literal reading would fail M2 in both
  arms on d229-031 ("Arlo Fisk is the composer of Blue Rook." -> 138i itself stores composer_of), because
  statements 138i already saves must stay identical (M4). The literal count is also reported.
- Scorer: subject match strips one leading "the " and maps USER aliases; value match is case-insensitive.
