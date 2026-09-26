# Free diagnosis of 0.2c rows S1 and H3 ("Making things up about you" thread, 2026-09-26 ~13:15 UTC, $0)

Counts only. chatpanel02c, creativepanel02c and bank D are TEST-ONLY: I read none of their items or replies. The
panel-level counts come from 0.2c's scored files; the claim-level counts come from one blind auditor agent that read
the judged chat packets and returned integer tables only.

## S1 (made-up facts about the user; X 26 vs T 16, FAIL)
- Judges' madeup sums (keys applied): pair_a X 19 vs G 10 (conversations with any: 13 vs 9); pair_b X 23 vs T 14
  (18 vs 13). Creative X 3, T 2. The same X text scored differently in the two packets in 8 of 60 conversations.
- Auditor, claims located in the flagged conversations (pair_a X | G | pair_b X | T): total 21 | 11 | 27 | 14.
  Two template kinds (the notebook's "you never told me" on a fact the user gave, and "I'll treat that as pretend")
  are byte-identical in X and G and equal in number (4 each in pair_a). Without them: 17 | 7 | 19 | 13.
- X-only claims: pair_a C 9, B 5, E 1; pair_b C 10, B 5, template 7 (C = assumes an event, plan, feeling or
  situation the user never described; B = distorts what the user said: whose event it was, their numbers or times;
  E = a check question proposing an untold fact). Mostly on feelings turns (X flagged on 6 of 12 feelings turns in
  pair_a's flagged conversations, G on 2 of 12), then advice. 24 of 27 X claims are new in the reply that makes them.
- Reply length (scored files, words per reply, X vs G): advice 51.0 vs 42.5, feelings 46.9 vs 35.3, followup 36.1
  vs 31.2, explain 45.0 vs 44.8. On a chat's first turn: feelings 51.0 vs 38.2 (n 5), advice 50.4 vs 43.9 (n 11).
- Code: X and G call the same chat338b/cre333d/think299b code with the same prompts and sampling (T 0.7, 4 samples,
  unseeded). Between them, only the sleep adapter changes the 1B's output (MANIFEST-02c.md: LoRA r16 on q/k/v/o in
  the one shared 1B). F1 (delivered history) and the lis-319 reader change the chat history and the notebook facts in
  the prompt, not the generator.
- Reading: suggested, not shown, that the sleep adapter makes chat replies longer and more assuming. Registered test:
  mu-402 (PASSMARKS.md here).

## H3 ("I don't know" when never told; X 18 vs G 33 of 36, FAIL)
- Bank D mechanical counts (score/mechanical.json): never_told X CONFIRM_OTHER 16, RIGHT 18, WRONG 2; G CONFIRM_OTHER
  3, RIGHT 33. All asks CONFIRM_OTHER X 69 vs G 41; confirm rows X 295 vs G 202.
- DEV bank run of X (artifacts/claude-e2e02c-dev-20260926 on builder-outbox; dev bank claude-e2e331-dev-20260924,
  readable; same wrong lis-301 weights as bank D, VERIFY-02c.md D1), scored with claude_e2e336_score.py:
  never_told CONFIRM_OTHER 7, RIGHT 3 of 10. The replies ask "Just to check: <a stored or half-read fact>?" instead of
  answering; 3 of the 7 pair a name from the question with a value from an earlier turn, the other 4 re-check an
  unrelated earlier fact (one of them after correctly saying it doesn't know). That fits the history reader running
  on weights that were not trained with history (inferred, not tested).
- Reading: likely the D1 weights bug. Month-end's registered 0.2d-r (007r, PASSMARKS-02dr.md) settles it:
  H3 >= 31 means the weights; <= 23 means it is real. Nothing is built for H3 before that result.
