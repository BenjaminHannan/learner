# dl-5s VERIFY: blind recount (Fix-sleep thread; filed 2026-09-26T23:29:46Z, date -u)
A separate read-only agent recounted after the run (about 22:55 UTC 09-26), reading PASSMARKS.md,
scripts/claude_dl5s_switch.py, cpu/dl5s_results.json, and the source data artifacts/claude-dl5-20260926/carry/
dl5_carry.json and artifacts/claude-dl5-20260926/gpu/dl5_results.json. It loaded no model. Its report, as returned
(lightly reformatted into lines):

- Agreement: dl5s_results.json agrees with the source files on every number. One wrong sentence, in PASSMARKS.md
  (the 19:41 addendum): "139 of 300 items (bigger 119, count 20) contain digits". Only the 119 "bigger" items contain
  digits; no "count" question does (e.g. "How many legs does a spider have?"). No pass mark changes.
1. S lost/gained from dl5_carry.json (base right 200/300): dl5-S-s8 lost 98, gained 18, net 80, right 120; dl5-S-s9
   lost 61, gained 14, net 47, right 153. These match S_panel, and the night-5 "harm" in dl5_results.json.
2. X_panel: panel_on 0 of 300 (each kind 0/n), so serve() returns the base list: lost 0, gained 0, right 200 = base.
   S_lost_items_switched_on 0. Switch: test_on 762/762, held_neg_on 0/104.
3. Grid: final S night (5) in dl5_results.json has test seed 38990, 60 grids, 762 states; right 715 (seed 8) and 712
   (seed 9). The agent rebuilt grid_states(38990, 60) without a model and got 762. No state switched off, so the X
   grid bounds collapse to 715 and 712.
4. Expectations: X lost <= 5 each seed: 0 and 0, pass. On for >= 95% of 762 test states: 762, pass. Off for >= 95%
   of 300 panel items: 300, pass. Shown wrong (X lost > 0.5 x S lost): 0 > 49 and 0 > 30.5 are false, not triggered.
   Held-out base questions: 104/104 off.
5. Panel kinds from harm_panel()[:300]: bigger 119, capital 70, order 31, opposite 30, plural 30, count 20; sum 300.
6. Leaks: the switch was fitted only on the 600 practice states and 412 fit questions (scaling from that set only).
   0 of 762 test states are among the 9,571 practice states; no panel question is among either. Practice day seeds
   39901-39905 match seed 8's days.
Caveats from the agent (not errors): fit loss 0.0, so the task was very easy to separate; base questions have no
digits or panel words and all end in "?", and grid states share Claude's fixed grid wording, so the switch most
likely keys on that wording (dl-9's rewording row is report-only on number puzzles; grids wait for GLM grid wording).
The switch reads the user message without dl-5's answer prefix (fine for a switch that decides before answering).
The grid numbers are the always-on adapter's SAVED scores, kept by construction, not re-measured; the link between
dl5_results' night-5 scores and the carry row's adapters was not traced through the adapters' sha256.
