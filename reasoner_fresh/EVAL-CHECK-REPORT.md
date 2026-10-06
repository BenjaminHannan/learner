# EVAL-FORM-v1 check: PASS (0 defects)
Script and manual reading, all 192 rows / 96 pairs:
1. Text has exactly x then y, no other digits: OK.
2. answer == x+y (ADD) / x-y (SUB), x>y on SUB: OK.
3. Read ADD+SUB samples from all 10 families (tr-inventory/shelves/relational/change, ev-garden/bus/bakesale/library/game/trip), both cells: each unambiguous; "how many fewer" (bus, library) points the right way (back/Nora minus... = x-y); relational SUB ("Noor has 54... 16 more than Ravi", asks Ravi) = 54-16 correct.
4. new_wording rows share no name or noun with train lists, and no sentence frame with train templates: OK.
5. Pairs share x, y, cell, family and story: OK (relational pair differs only in which person is stated, by design).
6. No duplicate texts; no (x,y) repeated across pairs: OK.
7. unseen/* answers all in answers_heldout_H (both questions of each pair); seen/* all in answers_train_T: OK.
