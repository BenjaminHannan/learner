# 268b: the n-hop direction guard, tested where the bug lives (the one follow-up to 268)

Director (Opus, reasoning line), 2026-09-23 ~06:50 UTC. New file; nothing edited.

## Why 268 failed (verified)

268 is a registered FAIL: nhoppanel268 reverse_chain 10/24 on both arms (bar 22). Everything else passed, and 268 is byte-identical to 138m on all 70 panel items (my own row compare: 70/70 equal). Seals: build 18/18 OK, panel 5/5 OK.

My stage census of the panel rows on 138m's reverse_chain items:
- `loop153-reverse` 8 (right);
- `loop190-reverse` 2 (right);
- `none` 12 (not understood);
- `bench73` 2 (misses).

**None** of them reached `loop138-nhop`, the stage the guard switches off. So the blind panel never showed the bug on 138m, and the guard had nothing to do there. The n-hop diagnosis had been run on 138n. 138n has the 221/237 table reader, which understands backwards verb questions ("What did V write?"), so those questions get as far as the n-hop frame. 138m does not understand them at all (the 12 `none`). On the builder's own dev dialogs, the guard did what it was meant to: 21 of 21 predicted moves, 0 new wrong answers and 0 write changes.

My mistake: the 268 note chose 138m as the base and set a "right" bar that needed readers 138m does not have.

## The one change (unchanged)

**268b = 138nb + the 268 guard** (scripts/claude_fix268_nhopdir.py, used unchanged), so the two arms are 138nb and 138nb + guard. 138nb is the newest verified base on this line (VERIFIED PASS, board 06:00): it has 138n's table reader and the "(worked out backwards)" label.

## Marks (fixed before any build)

A fresh blind panel, nhoppanel268b. Its writer must show the bug on the base: every `bug` item has to get a forward-fact reply from stage `loop138-nhop` on 138nb, and the writer replaces any item that doesn't.

- M1 nhoppanel268b:
  - bug family: 138nb wrong on every item (by construction); 268b gives 0 wrong, and ≥ 14/16 right with the "(worked out backwards)" label (the rest must be honest abstains);
  - every other family byte-identical to 138nb;
  - 0 question writes.
- M2: invpanel138nb (regression only): 0 new wrong, and every item that is right on 138nb stays right.
- M3: frozen suites vs 138nb's rows: moves exactly the predicted list; 0 new WRONG, WRONG-WRITE, junk write or lost OK.
- M4: median added time ≤ +5 ms per turn.

## What would prove it wrong

- A forward-walk answer surviving on a bug item.
- Any change to a forward two-step answer.
- A backwards answer naming someone who is not in gold.
