# uw-2 ADDENDUM-1: the training-card code and one gate wording change (written 2026-09-26 20:43 UTC, before any training row exists)

No bar moves.

1. Training cards come from scripts/claude_uw2_data.py (new file; its sha256 is sealed with this addendum).
   - It follows claude_uw1_cards.cards_dev320's rules. As the PASSMARKS target rule says, it also treats lis-320's
     `correct_ref` intent as a correction. The sealed cards_dev320 only knows `correct`, because the uw-1 DEV
     pilots have no correct_ref turns. The prompt is claude_uw1_cards.messages(card, "B", "note"), byte for byte.
   - Selftest: on a relabelled copy of the DEV pilot2 (temp files only; never training data), every code target is
     graded RIGHT by the sealed grader. Every card's prompt equals the sealed prompt.
2. Data gate wording, made blinder.
   - The judges do not see the code label. Each packet shows the numbered notes, the earlier user turns and the new
     message.
   - Each judge answers {"note": N or 0 for no change, "new_value": ...}.
   - Code compares that answer with the label (gatecmp). A judge agrees with a correction label when it names note N
     and the new value, and with a NONE label when it answers 0.
   - The bar stays at 54 of 60, with 30 corrections (15 correct_ref) and 30 look-alike NONE cards, seed 4053.
3. The trainer's report-only dev rows are the 569 uw-1 DEV cards (devrows).
   - The DEV stop rule is still judged with claude_uw1_cards' grader on B's DEV run, not by the trainer's dev
     check.
