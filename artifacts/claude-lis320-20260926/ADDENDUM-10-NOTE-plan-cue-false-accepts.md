# lis-320 ADDENDUM-10 note: false accepts from the wider plan cue list (additive; ADDENDUM-10 stays as sealed because
# pilot 8's job checks its seal). Written 2026-09-27 06:04 UTC, before pilot 8's result, at the Thread manager's 06:03 ask.

Question: does check_we3's wider plan cue list (might, may, someday, some day, one day, eventually, in the future, later
on, at some point, down the line, sometime) accept rows it should not?
- By construction the plan cues are read only for turns whose planned family is plan (claude_lis320_check.py:222,
  CUES[intent]); no other family's keep/drop reads them.
- Measured: check_we2 vs check_we3 on every pilot raw file I hold (GLM pilots 4, 5, 6 and Luna pilot 7; 1,697 turns):
  non-plan turns whose keep/drop changed: 0 (pilot 4: 0, 5: 0, 6: 0, 7: 0). False accepts as plan: 0.
- Plan turns newly kept: 10 (pilot 6: 1, "one day i think ima get a dog and name him yable"; pilot 7: 9, all nine read
  by pilot 7's fresh agent as clear plans, e.g. "i might start working for Tavne Books at some point").
So the loose words stay as sealed. Pilot 8's own fresh read covers plan rows like every other family.
