# SPEC-COPY for joinpanel280p (re-test of the talking-line join)

joinpanel280p uses the same spec as joinpanel280m.
Below is a verbatim copy of the "Panel spec (joinpanel280m, 90 turns, fresh)" section
of design/v3/30-modes/280m-talking-join.md (origin/main), read for this blind-panel task only.

---

## Panel spec (joinpanel280m, 90 turns, fresh)
- 25 general ability questions ("what can you do" in many wordings).
- 8 plain teach turns "<Name>'s <relation> is <Value>." and 12 called/named questions in the four formal shapes,
  each question after its teach in the same dialog.
- 25 greetings, thanks and closings, typed casually.
- 10 turns that mix small talk with an ability or called question.
- 10 controls (plain teaches and plain questions).
Columns exactly: dialog_id, turn_index, user_text, category (ability / called / teach / smalltalk / mixed /
control), gold. Mixed items are owned by 260 for M1 agreement unless the builder's PASSMARKS predicts a piece
route for each one before the seal. Fictional names only.

---

Note: gold mapping per brief — "ability_list" for ability items, "smalltalk" for small talk,
the exact expected value for called and control questions, the stored triple
Subject|relation|Object for teach turns, or "abstain".
