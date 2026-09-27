# rsn-358e5 note (added 2026-09-27 03:57:05 UTC, after sealing; changes no mark): the kind is already an input

Every 358 net embeds the puzzle's kind (Item.env) and adds it to every cell: self.env = nn.Embedding(len(E.ENVS), d) and e = tok + slot + env (claude_rsn358a_run.py:78, :96). So the learned routers in rsn-358e, rsn-358e3 and rsn-358e4 could see the kind at every token. When they misrouted (358e) or never opened the new group (358e4 seed 4), that was a failure to learn the routing, not missing information (suggested).

For this test: warm routing adds no new information. What it adds is a hand-given *assignment*: for 10% of the new-kind batches, the code says which group must take them. So the stand-in disclosed in PASSMARKS-draft.md is the forced assignment, not access to the label.
