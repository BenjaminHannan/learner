# lis-320 ADDENDUM-5: what the sealed compiler lets any reader score, correction rows about people named earlier,
# and helper v1.1 (written before any lis-320 training row or reader read exists)

Written 2026-09-26 20:33 UTC by the reading thread. At this time no lis-320 training row exists (pilot 3 failed on the
route, 2 of 60 dialogs parsed), no lis-320 reader exists, and no reader has read the sealed panel.

## 1. Owners the sealed compiler cannot accept (counts only, by code)
The sealed scoring saves a fact only if claude_lis300_compiler.check_fact passes (claude_lis319_fullclaim.py:53), and
check_fact (claude_lis300_compiler.py:44-55) accepts an owner only when it is typed in the turn or the previous reply
("me" only with a first-person word there). scripts/claude_lis320_reachcount.py counts, on the sealed panel, the gold
facts whose owner fails that test for any reader (case-insensitive, so a lower bound; counts only, no panel text):
facts 358, unreachable 108; correction facts 52, unreachable 22; backref facts 96, unreachable 93.
- So lis-320's C1 can only gain on the 30 reachable corrections. In words: C1 asks for 10 more corrections saved right
  than lis-319f, out of the 30 that any reader can save on this panel. The bar (+10), the proved-wrong line (<= +2),
  the middle band (FAIL, not proved wrong) and the prediction do not change.
- The same holds for both readers: lis-319f is scored by the same compiler on the same panel, so the 22 and the 93 count
  for neither. The comparison is fair; it only caps how much either reader can show.
- Backref rows: 93 of 96 backref facts are unreachable, so R5 (wrong_person) and right backref saves can move only on
  the 3 reachable ones. The brain-first bet in PASSMARKS (owner resolved at encoding) cannot be judged by this panel
  under the sealed compiler; it is judged in step 2 below.

## 2. correct_ref rows (Wrong answers thread's catch, 20:28 UTC)
claude_lis320_seed.correct() always names the owner (:345), so lis-320 would never practise a correction about someone
named only earlier. New files scripts/claude_lis320_seed_cr.py and scripts/claude_lis320_check_cr.py (the originals stay
as y1t sealed them) add intent correct_ref: one CORRECT fact about a person named in the last 6 turns, referred to only by
a unique pronoun or a role word, never by name, old value named about half the time, weight 2.0 (as backref), checked
exactly as backref (owner in view, ref word present, pronoun unique or role link visible, no hedge, not former).
The pilot-4 and full-run seeds come from seed_cr (pilot 4: seed 323; full run: seed 324, dialog ids "s320cr-324-*",
which cannot collide with the stopped OpenRouter run's "s320-322-*").
Under the sealed compiler these rows train a skill the scored test cannot see (section 1). They are in lis-320 for step 2
only. They do not change any bar or prediction. A C1 count on the owner-named-earlier corrections is reported for both
readers and is expected to be 0 for both.

## 3. Step 2 (registered later, one change)
After lis-320's verdict: the lis-320 reader with a compiler that also accepts an owner typed in the visible history
(lis-319o's change, which failed with lis-319f). Only that step can count the 22 corrections and 93 backref facts above.
Its marks are written before it runs; nothing here pre-registers them.

## 4. Helper v1.1
The full run and pilot 4 call scripts/claude_lis320_glm_oc11.py, which uses the Director's helper
scripts/claude_glm_opencode_v11.py (sha256 7a067cfba8fd147f342d46ed71449ab3e065c46eee3615a9b263a22da5c708c4). v1.1 adds a
per-call --title tag and deletes exactly that session; the prompt, model and reply handling are v1's. Each job first runs
Trustworthy notes' scripts/claude_glm_leakcheck.py (one call); a LEAK or ROUTE-FAIL stops it. Pilot 3 failed on the route
itself (30 of 32 calls failed with v1: 27 exit 1, 3 timeouts), which v1.1 does not address. The route fix waits on the
diagnosis job (handoff/queue/lis320-ocdiag-mac.md) and goes in its own addendum before pilot 4.
